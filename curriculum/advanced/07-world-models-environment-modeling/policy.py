"""Application-owned controls for Advanced 07 world-model planning.

The simulator predicts. This module validates evidence, model applicability,
constraints, approvals, and fresh-state execution preconditions. A successful
simulation is evidence for a proposal; it is never production authorization.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

POLICY_VERSION = "northstar-world-model-policy-v1"
UTILITY_POLICY_VERSION = "northstar-incident-utility-v1"
CONSTRAINT_POLICY_VERSION = "northstar-incident-constraints-v1"
SCENARIO_GENERATION_VERSION = "northstar-monte-carlo-v2"
APPROVER_ROLE = "incident.approver"


class WorldModelPolicyError(ValueError):
    """A fail-closed decision with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SensorQuality(StrEnum):
    GOOD = "GOOD"
    DELAYED = "DELAYED"
    MISSING = "MISSING"
    NOISY = "NOISY"
    UNTRUSTED = "UNTRUSTED"


class ModelValidityStatus(StrEnum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"
    UNVALIDATED = "UNVALIDATED"


class PlanningStatus(StrEnum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    MODEL_INVALID = "MODEL_INVALID"
    NO_FEASIBLE_ACTION = "NO_FEASIBLE_ACTION"
    DECISION_UNSTABLE = "DECISION_UNSTABLE"


class ActionType(StrEnum):
    ROLLBACK_DEPLOYMENT = "ROLLBACK_DEPLOYMENT"
    DISABLE_3DS = "DISABLE_3DS"
    SHIFT_TRAFFIC = "SHIFT_TRAFFIC"
    WAIT_AND_OBSERVE = "WAIT_AND_OBSERVE"
    DATABASE_ROLLBACK = "DATABASE_ROLLBACK"


ACTION_EXECUTION_CAPABILITY = {
    ActionType.ROLLBACK_DEPLOYMENT: "production.rollback",
    ActionType.DISABLE_3DS: "feature-flag.write",
    ActionType.SHIFT_TRAFFIC: "traffic.shift",
    ActionType.WAIT_AND_OBSERVE: "telemetry.read",
    ActionType.DATABASE_ROLLBACK: "database.restore",
}


class ApprovalStatus(StrEnum):
    VALID = "VALID"
    REVOKED = "REVOKED"


class DriftStatus(StrEnum):
    NONE = "NONE"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"


class StateVariable(FrozenModel):
    """A model input definition, including units and validated domain."""

    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    minimum: float
    maximum: float
    required: bool = True

    @model_validator(mode="after")
    def ordered_range(self) -> "StateVariable":
        if self.minimum > self.maximum:
            raise ValueError("INVALID_VALIDATED_RANGE")
        return self


class Observation(FrozenModel):
    observation_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    observed_at: datetime
    retrieved_at: datetime
    tenant: str = Field(min_length=1)
    variable: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    value: float | None
    quality: SensorQuality

    @model_validator(mode="after")
    def timestamps_and_missing_value(self) -> "Observation":
        if self.retrieved_at < self.observed_at:
            raise ValueError("OBSERVATION_TIME_INVALID")
        if self.quality is SensorQuality.MISSING and self.value is not None:
            raise ValueError("MISSING_SENSOR_MUST_NOT_HAVE_VALUE")
        if self.quality is not SensorQuality.MISSING and self.value is None:
            raise ValueError("OBSERVATION_VALUE_REQUIRED")
        return self


class ObservedState(FrozenModel):
    """Trusted production observations. Never populated by the simulator."""

    state_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    captured_at: datetime
    deployment_version: str = Field(min_length=1)
    provider_status: str = Field(min_length=1)
    observations: tuple[Observation, ...]

    @field_validator("observations")
    @classmethod
    def unique_variables(
        cls, observations: tuple[Observation, ...]
    ) -> tuple[Observation, ...]:
        names = [item.variable for item in observations]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_STATE_VARIABLE")
        return observations


class PredictedState(FrozenModel):
    """Simulator output. Its distinct type prevents observed/predicted confusion."""

    predicted_state_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    deployment_version: str = Field(min_length=1)
    checkout_error_rate_pct: float = Field(ge=0, le=100)
    checkout_p99_ms: float = Field(ge=0)
    queue_depth: float = Field(ge=0)
    db_utilization_pct: float = Field(ge=0, le=100)
    provider_available: bool
    derived_from_snapshot_id: str = Field(min_length=1)


class ModelSnapshot(FrozenModel):
    model_version: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    snapshot_time: datetime
    calibration_time: datetime
    input_state_digest: str = Field(min_length=64, max_length=64)
    tenant: str = Field(min_length=1)
    transition_model_version: str = Field(min_length=1)
    state_variables: tuple[StateVariable, ...]
    random_seed: int = 42

    @field_validator("state_variables")
    @classmethod
    def unique_state_variables(
        cls, variables: tuple[StateVariable, ...]
    ) -> tuple[StateVariable, ...]:
        names = [item.name for item in variables]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_MODEL_VARIABLE")
        return variables

    @model_validator(mode="after")
    def calibration_precedes_snapshot(self) -> "ModelSnapshot":
        if self.calibration_time > self.snapshot_time:
            raise ValueError("CALIBRATION_AFTER_SNAPSHOT")
        return self


class ModelValidity(FrozenModel):
    status: ModelValidityStatus
    reason_codes: tuple[str, ...]
    # Negative values preserve impossible future timestamps for diagnosis.
    model_age_seconds: float
    snapshot_age_seconds: float
    oldest_sensor_age_seconds: float
    missing_variables: tuple[str, ...] = ()
    out_of_distribution_variables: tuple[str, ...] = ()


class ActionProposal(FrozenModel):
    proposal_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    action_type: ActionType
    target: str = Field(min_length=1)
    parameters: Mapping[str, Any]
    required_capability: str = Field(min_length=1)
    approval_required: bool
    world_model_snapshot_id: str = Field(min_length=1)
    observed_state_digest: str = Field(min_length=64, max_length=64)
    created_at: datetime
    preconditions: tuple[str, ...]
    proposal_digest: str = Field(min_length=64, max_length=64)


class SimulationScenario(FrozenModel):
    scenario_id: str = Field(min_length=1)
    simulation_run_id: str = Field(min_length=1)
    sample_index: int = Field(ge=0)
    traffic_multiplier: float = Field(gt=0)
    provider_latency_multiplier: float = Field(gt=0)
    dependency_available: bool
    db_capacity_multiplier: float = Field(gt=0)
    scenario_generation_version: str = Field(min_length=1)


class PredictedOutcome(FrozenModel):
    scenario: SimulationScenario
    predicted_state: PredictedState
    recovered: bool
    recovery_minutes: float = Field(ge=0)
    customer_impact: float = Field(ge=0, le=1)
    sla_exposure: float = Field(ge=0, le=1)
    data_loss: bool
    reversibility: float = Field(ge=0, le=1)
    operational_complexity: float = Field(ge=0, le=1)
    affected_entities: tuple[str, ...]
    affected_tenants: tuple[str, ...]
    affected_services: tuple[str, ...]
    data_mutations: int = Field(ge=0)
    invariant_violations: tuple[str, ...]


class OutcomeDistribution(FrozenModel):
    action_type: ActionType
    sample_count: int = Field(gt=0)
    outcomes: tuple[PredictedOutcome, ...]
    recovery_probability: float = Field(ge=0, le=1)
    data_loss_probability: float = Field(ge=0, le=1)
    mean_recovery_minutes: float = Field(ge=0)
    p10_recovery_minutes: float = Field(ge=0)
    p50_recovery_minutes: float = Field(ge=0)
    p90_recovery_minutes: float = Field(ge=0)
    mean_customer_impact: float = Field(ge=0, le=1)
    mean_sla_exposure: float = Field(ge=0, le=1)
    robustness_score: float = Field(ge=0, le=1)
    worst_case_downtime_minutes: float = Field(ge=0)
    worst_case_data_loss: bool


class UtilityWeights(FrozenModel):
    recovery_benefit: float = Field(default=4.0, ge=0)
    customer_impact: float = Field(default=2.0, ge=0)
    data_loss_risk: float = Field(default=8.0, ge=0)
    sla_exposure: float = Field(default=1.5, ge=0)
    operational_complexity: float = Field(default=0.8, ge=0)
    reversibility: float = Field(default=1.0, ge=0)
    uncertainty: float = Field(default=1.2, ge=0)


class PlanningConstraints(FrozenModel):
    allowed_tenant: str = Field(min_length=1)
    allowed_services: tuple[str, ...]
    maximum_downtime_minutes: float = Field(default=60, gt=0)
    maximum_data_loss_probability: float = Field(default=0, ge=0, le=1)
    minimum_robustness: float = Field(default=0.75, ge=0, le=1)


class ScenarioScore(FrozenModel):
    proposal_id: str
    action_type: ActionType
    expected_utility: float
    recovery_benefit: float
    uncertainty_penalty: float = Field(ge=0)
    robustness_score: float = Field(ge=0, le=1)
    hard_constraint_violations: tuple[str, ...]
    utility_policy_version: str = Field(min_length=1)
    constraint_policy_version: str = Field(min_length=1)


class SimulationResult(FrozenModel):
    simulation_run_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    proposal_digest: str = Field(min_length=64, max_length=64)
    model_version: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    model_snapshot_digest: str = Field(min_length=64, max_length=64)
    observed_state_digest: str = Field(min_length=64, max_length=64)
    scenario_generation_version: str = Field(min_length=1)
    started_at: datetime
    distribution: OutcomeDistribution
    score: ScenarioScore


class PlanningDecision(FrozenModel):
    decision_id: str = Field(min_length=1)
    status: PlanningStatus
    model_validity: ModelValidity
    recommended_proposal_id: str | None
    simulation_results: tuple[SimulationResult, ...]
    joint_stress_winners: tuple[str, ...]
    reason_codes: tuple[str, ...]
    utility_policy_version: str = Field(min_length=1)
    constraint_policy_version: str = Field(min_length=1)
    created_at: datetime


class ApprovalReceipt(FrozenModel):
    approval_id: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    approver_roles: tuple[str, ...]
    tenant: str = Field(min_length=1)
    action: ActionType
    target: str = Field(min_length=1)
    proposal_digest: str = Field(min_length=64, max_length=64)
    simulation_run_id: str = Field(min_length=1)
    world_model_snapshot_id: str = Field(min_length=1)
    model_snapshot_digest: str = Field(min_length=64, max_length=64)
    observed_state_digest: str = Field(min_length=64, max_length=64)
    policy_version: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    status: ApprovalStatus

    @model_validator(mode="after")
    def valid_time_window(self) -> "ApprovalReceipt":
        if self.expires_at <= self.issued_at:
            raise ValueError("APPROVAL_TIME_WINDOW_INVALID")
        return self


class ExecutionProposal(FrozenModel):
    execution_id: str = Field(min_length=1)
    approval_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    proposal_digest: str = Field(min_length=64, max_length=64)
    simulation_run_id: str = Field(min_length=1)
    model_snapshot_digest: str = Field(min_length=64, max_length=64)
    observed_state_digest: str = Field(min_length=64, max_length=64)
    action: ActionType
    target: str
    parameters: Mapping[str, Any]
    required_capability: str
    authorized_at: datetime


class ObservedOutcome(FrozenModel):
    outcome_id: str
    execution_id: str
    tenant: str
    observed_at: datetime
    recovered: bool
    recovery_minutes: float = Field(ge=0)
    checkout_p99_ms: float = Field(ge=0)
    checkout_error_rate_pct: float = Field(ge=0, le=100)
    data_loss: bool
    source_ids: tuple[str, ...]


class PredictionError(FrozenModel):
    prediction_id: str
    observed_outcome_id: str
    absolute_recovery_error_minutes: float = Field(ge=0)
    relative_recovery_error: float = Field(ge=0)
    absolute_latency_error_ms: float = Field(ge=0)
    slo_impact: bool
    ranking_changed: bool
    material: bool


class CalibrationRecord(FrozenModel):
    record_id: str
    model_version: str
    prediction_error: PredictionError
    predicted_recovery_minutes: float = Field(ge=0)
    observed_recovery_minutes: float = Field(ge=0)
    predicted_recovery_probability: float = Field(ge=0, le=1)
    recovery_occurred: bool
    interval_lower_minutes: float = Field(ge=0)
    interval_upper_minutes: float = Field(ge=0)

    @model_validator(mode="after")
    def valid_interval_and_error(self) -> "CalibrationRecord":
        if self.interval_lower_minutes > self.interval_upper_minutes:
            raise ValueError("PREDICTION_INTERVAL_INVALID")
        expected_error = abs(
            self.predicted_recovery_minutes - self.observed_recovery_minutes
        )
        if not math.isclose(
            expected_error,
            self.prediction_error.absolute_recovery_error_minutes,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValueError("CALIBRATION_ERROR_MISMATCH")
        return self


class CalibrationMetrics(FrozenModel):
    sample_count: int = Field(gt=0)
    mae_minutes: float = Field(ge=0)
    rmse_minutes: float = Field(ge=0)
    mean_relative_error: float = Field(ge=0)
    interval_coverage: float = Field(ge=0, le=1)
    brier_score: float = Field(ge=0, le=1)


class DriftSignal(FrozenModel):
    model_version: str
    status: DriftStatus
    reason_codes: tuple[str, ...]
    metrics: CalibrationMetrics
    detected_at: datetime


class ModelUpdateProposal(FrozenModel):
    update_id: str
    current_model_version: str
    candidate_model_version: str
    calibration_record_ids: tuple[str, ...]
    proposed_by: str
    created_at: datetime


class ValidationReport(FrozenModel):
    report_id: str
    candidate_model_version: str
    historical_scenarios: int = Field(gt=0)
    metrics: CalibrationMetrics
    constraint_violation_miss_rate: float = Field(ge=0, le=1)
    ranking_accuracy: float = Field(ge=0, le=1)
    approved_for_promotion: bool
    reason_codes: tuple[str, ...]
    validated_at: datetime


def canonical_digest(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def observed_state_digest(state: ObservedState) -> str:
    return canonical_digest(state)


def model_snapshot_digest(snapshot: ModelSnapshot) -> str:
    """Bind the immutable, application-owned model artifact and its metadata."""

    return canonical_digest(snapshot)


def action_proposal_payload(proposal: ActionProposal | Mapping[str, Any]) -> dict[str, Any]:
    data = (
        proposal.model_dump(mode="json")
        if isinstance(proposal, ActionProposal)
        else dict(proposal)
    )
    data.pop("proposal_digest", None)
    return data


def build_action_proposal(**values: Any) -> ActionProposal:
    payload = dict(values)
    payload["proposal_digest"] = "0" * 64
    provisional = ActionProposal(**payload)
    return provisional.model_copy(
        update={"proposal_digest": canonical_digest(action_proposal_payload(provisional))}
    )


def validate_action_proposal(
    proposal: ActionProposal,
    *,
    observed_state: ObservedState,
    snapshot: ModelSnapshot,
    allowed_proposal_actions: Sequence[ActionType],
) -> None:
    """Validate whether planning may propose an action, not whether it may execute."""

    checks = {
        "PROPOSAL_DIGEST_MISMATCH": proposal.proposal_digest
        == canonical_digest(action_proposal_payload(proposal)),
        "PROPOSAL_INCIDENT_MISMATCH": proposal.incident_id
        == observed_state.incident_id,
        "PROPOSAL_TENANT_MISMATCH": proposal.tenant == observed_state.tenant,
        "PROPOSAL_SNAPSHOT_MISMATCH": proposal.world_model_snapshot_id
        == snapshot.snapshot_id,
        "PROPOSAL_STATE_DIGEST_MISMATCH": proposal.observed_state_digest
        == observed_state_digest(observed_state),
        "PROPOSAL_ACTION_DENIED": proposal.action_type in allowed_proposal_actions,
        "ACTION_CAPABILITY_BINDING_INVALID": proposal.required_capability
        == ACTION_EXECUTION_CAPABILITY[proposal.action_type],
    }
    for code, valid in checks.items():
        if not valid:
            raise WorldModelPolicyError(code)

    allowed_parameters = {
        ActionType.ROLLBACK_DEPLOYMENT: {"from_deployment", "to_deployment"},
        ActionType.DISABLE_3DS: {"integration", "region"},
        ActionType.SHIFT_TRAFFIC: {"from_region", "to_region", "percentage"},
        ActionType.WAIT_AND_OBSERVE: {"minutes"},
        ActionType.DATABASE_ROLLBACK: {"database", "restore_point"},
    }
    if set(proposal.parameters) != allowed_parameters[proposal.action_type]:
        raise WorldModelPolicyError("ACTION_SCHEMA_INVALID")
    if proposal.action_type is not ActionType.WAIT_AND_OBSERVE and not proposal.approval_required:
        raise WorldModelPolicyError("CONSEQUENTIAL_ACTION_REQUIRES_APPROVAL")
    if proposal.action_type is ActionType.ROLLBACK_DEPLOYMENT:
        if proposal.parameters["from_deployment"] != observed_state.deployment_version:
            raise WorldModelPolicyError("PRECONDITION_STALE")


def assess_model_validity(
    snapshot: ModelSnapshot,
    state: ObservedState,
    *,
    now: datetime,
    maximum_sensor_age: timedelta = timedelta(minutes=2),
    maximum_snapshot_age: timedelta = timedelta(minutes=5),
    maximum_calibration_age: timedelta = timedelta(days=30),
) -> ModelValidity:
    sensor_ages = [(now - item.observed_at).total_seconds() for item in state.observations]
    oldest_sensor_age = max(sensor_ages, default=0.0)
    snapshot_age = (now - snapshot.snapshot_time).total_seconds()
    model_age = (now - snapshot.calibration_time).total_seconds()
    reasons: list[str] = []

    if state.captured_at > now:
        reasons.append("OBSERVED_STATE_FROM_FUTURE")
    if any(item.observed_at > now for item in state.observations):
        reasons.append("OBSERVATION_FROM_FUTURE")
    if any(item.retrieved_at > now for item in state.observations):
        reasons.append("OBSERVATION_RETRIEVAL_FROM_FUTURE")
    if snapshot.snapshot_time > now:
        reasons.append("MODEL_SNAPSHOT_FROM_FUTURE")
    if snapshot.calibration_time > snapshot.snapshot_time:
        reasons.append("CALIBRATION_AFTER_SNAPSHOT")

    if snapshot.tenant != state.tenant:
        reasons.append("MODEL_TENANT_MISMATCH")
    if snapshot.input_state_digest != observed_state_digest(state):
        reasons.append("MODEL_INPUT_DIGEST_MISMATCH")

    observations = {item.variable: item for item in state.observations}
    required = {item.name for item in snapshot.state_variables if item.required}
    missing = tuple(
        sorted(
            name
            for name in required
            if name not in observations
            or observations[name].value is None
            or observations[name].quality is SensorQuality.MISSING
        )
    )
    if missing:
        reasons.append("MODEL_STATE_INCOMPLETE")

    if any(item.tenant != state.tenant for item in state.observations):
        reasons.append("OBSERVATION_TENANT_MISMATCH")

    unreliable = [
        item.variable
        for item in state.observations
        if item.quality in {SensorQuality.MISSING, SensorQuality.NOISY, SensorQuality.UNTRUSTED}
    ]
    if unreliable:
        reasons.append("SENSOR_QUALITY_INVALID")

    ood: list[str] = []
    for definition in snapshot.state_variables:
        observation = observations.get(definition.name)
        if observation is None or observation.value is None:
            continue
        if observation.unit != definition.unit:
            reasons.append("STATE_UNIT_MISMATCH")
            continue
        if not definition.minimum <= observation.value <= definition.maximum:
            ood.append(definition.name)

    if missing or unreliable or any(
        reason in reasons
        for reason in (
            "STATE_UNIT_MISMATCH",
            "MODEL_TENANT_MISMATCH",
            "MODEL_INPUT_DIGEST_MISMATCH",
            "OBSERVATION_TENANT_MISMATCH",
            "OBSERVED_STATE_FROM_FUTURE",
            "OBSERVATION_FROM_FUTURE",
            "OBSERVATION_RETRIEVAL_FROM_FUTURE",
            "MODEL_SNAPSHOT_FROM_FUTURE",
            "CALIBRATION_AFTER_SNAPSHOT",
        )
    ):
        status = ModelValidityStatus.UNVALIDATED
    elif ood:
        status = ModelValidityStatus.OUT_OF_DISTRIBUTION
        reasons.append("MODEL_OUT_OF_DOMAIN")
    elif (
        oldest_sensor_age > maximum_sensor_age.total_seconds()
        or snapshot_age > maximum_snapshot_age.total_seconds()
        or model_age > maximum_calibration_age.total_seconds()
    ):
        status = ModelValidityStatus.STALE
        if oldest_sensor_age > maximum_sensor_age.total_seconds():
            reasons.append("SENSOR_STATE_STALE")
        if snapshot_age > maximum_snapshot_age.total_seconds():
            reasons.append("MODEL_SNAPSHOT_STALE")
        if model_age > maximum_calibration_age.total_seconds():
            reasons.append("MODEL_CALIBRATION_STALE")
    elif any(item.quality is SensorQuality.DELAYED for item in state.observations):
        status = ModelValidityStatus.DEGRADED
        reasons.append("SENSOR_DELAYED")
    else:
        status = ModelValidityStatus.VALID

    return ModelValidity(
        status=status,
        reason_codes=tuple(dict.fromkeys(reasons)),
        model_age_seconds=model_age,
        snapshot_age_seconds=snapshot_age,
        oldest_sensor_age_seconds=oldest_sensor_age,
        missing_variables=missing,
        out_of_distribution_variables=tuple(sorted(ood)),
    )


def percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("EMPTY_DISTRIBUTION")
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def summarize_outcomes(
    action_type: ActionType, outcomes: Sequence[PredictedOutcome]
) -> OutcomeDistribution:
    if not outcomes:
        raise ValueError("EMPTY_DISTRIBUTION")
    recovery = [item.recovery_minutes for item in outcomes]
    acceptable = [
        item
        for item in outcomes
        if item.recovered
        and not item.invariant_violations
        and not item.data_loss
        and item.recovery_minutes <= 60
    ]
    count = len(outcomes)
    return OutcomeDistribution(
        action_type=action_type,
        sample_count=count,
        outcomes=tuple(outcomes),
        recovery_probability=sum(item.recovered for item in outcomes) / count,
        data_loss_probability=sum(item.data_loss for item in outcomes) / count,
        mean_recovery_minutes=sum(recovery) / count,
        p10_recovery_minutes=percentile(recovery, 0.10),
        p50_recovery_minutes=percentile(recovery, 0.50),
        p90_recovery_minutes=percentile(recovery, 0.90),
        mean_customer_impact=sum(item.customer_impact for item in outcomes) / count,
        mean_sla_exposure=sum(item.sla_exposure for item in outcomes) / count,
        robustness_score=len(acceptable) / count,
        worst_case_downtime_minutes=max(recovery),
        worst_case_data_loss=any(item.data_loss for item in outcomes),
    )


def score_distribution(
    proposal: ActionProposal,
    distribution: OutcomeDistribution,
    *,
    weights: UtilityWeights,
    constraints: PlanningConstraints,
    utility_policy_version: str = UTILITY_POLICY_VERSION,
    constraint_policy_version: str = CONSTRAINT_POLICY_VERSION,
) -> ScenarioScore:
    violations: list[str] = []
    outcomes = distribution.outcomes
    affected_tenants = {tenant for item in outcomes for tenant in item.affected_tenants}
    affected_services = {service for item in outcomes for service in item.affected_services}
    invariant_violations = {
        violation for item in outcomes for violation in item.invariant_violations
    }

    if affected_tenants - {constraints.allowed_tenant}:
        violations.append("BLAST_RADIUS_VIOLATION")
    if affected_services - set(constraints.allowed_services):
        violations.append("SERVICE_SCOPE_VIOLATION")
    if distribution.data_loss_probability > constraints.maximum_data_loss_probability:
        violations.append("DATA_LOSS_CONSTRAINT")
    if distribution.worst_case_downtime_minutes > constraints.maximum_downtime_minutes:
        violations.append("WORST_CASE_DOWNTIME_CONSTRAINT")
    if distribution.robustness_score < constraints.minimum_robustness:
        violations.append("ROBUSTNESS_CONSTRAINT")
    violations.extend(sorted(invariant_violations))

    uncertainty_penalty = max(
        0.0,
        (distribution.p90_recovery_minutes - distribution.p10_recovery_minutes)
        / constraints.maximum_downtime_minutes,
    )
    mean_complexity = sum(item.operational_complexity for item in outcomes) / len(outcomes)
    mean_reversibility = sum(item.reversibility for item in outcomes) / len(outcomes)
    recovery_benefit = distribution.recovery_probability
    utility = (
        weights.recovery_benefit * recovery_benefit
        - weights.customer_impact * distribution.mean_customer_impact
        - weights.data_loss_risk * distribution.data_loss_probability
        - weights.sla_exposure * distribution.mean_sla_exposure
        - weights.operational_complexity * mean_complexity
        + weights.reversibility * mean_reversibility
        - weights.uncertainty * uncertainty_penalty
    )
    return ScenarioScore(
        proposal_id=proposal.proposal_id,
        action_type=proposal.action_type,
        expected_utility=utility,
        recovery_benefit=recovery_benefit,
        uncertainty_penalty=uncertainty_penalty,
        robustness_score=distribution.robustness_score,
        hard_constraint_violations=tuple(dict.fromkeys(violations)),
        utility_policy_version=utility_policy_version,
        constraint_policy_version=constraint_policy_version,
    )


def validate_approval(
    proposal: ActionProposal,
    simulation: SimulationResult,
    decision: PlanningDecision,
    approval: ApprovalReceipt | None,
    *,
    snapshot: ModelSnapshot,
    current_state: ObservedState,
    executor_capabilities: Sequence[str],
    now: datetime,
) -> ExecutionProposal:
    """Authorize an exact, still-current execution proposal or fail closed."""

    if approval is None:
        raise WorldModelPolicyError("APPROVAL_REQUIRED")
    if decision.status is not PlanningStatus.READY_FOR_REVIEW:
        raise WorldModelPolicyError("PLANNING_DECISION_NOT_EXECUTABLE")
    if decision.recommended_proposal_id != proposal.proposal_id:
        raise WorldModelPolicyError("PROPOSAL_NOT_RECOMMENDED")
    if simulation not in decision.simulation_results:
        raise WorldModelPolicyError("SIMULATION_NOT_IN_DECISION")
    if simulation.score.hard_constraint_violations:
        raise WorldModelPolicyError("SIMULATION_HARD_CONSTRAINT_VIOLATION")
    if decision.model_validity.status is not ModelValidityStatus.VALID:
        raise WorldModelPolicyError("DECISION_MODEL_INVALID")
    checks = {
        "PROPOSAL_DIGEST_MISMATCH": proposal.proposal_digest
        == canonical_digest(action_proposal_payload(proposal)),
        "SIMULATION_BINDING_MISMATCH": simulation.proposal_id == proposal.proposal_id
        and simulation.proposal_digest == proposal.proposal_digest
        and simulation.snapshot_id == proposal.world_model_snapshot_id
        and simulation.observed_state_digest == proposal.observed_state_digest,
        "MODEL_SNAPSHOT_ID_MISMATCH": snapshot.snapshot_id
        == proposal.world_model_snapshot_id,
        "MODEL_SNAPSHOT_DIGEST_MISMATCH": simulation.model_snapshot_digest
        == model_snapshot_digest(snapshot),
        "MODEL_VERSION_MISMATCH": simulation.model_version == snapshot.model_version,
        "SCENARIO_GENERATION_VERSION_MISMATCH": simulation.scenario_generation_version
        == SCENARIO_GENERATION_VERSION,
        "UTILITY_POLICY_VERSION_MISMATCH": simulation.score.utility_policy_version
        == decision.utility_policy_version
        == UTILITY_POLICY_VERSION,
        "CONSTRAINT_POLICY_VERSION_MISMATCH": simulation.score.constraint_policy_version
        == decision.constraint_policy_version
        == CONSTRAINT_POLICY_VERSION,
        "APPROVAL_STATUS_INVALID": approval.status is ApprovalStatus.VALID,
        "APPROVER_ROLE_DENIED": APPROVER_ROLE in approval.approver_roles,
        "APPROVAL_TENANT_MISMATCH": approval.tenant == proposal.tenant,
        "APPROVAL_ACTION_MISMATCH": approval.action == proposal.action_type,
        "APPROVAL_TARGET_MISMATCH": approval.target == proposal.target,
        "APPROVAL_DIGEST_MISMATCH": approval.proposal_digest
        == proposal.proposal_digest,
        "APPROVAL_SIMULATION_MISMATCH": approval.simulation_run_id
        == simulation.simulation_run_id,
        "APPROVAL_SNAPSHOT_MISMATCH": approval.world_model_snapshot_id
        == proposal.world_model_snapshot_id,
        "APPROVAL_MODEL_DIGEST_MISMATCH": approval.model_snapshot_digest
        == simulation.model_snapshot_digest,
        "APPROVAL_STATE_MISMATCH": approval.observed_state_digest
        == proposal.observed_state_digest,
        "APPROVAL_POLICY_MISMATCH": approval.policy_version == POLICY_VERSION,
        "APPROVAL_NOT_YET_VALID": approval.issued_at <= now,
        "APPROVAL_PREDATES_PROPOSAL": approval.issued_at >= proposal.created_at,
        "APPROVAL_PREDATES_SIMULATION": approval.issued_at >= simulation.started_at,
        "APPROVAL_EXPIRED": now <= approval.expires_at,
        "EXECUTION_CAPABILITY_DENIED": proposal.required_capability
        in executor_capabilities,
    }
    for code, valid in checks.items():
        if not valid:
            raise WorldModelPolicyError(code)

    current_digest = observed_state_digest(current_state)
    if current_digest != proposal.observed_state_digest:
        raise WorldModelPolicyError("SIMULATION_STALE")
    if current_state.tenant != proposal.tenant:
        raise WorldModelPolicyError("EXECUTION_TENANT_MISMATCH")

    current_validity = assess_model_validity(snapshot, current_state, now=now)
    if current_validity.status is not ModelValidityStatus.VALID:
        raise WorldModelPolicyError("MODEL_STATE_STALE")
    if proposal.action_type is ActionType.ROLLBACK_DEPLOYMENT:
        if current_state.deployment_version != proposal.parameters["from_deployment"]:
            raise WorldModelPolicyError("PRECONDITION_STALE")

    return ExecutionProposal(
        execution_id=f"exec-{approval.approval_id}",
        approval_id=approval.approval_id,
        proposal_id=proposal.proposal_id,
        proposal_digest=proposal.proposal_digest,
        simulation_run_id=simulation.simulation_run_id,
        model_snapshot_digest=simulation.model_snapshot_digest,
        observed_state_digest=current_digest,
        action=proposal.action_type,
        target=proposal.target,
        parameters=proposal.parameters,
        required_capability=proposal.required_capability,
        authorized_at=now,
    )


def compare_prediction(
    prediction: OutcomeDistribution,
    observed: ObservedOutcome,
    *,
    prediction_id: str,
    predicted_latency_ms: float,
    latency_slo_ms: float = 500,
    material_recovery_error_minutes: float = 5,
) -> PredictionError:
    absolute_recovery = abs(prediction.mean_recovery_minutes - observed.recovery_minutes)
    denominator = max(observed.recovery_minutes, 1.0)
    absolute_latency = abs(predicted_latency_ms - observed.checkout_p99_ms)
    slo_impact = (predicted_latency_ms <= latency_slo_ms) != (
        observed.checkout_p99_ms <= latency_slo_ms
    )
    material = absolute_recovery >= material_recovery_error_minutes or slo_impact
    return PredictionError(
        prediction_id=prediction_id,
        observed_outcome_id=observed.outcome_id,
        absolute_recovery_error_minutes=absolute_recovery,
        relative_recovery_error=absolute_recovery / denominator,
        absolute_latency_error_ms=absolute_latency,
        slo_impact=slo_impact,
        ranking_changed=False,
        material=material,
    )


def calculate_calibration_metrics(
    records: Sequence[CalibrationRecord],
) -> CalibrationMetrics:
    if not records:
        raise ValueError("CALIBRATION_RECORDS_REQUIRED")
    errors = [item.prediction_error.absolute_recovery_error_minutes for item in records]
    relative = [item.prediction_error.relative_recovery_error for item in records]
    coverage = [
        item.interval_lower_minutes
        <= item.observed_recovery_minutes
        <= item.interval_upper_minutes
        for item in records
    ]
    brier = [
        (item.predicted_recovery_probability - float(item.recovery_occurred)) ** 2
        for item in records
    ]
    count = len(records)
    return CalibrationMetrics(
        sample_count=count,
        mae_minutes=sum(errors) / count,
        rmse_minutes=math.sqrt(sum(error**2 for error in errors) / count),
        mean_relative_error=sum(relative) / count,
        interval_coverage=sum(coverage) / count,
        brier_score=sum(brier) / count,
    )


def detect_drift(
    model_version: str,
    metrics: CalibrationMetrics,
    *,
    now: datetime,
    maximum_mae_minutes: float = 5,
    maximum_brier_score: float = 0.25,
    minimum_interval_coverage: float = 0.8,
) -> DriftSignal:
    reasons: list[str] = []
    if metrics.mae_minutes > maximum_mae_minutes:
        reasons.append("MAE_DRIFT")
    if metrics.brier_score > maximum_brier_score:
        reasons.append("PROBABILITY_CALIBRATION_DRIFT")
    if metrics.interval_coverage < minimum_interval_coverage:
        reasons.append("INTERVAL_COVERAGE_DRIFT")
    status = DriftStatus.MATERIAL if reasons else DriftStatus.NONE
    if len(reasons) >= 2:
        status = DriftStatus.CRITICAL
    return DriftSignal(
        model_version=model_version,
        status=status,
        reason_codes=tuple(reasons),
        metrics=metrics,
        detected_at=now,
    )


def validate_model_update(
    update: ModelUpdateProposal,
    records: Sequence[CalibrationRecord],
    *,
    constraint_violation_miss_rate: float,
    ranking_accuracy: float,
    now: datetime,
) -> ValidationReport:
    if update.candidate_model_version == update.current_model_version:
        raise WorldModelPolicyError("MODEL_VERSION_NOT_ADVANCED")
    known_ids = {item.record_id for item in records}
    if not set(update.calibration_record_ids).issubset(known_ids):
        raise WorldModelPolicyError("CALIBRATION_LINEAGE_MISSING")
    metrics = calculate_calibration_metrics(records)
    reasons: list[str] = []
    if metrics.mae_minutes > 5:
        reasons.append("BACKTEST_MAE_FAILED")
    if constraint_violation_miss_rate > 0:
        reasons.append("CONSTRAINT_MISS_RATE_FAILED")
    if ranking_accuracy < 0.8:
        reasons.append("RANKING_ACCURACY_FAILED")
    if metrics.interval_coverage < 0.8:
        reasons.append("INTERVAL_COVERAGE_FAILED")
    return ValidationReport(
        report_id=f"validation-{update.update_id}",
        candidate_model_version=update.candidate_model_version,
        historical_scenarios=len(records),
        metrics=metrics,
        constraint_violation_miss_rate=constraint_violation_miss_rate,
        ranking_accuracy=ranking_accuracy,
        approved_for_promotion=not reasons,
        reason_codes=tuple(reasons),
        validated_at=now,
    )


def promote_model(
    current: ModelSnapshot,
    update: ModelUpdateProposal,
    report: ValidationReport,
    *,
    new_snapshot_id: str,
    new_state_digest: str,
    promoted_at: datetime,
) -> ModelSnapshot:
    if update.current_model_version != current.model_version:
        raise WorldModelPolicyError("MODEL_UPDATE_BASE_MISMATCH")
    if report.candidate_model_version != update.candidate_model_version:
        raise WorldModelPolicyError("MODEL_VALIDATION_BINDING_MISMATCH")
    if not report.approved_for_promotion:
        raise WorldModelPolicyError("MODEL_PROMOTION_DENIED")
    return current.model_copy(
        update={
            "model_version": update.candidate_model_version,
            "snapshot_id": new_snapshot_id,
            "snapshot_time": promoted_at,
            "calibration_time": promoted_at,
            "input_state_digest": new_state_digest,
        }
    )
