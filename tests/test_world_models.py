"""Advanced Course 07 world-model and authorization invariants."""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "advanced"
    / "07-world-models-environment-modeling"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course07_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course07_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _planned():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    decision = lab.run_planning_cycle(state, snapshot)
    proposal, simulation = lab.recommended_artifacts(state, snapshot, decision)
    return state, snapshot, decision, proposal, simulation


def test_models_forbid_extra_fields():
    state = lab.observed_state()
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.ObservedState.model_validate(
            {**state.model_dump(), "simulation_verified_safe": True}
        )


def test_observed_and_predicted_state_are_distinct_types():
    state, _, _, _, simulation = _planned()
    predicted = simulation.distribution.outcomes[0].predicted_state
    assert isinstance(state, policy.ObservedState)
    assert isinstance(predicted, policy.PredictedState)
    assert not isinstance(predicted, policy.ObservedState)


def test_observation_carries_required_provenance_and_units():
    observation = lab.observed_state().observations[0]
    assert observation.observation_id
    assert observation.source == "northstar-telemetry"
    assert observation.source_version == "otel-pipeline-v7"
    assert observation.observed_at < observation.retrieved_at
    assert observation.tenant == lab.TENANT
    assert observation.unit == "requests/second"
    assert observation.quality is policy.SensorQuality.GOOD


def test_observation_rejects_retrieval_before_observation():
    with pytest.raises(ValidationError, match="OBSERVATION_TIME_INVALID"):
        lab._observation(
            "traffic_rps",
            "requests/second",
            100,
            observed_at=lab.FIXED_TIME,
        )


def test_missing_sensor_cannot_claim_a_value():
    values = lab._observation(
        "traffic_rps", "requests/second", 100
    ).model_dump()
    values["quality"] = policy.SensorQuality.MISSING
    with pytest.raises(ValidationError, match="MISSING_SENSOR_MUST_NOT_HAVE_VALUE"):
        policy.Observation(**values)


def test_non_missing_sensor_requires_value():
    values = lab._observation(
        "traffic_rps", "requests/second", 100
    ).model_dump()
    values["value"] = None
    with pytest.raises(ValidationError, match="OBSERVATION_VALUE_REQUIRED"):
        policy.Observation(**values)


def test_observed_state_rejects_duplicate_variables():
    state = lab.observed_state()
    with pytest.raises(ValidationError, match="DUPLICATE_STATE_VARIABLE"):
        policy.ObservedState(
            **{
                **state.model_dump(),
                "observations": (state.observations[0], state.observations[0]),
            }
        )


def test_model_snapshot_binds_version_time_and_input_digest():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    assert snapshot.model_version == "world-model-v12"
    assert snapshot.snapshot_id
    assert snapshot.calibration_time < snapshot.snapshot_time
    assert snapshot.input_state_digest == policy.observed_state_digest(state)


def test_model_snapshot_rejects_invalid_range():
    with pytest.raises(ValidationError, match="INVALID_VALIDATED_RANGE"):
        policy.StateVariable(
            name="traffic_rps", unit="requests/second", minimum=10, maximum=1
        )


def test_valid_fixture_reports_measurable_ages():
    state = lab.observed_state()
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.VALID
    assert result.oldest_sensor_age_seconds == 30
    assert result.snapshot_age_seconds == 2
    assert result.model_age_seconds == timedelta(days=7).total_seconds()


def test_out_of_distribution_traffic_blocks_model_use():
    state = lab.observed_state(traffic_rps=7_000)
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.OUT_OF_DISTRIBUTION
    assert result.out_of_distribution_variables == ("traffic_rps",)
    assert "MODEL_OUT_OF_DOMAIN" in result.reason_codes


def test_missing_required_sensor_makes_state_unvalidated():
    state = lab.observed_state(
        observation_overrides={
            "queue_depth": {"quality": policy.SensorQuality.MISSING}
        }
    )
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "MODEL_STATE_INCOMPLETE" in result.reason_codes
    assert "SENSOR_QUALITY_INVALID" in result.reason_codes


@pytest.mark.parametrize(
    "quality", [policy.SensorQuality.NOISY, policy.SensorQuality.UNTRUSTED]
)
def test_unreliable_sensor_quality_makes_model_unvalidated(quality):
    state = lab.observed_state(
        observation_overrides={"traffic_rps": {"quality": quality}}
    )
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.UNVALIDATED


def test_delayed_but_fresh_sensor_is_degraded():
    state = lab.observed_state(
        observation_overrides={
            "traffic_rps": {"quality": policy.SensorQuality.DELAYED}
        }
    )
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.DEGRADED
    assert "SENSOR_DELAYED" in result.reason_codes


def test_stale_sensor_is_rejected():
    state = lab.observed_state(
        observation_overrides={
            "traffic_rps": {
                "observed_at": lab.FIXED_TIME - timedelta(minutes=5)
            }
        }
    )
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.STALE
    assert "SENSOR_STATE_STALE" in result.reason_codes


def test_stale_snapshot_is_rejected():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(
        state, snapshot_time=lab.FIXED_TIME - timedelta(minutes=10)
    )
    result = policy.assess_model_validity(snapshot, state, now=lab.FIXED_TIME)
    assert result.status is policy.ModelValidityStatus.STALE
    assert "MODEL_SNAPSHOT_STALE" in result.reason_codes


def test_stale_calibration_is_rejected():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(
        state, calibration_time=lab.FIXED_TIME - timedelta(days=45)
    )
    result = policy.assess_model_validity(snapshot, state, now=lab.FIXED_TIME)
    assert result.status is policy.ModelValidityStatus.STALE
    assert "MODEL_CALIBRATION_STALE" in result.reason_codes


def test_future_observation_is_rejected_instead_of_treated_as_age_zero():
    state = lab.observed_state()
    future = state.observations[0].model_copy(
        update={
            "observed_at": lab.FIXED_TIME + timedelta(minutes=1),
            "retrieved_at": lab.FIXED_TIME + timedelta(minutes=1),
        }
    )
    state = state.model_copy(update={"observations": (future, *state.observations[1:])})
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "OBSERVATION_FROM_FUTURE" in result.reason_codes


def test_future_model_snapshot_is_rejected():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(
        state, snapshot_time=lab.FIXED_TIME + timedelta(minutes=1)
    )
    result = policy.assess_model_validity(snapshot, state, now=lab.FIXED_TIME)
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "MODEL_SNAPSHOT_FROM_FUTURE" in result.reason_codes


def test_calibration_after_snapshot_is_rejected():
    state = lab.observed_state()
    with pytest.raises(ValidationError, match="CALIBRATION_AFTER_SNAPSHOT"):
        lab.model_snapshot(
            state,
            snapshot_time=lab.FIXED_TIME - timedelta(minutes=2),
            calibration_time=lab.FIXED_TIME - timedelta(minutes=1),
        )


def test_unit_mismatch_makes_model_unvalidated():
    state = lab.observed_state()
    first = state.observations[0].model_copy(update={"unit": "milliseconds"})
    state = state.model_copy(update={"observations": (first, *state.observations[1:])})
    snapshot = lab.model_snapshot(state)
    result = policy.assess_model_validity(snapshot, state, now=lab.FIXED_TIME)
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "STATE_UNIT_MISMATCH" in result.reason_codes


def test_snapshot_input_digest_mismatch_is_rejected():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state, input_state_digest="0" * 64)
    result = policy.assess_model_validity(snapshot, state, now=lab.FIXED_TIME)
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "MODEL_INPUT_DIGEST_MISMATCH" in result.reason_codes


def test_model_tenant_mismatch_is_rejected():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state).model_copy(update={"tenant": "globex"})
    result = policy.assess_model_validity(snapshot, state, now=lab.FIXED_TIME)
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "MODEL_TENANT_MISMATCH" in result.reason_codes


def test_cross_tenant_observation_is_rejected():
    state = lab.observed_state()
    first = state.observations[0].model_copy(update={"tenant": "globex"})
    state = state.model_copy(update={"observations": (first, *state.observations[1:])})
    result = policy.assess_model_validity(
        lab.model_snapshot(state), state, now=lab.FIXED_TIME
    )
    assert result.status is policy.ModelValidityStatus.UNVALIDATED
    assert "OBSERVATION_TENANT_MISMATCH" in result.reason_codes


def test_valid_plan_may_contain_approval_gated_actions():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposals = lab.action_proposals(state, snapshot)
    for proposal in proposals:
        policy.validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=lab.ALLOWED_PROPOSAL_ACTIONS,
        )
    assert any(item.approval_required for item in proposals)


def test_planner_may_propose_rollback_without_production_rollback_authority():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    rollback = lab.action_proposals(state, snapshot)[0]
    assert rollback.required_capability == "production.rollback"
    policy.validate_action_proposal(
        rollback,
        observed_state=state,
        snapshot=snapshot,
        allowed_proposal_actions=(policy.ActionType.ROLLBACK_DEPLOYMENT,),
    )


def test_consequential_action_cannot_disable_approval_gate():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0].model_copy(
        update={"approval_required": False}
    )
    proposal = proposal.model_copy(
        update={
            "proposal_digest": policy.canonical_digest(
                policy.action_proposal_payload(proposal)
            )
        }
    )
    with pytest.raises(
        policy.WorldModelPolicyError,
        match="CONSEQUENTIAL_ACTION_REQUIRES_APPROVAL",
    ):
        policy.validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=lab.ALLOWED_PROPOSAL_ACTIONS,
        )


def test_action_schema_rejects_arbitrary_sql_or_shell_parameters():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    unsafe = proposal.model_copy(update={"parameters": {"sql": "DROP TABLE orders"}})
    unsafe = unsafe.model_copy(
        update={
            "proposal_digest": policy.canonical_digest(
                policy.action_proposal_payload(unsafe)
            )
        }
    )
    with pytest.raises(policy.WorldModelPolicyError, match="ACTION_SCHEMA_INVALID"):
        policy.validate_action_proposal(
            unsafe,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=lab.ALLOWED_PROPOSAL_ACTIONS,
        )


def test_proposal_policy_is_separate_from_production_capability():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    # The planning gate reasons over action types, never production credentials.
    with pytest.raises(policy.WorldModelPolicyError, match="PROPOSAL_ACTION_DENIED"):
        policy.validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=(policy.ActionType.WAIT_AND_OBSERVE,),
        )


def test_action_cannot_claim_a_weaker_execution_capability():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0].model_copy(
        update={"required_capability": "telemetry.read"}
    )
    proposal = proposal.model_copy(
        update={
            "proposal_digest": policy.canonical_digest(
                policy.action_proposal_payload(proposal)
            )
        }
    )
    with pytest.raises(
        policy.WorldModelPolicyError,
        match="ACTION_CAPABILITY_BINDING_INVALID",
    ):
        policy.validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=lab.ALLOWED_PROPOSAL_ACTIONS,
        )


def test_stale_rollback_precondition_rejected_during_planning():
    state = lab.observed_state(deployment_version="deploy-1843")
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    with pytest.raises(policy.WorldModelPolicyError, match="PRECONDITION_STALE"):
        policy.validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=lab.ALLOWED_PROPOSAL_ACTIONS,
        )


def test_tampered_proposal_digest_is_rejected():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0].model_copy(
        update={"proposal_digest": "0" * 64}
    )
    with pytest.raises(policy.WorldModelPolicyError, match="PROPOSAL_DIGEST_MISMATCH"):
        policy.validate_action_proposal(
            proposal,
            observed_state=state,
            snapshot=snapshot,
            allowed_proposal_actions=lab.ALLOWED_PROPOSAL_ACTIONS,
        )


def test_seeded_monte_carlo_is_reproducible():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    first = lab.simulate_proposal(proposal, snapshot, samples=40)
    second = lab.simulate_proposal(proposal, snapshot, samples=40)
    assert first == second


def test_seed_offset_changes_simulated_trajectory():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    first = lab.simulate_proposal(proposal, snapshot, samples=40)
    second = lab.simulate_proposal(proposal, snapshot, samples=40, seed_offset=1)
    assert first.outcomes != second.outcomes


def test_provider_latency_sensitivity_is_independent_of_traffic():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    baseline = lab.simulate_proposal(proposal, snapshot, samples=40)
    provider_only = lab.simulate_proposal(
        proposal,
        snapshot,
        samples=40,
        traffic_multiplier=1.0,
        provider_latency_multiplier=2.0,
    )
    scenario = provider_only.outcomes[0].scenario
    assert scenario.traffic_multiplier == 1.0
    assert scenario.provider_latency_multiplier == 2.0
    assert scenario.simulation_run_id != baseline.outcomes[0].scenario.simulation_run_id


def test_distribution_reports_real_quantiles_and_probabilities():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    distribution = lab.simulate_proposal(proposal, snapshot, samples=100)
    assert distribution.sample_count == len(distribution.outcomes) == 100
    assert 0 <= distribution.recovery_probability <= 1
    assert distribution.p10_recovery_minutes <= distribution.p50_recovery_minutes
    assert distribution.p50_recovery_minutes <= distribution.p90_recovery_minutes
    assert distribution.worst_case_downtime_minutes >= distribution.p90_recovery_minutes


def test_predicted_state_binds_to_model_snapshot():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    predicted = lab.simulate_proposal(
        proposal, snapshot, samples=1
    ).outcomes[0].predicted_state
    assert predicted.derived_from_snapshot_id == snapshot.snapshot_id


def test_uncertainty_penalty_is_derived_from_distribution_width():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    distribution = lab.simulate_proposal(proposal, snapshot, samples=100)
    score = policy.score_distribution(
        proposal,
        distribution,
        weights=policy.UtilityWeights(),
        constraints=lab.planning_constraints(),
    )
    assert score.uncertainty_penalty == pytest.approx(
        (distribution.p90_recovery_minutes - distribution.p10_recovery_minutes)
        / lab.planning_constraints().maximum_downtime_minutes
    )


def test_default_planning_decision_is_ready_for_review_not_execution():
    _, _, decision, proposal, _ = _planned()
    assert decision.status is policy.PlanningStatus.READY_FOR_REVIEW
    assert decision.recommended_proposal_id == "proposal-rollback"
    assert proposal.approval_required is True
    assert "REVIEW_AND_APPROVAL_STILL_REQUIRED" in decision.reason_codes


def test_utility_and_constraint_policy_versions_are_recorded():
    _, _, decision, _, simulation = _planned()
    assert decision.utility_policy_version == policy.UTILITY_POLICY_VERSION
    assert decision.constraint_policy_version == policy.CONSTRAINT_POLICY_VERSION
    assert simulation.score.utility_policy_version == decision.utility_policy_version
    assert simulation.score.constraint_policy_version == decision.constraint_policy_version
    assert simulation.scenario_generation_version == policy.SCENARIO_GENERATION_VERSION


def test_database_rollback_is_hard_constraint_blocked():
    _, _, decision, _, _ = _planned()
    result = next(
        item
        for item in decision.simulation_results
        if item.score.action_type is policy.ActionType.DATABASE_ROLLBACK
    )
    assert "DATA_LOSS_CONSTRAINT" in result.score.hard_constraint_violations
    assert "BLAST_RADIUS_VIOLATION" in result.score.hard_constraint_violations
    assert "CROSS_TENANT_MUTATION" in result.score.hard_constraint_violations


def test_wait_action_fails_worst_case_and_robustness_constraints():
    _, _, decision, _, _ = _planned()
    result = next(
        item
        for item in decision.simulation_results
        if item.score.action_type is policy.ActionType.WAIT_AND_OBSERVE
    )
    assert "WORST_CASE_DOWNTIME_CONSTRAINT" in result.score.hard_constraint_violations
    assert "ROBUSTNESS_CONSTRAINT" in result.score.hard_constraint_violations


def test_explicit_weight_change_changes_utility_not_raw_predictions():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    proposal = lab.action_proposals(state, snapshot)[0]
    distribution = lab.simulate_proposal(proposal, snapshot, samples=50)
    default = policy.score_distribution(
        proposal,
        distribution,
        weights=policy.UtilityWeights(),
        constraints=lab.planning_constraints(),
    )
    conservative = policy.score_distribution(
        proposal,
        distribution,
        weights=policy.UtilityWeights(uncertainty=10),
        constraints=lab.planning_constraints(),
    )
    assert conservative.expected_utility < default.expected_utility
    assert conservative.robustness_score == default.robustness_score


def test_impossible_constraints_produce_no_feasible_action():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    constraints = lab.planning_constraints().model_copy(
        update={"minimum_robustness": 1.0, "maximum_downtime_minutes": 1}
    )
    decision = lab.run_planning_cycle(
        state, snapshot, samples=50, constraints=constraints
    )
    assert decision.status is policy.PlanningStatus.NO_FEASIBLE_ACTION
    assert decision.recommended_proposal_id is None


def test_joint_stress_winner_change_produces_unstable_decision():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    constraints = lab.planning_constraints().model_copy(
        update={"minimum_robustness": 0.75}
    )
    decision = lab.run_planning_cycle(
        state,
        snapshot,
        samples=200,
        joint_stress_multipliers=(1.0, 2.0),
        constraints=constraints,
    )
    assert decision.status is policy.PlanningStatus.DECISION_UNSTABLE
    assert len(set(decision.joint_stress_winners)) > 1


def test_invalid_model_is_blocked_before_simulation():
    state = lab.observed_state(traffic_rps=7_000)
    decision = lab.run_planning_cycle(state, lab.model_snapshot(state))
    assert decision.status is policy.PlanningStatus.MODEL_INVALID
    assert decision.simulation_results == ()
    assert decision.recommended_proposal_id is None


def test_execution_without_approval_is_blocked():
    state, snapshot, decision, proposal, simulation = _planned()
    with pytest.raises(policy.WorldModelPolicyError, match="APPROVAL_REQUIRED"):
        lab.authorize_recommended_action(
            state, snapshot, decision, proposal, simulation, None
        )


def test_valid_approval_may_create_execution_envelope():
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(proposal, simulation)
    command = lab.authorize_recommended_action(
        state, snapshot, decision, proposal, simulation, approval
    )
    assert command.approval_id == approval.approval_id
    assert command.observed_state_digest == policy.observed_state_digest(state)
    assert command.model_snapshot_digest == policy.model_snapshot_digest(snapshot)
    assert command.action is policy.ActionType.ROLLBACK_DEPLOYMENT


def test_simulation_cannot_expand_execution_capabilities():
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(proposal, simulation)
    with pytest.raises(
        policy.WorldModelPolicyError, match="EXECUTION_CAPABILITY_DENIED"
    ):
        lab.authorize_recommended_action(
            state,
            snapshot,
            decision,
            proposal,
            simulation,
            approval,
            executor_capabilities=("telemetry.read",),
        )


@pytest.mark.parametrize(
    ("approval_updates", "reason"),
    [
        ({"tenant": "globex"}, "APPROVAL_TENANT_MISMATCH"),
        ({"proposal_digest": "0" * 64}, "APPROVAL_DIGEST_MISMATCH"),
        ({"simulation_run_id": "sim-other"}, "APPROVAL_SIMULATION_MISMATCH"),
        ({"model_snapshot_digest": "0" * 64}, "APPROVAL_MODEL_DIGEST_MISMATCH"),
        ({"approver_roles": ("incident.viewer",)}, "APPROVER_ROLE_DENIED"),
        ({"status": policy.ApprovalStatus.REVOKED}, "APPROVAL_STATUS_INVALID"),
        ({"policy_version": "obsolete-policy"}, "APPROVAL_POLICY_MISMATCH"),
    ],
)
def test_approval_binding_failures_are_rejected(approval_updates, reason):
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(proposal, simulation).model_copy(
        update=approval_updates
    )
    with pytest.raises(policy.WorldModelPolicyError, match=reason):
        lab.authorize_recommended_action(
            state, snapshot, decision, proposal, simulation, approval
        )


def test_expired_approval_is_rejected():
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(
        proposal,
        simulation,
        issued_at=lab.FIXED_TIME - timedelta(milliseconds=500),
        expires_at=lab.FIXED_TIME - timedelta(milliseconds=100),
    )
    with pytest.raises(policy.WorldModelPolicyError, match="APPROVAL_EXPIRED"):
        lab.authorize_recommended_action(
            state, snapshot, decision, proposal, simulation, approval
        )


def test_approval_receipt_rejects_non_positive_time_window():
    _, _, _, proposal, simulation = _planned()
    values = lab.approval_receipt(proposal, simulation).model_dump()
    values["expires_at"] = values["issued_at"]
    with pytest.raises(ValidationError, match="APPROVAL_TIME_WINDOW_INVALID"):
        policy.ApprovalReceipt.model_validate(values)


def test_execution_rejects_simulation_not_contained_in_decision():
    state, snapshot, decision, proposal, simulation = _planned()
    fabricated = simulation.model_copy(update={"simulation_run_id": "sim-fabricated"})
    approval = lab.approval_receipt(proposal, fabricated)
    with pytest.raises(
        policy.WorldModelPolicyError, match="SIMULATION_NOT_IN_DECISION"
    ):
        lab.authorize_recommended_action(
            state, snapshot, decision, proposal, fabricated, approval
        )


def test_material_state_change_invalidates_approved_simulation():
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(proposal, simulation)
    changed_state = lab.observed_state(deployment_version="deploy-1843")
    with pytest.raises(policy.WorldModelPolicyError, match="SIMULATION_STALE"):
        lab.authorize_recommended_action(
            changed_state, snapshot, decision, proposal, simulation, approval
        )


def test_unexpired_approval_cannot_authorize_stale_sensor_state():
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(proposal, simulation)
    with pytest.raises(policy.WorldModelPolicyError, match="MODEL_STATE_STALE"):
        lab.authorize_recommended_action(
            state,
            snapshot,
            decision,
            proposal,
            simulation,
            approval,
            now=lab.FIXED_TIME + timedelta(minutes=5),
        )


def test_fabricated_ready_decision_cannot_bypass_hard_constraints():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    original = lab.run_planning_cycle(state, snapshot)
    simulation = next(
        item
        for item in original.simulation_results
        if item.score.action_type is policy.ActionType.DATABASE_ROLLBACK
    )
    proposal = next(
        item
        for item in lab.action_proposals(state, snapshot)
        if item.proposal_id == simulation.proposal_id
    )
    fabricated = original.model_copy(
        update={
            "status": policy.PlanningStatus.READY_FOR_REVIEW,
            "recommended_proposal_id": proposal.proposal_id,
        }
    )
    approval = lab.approval_receipt(proposal, simulation)
    with pytest.raises(
        policy.WorldModelPolicyError,
        match="SIMULATION_HARD_CONSTRAINT_VIOLATION",
    ):
        lab.authorize_recommended_action(
            state,
            snapshot,
            fabricated,
            proposal,
            simulation,
            approval,
            executor_capabilities=("database.restore",),
        )


def test_execution_rejects_non_valid_planning_model_status():
    state, snapshot, decision, proposal, simulation = _planned()
    invalid_validity = decision.model_validity.model_copy(
        update={
            "status": policy.ModelValidityStatus.STALE,
            "reason_codes": ("SENSOR_STATE_STALE",),
        }
    )
    fabricated = decision.model_copy(update={"model_validity": invalid_validity})
    approval = lab.approval_receipt(proposal, simulation)
    with pytest.raises(policy.WorldModelPolicyError, match="DECISION_MODEL_INVALID"):
        lab.authorize_recommended_action(
            state,
            snapshot,
            fabricated,
            proposal,
            simulation,
            approval,
        )


def test_model_snapshot_digest_mismatch_is_rejected():
    state, snapshot, decision, proposal, simulation = _planned()
    approval = lab.approval_receipt(proposal, simulation)
    altered_snapshot = snapshot.model_copy(update={"random_seed": 999})
    with pytest.raises(
        policy.WorldModelPolicyError, match="MODEL_SNAPSHOT_DIGEST_MISMATCH"
    ):
        lab.authorize_recommended_action(
            state,
            altered_snapshot,
            decision,
            proposal,
            simulation,
            approval,
        )


def test_text_token_is_not_an_approval_receipt():
    state, snapshot, decision, proposal, simulation = _planned()
    with pytest.raises(ValidationError):
        policy.ApprovalReceipt.model_validate({"text": "APPROVED"})
    with pytest.raises(policy.WorldModelPolicyError, match="APPROVAL_REQUIRED"):
        lab.authorize_recommended_action(
            state, snapshot, decision, proposal, simulation, None
        )


def test_small_relative_latency_error_is_not_automatically_material():
    _, _, _, proposal, simulation = _planned()
    execution = policy.ExecutionProposal(
        execution_id="exec-small-gap",
        approval_id="approval-small-gap",
        proposal_id=proposal.proposal_id,
        proposal_digest=proposal.proposal_digest,
        simulation_run_id=simulation.simulation_run_id,
        model_snapshot_digest=simulation.model_snapshot_digest,
        observed_state_digest=proposal.observed_state_digest,
        action=proposal.action_type,
        target=proposal.target,
        parameters=proposal.parameters,
        required_capability=proposal.required_capability,
        authorized_at=lab.FIXED_TIME,
    )
    observed = lab.fixture_observed_outcome(execution).model_copy(
        update={"recovery_minutes": simulation.distribution.mean_recovery_minutes, "checkout_p99_ms": 2}
    )
    error = policy.compare_prediction(
        simulation.distribution,
        observed,
        prediction_id="prediction-small-gap",
        predicted_latency_ms=1,
    )
    assert error.absolute_latency_error_ms == 1
    assert error.slo_impact is False
    assert error.material is False


def test_large_latency_error_crossing_slo_is_material():
    _, _, _, proposal, simulation = _planned()
    execution = policy.ExecutionProposal(
        execution_id="exec-large-gap",
        approval_id="approval-large-gap",
        proposal_id=proposal.proposal_id,
        proposal_digest=proposal.proposal_digest,
        simulation_run_id=simulation.simulation_run_id,
        model_snapshot_digest=simulation.model_snapshot_digest,
        observed_state_digest=proposal.observed_state_digest,
        action=proposal.action_type,
        target=proposal.target,
        parameters=proposal.parameters,
        required_capability=proposal.required_capability,
        authorized_at=lab.FIXED_TIME,
    )
    observed = lab.fixture_observed_outcome(execution).model_copy(
        update={"recovery_minutes": simulation.distribution.mean_recovery_minutes, "checkout_p99_ms": 4_200}
    )
    error = policy.compare_prediction(
        simulation.distribution,
        observed,
        prediction_id="prediction-large-gap",
        predicted_latency_ms=10,
    )
    assert error.absolute_latency_error_ms == 4_190
    assert error.slo_impact is True
    assert error.material is True


def test_calibration_metrics_include_mae_rmse_coverage_and_brier():
    metrics = policy.calculate_calibration_metrics(lab.shadow_calibration_records())
    assert metrics.sample_count == 5
    assert metrics.mae_minutes == pytest.approx(2.5)
    assert metrics.rmse_minutes > metrics.mae_minutes
    assert metrics.interval_coverage == 1
    assert 0 <= metrics.brier_score <= 1


def test_prediction_interval_coverage_uses_observed_value_not_absolute_error():
    record = lab.shadow_calibration_records()[0]
    assert record.predicted_recovery_minutes == 10
    assert record.observed_recovery_minutes == 12
    assert record.prediction_error.absolute_recovery_error_minutes == 2
    assert not (
        record.interval_lower_minutes
        <= record.prediction_error.absolute_recovery_error_minutes
        <= record.interval_upper_minutes
    )
    assert policy.calculate_calibration_metrics((record,)).interval_coverage == 1


def test_calibration_record_rejects_inconsistent_prediction_error():
    values = lab.shadow_calibration_records()[0].model_dump()
    values["observed_recovery_minutes"] = 20
    with pytest.raises(ValidationError, match="CALIBRATION_ERROR_MISMATCH"):
        policy.CalibrationRecord.model_validate(values)


def test_well_calibrated_shadow_fixture_has_no_drift_signal():
    metrics = policy.calculate_calibration_metrics(lab.shadow_calibration_records())
    signal = policy.detect_drift(
        "world-model-v12", metrics, now=lab.FIXED_TIME
    )
    assert signal.status is policy.DriftStatus.NONE
    assert signal.reason_codes == ()


def test_multiple_failed_calibration_gates_create_critical_drift():
    metrics = policy.CalibrationMetrics(
        sample_count=10,
        mae_minutes=12,
        rmse_minutes=15,
        mean_relative_error=1.2,
        interval_coverage=0.4,
        brier_score=0.4,
    )
    signal = policy.detect_drift(
        "world-model-v12", metrics, now=lab.FIXED_TIME
    )
    assert signal.status is policy.DriftStatus.CRITICAL
    assert len(signal.reason_codes) == 3


def test_model_update_requires_calibration_lineage():
    update = policy.ModelUpdateProposal(
        update_id="update-v13",
        current_model_version="world-model-v12",
        candidate_model_version="world-model-v13",
        calibration_record_ids=("unknown-record",),
        proposed_by="calibration-pipeline",
        created_at=lab.FIXED_TIME,
    )
    with pytest.raises(
        policy.WorldModelPolicyError, match="CALIBRATION_LINEAGE_MISSING"
    ):
        policy.validate_model_update(
            update,
            lab.shadow_calibration_records(),
            constraint_violation_miss_rate=0,
            ranking_accuracy=0.9,
            now=lab.FIXED_TIME,
        )


def test_model_update_rejects_same_version_candidate():
    records = lab.shadow_calibration_records()
    update = policy.ModelUpdateProposal(
        update_id="update-v12-noop",
        current_model_version="world-model-v12",
        candidate_model_version="world-model-v12",
        calibration_record_ids=tuple(item.record_id for item in records),
        proposed_by="calibration-pipeline",
        created_at=lab.FIXED_TIME,
    )
    with pytest.raises(policy.WorldModelPolicyError, match="MODEL_VERSION_NOT_ADVANCED"):
        policy.validate_model_update(
            update,
            records,
            constraint_violation_miss_rate=0,
            ranking_accuracy=0.9,
            now=lab.FIXED_TIME,
        )


def test_failed_backtest_cannot_promote_candidate_model():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    records = lab.shadow_calibration_records()
    update = policy.ModelUpdateProposal(
        update_id="update-v13",
        current_model_version=snapshot.model_version,
        candidate_model_version="world-model-v13",
        calibration_record_ids=tuple(item.record_id for item in records),
        proposed_by="calibration-pipeline",
        created_at=lab.FIXED_TIME,
    )
    report = policy.validate_model_update(
        update,
        records,
        constraint_violation_miss_rate=0.1,
        ranking_accuracy=0.6,
        now=lab.FIXED_TIME,
    )
    assert report.approved_for_promotion is False
    with pytest.raises(policy.WorldModelPolicyError, match="MODEL_PROMOTION_DENIED"):
        policy.promote_model(
            snapshot,
            update,
            report,
            new_snapshot_id="snapshot-v13",
            new_state_digest="1" * 64,
            promoted_at=lab.FIXED_TIME,
        )


def test_passing_backtest_promotes_new_version_without_mutating_old_snapshot():
    state = lab.observed_state()
    snapshot = lab.model_snapshot(state)
    records = lab.shadow_calibration_records()
    update = policy.ModelUpdateProposal(
        update_id="update-v13",
        current_model_version=snapshot.model_version,
        candidate_model_version="world-model-v13",
        calibration_record_ids=tuple(item.record_id for item in records),
        proposed_by="calibration-pipeline",
        created_at=lab.FIXED_TIME,
    )
    report = policy.validate_model_update(
        update,
        records,
        constraint_violation_miss_rate=0,
        ranking_accuracy=0.9,
        now=lab.FIXED_TIME,
    )
    promoted = policy.promote_model(
        snapshot,
        update,
        report,
        new_snapshot_id="snapshot-v13",
        new_state_digest="1" * 64,
        promoted_at=lab.FIXED_TIME,
    )
    assert report.approved_for_promotion is True
    assert promoted.model_version == "world-model-v13"
    assert snapshot.model_version == "world-model-v12"


def test_shadow_fixture_is_labelled_as_observation_only():
    records = lab.shadow_calibration_records()
    assert records
    assert all(item.record_id.startswith("cal-") for item in records)
    assert all(item.model_version == "world-model-v12" for item in records)


def test_demo_summary_has_no_production_side_effect():
    summary = lab.demo_summary(samples=50)
    assert summary["blocked_without_approval"] is True
    assert summary["execution_envelope_created"].startswith("exec-")
    assert summary["production_side_effects"] == 0
    assert "does not establish production safety" in summary["message"]
