"""Advanced Course 12 benchmark governance and release invariants."""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

COURSE_DIR = Path(__file__).resolve().parents[1] / "curriculum" / "advanced" / "12-agent-benchmarks"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course12_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course12_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _case(case_id: str):
    return next(case for case in lab.northstar_cases() if case.case_id == case_id)


def _selected_cases():
    return tuple(case for case in lab.northstar_cases() if case.split is not policy.DatasetSplit.DEVELOPMENT)


def _observation(case_id: str, profile: str = "repaired", **updates):
    observation = lab.fixture_observation(_case(case_id), profile)
    return policy.CaseObservation.model_validate({**observation.model_dump(), **updates})


def _evaluate(case_id: str, profile: str = "repaired", **updates):
    case = _case(case_id)
    observation = _observation(case_id, profile, **updates)
    return lab.evaluate_case(case, observation, lab.run_manifest(profile, f"run-{profile}"))


def test_suite_has_twenty_reviewed_cases_and_held_out_release_set():
    cases = lab.northstar_cases()
    assert len(cases) == 20
    assert sum(case.split is policy.DatasetSplit.DEVELOPMENT for case in cases) == 4
    assert len(_selected_cases()) == 16
    assert {case.status for case in cases} == {policy.CaseStatus.ACTIVE}


def test_scenario_matrix_spans_required_failure_modes():
    tags = {tag for case in lab.northstar_cases() for tag in case.scenario_tags}
    assert {"routine", "ambiguous", "adversarial", "failure-retry", "authorization", "cross-tenant", "long-running", "provider-outage", "stale-state"} <= tags


def test_risk_slices_span_consequential_controls():
    tags = {tag for case in lab.northstar_cases() for tag in case.risk_tags}
    assert {"financial", "production-mutation", "PII", "tenant-isolation", "approval-gated", "authorization"} <= tags


def test_case_digest_detects_changed_expected_behavior():
    case = _case("01-grounded-diagnosis")
    changed = case.model_copy(update={"expected": case.expected.model_copy(update={"authoritative_state": "OTHER"})})
    with pytest.raises(policy.BenchmarkPolicyError, match="CASE_DIGEST_MISMATCH"):
        lab.validate_case_digest(changed)


def test_case_version_and_digest_are_immutable_identity():
    case = _case("01-grounded-diagnosis")
    assert case.case_version == "1.0.0"
    assert len(case.case_digest) == 64
    lab.validate_case_digest(case)


def test_active_case_requires_review_approval():
    case = _case("01-grounded-diagnosis").model_dump()
    case["approved_by"] = None
    with pytest.raises(ValidationError, match="ACTIVE_CASE_REQUIRES_APPROVAL"):
        policy.BenchmarkCase.model_validate(case)


def test_held_out_case_rejects_development_exposure():
    case = _case("05-cross-tenant-evidence").model_dump()
    case["development_exposures"] = ("few-shot-example",)
    with pytest.raises(ValidationError, match="HELD_OUT_CASE_EXPOSED_TO_DEVELOPMENT"):
        policy.BenchmarkCase.model_validate(case)


def test_candidate_case_requires_explicit_approval_to_activate():
    data = _case("01-grounded-diagnosis").model_dump()
    data.update(status=policy.CaseStatus.CANDIDATE, approved_by=None)
    candidate = policy.BenchmarkCase.model_validate(data)
    active = lab.approve_case(candidate, "security-owner")
    assert active.status is policy.CaseStatus.ACTIVE
    assert active.approved_by == "security-owner"


def test_active_case_cannot_be_reapproved_silently():
    with pytest.raises(policy.BenchmarkPolicyError, match="CASE_NOT_APPROVABLE"):
        lab.approve_case(_case("01-grounded-diagnosis"), "other-owner")


def test_suite_versions_bind_cases_to_policy_and_environment():
    suite = lab.benchmark_suite()
    assert suite.identity.dataset_version == lab.DATASET_VERSION
    assert all(case.policy_version == suite.identity.policy_version for case in suite.cases)
    assert all(case.environment_version == suite.identity.environment_version for case in suite.cases)


def test_models_reject_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.ExpectedOutcome(authoritative_state="OK", invented_score=1)


def test_tool_contract_rejects_required_forbidden_overlap():
    with pytest.raises(ValidationError, match="CONFLICTING_TOOL_CONSTRAINT"):
        policy.ToolConstraint(required=("write",), forbidden=("write",))


def test_partial_order_rejects_self_ordering():
    with pytest.raises(ValidationError, match="SELF_ORDER_CONSTRAINT"):
        policy.PartialOrderConstraint(before="x", after="x", reason="impossible")


def test_public_benchmark_exposure_is_not_an_invented_risk_rating():
    assert set(policy.ContaminationExposure) == {
        policy.ContaminationExposure.PUBLIC_SOURCE,
        policy.ContaminationExposure.CONTROLLED_ENVIRONMENT,
        policy.ContaminationExposure.PRIVATE_HELD_OUT,
    }


def test_pseudonymization_is_keyed_stable_and_key_specific():
    first = lab.pseudonymize_identifier("predictable-tenant", b"key-a")
    assert first == lab.pseudonymize_identifier("predictable-tenant", b"key-a")
    assert first != lab.pseudonymize_identifier("predictable-tenant", b"key-b")
    assert "predictable-tenant" not in first


def test_pseudonymization_requires_secret_key():
    with pytest.raises(policy.BenchmarkPolicyError, match="PSEUDONYMIZATION_KEY_REQUIRED"):
        lab.pseudonymize_identifier("tenant", b"")


def test_trace_sanitizer_removes_nested_fields_and_free_text_pii():
    raw = {
        "user_email": "top@example.com",
        "nested": {"credit_card": "4111111111111111", "message": "Contact Jane@example.com with tok-abcdefghijk"},
    }
    clean = lab.sanitize_trace(raw)
    assert "user_email" not in clean
    assert "credit_card" not in clean["nested"]
    assert clean["nested"]["message"].count("[REDACTED]") == 2
    assert lab.sensitive_findings(clean) == ()


def test_sensitive_scanner_finds_fields_and_unstructured_values():
    findings = lab.sensitive_findings({"secret": "value", "note": "mail me at a@b.com"})
    assert any(item.startswith("FORBIDDEN_FIELD") for item in findings)
    assert any(item.startswith("SENSITIVE_TEXT") for item in findings)


def test_agent_configuration_digest_binds_router_and_memory_versions():
    base = {"model": "m", "prompt": "p", "router": "r1", "memory": "v1"}
    changed = {**base, "router": "r2"}
    assert lab.agent_config_digest(base) != lab.agent_config_digest(changed)


def test_run_manifest_records_reproducibility_inputs():
    manifest = lab.run_manifest("candidate", "run-1")
    assert manifest.seed == manifest.environment.seed
    assert manifest.environment.reset_between_cases
    assert manifest.environment.cache_policy == "reset-per-case"
    assert len(manifest.agent.config_digest) == 64


def test_manifest_dataset_mismatch_fails_closed():
    case = _case("05-cross-tenant-evidence")
    manifest = lab.run_manifest("candidate", "run")
    changed = manifest.model_copy(update={"dataset_version": "other"})
    with pytest.raises(policy.BenchmarkPolicyError, match="RUN_MANIFEST_DATASET_MISMATCH"):
        lab.evaluate_case(case, lab.fixture_observation(case, "repaired"), changed)


def test_manifest_evaluator_mismatch_fails_closed():
    case = _case("05-cross-tenant-evidence")
    manifest = lab.run_manifest("candidate", "run").model_copy(update={"evaluator_version": "judge-v99"})
    with pytest.raises(policy.BenchmarkPolicyError, match="RUN_MANIFEST_EVALUATOR_MISMATCH"):
        lab.evaluate_case(case, lab.fixture_observation(case, "repaired"), manifest)


def test_observation_must_bind_to_case_identity():
    case = _case("05-cross-tenant-evidence")
    observation = lab.fixture_observation(case, "repaired").model_copy(update={"case_id": "other"})
    with pytest.raises(policy.BenchmarkPolicyError, match="OBSERVATION_CASE_BINDING_MISMATCH"):
        lab.evaluate_case(case, observation, lab.run_manifest("repaired", "run"))


def test_environment_version_mismatch_is_invalid_not_agent_failure():
    result = _evaluate("05-cross-tenant-evidence", environment_version="other")
    assert result.outcome is policy.CaseOutcome.INVALID_RUN
    assert result.failure_reasons == ("ENVIRONMENT_VERSION_MISMATCH",)


def test_harness_failure_is_invalid_not_agent_failure():
    case = _case("05-cross-tenant-evidence")
    result = lab.evaluate_case(case, lab.fixture_observation(case, "harness-error"), lab.run_manifest("harness-error", "run"))
    assert result.outcome is policy.CaseOutcome.INVALID_RUN
    assert "HARNESS_FAILURE" in result.failure_reasons


def test_agent_self_reported_success_does_not_override_authoritative_state():
    result = _evaluate("14-wrong-model-route", "baseline")
    assert not result.task_success
    assert result.outcome is policy.CaseOutcome.FAIL
    assert "SELF_REPORTED_SUCCESS_NOT_AUTHORITATIVE" in result.failure_reasons


def test_platform_blocked_unauthorized_attempt_still_fails_agent_policy():
    result = _evaluate("04-unauthorized-mutation", "candidate")
    assert result.task_success
    assert not result.compliant_success
    assert result.platform_containment_succeeded
    assert result.trajectory.forbidden_tool_attempts == ("production.rollback",)
    assert "UNAUTHORIZED_TOOL_ATTEMPT" in result.failure_reasons


def test_cross_tenant_evidence_hard_fails_even_when_outcome_matches():
    result = _evaluate("05-cross-tenant-evidence", "candidate")
    assert result.task_success
    assert not result.compliant_success
    assert "CROSS_TENANT_ACCESS" in result.failure_reasons


def test_cross_tenant_trace_event_fails_without_foreign_evidence_record():
    case = _case("05-cross-tenant-evidence")
    observation = lab.fixture_observation(case, "repaired")
    foreign = observation.events[0].model_copy(update={"tenant_id": "globex"})
    changed = observation.model_copy(update={"events": (foreign, *observation.events[1:])})
    result = lab.evaluate_case(case, changed, lab.run_manifest("repaired", "run"))
    assert "CROSS_TENANT_ACCESS" in result.failure_reasons


def test_trace_sequence_must_be_unique_and_contiguous():
    case = _case("20-low-cost-compliant")
    observation = lab.fixture_observation(case, "repaired")
    duplicate = observation.events[1].model_copy(update={"sequence": 1})
    changed = observation.model_copy(update={"events": (observation.events[0], duplicate)})
    result = lab.evaluate_case(case, changed, lab.run_manifest("repaired", "run"))
    assert "INVALID_TRACE_SEQUENCE" in result.failure_reasons


def test_harness_usage_accounting_must_match_observable_tool_calls():
    observation = _observation("20-low-cost-compliant")
    changed_usage = observation.operational.model_copy(update={"tool_calls": 99})
    result = _evaluate("20-low-cost-compliant", operational=changed_usage)
    assert "USAGE_ACCOUNTING_MISMATCH" in result.failure_reasons


def test_required_action_is_checked_as_set_not_exact_sequence():
    case = _case("01-grounded-diagnosis")
    observation = lab.fixture_observation(case, "repaired")
    extra = policy.TraceEvent(event_id="extra", sequence=1, event_type=policy.EventType.TOOL_CALL, tenant_id="northstar", tool_id="logs.search")
    shifted = tuple(event.model_copy(update={"sequence": event.sequence + 1}) for event in observation.events)
    usage = observation.operational.model_copy(update={"tool_calls": observation.operational.tool_calls + 1})
    changed = observation.model_copy(update={"events": (extra, *shifted), "operational": usage})
    result = lab.evaluate_case(case, changed, lab.run_manifest("repaired", "run"))
    assert result.compliant_success


def test_missing_required_action_fails_trajectory():
    case = _case("14-wrong-model-route")
    observation = lab.fixture_observation(case, "repaired")
    events = tuple(event for event in observation.events if event.tool_id != "router.select")
    result = lab.evaluate_case(case, observation.model_copy(update={"events": events}), lab.run_manifest("repaired", "run"))
    assert result.trajectory.missing_required_actions == ("router.select",)
    assert "MISSING_REQUIRED_ACTION" in result.failure_reasons


def test_partial_order_allows_other_harmless_reads():
    assert _evaluate("03-safe-mitigation").compliant_success


def test_partial_order_violation_is_detected_without_exact_sequence_matching():
    case = _case("03-safe-mitigation")
    observation = lab.fixture_observation(case, "repaired")
    events = list(observation.events)
    first, second = events[0], events[1]
    events[0] = second.model_copy(update={"sequence": 1})
    events[1] = first.model_copy(update={"sequence": 2})
    result = lab.evaluate_case(case, observation.model_copy(update={"events": tuple(events)}), lab.run_manifest("repaired", "run"))
    assert result.trajectory.order_violations == ("metrics.read>mitigation.propose",)
    assert "TRAJECTORY_ORDER_VIOLATION" in result.failure_reasons


def test_evidence_coverage_requires_existing_cited_evidence():
    case = _case("12-successful-reconciliation")
    observation = lab.fixture_observation(case, "repaired").model_copy(update={"evidence": ()})
    result = lab.evaluate_case(case, observation, lab.run_manifest("repaired", "run"))
    assert result.trajectory.evidence_coverage == 0
    assert result.outcome is policy.CaseOutcome.INSUFFICIENT_EVIDENCE


def test_evidence_id_must_support_the_expected_claim():
    case = _case("12-successful-reconciliation")
    observation = lab.fixture_observation(case, "repaired")
    unsupported = observation.evidence[0].model_copy(update={"supported_claims": ("OTHER_CLAIM",)})
    result = lab.evaluate_case(case, observation.model_copy(update={"evidence": (unsupported,)}), lab.run_manifest("repaired", "run"))
    assert "MISSING_REQUIRED_EVIDENCE" in result.failure_reasons


def test_valid_abstention_remains_typed_and_can_be_compliant():
    result = _evaluate("18-evaluator-abstention")
    assert result.outcome is policy.CaseOutcome.ABSTAIN
    assert result.compliant_success


def test_artifact_contract_is_application_validated():
    result = _evaluate("20-low-cost-compliant", final_artifact={})
    assert not result.compliant_success
    assert "INVALID_FINAL_ARTIFACT" in result.failure_reasons


def test_sensitive_output_is_a_hard_gate():
    result = _evaluate("20-low-cost-compliant", final_artifact={"summary": "Contact jane@example.com"})
    assert not result.compliant_success
    assert "SECRET_EXPOSURE" in result.failure_reasons


def test_tool_call_budget_is_enforced_not_merely_reported():
    case = _case("20-low-cost-compliant")
    observation = lab.fixture_observation(case, "repaired")
    events = list(observation.events[:-1])
    for index in range(case.tools.max_tool_calls):
        events.append(policy.TraceEvent(event_id=f"extra-{index}", sequence=len(events) + 1, event_type=policy.EventType.TOOL_CALL, tenant_id=case.tenant_id, tool_id="records.read"))
    final = observation.events[-1].model_copy(update={"sequence": len(events) + 1})
    events.append(final)
    operational = observation.operational.model_copy(update={"tool_calls": sum(event.event_type is policy.EventType.TOOL_CALL for event in events)})
    result = lab.evaluate_case(case, observation.model_copy(update={"events": tuple(events), "operational": operational}), lab.run_manifest("repaired", "run"))
    assert not result.compliant_success
    assert "TOOL_BUDGET_EXCEEDED" in result.failure_reasons


def test_success_over_cost_budget_is_not_compliant_success():
    result = _evaluate("19-high-cost-success", "candidate")
    assert result.task_success
    assert not result.compliant_success
    assert "COST_BUDGET_EXCEEDED" in result.failure_reasons


def test_wall_clock_deadline_is_distinct_from_accumulated_component_work():
    observation = _observation("11-provider-timeout")
    operational = observation.operational.model_copy(update={"wall_clock_ms": 901, "model_latency_ms": 700, "tool_latency_ms": 400})
    result = _evaluate("11-provider-timeout", operational=operational)
    assert "DEADLINE_EXCEEDED" in result.failure_reasons
    assert operational.model_latency_ms + operational.tool_latency_ms > operational.wall_clock_ms


def test_private_reasoning_is_not_a_trajectory_event_type():
    assert "THINK" not in {event.value for event in policy.EventType}
    assert {"TOOL_CALL", "TOOL_RESULT", "PROPOSAL", "APPROVAL", "EXECUTION_RECEIPT", "STATE_TRANSITION", "FINAL_ARTIFACT"} <= {event.value for event in policy.EventType}


def test_wilson_interval_exposes_small_sample_uncertainty():
    small = lab.wilson_interval(3, 3)
    large = lab.wilson_interval(300, 300)
    assert small.estimate == large.estimate == 1
    assert small.lower < large.lower


def test_wilson_interval_validates_population_counts():
    with pytest.raises(ValueError, match="INVALID_RATE_COUNTS"):
        lab.wilson_interval(4, 3)


def test_repeated_trials_expose_flakiness_instead_of_majority_hiding_it():
    summary = lab.repeated_trial_summary("stochastic-case", [True, True, True, False, False])
    assert summary.success_probability == 0.6
    assert summary.variance == pytest.approx(0.24)
    assert summary.flaky


def test_deterministic_repeated_trials_are_not_marked_flaky():
    assert not lab.repeated_trial_summary("deterministic", [True, True, True]).flaky


def test_repeated_trials_require_observations():
    with pytest.raises(ValueError, match="TRIALS_REQUIRED"):
        lab.repeated_trial_summary("empty", [])


def test_agent_timeout_is_distinct_from_harness_failure():
    case = _case("11-provider-timeout")
    observation = lab.fixture_observation(case, "repaired").model_copy(
        update={"authoritative_state": None, "reported_outcome": "TIMEOUT", "failure_origin": policy.FailureOrigin.AGENT}
    )
    result = lab.evaluate_case(case, observation, lab.run_manifest("repaired", "run"))
    assert result.outcome is policy.CaseOutcome.TIMEOUT
    assert "HARNESS_FAILURE" not in result.failure_reasons


def test_metrics_exclude_invalid_runs_and_report_them_separately():
    cases = _selected_cases()
    valid = list(lab.evaluate_profile("repaired", cases))
    broken_case = cases[0]
    invalid = lab.evaluate_case(broken_case, lab.fixture_observation(broken_case, "harness-error"), lab.run_manifest("harness-error", "broken"))
    valid[0] = invalid
    metrics = lab.benchmark_metrics(valid, cases)
    assert metrics.total_runs == 16
    assert metrics.valid_agent_runs == 15
    assert metrics.invalid_runs == 1
    assert metrics.harness_failures == 1


def test_metrics_report_support_with_every_slice_percentage():
    cases = _selected_cases()
    metrics = lab.benchmark_metrics(lab.evaluate_profile("repaired", cases), cases)
    tenant = next(item for item in metrics.per_slice if item.slice_id == "tenant-isolation")
    assert tenant.support == 1
    assert tenant.compliant_success_rate == 1


def test_cost_per_compliant_success_includes_failed_run_costs():
    cases = _selected_cases()
    results = lab.evaluate_profile("candidate", cases)
    metrics = lab.benchmark_metrics(results, cases)
    successful_cost_only = sum(row.operational.total_cost_usd for row in results if row.compliant_success) / sum(row.compliant_success for row in results)
    assert metrics.cost_per_successful_compliant_task_usd > successful_cost_only


def test_operational_metrics_separate_wall_clock_and_total_work():
    metrics = _observation("20-low-cost-compliant").operational
    assert metrics.wall_clock_ms != metrics.model_latency_ms + metrics.tool_latency_ms + metrics.queue_wait_ms
    assert metrics.model_calls == 2
    assert metrics.tool_calls == 1


def test_paired_comparison_requires_identical_case_set():
    cases = _selected_cases()
    baseline = lab.evaluate_profile("baseline", cases)
    candidate = lab.evaluate_profile("candidate", cases)
    with pytest.raises(policy.BenchmarkPolicyError, match="PAIRED_CASE_SET_MISMATCH"):
        lab.paired_comparison(baseline[:-1], candidate, cases)


def test_paired_comparison_exposes_improvements_and_critical_regression():
    cases = _selected_cases()
    comparison = lab.paired_comparison(lab.evaluate_profile("baseline", cases), lab.evaluate_profile("candidate", cases), cases)
    assert comparison.improvements == 3
    assert comparison.regressions == 1
    assert comparison.critical_regressions == 1
    assert next(row for row in comparison.rows if row.case_id == "05-cross-tenant-evidence").classification == "REGRESSION"


def test_high_aggregate_rate_cannot_hide_critical_safety_regression():
    cases = _selected_cases()
    candidate = lab.evaluate_profile("candidate", cases)
    metrics = lab.benchmark_metrics(candidate, cases)
    comparison = lab.paired_comparison(lab.evaluate_profile("baseline", cases), candidate, cases)
    decision = lab.release_decision(metrics, comparison)
    assert metrics.compliant_success.estimate >= 0.80
    assert decision.status is policy.ReleaseStatus.BLOCK
    assert "CRITICAL_REGRESSION_BUDGET_EXCEEDED" in decision.reason_codes


def test_repaired_candidate_passes_blocking_policy():
    cases = _selected_cases()
    repaired = lab.evaluate_profile("repaired", cases)
    metrics = lab.benchmark_metrics(repaired, cases)
    comparison = lab.paired_comparison(lab.evaluate_profile("baseline", cases), repaired, cases)
    decision = lab.release_decision(metrics, comparison)
    assert decision.status is policy.ReleaseStatus.PASS
    assert decision.permits_release


def test_shadow_mode_reports_violations_without_blocking():
    cases = _selected_cases()
    candidate = lab.evaluate_profile("candidate", cases)
    comparison = lab.paired_comparison(lab.evaluate_profile("baseline", cases), candidate, cases)
    shadow = policy.ReleasePolicy.model_validate({**lab.DEFAULT_RELEASE_POLICY.model_dump(), "mode": policy.ReleaseMode.SHADOW})
    decision = lab.release_decision(lab.benchmark_metrics(candidate, cases), comparison, shadow)
    assert decision.status is policy.ReleaseStatus.WARN
    assert decision.permits_release
    assert decision.reason_codes


def test_minimum_slice_support_is_a_release_gate():
    cases = _selected_cases()
    repaired = lab.evaluate_profile("repaired", cases)
    comparison = lab.paired_comparison(lab.evaluate_profile("baseline", cases), repaired, cases)
    strict = policy.ReleasePolicy.model_validate({**lab.DEFAULT_RELEASE_POLICY.model_dump(), "minimum_slice_support": {"tenant-isolation": 2}})
    decision = lab.release_decision(lab.benchmark_metrics(repaired, cases), comparison, strict)
    assert decision.status is policy.ReleaseStatus.BLOCK
    assert "SLICE_SUPPORT_TOO_LOW:tenant-isolation" in decision.reason_codes


def test_exception_must_be_live_and_scoped_to_decision():
    decision = policy.ReleaseDecision(status=policy.ReleaseStatus.BLOCK, permits_release=False, mode=policy.ReleaseMode.BLOCKING, reason_codes=("P95_LATENCY_EXCEEDED",))
    exception = policy.BenchmarkException(exception_id="ex-1", owner="sre", reason="temporary provider issue", mitigation="canary only", scoped_reason_codes=("P95_LATENCY_EXCEEDED",), issued_at=lab.FIXED_TIME, expires_at=lab.FIXED_TIME + timedelta(days=1))
    lab.validate_exception(exception, lab.FIXED_TIME + timedelta(hours=1), decision)
    with pytest.raises(policy.BenchmarkPolicyError, match="EXCEPTION_EXPIRED"):
        lab.validate_exception(exception, lab.FIXED_TIME + timedelta(days=2), decision)


def test_fixture_does_not_allow_critical_gate_waiver():
    decision = policy.ReleaseDecision(status=policy.ReleaseStatus.BLOCK, permits_release=False, mode=policy.ReleaseMode.BLOCKING, reason_codes=("CRITICAL_REGRESSION_BUDGET_EXCEEDED",))
    exception = policy.BenchmarkException(exception_id="ex-2", owner="product", reason="ship now", mitigation="monitor", scoped_reason_codes=decision.reason_codes, issued_at=lab.FIXED_TIME, expires_at=lab.FIXED_TIME + timedelta(hours=1))
    with pytest.raises(policy.BenchmarkPolicyError, match="CRITICAL_GATE_NOT_WAIVABLE_IN_FIXTURE"):
        lab.validate_exception(exception, lab.FIXED_TIME, decision)


def test_regression_clustering_uses_stable_reason_codes():
    cases = _selected_cases()
    candidate = lab.evaluate_profile("candidate", cases)
    comparison = lab.paired_comparison(lab.evaluate_profile("baseline", cases), candidate, cases)
    assert lab.regression_clusters(comparison, candidate) == {"CROSS_TENANT_ACCESS": 1}


def test_case_order_does_not_change_results():
    cases = _selected_cases()
    forward = lab.evaluate_profile("repaired", cases)
    reverse = lab.evaluate_profile("repaired", tuple(reversed(cases)))
    assert {row.case_id: row.compliant_success for row in forward} == {row.case_id: row.compliant_success for row in reverse}


def test_development_cases_are_not_used_for_release_metrics():
    report = lab.suite_report("repaired")
    assert report["valid_cases"] == 16
    assert len(lab.northstar_cases()) == 20


def test_fixture_profile_is_deterministic_and_credential_free():
    first = lab.suite_report("candidate")
    second = lab.suite_report("candidate")
    assert first == second
    assert first["run"] == "run-candidate"


def test_benchmark_taxonomy_keeps_distinct_evaluation_purposes():
    assert set(policy.BenchmarkType) == {
        policy.BenchmarkType.CAPABILITY,
        policy.BenchmarkType.SYSTEM,
        policy.BenchmarkType.SAFETY,
        policy.BenchmarkType.REGRESSION,
        policy.BenchmarkType.LOAD_PERFORMANCE,
        policy.BenchmarkType.PRODUCTION_SHADOW,
    }


def test_case_outcomes_do_not_collapse_harness_error_into_agent_failure():
    assert {"PASS", "FAIL", "ABSTAIN", "ENVIRONMENT_ERROR", "TIMEOUT", "INVALID_RUN", "INSUFFICIENT_EVIDENCE"} == {item.value for item in policy.CaseOutcome}


def test_suite_report_shows_block_then_repair():
    blocked = lab.suite_report("candidate")
    repaired = lab.suite_report("repaired")
    assert blocked["release"] == "BLOCK"
    assert repaired["release"] == "PASS"
    assert blocked["critical_regressions"] == 1
    assert repaired["critical_regressions"] == 0
