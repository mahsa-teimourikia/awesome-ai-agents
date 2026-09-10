"""Advanced Course 04 invariants for an application-owned architecture control plane."""

from __future__ import annotations

from datetime import timedelta
import importlib.util
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "advanced"
    / "04-hybrid-production-architecture"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course04_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course04_lab", COURSE_DIR / "lab.py")
adapter = _load("course04_adapters", COURSE_DIR / "framework_adapters.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _contract(name: str):
    context = lab.build_context(f"contract-{name}")
    classification = policy.propose_classification(lab.REQUESTS[name], context)
    decision = policy.decide_architecture(context, classification)
    return context, classification, policy.build_execution_contract(
        context, classification, decision
    )


def _result_for(name: str, **run_options):
    return lab.run_control_plane(
        lab.REQUESTS[name], lab.build_context(f"run-{name}"), **run_options
    )


def _valid_rollback_run(*, context=None):
    context = context or lab.build_context("run-rollback-approved")
    classification = policy.propose_classification(lab.REQUESTS["rollback"], context)
    decision = policy.decide_architecture(context, classification)
    contract = policy.build_execution_contract(context, classification, decision)
    receipt = lab.build_rollback_approval(contract)
    return lab.run_control_plane(
        lab.REQUESTS["rollback"], context, approval_receipt=receipt
    )


def _evidence_registry(contract):
    return policy.AcceptedEvidenceRegistry(
        request_id=contract.request_id, tenant_id=contract.tenant_id
    )


def test_models_forbid_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        lab.build_context("x").model_copy(update={"hidden_authority": True}).model_validate(
            {**lab.build_context("x").model_dump(), "hidden_authority": True}
        )


def test_request_context_is_immutable():
    context = lab.build_context("immutable")
    with pytest.raises(ValidationError, match="frozen"):
        context.tenant_id = "other"


@pytest.mark.parametrize(
    ("name", "architecture"),
    [
        ("status", policy.ArchitectureType.DIRECT_FUNCTION),
        ("password", policy.ArchitectureType.DETERMINISTIC_WORKFLOW),
        ("diagnosis", policy.ArchitectureType.BOUNDED_SINGLE_AGENT),
        ("pipeline", policy.ArchitectureType.PIPELINE),
        ("team", policy.ArchitectureType.SELECTOR_TEAM),
        ("rollback", policy.ArchitectureType.DETERMINISTIC_WORKFLOW),
    ],
)
def test_northstar_requests_route_to_expected_architecture(name, architecture):
    run = _result_for(name)
    assert run.decision.architecture is architecture


def test_unknown_destructive_request_is_high_risk_and_unprivileged():
    run = _result_for("unknown_destructive")
    assert run.classification.risk_tier is policy.RiskTier.HIGH_RISK_UNKNOWN
    assert run.classification.ambiguity is policy.ClassificationConfidence.UNKNOWN
    assert run.decision.architecture is policy.ArchitectureType.HUMAN_ESCALATION
    assert run.decision.allowed_capabilities == ()


def test_high_risk_rule_overrides_low_risk_classifier_proposal():
    context = lab.build_context("risk-override")
    proposal = policy.propose_classification(lab.REQUESTS["status"], context).model_copy(
        update={"intent": policy.Intent.PRODUCTION_ROLLBACK}
    )
    validated = policy.validate_classification(
        lab.REQUESTS["rollback"], context, proposal
    )
    assert validated.risk_tier is policy.RiskTier.HIGH
    assert validated.requires_human_approval


def test_classifier_cannot_change_known_intent():
    context = lab.build_context("intent-conflict")
    proposal = policy.propose_classification(lab.REQUESTS["diagnosis"], context)
    with pytest.raises(policy.PolicyError, match="CLASSIFIER_INTENT_CONFLICT"):
        policy.validate_classification(lab.REQUESTS["status"], context, proposal)


def test_classifier_cannot_downgrade_data_sensitivity():
    context = lab.build_context(
        "data-downgrade", data_classification=policy.DataClassification.RESTRICTED
    )
    proposal = policy.propose_classification(lab.REQUESTS["status"], context).model_copy(
        update={"data_sensitivity": policy.DataClassification.INTERNAL}
    )
    with pytest.raises(policy.PolicyError, match="CLASSIFIER_DATA_DOWNGRADE"):
        policy.validate_classification(lab.REQUESTS["status"], context, proposal)


def test_missing_minimum_capabilities_are_denied_during_admission():
    allowed = (policy.Capability.CHECKOUT_HEALTH_READ,)
    context = lab.build_context("attenuate", allowed_capabilities=allowed)
    classification = policy.propose_classification(lab.REQUESTS["diagnosis"], context)
    with pytest.raises(policy.PolicyError, match="AUTH_DENIED"):
        policy.decide_architecture(context, classification)


def test_impossible_contract_is_rejected_before_runner_invocation(monkeypatch):
    called = False

    def unexpected_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("runner must not be invoked")

    monkeypatch.setattr(lab.ArchitectureRegistry, "run", unexpected_run)
    context = lab.build_context(
        "early-denial",
        allowed_capabilities=(policy.Capability.CHECKOUT_HEALTH_READ,),
    )
    with pytest.raises(policy.PolicyError, match="AUTH_DENIED"):
        lab.run_control_plane(lab.REQUESTS["diagnosis"], context)
    assert not called


def test_execution_contract_preserves_authenticated_principal():
    context, _, contract = _contract("password")
    assert contract.user_id == context.user_id
    assert contract.roles == context.roles


def test_contract_rejects_capability_widening():
    context, classification, contract = _contract("status")
    decision = policy.decide_architecture(context, classification).model_copy(
        update={"allowed_capabilities": (policy.Capability.PRODUCTION_ROLLBACK,)}
    )
    narrowed_context = context.model_copy(
        update={"allowed_capabilities": (policy.Capability.CHECKOUT_HEALTH_READ,)}
    )
    with pytest.raises(policy.PolicyError, match="ARCHITECTURE_CAPABILITY_WIDENING"):
        policy.build_execution_contract(narrowed_context, classification, decision)


def test_cross_tenant_evidence_access_is_denied():
    context = lab.build_context("tenant", tenant_id="other-tenant")
    run = lab.run_control_plane(lab.REQUESTS["status"], context)
    assert run.result.failure_code is policy.FailureCode.AUTH_DENIED
    assert run.result.tool_calls == 0


def test_password_reset_waits_after_sending_otp():
    run = _result_for("password")
    assert run.result.status is policy.ExecutionStatus.WAITING
    assert run.result.output["workflow_state"] == "WAITING_FOR_OTP"


def test_password_reset_rejects_invalid_otp():
    run = _result_for("password", supplied_otp="000000")
    assert run.result.status is policy.ExecutionStatus.BLOCKED
    assert run.result.output["workflow_state"] == "INVALID_OTP"


def test_password_reset_accepts_fixture_otp():
    run = _result_for("password", supplied_otp=lab.FIXTURE_OTP)
    assert run.result.status is policy.ExecutionStatus.SUCCEEDED
    assert run.result.output["workflow_state"] == "COMPLETED"


def test_password_reset_subject_mismatch_is_denied():
    run = _result_for("password", subject_user_id="user-b")
    assert run.contract.user_id == "user-1042"
    assert run.result.failure_code is policy.FailureCode.AUTH_DENIED
    assert "SUBJECT_MISMATCH" in run.result.policy_events


def test_restricted_password_context_is_not_downgraded():
    context = lab.build_context(
        "restricted-password", data_classification=policy.DataClassification.RESTRICTED
    )
    run = lab.run_control_plane(lab.REQUESTS["password"], context)
    assert run.classification.data_sensitivity is policy.DataClassification.RESTRICTED
    assert run.result.status is policy.ExecutionStatus.WAITING


def test_password_reset_expired_otp_never_authorizes_update():
    _, _, contract = _contract("password")
    state = lab.begin_password_reset(contract)
    status = lab.submit_otp(
        state,
        lab.FIXTURE_OTP,
        attempt_id="attempt-1",
        now=state.otp_expires_at + timedelta(seconds=1),
    )
    assert status is policy.PasswordResetStatus.EXPIRED_OTP
    assert not state.update_authorized
    assert state.password_update_count == 0


def test_password_reset_stops_after_max_attempts():
    context = lab.build_context("max-attempts")
    classification = policy.propose_classification(lab.REQUESTS["password"], context)
    decision = policy.decide_architecture(context, classification)
    contract = policy.build_execution_contract(context, classification, decision)
    state = lab.begin_password_reset(contract, max_attempts=2)
    lab.submit_otp(state, "bad", attempt_id="attempt-1")
    assert lab.submit_otp(state, "bad", attempt_id="attempt-2") is policy.PasswordResetStatus.MAX_ATTEMPTS
    with pytest.raises(ValueError, match="OTP_NOT_EXPECTED"):
        lab.submit_otp(state, lab.FIXTURE_OTP, attempt_id="attempt-3")


def test_password_reset_rejects_duplicate_attempt_id():
    context = lab.build_context("duplicate")
    classification = policy.propose_classification(lab.REQUESTS["password"], context)
    contract = policy.build_execution_contract(
        context, classification, policy.decide_architecture(context, classification)
    )
    state = lab.begin_password_reset(contract)
    lab.submit_otp(state, "bad", attempt_id="attempt-1")
    with pytest.raises(ValueError, match="DUPLICATE_ATTEMPT"):
        lab.submit_otp(state, "bad", attempt_id="attempt-1")


def test_password_update_requires_verified_identity():
    _, _, contract = _contract("password")
    state = lab.begin_password_reset(contract)
    with pytest.raises(ValueError, match="IDENTITY_NOT_VERIFIED"):
        lab.authorize_password_update(state)


def test_password_update_has_stable_logical_idempotency():
    context = lab.build_context("idempotent")
    classification = policy.propose_classification(lab.REQUESTS["password"], context)
    contract = policy.build_execution_contract(
        context, classification, policy.decide_architecture(context, classification)
    )
    state = lab.begin_password_reset(contract)
    lab.submit_otp(state, lab.FIXTURE_OTP, attempt_id="attempt-1")
    lab.authorize_password_update(state)
    assert lab.execute_password_update(state)
    assert not lab.execute_password_update(state)
    assert state.password_update_count == 1


def test_distinct_password_reset_requests_get_distinct_logical_ids():
    first_context = lab.build_context("reset-operation-1")
    second_context = lab.build_context("reset-operation-2")
    first_classification = policy.propose_classification(
        lab.REQUESTS["password"], first_context
    )
    second_classification = policy.propose_classification(
        lab.REQUESTS["password"], second_context
    )
    first_contract = policy.build_execution_contract(
        first_context,
        first_classification,
        policy.decide_architecture(first_context, first_classification),
    )
    second_contract = policy.build_execution_contract(
        second_context,
        second_classification,
        policy.decide_architecture(second_context, second_classification),
    )
    first = lab.begin_password_reset(first_contract)
    first_retry = lab.begin_password_reset(first_contract)
    second = lab.begin_password_reset(second_contract)
    assert first.logical_operation_id == first_retry.logical_operation_id
    assert first.logical_operation_id != second.logical_operation_id


def test_password_reset_restart_preserves_attempts_and_expiry(tmp_path):
    context = lab.build_context("restart")
    classification = policy.propose_classification(lab.REQUESTS["password"], context)
    contract = policy.build_execution_contract(
        context, classification, policy.decide_architecture(context, classification)
    )
    state = lab.begin_password_reset(contract)
    lab.submit_otp(state, "bad", attempt_id="attempt-1")
    path = tmp_path / "password-state.json"
    lab.save_password_state(state, path)
    restored = lab.load_password_state(path)
    assert restored.attempt_count == 1
    assert restored.attempt_ids == ("attempt-1",)
    assert restored.otp_expires_at == state.otp_expires_at


def test_password_reset_cancellation_precedes_next_step():
    context = lab.build_context("cancel-password")
    classification = policy.propose_classification(lab.REQUESTS["password"], context)
    contract = policy.build_execution_contract(
        context, classification, policy.decide_architecture(context, classification)
    )
    state = lab.begin_password_reset(contract)
    lab.cancel_password_reset(state)
    with pytest.raises(ValueError, match="CANCELLED"):
        lab.submit_otp(state, lab.FIXTURE_OTP, attempt_id="attempt-1")
    assert state.password_update_count == 0


def test_rollback_requires_capability():
    context = lab.build_context("rollback-denied", allowed_capabilities=())
    with pytest.raises(policy.PolicyError, match="AUTH_DENIED"):
        lab.run_control_plane(lab.REQUESTS["rollback"], context)


def test_valid_rollback_plan_does_not_authorize_execution():
    run = _result_for("rollback")
    assert run.decision.approval_required
    assert run.contract.approval_required
    assert run.result.status is policy.ExecutionStatus.BLOCKED
    assert run.result.failure_code is policy.FailureCode.POLICY_BLOCKED


def test_rollback_with_validated_approval_may_execute():
    run = _valid_rollback_run()
    assert run.result.status is policy.ExecutionStatus.SUCCEEDED
    assert "APPROVAL_VALIDATED" in run.result.policy_events
    assert run.result.privileged_capability_exposure == 1


@pytest.mark.parametrize(
    ("updates", "event"),
    [
        ({"target": "deploy-1841"}, "APPROVAL_TARGET_MISMATCH"),
        ({"tenant_id": "other-tenant"}, "APPROVAL_TENANT_MISMATCH"),
        (
            {
                "issued_at": lab.FIXED_TIME - timedelta(minutes=10),
                "expires_at": lab.FIXED_TIME - timedelta(seconds=1),
            },
            "APPROVAL_EXPIRED",
        ),
        ({"policy_version": "stale-policy"}, "APPROVAL_POLICY_STALE"),
    ],
)
def test_rollback_rejects_mismatched_approval_receipt(updates, event):
    context, _, contract = _contract("rollback")
    receipt = lab.build_rollback_approval(contract).model_copy(update=updates)
    run = lab.run_control_plane(
        lab.REQUESTS["rollback"], context, approval_receipt=receipt
    )
    assert run.result.status is policy.ExecutionStatus.BLOCKED
    assert event in run.result.policy_events
    assert run.result.tool_calls == 0


def test_rollback_rejects_changed_proposal_digest():
    context, _, contract = _contract("rollback")
    receipt = lab.build_rollback_approval(contract).model_copy(
        update={"proposal_digest": "0" * 64}
    )
    run = lab.run_control_plane(
        lab.REQUESTS["rollback"], context, approval_receipt=receipt
    )
    assert "APPROVAL_PROPOSAL_MISMATCH" in run.result.policy_events
    assert run.result.tool_calls == 0


def test_pipeline_uses_an_independent_review_and_deterministic_gate():
    run = _result_for("pipeline")
    assert run.result.output["security_review"] == "PASS_WITH_APPROVAL_REQUIRED"
    assert run.result.output["deterministic_gate_state"] == "PROPOSAL_REVIEWED"
    assert "DETERMINISTIC_GATE_PASSED" in run.result.policy_events


def test_agent_is_read_only_and_bounded():
    run = _result_for("diagnosis")
    assert run.result.status is policy.ExecutionStatus.SUCCEEDED
    assert run.result.model_calls <= run.contract.max_model_calls
    assert run.result.tool_calls <= run.contract.max_tool_calls
    assert policy.Capability.PRODUCTION_ROLLBACK not in run.contract.allowed_capabilities


def test_worker_can_request_but_not_apply_architecture_upgrade():
    context, _, contract = _contract("diagnosis")
    result = lab.ArchitectureRegistry().run(
        contract, policy.ExecutionRequest(text="I need a team")
    )
    assert result.output["event"] == "ARCHITECTURE_ESCALATION_REQUEST"
    assert result.architecture is policy.ArchitectureType.BOUNDED_SINGLE_AGENT


def test_agent_to_team_transition_is_separately_readmitted():
    transition, decision = lab.build_agent_to_team_escalation(
        lab.build_context("transition")
    )
    assert transition.transitions == 1
    assert transition.current is policy.ArchitectureType.SELECTOR_TEAM
    assert decision.architecture is policy.ArchitectureType.SELECTOR_TEAM


def test_direct_function_cannot_self_escalate_to_team():
    context = lab.build_context("bad-transition")
    original = policy.propose_classification(lab.REQUESTS["status"], context)
    state = policy.ArchitectureTransitionState(
        request_id=context.request_id,
        original_request_text=lab.REQUESTS["status"],
        original_classification=original,
        current=policy.ArchitectureType.DIRECT_FUNCTION,
    )
    escalation = policy.ArchitectureEscalationRequest(
        request_id=context.request_id,
        proposed_architecture=policy.ArchitectureType.SELECTOR_TEAM,
        reason_code=policy.ReasonCode.DYNAMIC_RECOVERY_REQUIRED,
        evidence_gap="customer-impact",
    )
    with pytest.raises(policy.PolicyError, match="ARCHITECTURE_TRANSITION_DENIED"):
        policy.admit_architecture_transition(state, escalation, context=context)


def test_transition_budget_prevents_repeated_upgrade():
    context = lab.build_context("transition-budget")
    original = policy.propose_classification(lab.REQUESTS["diagnosis"], context)
    state = policy.ArchitectureTransitionState(
        request_id=context.request_id,
        original_request_text=lab.REQUESTS["diagnosis"],
        original_classification=original,
        current=policy.ArchitectureType.BOUNDED_SINGLE_AGENT,
        transitions=1,
    )
    escalation = policy.ArchitectureEscalationRequest(
        request_id=context.request_id,
        proposed_architecture=policy.ArchitectureType.SELECTOR_TEAM,
        reason_code=policy.ReasonCode.DYNAMIC_RECOVERY_REQUIRED,
        evidence_gap="customer-impact",
    )
    with pytest.raises(policy.PolicyError, match="ARCHITECTURE_TRANSITION_BUDGET_EXCEEDED"):
        policy.admit_architecture_transition(
            state,
            escalation,
            context=context,
        )


def test_transition_revalidates_the_original_request():
    context = lab.build_context("original-request")
    diagnosis = policy.propose_classification(lab.REQUESTS["diagnosis"], context)
    state = policy.ArchitectureTransitionState(
        request_id=context.request_id,
        original_request_text=lab.REQUESTS["status"],
        original_classification=diagnosis,
        current=policy.ArchitectureType.BOUNDED_SINGLE_AGENT,
    )
    escalation = policy.ArchitectureEscalationRequest(
        request_id=context.request_id,
        proposed_architecture=policy.ArchitectureType.SELECTOR_TEAM,
        reason_code=policy.ReasonCode.DYNAMIC_RECOVERY_REQUIRED,
        evidence_gap="customer-impact",
    )
    with pytest.raises(policy.PolicyError, match="CLASSIFIER_INTENT_CONFLICT"):
        policy.admit_architecture_transition(state, escalation, context=context)


@pytest.mark.parametrize("gap", ["missing-otp", "unauthorized-rollback"])
def test_transition_rejects_gap_the_target_architecture_cannot_address(gap):
    context = lab.build_context(f"invalid-gap-{gap}")
    original = policy.propose_classification(lab.REQUESTS["diagnosis"], context)
    state = policy.ArchitectureTransitionState(
        request_id=context.request_id,
        original_request_text=lab.REQUESTS["diagnosis"],
        original_classification=original,
        current=policy.ArchitectureType.BOUNDED_SINGLE_AGENT,
    )
    escalation = policy.ArchitectureEscalationRequest(
        request_id=context.request_id,
        proposed_architecture=policy.ArchitectureType.SELECTOR_TEAM,
        reason_code=policy.ReasonCode.DYNAMIC_RECOVERY_REQUIRED,
        evidence_gap=gap,
    )
    with pytest.raises(policy.PolicyError, match="EVIDENCE_GAP_NOT_ADDRESSABLE"):
        policy.admit_architecture_transition(state, escalation, context=context)


@pytest.mark.parametrize("available", ["classifier", "router"])
def test_control_plane_failure_falls_back_to_human_without_calls(available):
    options = {f"{available}_available": False}
    run = lab.run_control_plane(
        lab.REQUESTS["diagnosis"], lab.build_context(f"down-{available}"), **options
    )
    assert run.decision.architecture is policy.ArchitectureType.HUMAN_ESCALATION
    assert run.result.model_calls == 0
    assert run.result.tool_calls == 0


def test_model_outage_does_not_break_direct_or_workflow_routes():
    direct = _result_for("status", model_available=False)
    workflow = _result_for("password", model_available=False)
    assert direct.result.status is policy.ExecutionStatus.SUCCEEDED
    assert workflow.result.status is policy.ExecutionStatus.WAITING


@pytest.mark.parametrize("name", ["diagnosis", "pipeline", "team"])
def test_model_outage_escalates_model_driven_routes(name):
    run = _result_for(name, model_available=False)
    assert run.result.status is policy.ExecutionStatus.ESCALATED
    assert run.result.failure_code is policy.FailureCode.MODEL_UNAVAILABLE
    assert run.result.model_calls == 0


def test_dependency_outage_is_explicit_and_does_not_guess():
    run = _result_for("status", dependencies_available=False)
    assert run.result.status is policy.ExecutionStatus.DEGRADED
    assert run.result.failure_code is policy.FailureCode.DEPENDENCY_UNAVAILABLE
    assert "not guessed" in run.result.output["message"]


@pytest.mark.parametrize("name", ["password", "rollback"])
def test_workflow_dependency_outage_attempts_no_write(name):
    run = _result_for(
        name,
        dependencies_available=False,
    )
    assert run.result.status is policy.ExecutionStatus.DEGRADED
    assert run.result.failure_code is policy.FailureCode.DEPENDENCY_UNAVAILABLE
    assert run.result.tool_calls == 0
    assert "WRITE_NOT_ATTEMPTED" in run.result.policy_events


@pytest.mark.parametrize("name", ["diagnosis", "team"])
def test_agentic_dependency_outage_is_explicit(name):
    run = _result_for(name, dependencies_available=False)
    assert run.result.status is policy.ExecutionStatus.DEGRADED
    assert run.result.failure_code is policy.FailureCode.DEPENDENCY_UNAVAILABLE


@pytest.mark.parametrize("name", ["status", "password", "diagnosis", "pipeline", "team", "rollback"])
def test_cancellation_stops_next_runner_call(name):
    run = _result_for(name, cancelled=True)
    assert run.result.status is policy.ExecutionStatus.CANCELLED
    assert run.result.model_calls == 0
    assert run.result.tool_calls == 0


def test_result_gateway_rejects_model_call_budget_overrun():
    _, _, contract = _contract("diagnosis")
    accepted = _evidence_registry(contract)
    candidate = lab.BoundedAgentRunner().run(
        contract,
        policy.ExecutionRequest(text=lab.REQUESTS["diagnosis"]),
        accepted,
    ).model_copy(update={"model_calls": contract.max_model_calls + 1})
    with pytest.raises(policy.PolicyError, match="MODEL_CALL_BUDGET_EXCEEDED"):
        policy.validate_execution_result(candidate, contract, accepted_evidence=accepted)


def test_result_gateway_rejects_missing_evidence():
    _, _, contract = _contract("status")
    accepted = _evidence_registry(contract)
    candidate = lab.DirectFunctionRunner().run(
        contract,
        policy.ExecutionRequest(text=lab.REQUESTS["status"]),
        accepted,
    ).model_copy(update={"evidence_ids": ()})
    with pytest.raises(policy.PolicyError, match="INSUFFICIENT_EVIDENCE"):
        policy.validate_execution_result(candidate, contract, accepted_evidence=accepted)


def test_fake_evidence_id_strings_are_not_authoritative():
    _, _, contract = _contract("diagnosis")
    accepted = _evidence_registry(contract)
    candidate = lab._result(
        contract,
        status=policy.ExecutionStatus.SUCCEEDED,
        output={"hypothesis": "unsupported"},
        evidence_ids=contract.required_evidence,
    )
    with pytest.raises(policy.PolicyError, match="INVALID_EVIDENCE"):
        policy.validate_execution_result(candidate, contract, accepted_evidence=accepted)


def test_result_gateway_rejects_cross_tenant_output():
    _, _, contract = _contract("status")
    accepted = _evidence_registry(contract)
    candidate = lab.DirectFunctionRunner().run(
        contract,
        policy.ExecutionRequest(text=lab.REQUESTS["status"]),
        accepted,
    ).model_copy(update={"tenant_id": "other"})
    with pytest.raises(policy.PolicyError, match="RESULT_TENANT_MISMATCH"):
        policy.validate_execution_result(candidate, contract, accepted_evidence=accepted)


def test_output_size_is_a_limit_not_an_exfiltration_proof():
    _, _, contract = _contract("status")
    accepted = _evidence_registry(contract)
    candidate = lab.DirectFunctionRunner().run(
        contract,
        policy.ExecutionRequest(text=lab.REQUESTS["status"]),
        accepted,
    ).model_copy(update={"output": {"text": "x" * 500}})
    with pytest.raises(policy.PolicyError, match="OUTPUT_SIZE_LIMIT"):
        policy.validate_execution_result(
            candidate,
            contract,
            accepted_evidence=accepted,
            max_output_chars=100,
        )


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (policy.PIIAction.ALLOW, "person@example.com"),
        (policy.PIIAction.MASK, "[MASKED]"),
        (policy.PIIAction.REDACT, "[REDACTED]"),
    ],
)
def test_pii_policy_has_explicit_non_blocking_actions(action, expected):
    assert expected in policy.apply_pii_policy("owner: person@example.com", action)


def test_pii_policy_can_block():
    with pytest.raises(policy.PolicyError, match="PII_BLOCKED"):
        policy.apply_pii_policy("owner: person@example.com", policy.PIIAction.BLOCK)


def test_structured_pii_redaction_preserves_output_shape():
    protected = policy.apply_structured_pii_policy(
        {
            "owner": "person@example.com",
            "nested": {"contacts": ["safe", "other@example.com"]},
        },
        policy.PIIAction.REDACT,
    )
    assert set(protected) == {"owner", "nested"}
    assert protected["owner"] == "[REDACTED]"
    assert protected["nested"]["contacts"] == ["safe", "[REDACTED]"]


def test_parallel_team_tracks_total_work_separately_from_wall_clock():
    run = _result_for("team")
    assert run.result.total_work_ms == 290
    assert run.result.wall_clock_ms == 150
    assert run.result.total_work_ms > run.result.wall_clock_ms


def test_same_workload_fixture_has_comparable_fields():
    rows = lab.same_workload_benchmark()
    assert len(rows) == 4
    assert {row.architecture for row in rows} >= {
        policy.ArchitectureType.DIRECT_FUNCTION,
        policy.ArchitectureType.BOUNDED_SINGLE_AGENT,
        policy.ArchitectureType.SELECTOR_TEAM,
    }
    assert all(row.cost_per_successful_compliant_request is not None for row in rows)


def test_routing_eval_perfect_fixture_has_no_weighted_loss():
    metrics = lab.evaluate_routing()
    assert metrics.intent_accuracy == 1
    assert metrics.risk_accuracy == 1
    assert metrics.high_risk_false_negative_rate == 0
    assert metrics.architecture_validity_rate == 1
    assert metrics.weighted_routing_loss == 0


def test_routing_eval_weights_high_risk_false_negative():
    metrics = lab.evaluate_routing(
        forced_architectures={"rollback": policy.ArchitectureType.BOUNDED_SINGLE_AGENT},
        forced_risks={"rollback": policy.RiskTier.LOW},
    )
    assert metrics.high_risk_false_negative_rate > 0
    assert metrics.architecture_validity_rate < 1
    assert metrics.weighted_routing_loss > 0


def test_valid_architecture_is_not_necessarily_optimal():
    status_case = lab.labelled_requests()[0]
    assert policy.ArchitectureType.BOUNDED_SINGLE_AGENT in status_case.valid_architectures
    regret = lab.architecture_regret(
        policy.ArchitectureType.BOUNDED_SINGLE_AGENT,
        status_case.best_compliant_architecture,
    )
    assert regret["extra_cost_usd"] > 0
    assert regret["extra_complexity"] > 0


def test_every_architecture_has_a_profile_and_missing_profile_is_not_zero_regret():
    assert set(lab.ARCHITECTURE_PROFILES) == set(policy.ArchitectureType)
    with pytest.raises(ValueError, match="ARCHITECTURE_PROFILE_MISSING"):
        lab.architecture_regret(
            policy.ArchitectureType.SELECTOR_TEAM,
            policy.ArchitectureType.DIRECT_FUNCTION,
            profiles={},
        )
    with pytest.raises(ValueError, match="ARCHITECTURE_PROFILE_MISSING"):
        lab.architecture_regret(
            policy.ArchitectureType.DIRECT_FUNCTION,
            policy.ArchitectureType.DIRECT_FUNCTION,
            profiles={},
        )


def test_regression_gate_rejects_safety_or_success_regression():
    baseline = lab.RouterCandidateMetrics(
        success_rate=0.95,
        high_risk_violation_rate=0,
        mean_cost_usd=0.02,
        mean_latency_ms=200,
        complexity_score=5,
    )
    unsafe = baseline.model_copy(update={"high_risk_violation_rate": 0.01})
    weaker = baseline.model_copy(update={"success_rate": 0.90})
    assert lab.architecture_regression_gate(baseline, unsafe) == "REJECT_CANDIDATE"
    assert lab.architecture_regression_gate(baseline, weaker) == "REJECT_CANDIDATE"


def test_regression_gate_requires_efficiency_to_justify_complexity():
    baseline = lab.RouterCandidateMetrics(
        success_rate=0.95,
        high_risk_violation_rate=0,
        mean_cost_usd=0.02,
        mean_latency_ms=200,
        complexity_score=5,
    )
    complex_only = baseline.model_copy(update={"complexity_score": 8})
    efficient = complex_only.model_copy(update={"mean_latency_ms": 150})
    assert lab.architecture_regression_gate(baseline, complex_only) == "REJECT_CANDIDATE"
    assert lab.architecture_regression_gate(baseline, efficient) == "ACCEPT_CANDIDATE"


def test_shadow_routing_does_not_execute():
    decision = lab.shadow_route(lab.REQUESTS["rollback"], lab.build_context("shadow"))
    assert decision.approval_required
    assert decision.architecture is policy.ArchitectureType.DETERMINISTIC_WORKFLOW


def test_canary_is_limited_to_low_risk_side_effect_free_requests():
    context = lab.build_context("canary")
    status = policy.propose_classification(lab.REQUESTS["status"], context)
    rollback = policy.propose_classification(lab.REQUESTS["rollback"], context)
    assert lab.low_risk_canary_eligible(status)
    assert not lab.low_risk_canary_eligible(rollback)


def test_restricted_multi_domain_data_routes_to_human():
    context = lab.build_context(
        "restricted", data_classification=policy.DataClassification.RESTRICTED
    )
    run = lab.run_control_plane(lab.REQUESTS["team"], context)
    assert run.decision.architecture is policy.ArchitectureType.HUMAN_ESCALATION
    assert run.decision.allowed_capabilities == ()


def test_sync_and_async_modes_are_explicit():
    assert _result_for("status").contract.execution_mode is policy.ExecutionMode.SYNC
    assert _result_for("team").contract.execution_mode is policy.ExecutionMode.ASYNC


def test_audit_records_policy_classifier_and_router_versions():
    run = _result_for("diagnosis")
    assert run.audit.decision.policy_version == policy.POLICY_VERSION
    assert run.audit.decision.classifier_version == policy.CLASSIFIER_VERSION
    assert run.audit.decision.router_version == policy.ROUTER_VERSION


def test_audit_minimizes_request_content():
    run = _result_for("diagnosis")
    assert not hasattr(run.audit, "request_text")
    assert run.audit.request_reference == f"request:{run.audit.request_id}"
    assert len(run.audit.request_digest) == 64


def test_failure_taxonomy_is_stable_and_complete():
    assert {item.value for item in policy.FailureCode} == {
        "AUTH_DENIED",
        "POLICY_BLOCKED",
        "TIMEOUT",
        "DEPENDENCY_UNAVAILABLE",
        "INSUFFICIENT_EVIDENCE",
        "BUDGET_EXCEEDED",
        "CANCELLED",
        "MODEL_UNAVAILABLE",
    }


def test_optional_adapter_status_is_credential_free():
    status = adapter.adapter_status()
    assert not status["langgraph"]["credentials_required_to_instantiate"]
    assert not status["openai_agents"]["credentials_required_to_instantiate"]


@pytest.mark.skipif(
    importlib.util.find_spec("langgraph") is None,
    reason="optional frameworks extra not installed",
)
def test_langgraph_adapter_instantiates_without_credentials():
    _, _, contract = _contract("password")
    graph = adapter.build_langgraph_workflow_adapter(contract)
    assert graph.invoke(
        {"request_id": contract.request_id, "stage": "REQUESTED", "policy_events": []}
    )["stage"] == "WAITING_FOR_OTP"


@pytest.mark.skipif(
    importlib.util.find_spec("agents") is None,
    reason="optional frameworks extra not installed",
)
def test_openai_agents_adapter_instantiates_without_credentials():
    _, _, contract = _contract("diagnosis")
    agent = adapter.build_openai_agent_adapter(contract)
    assert agent.name == "Northstar bounded incident analyst"
