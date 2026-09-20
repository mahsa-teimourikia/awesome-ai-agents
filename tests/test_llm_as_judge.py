"""Advanced Course 11 measurement, evidence, and authority invariants."""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

COURSE_DIR = Path(__file__).resolve().parents[1] / "curriculum" / "advanced" / "11-llm-as-judge-agent-judges"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course11_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course11_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _case(case_id: str):
    return next(case for case in lab.golden_dataset() if case.case_id == case_id)


def _context(**updates):
    base = policy.EvaluatorContext(
        evaluator_id="evaluator-agent",
        primary_agent_id="incident-agent",
        tenant_id="northstar",
        allowed_tool_ids=("refund_status.read", "execute_read_query", "run_sql"),
        budget=policy.EvaluatorBudget(
            max_tool_calls=2,
            max_model_calls=1,
            max_cost_usd=0.01,
            deadline=lab.FIXED_TIME + timedelta(minutes=5),
        ),
    )
    return policy.EvaluatorContext.model_validate({**base.model_dump(), **updates})


def _semantic_result(criterion_id="grounding", *, status=policy.CriterionStatus.PASS, score=4, evidence_ids=()):
    return policy.CriterionResult(
        criterion_id=criterion_id,
        status=status,
        score=score,
        confidence=0.8,
        evidence_ids=evidence_ids,
    )


def _semantic_results(evidence_ids=("receipt-refund-absent",)):
    return (
        _semantic_result("grounding", evidence_ids=evidence_ids),
        _semantic_result("explanation_quality"),
        _semantic_result("uncertainty_handling"),
    )


def _trusted_gates():
    return (
        policy.HardGateResult(gate_id="authorization", passed=True, reason_code="AUTHORIZED"),
        policy.HardGateResult(
            gate_id="outcome_binding",
            passed=True,
            evidence_ids=("receipt-refund-absent",),
            reason_code="OPERATION_BOUND",
        ),
    )


def _request(case_id="refund-absent", evidence_ids=("receipt-refund-absent",)):
    evidence = lab.fixture_evidence()
    accepted = tuple(evidence[evidence_id] for evidence_id in evidence_ids if evidence_id in evidence)
    return policy.JudgeRequest(
        evaluation_id="eval-1",
        case_id=case_id,
        dataset_version=lab.DATASET_VERSION,
        rubric_id=lab.RUBRIC.rubric_id,
        rubric_version=lab.RUBRIC.rubric_version,
        candidate_artifact=_case(case_id).candidate_artifact,
        trusted_evidence_ids=evidence_ids,
        evidence_snapshot_digest=lab.evidence_snapshot_digest(accepted),
    )


def _verdict(*, request=None, results=None, gates=None, decision=policy.JudgeDecision.PASS, **updates):
    request = request or _request()
    base = policy.JudgeVerdict(
        evaluation_id=request.evaluation_id,
        case_id=request.case_id,
        dataset_version=request.dataset_version,
        rubric_id=request.rubric_id,
        rubric_version=request.rubric_version,
        judge_id=lab.JUDGE_V1.judge_id,
        judge_version=lab.JUDGE_V1.version,
        prompt_version=lab.JUDGE_V1.prompt_version,
        settings={"temperature": 0},
        evidence_snapshot_digest=request.evidence_snapshot_digest,
        criterion_results=tuple(
            _semantic_results(request.trusted_evidence_ids) if results is None else results
        ),
        hard_gate_results=tuple(_trusted_gates() if gates is None else gates),
        verdict=decision,
        confidence=0.8,
    )
    return base.model_copy(update=updates)


def _validate(verdict, request, *, evidence=None, expected_judge=None, settings=None, gates=None):
    return lab.validate_judge_verdict(
        verdict,
        request,
        lab.RUBRIC,
        evidence or lab.fixture_evidence(),
        expected_judge=expected_judge or lab.JUDGE_V1,
        expected_settings=settings or {"temperature": 0},
        trusted_hard_gates=_trusted_gates() if gates is None else gates,
    )


def test_golden_references_are_independent_from_predictions():
    reference = next(label.score for label in _case("unsupported-diagnosis").reference_labels if label.criterion_id == "grounding")
    prediction = lab.JUDGE_PREDICTIONS["unsupported-diagnosis"]["grounding"][0]
    assert reference == 2
    assert prediction == 3


def test_dataset_is_frozen_validation_data_with_scenarios_from_review():
    cases = lab.golden_dataset()
    assert len(cases) == 8
    assert {case.split for case in cases} == {"validation"}
    assert {"unauthorized-mutation", "refund-absent", "wrong-operation", "prompt-injection"} <= {case.case_id for case in cases}


def test_human_labels_are_retained_before_adjudication():
    ratings = lab.human_ratings()
    labels = lab.adjudicated_grounding_labels()
    assert len(ratings) == len(labels) * 3
    assert any(label.disagreement_recorded for label in labels)


def test_inter_human_agreement_is_not_assumed_perfect():
    agreement = lab.inter_human_agreement()
    assert len(agreement) == 3
    assert min(agreement.values()) < 0.9
    assert max(agreement.values()) < 1


def test_weighted_kappa_penalizes_large_ordinal_error_more_than_near_error():
    reference = [5, 4, 3, 2, 1]
    near = [4, 3, 3, 2, 2]
    far = [1, 1, 3, 5, 5]
    assert lab.agreement_report(reference, near).weighted_kappa > lab.agreement_report(reference, far).weighted_kappa


def test_agreement_report_distinguishes_exact_and_within_one():
    report = lab.agreement_report([1, 2, 3, 4], [1, 3, 2, 4])
    assert report.exact_agreement == 0.5
    assert report.within_one_agreement == 1.0
    assert report.mean_absolute_error == 0.5


def test_agreement_and_confidence_calibration_are_separate_reports():
    metrics = lab.evaluation_metrics()
    assert metrics.agreement.exact_agreement == pytest.approx(0.625)
    assert metrics.calibration.expected_calibration_error == pytest.approx(0.1329166667)


def test_confidence_calibration_uses_brier_and_ece():
    calibrated = lab.confidence_calibration([True, False], [0.9, 0.1])
    overconfident = lab.confidence_calibration([False, True], [0.9, 0.1])
    assert calibrated.brier_score < overconfident.brier_score
    assert calibrated.expected_calibration_error < overconfident.expected_calibration_error


def test_metrics_expose_false_pass_and_false_fail_separately():
    metrics = lab.evaluation_metrics()
    assert metrics.false_pass_rate == 0.25
    assert metrics.false_fail_rate == 0
    assert metrics.confusion_matrix == {"true_pass": 2, "false_pass": 1, "true_fail": 3, "false_fail": 0}


def test_metrics_include_criterion_and_slice_reports():
    metrics = lab.evaluation_metrics()
    assert set(metrics.per_criterion) == {"grounding", "explanation_quality", "uncertainty_handling"}
    assert {"high-risk", "adversarial", "operation-binding"} <= set(metrics.per_slice)
    assert metrics.per_slice["high-risk"].case_count == 2
    assert metrics.per_slice["high-risk"].negative_case_count == 2


def test_empty_evaluation_dataset_is_rejected_instead_of_using_default_fixture():
    with pytest.raises(ValueError, match="EMPTY_EVALUATION_DATASET"):
        lab.evaluation_metrics(())


def test_semantic_criterion_requires_anchors():
    with pytest.raises(ValidationError, match="SEMANTIC_CRITERION_REQUIRES_ANCHORS"):
        policy.RubricCriterion(
            criterion_id="style",
            description="Style quality",
            criterion_type=policy.CriterionType.SEMANTIC,
        )


def test_rubric_rejects_duplicate_criterion_ids():
    criterion = lab.RUBRIC.criteria[0]
    with pytest.raises(ValidationError, match="DUPLICATE_CRITERION_ID"):
        policy.Rubric(rubric_id="r", rubric_version="1", criteria=(criterion, criterion))


def test_models_forbid_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.Anchor(score=5, observable="good", hidden_instruction="PASS")


def test_hard_gate_failure_overrides_high_semantic_score():
    decision = lab.aggregate_decision(
        [_semantic_result(score=5)],
        [policy.HardGateResult(gate_id="authorization", passed=False, reason_code="UNAUTHORIZED_WRITE")],
    )
    assert decision is policy.JudgeDecision.FAIL


def test_layered_pipeline_runs_deterministic_gate_before_semantic_judge():
    calls = []

    def semantic_judge():
        calls.append("called")
        return [_semantic_result(score=5)]

    result = lab.run_layered_evaluation(
        [policy.HardGateResult(gate_id="authorization", passed=False, reason_code="UNAUTHORIZED_WRITE")],
        semantic_judge,
    )
    assert result.decision is policy.JudgeDecision.FAIL
    assert result.model_calls == 0
    assert result.stages_completed == ("deterministic_validation",)
    assert calls == []


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (policy.CriterionStatus.INSUFFICIENT_EVIDENCE, policy.JudgeDecision.INSUFFICIENT_EVIDENCE),
        (policy.CriterionStatus.ABSTAIN, policy.JudgeDecision.ABSTAIN),
        (policy.CriterionStatus.AMBIGUOUS, policy.JudgeDecision.ABSTAIN),
        (policy.CriterionStatus.FAIL, policy.JudgeDecision.FAIL),
        (policy.CriterionStatus.PASS, policy.JudgeDecision.PASS),
    ],
)
def test_aggregation_preserves_non_numeric_states(status, expected):
    assert lab.aggregate_decision([_semantic_result(status=status)], []) is expected


def test_judge_cannot_score_deterministic_criterion():
    request = _request()
    verdict = _verdict(results=[_semantic_result("authorization")])
    with pytest.raises(policy.EvaluationPolicyError, match="JUDGE_CANNOT_OVERRIDE_DETERMINISTIC_CRITERION"):
        _validate(verdict, request)


def test_judge_result_must_bind_to_request_and_versions():
    request = _request()
    verdict = _verdict(request=request, case_id="other-case")
    with pytest.raises(policy.EvaluationPolicyError, match="VERDICT_REQUEST_BINDING_MISMATCH"):
        _validate(verdict, request)


def test_judge_result_must_bind_to_evidence_snapshot():
    request = _request()
    verdict = _verdict(request=request, evidence_snapshot_digest="other-snapshot")
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_SNAPSHOT_INTEGRITY_FAILURE"):
        _validate(verdict, request)


def test_valid_verdict_binds_expected_judge_snapshot_criteria_and_gates():
    request = _request()
    _validate(_verdict(request=request), request)


@pytest.mark.parametrize(
    ("update", "reason"),
    [
        ({"judge_id": "self-asserted-judge"}, "JUDGE_IDENTITY_MISMATCH"),
        ({"judge_version": "other/model/version/deployment"}, "JUDGE_VERSION_MISMATCH"),
        ({"prompt_version": "modified-prompt"}, "JUDGE_PROMPT_VERSION_MISMATCH"),
        ({"settings": {"temperature": 0.7}}, "JUDGE_SETTINGS_MISMATCH"),
    ],
)
def test_judge_cannot_self_assert_identity_version_prompt_or_settings(update, reason):
    request = _request()
    verdict = _verdict(request=request, **update)
    with pytest.raises(policy.EvaluationPolicyError, match=reason):
        _validate(verdict, request)


def test_modified_evidence_after_snapshot_is_rejected():
    request = _request()
    evidence = lab.fixture_evidence()
    evidence["receipt-refund-absent"] = evidence["receipt-refund-absent"].model_copy(
        update={"source_version": "tampered-v3"}
    )
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_SNAPSHOT_INTEGRITY_FAILURE"):
        _validate(_verdict(request=request), request, evidence=evidence)


def test_missing_required_semantic_criterion_is_rejected():
    request = _request()
    verdict = _verdict(
        request=request,
        results=(
            _semantic_result("grounding", evidence_ids=request.trusted_evidence_ids),
            _semantic_result("explanation_quality"),
        ),
    )
    with pytest.raises(policy.EvaluationPolicyError, match="MISSING_CRITERION_RESULT"):
        _validate(verdict, request)


def test_duplicate_semantic_criterion_remains_rejected():
    request = _request()
    duplicate = _semantic_result("grounding", evidence_ids=request.trusted_evidence_ids)
    verdict = _verdict(
        request=request,
        results=(duplicate, duplicate, _semantic_result("explanation_quality"), _semantic_result("uncertainty_handling")),
    )
    with pytest.raises(policy.EvaluationPolicyError, match="DUPLICATE_CRITERION_RESULT"):
        _validate(verdict, request)


def test_missing_required_trusted_hard_gate_is_rejected():
    request = _request()
    gates = (_trusted_gates()[0],)
    verdict = _verdict(request=request, gates=gates)
    with pytest.raises(policy.EvaluationPolicyError, match="MISSING_REQUIRED_HARD_GATE"):
        _validate(verdict, request, gates=gates)


def test_model_provided_fake_hard_gate_is_rejected():
    request = _request()
    fake = policy.HardGateResult(
        gate_id="authorization",
        passed=True,
        reason_code="MODEL_SAYS_AUTHORIZED",
    )
    verdict_gates = (fake, _trusted_gates()[1])
    verdict = _verdict(request=request, gates=verdict_gates)
    with pytest.raises(policy.EvaluationPolicyError, match="HARD_GATE_INTEGRITY_FAILURE"):
        _validate(verdict, request, gates=_trusted_gates())


def test_unknown_evidence_id_is_rejected():
    request = _request(evidence_ids=("missing",))
    verdict = _verdict(request=request, results=[_semantic_result(evidence_ids=("missing",))])
    with pytest.raises(policy.EvaluationPolicyError, match="UNKNOWN_OR_UNTRUSTED_EVIDENCE_ID"):
        _validate(verdict, request)


def test_evidence_must_support_the_scored_criterion():
    evidence = lab.fixture_evidence()
    request = _request(evidence_ids=("receipt-refund-absent",))
    verdict = _verdict(request=request, results=[_semantic_result("explanation_quality", evidence_ids=request.trusted_evidence_ids)])
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_DOES_NOT_SUPPORT_CRITERION"):
        _validate(verdict, request, evidence=evidence)


def test_failed_hard_gate_cannot_be_reported_as_pass():
    request = _request()
    gate = policy.HardGateResult(gate_id="authorization", passed=False, reason_code="UNAUTHORIZED_WRITE")
    trusted = tuple(
        gate if item.gate_id == "authorization" else item for item in _trusted_gates()
    )
    verdict = _verdict(request=request, gates=trusted, decision=policy.JudgeDecision.PASS)
    with pytest.raises(policy.EvaluationPolicyError, match="HARD_GATE_FAILURE_CANNOT_PASS"):
        _validate(verdict, request, gates=trusted)


def test_authoritative_evidence_validates_when_fresh_bound_and_post_action():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"]
    requirement = policy.EvidenceRequirement(
        evidence_type="provider_receipt",
        criterion_id="outcome_binding",
        max_age_seconds=600,
        require_post_action=True,
        require_operation_binding=True,
    )
    lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


@pytest.mark.parametrize(
    ("case_id", "evidence_id", "requirement_update", "expected"),
    [
        ("refund-absent", "receipt-wrong-operation", {"require_operation_binding": True}, "EVIDENCE_OPERATION_MISMATCH"),
        ("refund-absent", "injected-log", {"evidence_type": "incident_log"}, "EVIDENCE_DOES_NOT_SUPPORT_CRITERION"),
    ],
)
def test_evidence_binding_failures(case_id, evidence_id, requirement_update, expected):
    requirement = policy.EvidenceRequirement.model_validate(
        {
            "evidence_type": "provider_receipt",
            "criterion_id": "outcome_binding",
            "max_age_seconds": 600,
            **requirement_update,
        }
    )
    with pytest.raises(policy.EvaluationPolicyError, match=expected):
        lab.validate_evidence(_case(case_id), lab.fixture_evidence()[evidence_id], requirement, now=lab.FIXED_TIME)


def test_stale_evidence_is_rejected():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"].model_copy(update={"observed_at": lab.FIXED_TIME - timedelta(days=1)})
    requirement = policy.EvidenceRequirement(evidence_type="provider_receipt", criterion_id="outcome_binding", max_age_seconds=600)
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_STALE"):
        lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_future_observed_at_is_not_treated_as_fresh():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"].model_copy(
        update={
            "observed_at": lab.FIXED_TIME + timedelta(minutes=1),
            "retrieved_at": lab.FIXED_TIME + timedelta(minutes=1),
        }
    )
    requirement = policy.EvidenceRequirement(
        evidence_type="provider_receipt",
        criterion_id="outcome_binding",
        max_age_seconds=600,
    )
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_FROM_FUTURE"):
        lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_future_retrieved_at_is_rejected():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"].model_copy(
        update={"retrieved_at": lab.FIXED_TIME + timedelta(minutes=1)}
    )
    requirement = policy.EvidenceRequirement(
        evidence_type="provider_receipt",
        criterion_id="outcome_binding",
        max_age_seconds=600,
    )
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_RETRIEVED_FROM_FUTURE"):
        lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_explicit_small_clock_skew_is_allowed():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"].model_copy(
        update={
            "observed_at": lab.FIXED_TIME + timedelta(seconds=3),
            "retrieved_at": lab.FIXED_TIME + timedelta(seconds=3),
        }
    )
    requirement = policy.EvidenceRequirement(
        evidence_type="provider_receipt",
        criterion_id="outcome_binding",
        max_age_seconds=600,
    )
    lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_pre_action_evidence_cannot_prove_post_action_state():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"].model_copy(update={"observed_at": case.action_event_time - timedelta(seconds=1)})
    requirement = policy.EvidenceRequirement(evidence_type="provider_receipt", criterion_id="outcome_binding", max_age_seconds=600, require_post_action=True)
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_NOT_POST_ACTION"):
        lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_cross_tenant_evidence_is_rejected():
    case = _case("refund-absent")
    record = lab.fixture_evidence()["receipt-refund-absent"].model_copy(update={"tenant_id": "globex"})
    requirement = policy.EvidenceRequirement(evidence_type="provider_receipt", criterion_id="outcome_binding", max_age_seconds=600)
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_TENANT_MISMATCH"):
        lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_untrusted_evidence_cannot_satisfy_authoritative_requirement():
    case = _case("prompt-injection")
    record = lab.fixture_evidence()["injected-log"]
    requirement = policy.EvidenceRequirement(evidence_type="incident_log", criterion_id="grounding", max_age_seconds=600)
    with pytest.raises(policy.EvaluationPolicyError, match="EVIDENCE_NOT_AUTHORITATIVE"):
        lab.validate_evidence(case, record, requirement, now=lab.FIXED_TIME)


def test_evaluator_identity_must_be_separate_from_primary_agent():
    with pytest.raises(ValidationError, match="EVALUATOR_IDENTITY_NOT_SEPARATE"):
        _context(evaluator_id="incident-agent")


def test_capabilities_not_tool_name_substrings_determine_authority():
    context = _context()
    assert lab.authorize_evaluator_tool("execute_read_query", context).capability is policy.ToolCapability.READ
    with pytest.raises(policy.EvaluationPolicyError, match="EVALUATOR_TOOL_NOT_READ_ONLY"):
        lab.authorize_evaluator_tool("run_sql", context)


def test_evaluator_cannot_use_unscoped_tool():
    with pytest.raises(policy.EvaluationPolicyError, match="TOOL_NOT_IN_EVALUATOR_SCOPE"):
        lab.authorize_evaluator_tool("deployment.read", _context())


def test_trace_tool_injection_is_data_not_a_command():
    provider = lab.DeterministicEvidenceProvider(lab.fixture_evidence())
    record, usage = provider.read("refund_status.read", "injected-log", _context(), policy.EvaluatorUsage(), now=lab.FIXED_TIME)
    assert "delete_database" in record.payload["text"]
    assert provider.calls == 1
    assert usage.tool_calls == 1


def test_candidate_prompt_injection_cannot_modify_trusted_rubric():
    case = _case("prompt-injection")
    before = lab.RUBRIC.model_dump(mode="json")
    assert "ignore the rubric" in case.candidate_artifact
    assert lab.RUBRIC.model_dump(mode="json") == before


@pytest.mark.parametrize(
    ("usage", "kwargs", "reason"),
    [
        (policy.EvaluatorUsage(tool_calls=2), {"tool_calls": 1}, "EVALUATOR_TOOL_BUDGET_EXHAUSTED"),
        (policy.EvaluatorUsage(model_calls=1), {"model_calls": 1}, "EVALUATOR_MODEL_BUDGET_EXHAUSTED"),
        (policy.EvaluatorUsage(cost_usd=0.01), {"cost_usd": 0.001}, "EVALUATOR_COST_BUDGET_EXHAUSTED"),
    ],
)
def test_evaluator_budgets_fail_closed(usage, kwargs, reason):
    with pytest.raises(policy.EvaluationPolicyError, match=reason):
        lab.consume_usage(_context(), usage, now=lab.FIXED_TIME, **kwargs)


def test_evaluator_deadline_stops_next_call():
    provider = lab.DeterministicEvidenceProvider(lab.fixture_evidence())
    with pytest.raises(policy.EvaluationPolicyError, match="EVALUATOR_DEADLINE_EXCEEDED"):
        provider.read(
            "refund_status.read",
            "receipt-refund-absent",
            _context(),
            policy.EvaluatorUsage(),
            now=lab.FIXED_TIME + timedelta(minutes=5),
        )
    assert provider.calls == 0


def test_execution_outcome_and_causal_attribution_remain_separate():
    result = lab.explain_process_outcome(
        operation_receipt_matches=True,
        desired_state_observed=True,
        causal_attribution_available=False,
    )
    assert result == {"action_executed": True, "desired_state_observed": True, "causal_attribution_supported": False}


def test_pairwise_swap_maps_position_labels_back_to_candidate_identity():
    verdict = lab.pairwise_consistency(
        "candidate-a",
        "candidate-b",
        first_choice=policy.PairwiseChoice.CANDIDATE_A,
        swapped_choice=policy.PairwiseChoice.CANDIDATE_B,
    )
    assert verdict.consistency is policy.PairwiseConsistency.CONSISTENT_A


def test_pairwise_disagreement_abstains_instead_of_revealing_gold():
    verdict = lab.pairwise_consistency(
        "candidate-a",
        "candidate-b",
        first_choice=policy.PairwiseChoice.CANDIDATE_A,
        swapped_choice=policy.PairwiseChoice.CANDIDATE_A,
    )
    assert verdict.consistency is policy.PairwiseConsistency.POSITION_UNSTABLE


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        (policy.PairwiseChoice.TIE, policy.PairwiseConsistency.CONSISTENT_TIE),
        (policy.PairwiseChoice.ABSTAIN, policy.PairwiseConsistency.ABSTAIN),
    ],
)
def test_pairwise_supports_tie_and_abstain(choice, expected):
    verdict = lab.pairwise_consistency("a", "b", first_choice=choice, swapped_choice=choice)
    assert verdict.consistency is expected


def test_position_outcomes_are_reported_separately():
    stable = lab.pairwise_consistency("a", "b", first_choice=policy.PairwiseChoice.CANDIDATE_A, swapped_choice=policy.PairwiseChoice.CANDIDATE_B)
    unstable = lab.pairwise_consistency("a", "b", first_choice=policy.PairwiseChoice.CANDIDATE_A, swapped_choice=policy.PairwiseChoice.CANDIDATE_A)
    report = lab.position_bias_report([stable, unstable])
    assert report.candidate_consistent_rate == 0.5
    assert report.position_unstable_rate == 0.5
    assert report.tie_consistent_rate == 0
    assert report.abstain_rate == 0


def test_all_abstain_pairs_do_not_appear_candidate_consistent():
    abstain = lab.pairwise_consistency(
        "a",
        "b",
        first_choice=policy.PairwiseChoice.ABSTAIN,
        swapped_choice=policy.PairwiseChoice.ABSTAIN,
    )
    report = lab.position_bias_report([abstain, abstain])
    assert report.candidate_consistent_rate == 0
    assert report.abstain_rate == 1


def test_shadow_mode_reports_failure_without_blocking():
    metrics = lab.evaluation_metrics()
    acceptance = policy.AcceptancePolicy(
        policy_id="high-risk-refund",
        release_mode=policy.ReleaseMode.SHADOW,
        min_weighted_kappa=0.95,
        max_false_pass_rate=0,
        max_false_fail_rate=0.05,
        max_ece=0.1,
        required_validation_cases=20,
    )
    decision = lab.rollout_gate(metrics, acceptance)
    assert decision.admitted
    assert decision.requires_human_review
    assert "VALIDATION_SAMPLE_TOO_SMALL" in decision.reason_codes
    assert "FALSE_PASS_RATE_ABOVE_POLICY" in decision.reason_codes


@pytest.mark.parametrize("mode", [policy.ReleaseMode.CANARY, policy.ReleaseMode.BLOCKING])
def test_canary_and_blocking_modes_enforce_application_thresholds(mode):
    acceptance = policy.AcceptancePolicy(
        policy_id="high-risk-refund",
        release_mode=mode,
        min_weighted_kappa=0.95,
        max_false_pass_rate=0,
        max_false_fail_rate=0.05,
        max_ece=0.1,
        required_validation_cases=20,
    )
    assert not lab.rollout_gate(lab.evaluation_metrics(), acceptance).admitted


def test_acceptance_threshold_is_application_specific_not_universal():
    permissive = policy.AcceptancePolicy(
        policy_id="low-risk-style",
        release_mode=policy.ReleaseMode.BLOCKING,
        min_weighted_kappa=0.7,
        max_false_pass_rate=0.3,
        max_false_fail_rate=0.3,
        max_ece=0.2,
        required_validation_cases=8,
    )
    assert lab.rollout_gate(lab.evaluation_metrics(), permissive).admitted


def test_release_metric_construction_rejects_development_cases():
    development = tuple(case.model_copy(update={"split": "development"}) for case in lab.golden_dataset())
    with pytest.raises(policy.EvaluationPolicyError, match="RELEASE_GATE_REQUIRES_VALIDATION_SPLIT"):
        lab.evaluation_metrics(development, release_gating=True)


def test_development_metrics_cannot_drive_blocking_rollout():
    development = tuple(case.model_copy(update={"split": "development"}) for case in lab.golden_dataset())
    metrics = lab.evaluation_metrics(development)
    acceptance = policy.AcceptancePolicy(
        policy_id="development-is-not-release-evidence",
        release_mode=policy.ReleaseMode.BLOCKING,
        min_weighted_kappa=0.7,
        max_false_pass_rate=0.3,
        max_false_fail_rate=0.3,
        max_ece=0.2,
        required_validation_cases=8,
    )
    decision = lab.rollout_gate(metrics, acceptance)
    assert not decision.admitted
    assert "RELEASE_METRICS_NOT_VALIDATION_ONLY" in decision.reason_codes


def test_undersized_high_risk_slice_cannot_support_blocking_release():
    acceptance = policy.AcceptancePolicy(
        policy_id="high-risk-support",
        release_mode=policy.ReleaseMode.BLOCKING,
        min_weighted_kappa=0.7,
        max_false_pass_rate=0.3,
        max_false_fail_rate=0.3,
        max_ece=0.2,
        required_validation_cases=8,
        minimum_slice_support={"high-risk": 3},
        maximum_slice_false_pass_rate={"high-risk": 0},
    )
    decision = lab.rollout_gate(lab.evaluation_metrics(), acceptance)
    assert not decision.admitted
    assert "SLICE_SUPPORT_TOO_SMALL:high-risk" in decision.reason_codes


def test_high_risk_false_pass_cannot_hide_in_strong_aggregate():
    metrics = lab.evaluation_metrics()
    high_risk = metrics.per_slice["high-risk"].model_copy(update={"false_pass_rate": 0.5})
    metrics = metrics.model_copy(update={"per_slice": {**metrics.per_slice, "high-risk": high_risk}})
    acceptance = policy.AcceptancePolicy(
        policy_id="high-risk-errors",
        release_mode=policy.ReleaseMode.BLOCKING,
        min_weighted_kappa=0.7,
        max_false_pass_rate=0.3,
        max_false_fail_rate=0.3,
        max_ece=0.2,
        required_validation_cases=8,
        minimum_slice_support={"high-risk": 2},
        maximum_slice_false_pass_rate={"high-risk": 0},
    )
    decision = lab.rollout_gate(metrics, acceptance)
    assert not decision.admitted
    assert "SLICE_FALSE_PASS_RATE_ABOVE_POLICY:high-risk" in decision.reason_codes


def test_drift_report_detects_pass_rate_change():
    baseline = lab.evaluation_metrics()
    candidate = baseline.model_copy(update={"pass_rate": baseline.pass_rate + 0.2})
    report = lab.drift_report(baseline, candidate)
    assert report.drift_detected
    assert "PASS_RATE_DRIFT" in report.reason_codes


def test_stable_metrics_do_not_report_drift():
    metrics = lab.evaluation_metrics()
    assert not lab.drift_report(metrics, metrics).drift_detected


def test_test_retest_stability_is_measured_not_promised():
    assert lab.self_consistency([policy.JudgeDecision.PASS] * 4 + [policy.JudgeDecision.FAIL]) == 0.8


def test_optional_ensemble_can_abstain_on_disagreement():
    decisions = [policy.JudgeDecision.PASS, policy.JudgeDecision.FAIL]
    assert lab.ensemble_decision(decisions) is policy.JudgeDecision.ABSTAIN
    assert lab.ensemble_decision(decisions, require_unanimous=True) is policy.JudgeDecision.ABSTAIN


def test_course_has_one_canonical_notebook_and_shared_modules():
    assert (COURSE_DIR / "11_llm_as_judge.ipynb").exists()
    assert not (COURSE_DIR / "llm_as_judge_agent_judges.ipynb").exists()
    assert (COURSE_DIR / "policy.py").exists()
    assert (COURSE_DIR / "lab.py").exists()


def test_course_text_does_not_repeat_unsafe_claims():
    text = "\n".join(path.read_text() for path in COURSE_DIR.glob("*.md"))
    forbidden = (
        "agreement is below 0.90",
        "perfectly aligns with human intuition",
        "ultimate defense",
        "cryptographic proof of outcome",
        "exceeds 3 sentences",
        "Always use a different model family",
    )
    assert all(phrase not in text for phrase in forbidden)


def test_notebook_uses_shared_lab_without_random_labels():
    notebook = (COURSE_DIR / "11_llm_as_judge.ipynb").read_text()
    assert "from lab import" in notebook
    assert "random.choice" not in notebook
    assert "correct_winner" not in notebook
