"""Credential-free world-model planning lab for Advanced Course 07.

The Northstar fixture is deterministic and deliberately does not call a real
production system. It demonstrates how simulation informs a proposal while
policy, approval, capability, and fresh-state checks remain separate controls.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from policy import (
    CONSTRAINT_POLICY_VERSION,
    POLICY_VERSION,
    SCENARIO_GENERATION_VERSION,
    UTILITY_POLICY_VERSION,
    ActionProposal,
    ActionType,
    ApprovalReceipt,
    ApprovalStatus,
    CalibrationRecord,
    ExecutionProposal,
    ModelSnapshot,
    ModelValidityStatus,
    Observation,
    ObservedOutcome,
    ObservedState,
    OutcomeDistribution,
    PlanningConstraints,
    PlanningDecision,
    PlanningStatus,
    PredictionError,
    PredictedOutcome,
    PredictedState,
    ScenarioScore,
    SensorQuality,
    SimulationResult,
    SimulationScenario,
    StateVariable,
    UtilityWeights,
    WorldModelPolicyError,
    assess_model_validity,
    build_action_proposal,
    canonical_digest,
    model_snapshot_digest,
    observed_state_digest,
    score_distribution,
    summarize_outcomes,
    validate_action_proposal,
    validate_approval,
)

FIXED_TIME = datetime(2026, 2, 10, 10, 0, tzinfo=UTC)
TENANT = "northstar-commerce"
INCIDENT_ID = "inc-eu-checkout-1842"

ALLOWED_PROPOSAL_ACTIONS = (
    ActionType.ROLLBACK_DEPLOYMENT,
    ActionType.DISABLE_3DS,
    ActionType.SHIFT_TRAFFIC,
    ActionType.WAIT_AND_OBSERVE,
    ActionType.DATABASE_ROLLBACK,
)

EXECUTION_CAPABILITIES = (
    "production.rollback",
    "feature-flag.write",
    "traffic.shift",
)


def _observation(
    variable: str,
    unit: str,
    value: float | None,
    *,
    quality: SensorQuality = SensorQuality.GOOD,
    observed_at: datetime = FIXED_TIME - timedelta(seconds=30),
    tenant: str = TENANT,
) -> Observation:
    return Observation(
        observation_id=f"obs-{variable}",
        source="northstar-telemetry",
        source_version="otel-pipeline-v7",
        observed_at=observed_at,
        retrieved_at=FIXED_TIME - timedelta(seconds=5),
        tenant=tenant,
        variable=variable,
        unit=unit,
        value=value,
        quality=quality,
    )


def observed_state(
    *,
    deployment_version: str = "deploy-1842",
    traffic_rps: float = 2_400,
    checkout_p99_ms: float = 4_200,
    checkout_error_rate_pct: float = 18,
    queue_depth: float = 1_100,
    db_utilization_pct: float = 78,
    observation_overrides: dict[str, dict[str, Any]] | None = None,
) -> ObservedState:
    values = {
        "traffic_rps": ("requests/second", traffic_rps),
        "checkout_p99_ms": ("milliseconds", checkout_p99_ms),
        "checkout_error_rate_pct": ("percent", checkout_error_rate_pct),
        "queue_depth": ("messages", queue_depth),
        "db_utilization_pct": ("percent", db_utilization_pct),
    }
    items = []
    overrides = observation_overrides or {}
    for variable, (unit, value) in values.items():
        item_values = {"quality": SensorQuality.GOOD, "observed_at": FIXED_TIME - timedelta(seconds=30)}
        item_values.update(overrides.get(variable, {}))
        if item_values["quality"] is SensorQuality.MISSING:
            value = None
        items.append(_observation(variable, unit, value, **item_values))
    return ObservedState(
        state_id=f"state-{deployment_version}-{int(traffic_rps)}",
        incident_id=INCIDENT_ID,
        tenant=TENANT,
        captured_at=FIXED_TIME - timedelta(seconds=5),
        deployment_version=deployment_version,
        provider_status="3ds-provider-degraded",
        observations=tuple(items),
    )


def model_snapshot(
    state: ObservedState,
    *,
    model_version: str = "world-model-v12",
    snapshot_time: datetime = FIXED_TIME - timedelta(seconds=2),
    calibration_time: datetime = FIXED_TIME - timedelta(days=7),
    input_state_digest: str | None = None,
) -> ModelSnapshot:
    return ModelSnapshot(
        model_version=model_version,
        snapshot_id="snapshot-eu-1842-v12",
        snapshot_time=snapshot_time,
        calibration_time=calibration_time,
        input_state_digest=input_state_digest or observed_state_digest(state),
        tenant=state.tenant,
        transition_model_version="northstar-discrete-event-v4",
        state_variables=(
            StateVariable(name="traffic_rps", unit="requests/second", minimum=0, maximum=5_000),
            StateVariable(name="checkout_p99_ms", unit="milliseconds", minimum=0, maximum=8_000),
            StateVariable(name="checkout_error_rate_pct", unit="percent", minimum=0, maximum=30),
            StateVariable(name="queue_depth", unit="messages", minimum=0, maximum=5_000),
            StateVariable(name="db_utilization_pct", unit="percent", minimum=0, maximum=95),
        ),
        random_seed=42,
    )


def action_proposals(state: ObservedState, snapshot: ModelSnapshot) -> tuple[ActionProposal, ...]:
    common = {
        "incident_id": state.incident_id,
        "tenant": state.tenant,
        "world_model_snapshot_id": snapshot.snapshot_id,
        "observed_state_digest": observed_state_digest(state),
        "created_at": FIXED_TIME - timedelta(seconds=1),
    }
    values = (
        {
            "proposal_id": "proposal-rollback",
            "action_type": ActionType.ROLLBACK_DEPLOYMENT,
            "target": "northstar-eu-checkout",
            "parameters": {"from_deployment": "deploy-1842", "to_deployment": "deploy-1841"},
            "required_capability": "production.rollback",
            "approval_required": True,
            "preconditions": ("current deployment is deploy-1842",),
        },
        {
            "proposal_id": "proposal-disable-3ds",
            "action_type": ActionType.DISABLE_3DS,
            "target": "northstar-eu-3ds",
            "parameters": {"integration": "3ds-v2", "region": "eu-west-1"},
            "required_capability": "feature-flag.write",
            "approval_required": True,
            "preconditions": ("3ds-v2 flag is enabled",),
        },
        {
            "proposal_id": "proposal-shift-traffic",
            "action_type": ActionType.SHIFT_TRAFFIC,
            "target": "northstar-eu-router",
            "parameters": {"from_region": "eu-west-1", "to_region": "eu-central-1", "percentage": 35},
            "required_capability": "traffic.shift",
            "approval_required": True,
            "preconditions": ("eu-central-1 has at least 35 percent spare capacity",),
        },
        {
            "proposal_id": "proposal-wait",
            "action_type": ActionType.WAIT_AND_OBSERVE,
            "target": "northstar-eu-checkout",
            "parameters": {"minutes": 10},
            "required_capability": "telemetry.read",
            "approval_required": False,
            "preconditions": ("monitoring remains available",),
        },
        {
            "proposal_id": "proposal-database-rollback",
            "action_type": ActionType.DATABASE_ROLLBACK,
            "target": "shared-checkout-database",
            "parameters": {"database": "checkout-primary", "restore_point": "09:45Z"},
            "required_capability": "database.restore",
            "approval_required": True,
            "preconditions": ("restore point exists",),
        },
    )
    return tuple(build_action_proposal(**common, **item) for item in values)


ACTION_PROFILE: dict[ActionType, dict[str, float]] = {
    ActionType.ROLLBACK_DEPLOYMENT: {
        "recovery_probability": 0.84,
        "recovery_minutes": 10,
        "customer_impact": 0.20,
        "sla_exposure": 0.16,
        "data_loss_probability": 0,
        "reversibility": 0.90,
        "complexity": 0.30,
        "healthy_latency_ms": 220,
    },
    ActionType.DISABLE_3DS: {
        "recovery_probability": 0.78,
        "recovery_minutes": 8,
        "customer_impact": 0.24,
        "sla_exposure": 0.20,
        "data_loss_probability": 0,
        "reversibility": 0.95,
        "complexity": 0.20,
        "healthy_latency_ms": 280,
    },
    ActionType.SHIFT_TRAFFIC: {
        "recovery_probability": 0.70,
        "recovery_minutes": 12,
        "customer_impact": 0.22,
        "sla_exposure": 0.18,
        "data_loss_probability": 0,
        "reversibility": 0.80,
        "complexity": 0.55,
        "healthy_latency_ms": 320,
    },
    ActionType.WAIT_AND_OBSERVE: {
        "recovery_probability": 0.35,
        "recovery_minutes": 30,
        "customer_impact": 0.65,
        "sla_exposure": 0.58,
        "data_loss_probability": 0,
        "reversibility": 1.00,
        "complexity": 0.05,
        "healthy_latency_ms": 650,
    },
    ActionType.DATABASE_ROLLBACK: {
        "recovery_probability": 0.90,
        "recovery_minutes": 7,
        "customer_impact": 0.42,
        "sla_exposure": 0.25,
        "data_loss_probability": 0.25,
        "reversibility": 0.20,
        "complexity": 0.85,
        "healthy_latency_ms": 180,
    },
}


def _service_scope(action_type: ActionType) -> tuple[str, ...]:
    return {
        ActionType.ROLLBACK_DEPLOYMENT: ("checkout", "deployment-control"),
        ActionType.DISABLE_3DS: ("checkout", "3ds-adapter"),
        ActionType.SHIFT_TRAFFIC: ("checkout", "traffic-router"),
        ActionType.WAIT_AND_OBSERVE: ("checkout",),
        ActionType.DATABASE_ROLLBACK: ("checkout", "shared-database"),
    }[action_type]


def simulate_proposal(
    proposal: ActionProposal,
    snapshot: ModelSnapshot,
    *,
    samples: int = 200,
    traffic_multiplier: float = 1.0,
    provider_latency_multiplier: float = 1.0,
    db_capacity_multiplier: float = 1.0,
    seed_offset: int = 0,
) -> OutcomeDistribution:
    """Run deterministic Monte Carlo scenario analysis; never execute an action."""

    if samples <= 0:
        raise ValueError("SIMULATION_SAMPLES_MUST_BE_POSITIVE")
    if min(
        traffic_multiplier,
        provider_latency_multiplier,
        db_capacity_multiplier,
    ) <= 0:
        raise ValueError("SIMULATION_MULTIPLIERS_MUST_BE_POSITIVE")
    action_index = list(ActionType).index(proposal.action_type)
    rng = random.Random(snapshot.random_seed + action_index * 1_000 + seed_offset)
    profile = ACTION_PROFILE[proposal.action_type]
    run_configuration = {
        "proposal_digest": proposal.proposal_digest,
        "model_snapshot_digest": model_snapshot_digest(snapshot),
        "samples": samples,
        "seed": snapshot.random_seed + action_index * 1_000 + seed_offset,
        "traffic_multiplier": traffic_multiplier,
        "provider_latency_multiplier": provider_latency_multiplier,
        "db_capacity_multiplier": db_capacity_multiplier,
        "db_capacity_range": (0.85, 1.10),
        "scenario_generation_version": SCENARIO_GENERATION_VERSION,
    }
    run_id = f"sim-{canonical_digest(run_configuration)[:24]}"
    outcomes: list[PredictedOutcome] = []
    probability = max(
        0.05,
        min(
            0.98,
            profile["recovery_probability"]
            - max(0.0, traffic_multiplier - 1) * 0.10
            - max(0.0, provider_latency_multiplier - 1) * 0.04,
        ),
    )

    for index in range(samples):
        dependency_available = rng.random() > 0.08
        scenario = SimulationScenario(
            scenario_id=f"{run_id}-scenario-{index:03d}",
            simulation_run_id=run_id,
            sample_index=index,
            traffic_multiplier=traffic_multiplier,
            provider_latency_multiplier=provider_latency_multiplier,
            dependency_available=dependency_available,
            db_capacity_multiplier=rng.uniform(0.85, 1.10)
            * db_capacity_multiplier,
            scenario_generation_version=SCENARIO_GENERATION_VERSION,
        )
        recovered = rng.random() < probability and dependency_available
        data_loss = rng.random() < profile["data_loss_probability"]
        jitter = rng.uniform(0.75, 1.35)
        recovery_minutes = profile["recovery_minutes"] * jitter * (1 if recovered else 3.5)
        latency = (
            profile["healthy_latency_ms"] * provider_latency_multiplier * jitter
            if recovered
            else 2_200 * provider_latency_multiplier * jitter
        )
        cross_tenant = proposal.action_type is ActionType.DATABASE_ROLLBACK
        tenants = (TENANT, "globex-commerce") if cross_tenant else (TENANT,)
        invariants: list[str] = []
        if cross_tenant:
            invariants.append("CROSS_TENANT_MUTATION")
        if data_loss:
            invariants.append("DATA_LOSS")
        predicted = PredictedState(
            predicted_state_id=f"predicted-{proposal.proposal_id}-{index:03d}",
            scenario_id=scenario.scenario_id,
            tenant=proposal.tenant,
            deployment_version=(
                str(proposal.parameters.get("to_deployment", "deploy-1842"))
                if recovered
                else "deploy-1842"
            ),
            checkout_error_rate_pct=rng.uniform(0.5, 2.0) if recovered else rng.uniform(8, 22),
            checkout_p99_ms=latency,
            queue_depth=rng.uniform(80, 400) if recovered else rng.uniform(1_000, 4_000),
            db_utilization_pct=min(
                100,
                rng.uniform(45, 75)
                * traffic_multiplier
                / db_capacity_multiplier,
            ),
            provider_available=dependency_available,
            derived_from_snapshot_id=snapshot.snapshot_id,
        )
        outcomes.append(
            PredictedOutcome(
                scenario=scenario,
                predicted_state=predicted,
                recovered=recovered,
                recovery_minutes=recovery_minutes,
                customer_impact=min(1, profile["customer_impact"] * traffic_multiplier * jitter),
                sla_exposure=min(1, profile["sla_exposure"] * traffic_multiplier * jitter),
                data_loss=data_loss,
                reversibility=profile["reversibility"],
                operational_complexity=profile["complexity"],
                affected_entities=(proposal.target,),
                affected_tenants=tenants,
                affected_services=_service_scope(proposal.action_type),
                data_mutations=(100 if proposal.action_type is ActionType.DATABASE_ROLLBACK else 0),
                invariant_violations=tuple(invariants),
            )
        )
    return summarize_outcomes(proposal.action_type, outcomes)


def planning_constraints() -> PlanningConstraints:
    return PlanningConstraints(
        allowed_tenant=TENANT,
        allowed_services=(
            "checkout",
            "deployment-control",
            "3ds-adapter",
            "traffic-router",
        ),
        maximum_downtime_minutes=60,
        maximum_data_loss_probability=0,
        minimum_robustness=0.60,
    )


def _winner(scores: list[ScenarioScore]) -> str | None:
    feasible = [item for item in scores if not item.hard_constraint_violations]
    if not feasible:
        return None
    return max(feasible, key=lambda item: item.expected_utility).proposal_id


def run_planning_cycle(
    state: ObservedState,
    snapshot: ModelSnapshot,
    *,
    samples: int = 200,
    joint_stress_multipliers: tuple[float, ...] = (1.0, 2.0),
    weights: UtilityWeights | None = None,
    constraints: PlanningConstraints | None = None,
) -> PlanningDecision:
    weights = weights or UtilityWeights()
    constraints = constraints or planning_constraints()
    validity = assess_model_validity(snapshot, state, now=FIXED_TIME)
    if validity.status is not ModelValidityStatus.VALID:
        return PlanningDecision(
            decision_id="decision-model-invalid",
            status=PlanningStatus.MODEL_INVALID,
            model_validity=validity,
            recommended_proposal_id=None,
            simulation_results=(),
            joint_stress_winners=(),
            reason_codes=(validity.status.value, *validity.reason_codes),
            utility_policy_version=UTILITY_POLICY_VERSION,
            constraint_policy_version=CONSTRAINT_POLICY_VERSION,
            created_at=FIXED_TIME,
        )

    proposals = action_proposals(state, snapshot)
    base_results: list[SimulationResult] = []
    for proposal in proposals:
        validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=ALLOWED_PROPOSAL_ACTIONS,
        )
        distribution = simulate_proposal(proposal, snapshot, samples=samples)
        score = score_distribution(
            proposal, distribution, weights=weights, constraints=constraints
        )
        base_results.append(
            SimulationResult(
                simulation_run_id=distribution.outcomes[0].scenario.simulation_run_id,
                proposal_id=proposal.proposal_id,
                proposal_digest=proposal.proposal_digest,
                model_version=snapshot.model_version,
                snapshot_id=snapshot.snapshot_id,
                model_snapshot_digest=model_snapshot_digest(snapshot),
                observed_state_digest=proposal.observed_state_digest,
                scenario_generation_version=SCENARIO_GENERATION_VERSION,
                started_at=FIXED_TIME - timedelta(seconds=1),
                distribution=distribution,
                score=score,
            )
        )

    base_winner = _winner([item.score for item in base_results])
    if base_winner is None:
        return PlanningDecision(
            decision_id="decision-no-feasible-action",
            status=PlanningStatus.NO_FEASIBLE_ACTION,
            model_validity=validity,
            recommended_proposal_id=None,
            simulation_results=tuple(base_results),
            joint_stress_winners=(),
            reason_codes=("ALL_ACTIONS_CONSTRAINT_BLOCKED",),
            utility_policy_version=UTILITY_POLICY_VERSION,
            constraint_policy_version=CONSTRAINT_POLICY_VERSION,
            created_at=FIXED_TIME,
        )

    joint_stress_winners: list[str] = []
    for index, multiplier in enumerate(joint_stress_multipliers):
        if multiplier == 1.0:
            winner = base_winner
        else:
            variant_scores = []
            for proposal in proposals:
                distribution = simulate_proposal(
                    proposal,
                    snapshot,
                    samples=samples,
                    traffic_multiplier=multiplier,
                    provider_latency_multiplier=multiplier,
                    seed_offset=(index + 1) * 10_000,
                )
                variant_scores.append(
                    score_distribution(
                        proposal,
                        distribution,
                        weights=weights,
                        constraints=constraints,
                    )
                )
            winner = _winner(variant_scores)
        joint_stress_winners.append(winner or "NO_FEASIBLE_ACTION")

    unique_winners = set(joint_stress_winners)
    if len(unique_winners) > 1:
        status = PlanningStatus.DECISION_UNSTABLE
        recommendation = None
        reasons = ("JOINT_STRESS_WINNER_CHANGED",)
    else:
        status = PlanningStatus.READY_FOR_REVIEW
        recommendation = base_winner
        reasons = (
            "SIMULATION_SUPPORTS_PROPOSAL",
            "REVIEW_AND_APPROVAL_STILL_REQUIRED",
        )
    return PlanningDecision(
        decision_id="decision-eu-checkout-1842",
        status=status,
        model_validity=validity,
        recommended_proposal_id=recommendation,
        simulation_results=tuple(base_results),
        joint_stress_winners=tuple(joint_stress_winners),
        reason_codes=reasons,
        utility_policy_version=UTILITY_POLICY_VERSION,
        constraint_policy_version=CONSTRAINT_POLICY_VERSION,
        created_at=FIXED_TIME,
    )


def recommended_artifacts(
    state: ObservedState,
    snapshot: ModelSnapshot,
    decision: PlanningDecision,
) -> tuple[ActionProposal, SimulationResult]:
    if decision.recommended_proposal_id is None:
        raise WorldModelPolicyError("NO_RECOMMENDED_PROPOSAL")
    proposal = next(
        item for item in action_proposals(state, snapshot)
        if item.proposal_id == decision.recommended_proposal_id
    )
    simulation = next(
        item for item in decision.simulation_results
        if item.proposal_id == proposal.proposal_id
    )
    return proposal, simulation


def approval_receipt(
    proposal: ActionProposal,
    simulation: SimulationResult,
    *,
    approver_roles: tuple[str, ...] = ("incident.approver",),
    tenant: str | None = None,
    proposal_digest: str | None = None,
    simulation_run_id: str | None = None,
    model_digest: str | None = None,
    state_digest: str | None = None,
    policy_version: str = POLICY_VERSION,
    status: ApprovalStatus = ApprovalStatus.VALID,
    issued_at: datetime = FIXED_TIME,
    expires_at: datetime = FIXED_TIME + timedelta(minutes=10),
) -> ApprovalReceipt:
    return ApprovalReceipt(
        approval_id="approval-eu-1842",
        approver_id="oncall-director-7",
        approver_roles=approver_roles,
        tenant=tenant or proposal.tenant,
        action=proposal.action_type,
        target=proposal.target,
        proposal_digest=proposal_digest or proposal.proposal_digest,
        simulation_run_id=simulation_run_id or simulation.simulation_run_id,
        world_model_snapshot_id=proposal.world_model_snapshot_id,
        model_snapshot_digest=model_digest or simulation.model_snapshot_digest,
        observed_state_digest=state_digest or proposal.observed_state_digest,
        policy_version=policy_version,
        issued_at=issued_at,
        expires_at=expires_at,
        status=status,
    )


def authorize_recommended_action(
    state: ObservedState,
    snapshot: ModelSnapshot,
    decision: PlanningDecision,
    proposal: ActionProposal,
    simulation: SimulationResult,
    approval: ApprovalReceipt | None,
    *,
    executor_capabilities: tuple[str, ...] = EXECUTION_CAPABILITIES,
    now: datetime = FIXED_TIME,
) -> ExecutionProposal:
    """Return a validated command envelope; this fixture performs no side effect."""

    return validate_approval(
        proposal,
        simulation,
        decision,
        approval,
        snapshot=snapshot,
        current_state=state,
        executor_capabilities=executor_capabilities,
        now=now,
    )


def shadow_calibration_records() -> tuple[CalibrationRecord, ...]:
    """Historical shadow predictions; the candidate model never controlled production."""

    values = (
        # id, prediction, observation, probability, recovered, interval
        ("cal-1", 10.0, 12.0, 0.80, True, 7.0, 14.0),
        ("cal-2", 10.0, 13.0, 0.75, True, 7.0, 14.0),
        ("cal-3", 10.0, 9.0, 0.30, False, 8.0, 12.0),
        ("cal-4", 10.0, 14.0, 0.70, True, 7.0, 15.0),
        ("cal-5", 10.0, 12.5, 0.65, True, 7.0, 14.0),
    )
    records = []
    for record_id, predicted, observed, probability, recovered, lower, upper in values:
        error = abs(predicted - observed)
        prediction_error = PredictionError(
            prediction_id=f"prediction-{record_id}",
            observed_outcome_id=f"outcome-{record_id}",
            absolute_recovery_error_minutes=error,
            relative_recovery_error=error / 10,
            absolute_latency_error_ms=error * 50,
            slo_impact=False,
            ranking_changed=False,
            material=False,
        )
        records.append(
            CalibrationRecord(
                record_id=record_id,
                model_version="world-model-v12",
                prediction_error=prediction_error,
                predicted_recovery_minutes=predicted,
                observed_recovery_minutes=observed,
                predicted_recovery_probability=probability,
                recovery_occurred=recovered,
                interval_lower_minutes=lower,
                interval_upper_minutes=upper,
            )
        )
    return tuple(records)


def fixture_observed_outcome(execution: ExecutionProposal) -> ObservedOutcome:
    return ObservedOutcome(
        outcome_id="observed-outcome-1842",
        execution_id=execution.execution_id,
        tenant=TENANT,
        observed_at=FIXED_TIME + timedelta(minutes=12),
        recovered=True,
        recovery_minutes=12,
        checkout_p99_ms=260,
        checkout_error_rate_pct=1.2,
        data_loss=False,
        source_ids=("metrics-eu-checkout-v9", "deployment-events-v4"),
    )


def demo_summary(samples: int = 200) -> dict[str, Any]:
    """Compact notebook entry point with no production execution."""

    state = observed_state()
    snapshot = model_snapshot(state)
    decision = run_planning_cycle(
        state, snapshot, samples=samples, joint_stress_multipliers=(1.0,)
    )
    proposal, simulation = recommended_artifacts(state, snapshot, decision)
    blocked_without_approval = False
    try:
        authorize_recommended_action(
            state, snapshot, decision, proposal, simulation, None
        )
    except WorldModelPolicyError as error:
        blocked_without_approval = str(error) == "APPROVAL_REQUIRED"
    approval = approval_receipt(proposal, simulation)
    command = authorize_recommended_action(
        state, snapshot, decision, proposal, simulation, approval
    )
    return {
        "model_validity": decision.model_validity.status.value,
        "planning_status": decision.status.value,
        "recommended_action": proposal.action_type.value,
        "simulation_run_id": simulation.simulation_run_id,
        "model_snapshot_digest": simulation.model_snapshot_digest,
        "observed_state_digest": proposal.observed_state_digest,
        "approval_required": proposal.approval_required,
        "blocked_without_approval": blocked_without_approval,
        "execution_envelope_created": command.execution_id,
        "production_side_effects": 0,
        "message": (
            "Simulation supports a proposal; it does not establish production safety. "
            "Fresh-state, policy, review, approval, and the real execution control plane remain required."
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(demo_summary(), indent=2))
