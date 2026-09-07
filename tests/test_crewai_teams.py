"""Advanced Course 03 invariants: CrewAI executes, application policy decides."""

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
    / "03-crewai-teams"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course03_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course03_lab", COURSE_DIR / "lab.py")
previous_lab = sys.modules.get("lab")
sys.modules["lab"] = lab
adapter = _load("course03_adapter", COURSE_DIR / "crewai_adapter.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy
if previous_lab is None:
    sys.modules.pop("lab", None)
else:
    sys.modules["lab"] = previous_lab


def rehash(artifact, **updates):
    changed = artifact.model_copy(update=updates)
    return changed.model_copy(update={"artifact_hash": policy.artifact_digest(changed)})


def test_northstar_case_matches_advanced_courses():
    assert "EU checkout conversion" in lab.QUESTION
    assert "deploy-1842" in lab.QUESTION
    assert lab.REQUIRED_EVIDENCE == (
        "health",
        "logs",
        "deployment",
        "customer-impact",
        "current-runbook",
    )


def test_models_forbid_extra_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.AgentDefinition(
            agent_id="x",
            role="MANAGER",
            goal="g",
            backstory="b",
            hidden_authority=True,
        )


def test_valid_task_graph_accepted():
    order = policy.validate_task_graph(lab.build_tasks())
    assert order[-2:] == ("synthesize-incident", "review-incident")


def test_missing_dependency_rejected():
    broken = lab.task("review-incident").model_copy(update={"dependencies": ("missing",)})
    with pytest.raises(policy.PolicyError, match="MISSING_DEPENDENCY"):
        policy.validate_task_graph((broken,))


def test_cycle_rejected():
    first = lab.task("collect-health").model_copy(update={"dependencies": ("collect-logs",)})
    second = lab.task("collect-logs").model_copy(update={"dependencies": ("collect-health",)})
    with pytest.raises(policy.PolicyError, match="TASK_CYCLE_DETECTED"):
        policy.validate_task_graph((first, second))


def test_self_dependency_rejected():
    broken = lab.task("collect-health").model_copy(update={"dependencies": ("collect-health",)})
    with pytest.raises(policy.PolicyError, match="SELF_DEPENDENCY"):
        policy.validate_task_graph((broken,))


def test_invalid_input_artifact_type_rejected():
    broken = lab.task("review-incident").model_copy(
        update={"required_inputs": (policy.ArtifactType.LOG_FINDING,), "dependencies": ("synthesize-incident",)}
    )
    with pytest.raises(policy.PolicyError, match="INVALID_INPUT_ARTIFACT_TYPE"):
        policy.validate_task_graph((*lab.build_tasks()[:-1], broken))


def test_task_identity_is_stable_not_execution_position():
    tasks = tuple(reversed(lab.build_tasks()))
    assert {item.task_id for item in tasks} == {item.task_id for item in lab.build_tasks()}


def test_initial_independent_tasks_are_ready_together():
    ready = policy.ready_task_ids(lab.build_tasks(), lab.build_flow_state().task_states)
    assert set(ready) == {item.task_id for item in lab.build_tasks()[:5]}


def test_sequential_task_readiness_waits_for_dependencies():
    state = lab.build_flow_state()
    assert "synthesize-incident" not in policy.ready_task_ids(lab.build_tasks(), state.task_states)
    for definition in lab.build_tasks()[:5]:
        state.task_states[definition.task_id] = policy.TaskStatus.SUCCEEDED
    assert "synthesize-incident" in policy.ready_task_ids(lab.build_tasks(), state.task_states)


def test_role_does_not_create_capability():
    fake_manager = lab.agent("manager").model_copy(update={"advertised_tools": (policy.Capability.DATABASE_DELETE,)})
    write = lab.task("collect-health").model_copy(update={"allowed_capabilities": (policy.Capability.DATABASE_DELETE,)})
    with pytest.raises(policy.PolicyError, match="UNAUTHORIZED_TOOL"):
        policy.authorize_task(fake_manager, write, lab.build_capability_policy(), tenant_id=lab.TENANT_ID)


def test_unauthorized_tool_rejected_even_if_advertised():
    worker = lab.agent("observability-worker").model_copy(
        update={"advertised_tools": (*lab.agent("observability-worker").advertised_tools, policy.Capability.PRODUCTION_ROLLBACK)}
    )
    task = lab.task("collect-health").model_copy(update={"allowed_capabilities": (policy.Capability.PRODUCTION_ROLLBACK,)})
    with pytest.raises(policy.PolicyError, match="UNAUTHORIZED_TOOL"):
        policy.authorize_task(worker, task, lab.build_capability_policy(), tenant_id=lab.TENANT_ID)


def test_valid_artifact_is_accepted():
    state = lab.build_flow_state()
    artifact = lab.build_artifact("collect-health")
    lab.accept_artifact(state, "collect-health", artifact)
    assert state.task_states["collect-health"] is policy.TaskStatus.SUCCEEDED


def test_wrong_tenant_artifact_rejected():
    artifact = lab.build_artifact("collect-health", tenant_id="globex")
    with pytest.raises(policy.PolicyError, match="ARTIFACT_TENANT_VIOLATION"):
        lab.accept_artifact(lab.build_flow_state(), "collect-health", artifact)


def test_wrong_producer_artifact_rejected():
    artifact = lab.build_artifact("collect-health", producer_agent_id="reviewer")
    with pytest.raises(policy.PolicyError, match="ARTIFACT_PRODUCER_VIOLATION"):
        lab.accept_artifact(lab.build_flow_state(), "collect-health", artifact)


def test_unknown_evidence_rejected():
    artifact = lab.build_artifact("synthesize-incident")
    artifact = rehash(
        artifact,
        evidence_ids=("invented",),
        source_refs=("invented/source",),
        payload={"claims": []},
    )
    with pytest.raises(policy.PolicyError, match="UNKNOWN_EVIDENCE"):
        lab.accept_artifact(lab.build_flow_state(), "synthesize-incident", artifact)


def test_wrong_source_reference_rejected():
    artifact = rehash(lab.build_artifact("collect-health"), source_refs=("wrong/source",))
    with pytest.raises(policy.PolicyError, match="SOURCE_PROVENANCE_MISMATCH"):
        lab.accept_artifact(lab.build_flow_state(), "collect-health", artifact)


def test_tampered_artifact_hash_rejected():
    artifact = lab.build_artifact("collect-health").model_copy(update={"artifact_hash": "tampered"})
    with pytest.raises(policy.PolicyError, match="ARTIFACT_HASH_MISMATCH"):
        lab.accept_artifact(lab.build_flow_state(), "collect-health", artifact)


def test_stale_policy_version_rejected():
    artifact = lab.build_artifact("collect-health", policy_version="stale")
    with pytest.raises(policy.PolicyError, match="POLICY_VERSION_MISMATCH"):
        lab.accept_artifact(lab.build_flow_state(), "collect-health", artifact)


def test_unsupported_claim_detected_despite_valid_schema():
    artifact = lab.build_artifact(
        "synthesize-incident",
        payload={
            "claims": [{
                "claim_id": "unsupported",
                "text": "Database was deleted",
                "evidence_ids": ["health"],
                "fact_keys": ["database_loss"],
            }]
        },
    )
    with pytest.raises(policy.PolicyError, match="UNSUPPORTED_CLAIM"):
        lab.accept_artifact(lab.build_flow_state(), "synthesize-incident", artifact)


def test_accepted_artifact_model_is_immutable():
    artifact = lab.build_artifact("collect-health")
    with pytest.raises(ValidationError, match="frozen_instance"):
        artifact.tenant_id = "globex"
    with pytest.raises(TypeError, match="immutable mapping"):
        artifact.payload["new"] = "cannot mutate accepted content"


def test_timeout_retry_is_bounded():
    assert policy.retry_disposition(policy.FailureCode.TIMEOUT, attempt_number=1, max_attempts=2) == "RETRY"
    assert policy.retry_disposition(policy.FailureCode.TIMEOUT, attempt_number=2, max_attempts=2) == "EXHAUSTED"


def test_invalid_artifact_gets_bounded_repair():
    assert policy.retry_disposition(policy.FailureCode.INVALID_ARTIFACT, attempt_number=1, max_attempts=2) == "RETRY"


def test_source_unavailable_uses_fallback_or_escalation():
    assert policy.retry_disposition(policy.FailureCode.SOURCE_UNAVAILABLE, attempt_number=1, max_attempts=2) == "FALLBACK_OR_ESCALATE"


def test_policy_denial_is_not_retried():
    assert policy.retry_disposition(policy.FailureCode.POLICY_BLOCKED, attempt_number=1, max_attempts=2) == "DO_NOT_RETRY"
    assert policy.retry_disposition(policy.FailureCode.AUTH_DENIED, attempt_number=1, max_attempts=2) == "DO_NOT_RETRY"


def test_attempt_ids_unique_logical_identity_stable():
    first = policy.TaskExecutionRecord(logical_task_execution_id="incident:task", attempt_id="attempt-1", task_id="task", attempt_number=1, status="RETRYABLE", failure_code="TIMEOUT", elapsed_ms=10, cost_usd=0)
    second = first.model_copy(update={"attempt_id": "attempt-2", "attempt_number": 2})
    assert first.logical_task_execution_id == second.logical_task_execution_id
    assert first.attempt_id != second.attempt_id


def test_duplicate_task_execution_detected():
    state = lab.build_flow_state()
    record = policy.TaskExecutionRecord(logical_task_execution_id="incident:task", attempt_id="attempt-1", task_id="task", attempt_number=1, status="SUCCEEDED", elapsed_ms=10, cost_usd=0)
    policy.register_execution(state, record)
    with pytest.raises(policy.PolicyError, match="DUPLICATE_TASK_EXECUTION"):
        policy.register_execution(state, record.model_copy(update={"attempt_id": "attempt-2"}))


def test_retry_attempt_may_reuse_logical_identity_after_retryable_failure():
    state = lab.build_flow_state()
    first = policy.TaskExecutionRecord(logical_task_execution_id="incident:task", attempt_id="attempt-1", task_id="task", attempt_number=1, status="RETRYABLE", failure_code="TIMEOUT", elapsed_ms=10, cost_usd=0)
    second = first.model_copy(update={"attempt_id": "attempt-2", "attempt_number": 2, "status": policy.TaskStatus.SUCCEEDED, "failure_code": None})
    policy.register_execution(state, first)
    policy.register_execution(state, second)
    assert state.executed_logical_ids == ("incident:task",)
    assert state.attempted_ids == ("attempt-1", "attempt-2")


def test_manager_valid_fallback_is_allowed():
    state = lab.build_flow_state()
    decision = lab.build_recovery_decision()
    result = policy.validate_manager_decision(decision, state=state, crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=tuple(item.task_id for item in lab.build_tasks()))
    assert result is policy.DelegationDecision.ALLOW


def test_manager_unknown_worker_rejected():
    decision = lab.build_recovery_decision().model_copy(update={"worker_agent_id": "unknown"})
    with pytest.raises(policy.PolicyError, match="MANAGER_UNKNOWN_WORKER"):
        policy.validate_manager_decision(decision, state=lab.build_flow_state(), crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=())


def test_manager_duplicate_task_rejected():
    decision = lab.build_recovery_decision(task_id="collect-health")
    with pytest.raises(policy.PolicyError, match="MANAGER_DUPLICATE_TASK"):
        policy.validate_manager_decision(decision, state=lab.build_flow_state(), crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=("collect-health",))


def test_manager_unauthorized_task_rejected():
    decision = lab.build_recovery_decision()
    proposed = decision.proposed_task.model_copy(update={"expected_artifact_type": policy.ArtifactType.REVIEW_DECISION})
    decision = decision.model_copy(update={"proposed_task": proposed})
    with pytest.raises(policy.PolicyError, match="MANAGER_UNAUTHORIZED_TASK"):
        policy.validate_manager_decision(decision, state=lab.build_flow_state(), crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=())


def test_manager_max_depth_enforced():
    decision = lab.build_recovery_decision(depth=3)
    with pytest.raises(policy.PolicyError, match="MANAGER_MAX_DEPTH_EXCEEDED"):
        policy.validate_manager_decision(decision, state=lab.build_flow_state(), crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=())


def test_manager_max_delegations_enforced():
    state = lab.build_flow_state()
    state.delegations = state.budget.max_delegations
    with pytest.raises(policy.PolicyError, match="MANAGER_MAX_DELEGATIONS_EXCEEDED"):
        policy.validate_manager_decision(lab.build_recovery_decision(), state=state, crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=())


def test_manager_no_progress_delegation_loop_detected():
    state = lab.build_flow_state()
    decision = lab.build_recovery_decision()
    policy.validate_manager_decision(decision, state=state, crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=())
    with pytest.raises(policy.PolicyError, match="DELEGATION_STALLED"):
        policy.validate_manager_decision(decision, state=state, crew=lab.build_crews()[2], capability_policy=lab.build_capability_policy(), known_task_ids=())


def test_manager_write_task_rejected():
    decision = lab.build_recovery_decision()
    proposed = decision.proposed_task.model_copy(update={"allowed_capabilities": (policy.Capability.PRODUCTION_ROLLBACK,)})
    decision = decision.model_copy(update={"proposed_task": proposed})
    manager_policy = lab.build_capability_policy().model_copy(update={"manager_capabilities": {"manager": (policy.Capability.PRODUCTION_ROLLBACK,)}})
    with pytest.raises(policy.PolicyError, match="MANAGER_WRITE_DENIED"):
        policy.validate_manager_decision(decision, state=lab.build_flow_state(), crew=lab.build_crews()[2], capability_policy=manager_policy, known_task_ids=())


def test_flow_invalid_transition_rejected():
    state = lab.build_flow_state()
    state.terminal_status = policy.RunStatus.COMPLETED
    event = policy.FlowEvent(event_type="CREW_STARTED", occurred_at=lab.FIXED_TIME)
    with pytest.raises(policy.PolicyError, match="INVALID_FLOW_TRANSITION"):
        policy.apply_flow_event(state, event)


def test_flow_cancellation_stops_next_crew():
    state = lab.build_flow_state()
    policy.apply_flow_event(state, policy.FlowEvent(event_type="CANCELLED", occurred_at=lab.FIXED_TIME))
    calls = state.worker_calls
    with pytest.raises(policy.PolicyError, match="RUN_CANCELLED"):
        policy.assert_crew_may_start(state)
    assert state.worker_calls == calls


def test_flow_completion_requires_review_pass():
    state, _ = lab.run_flow_controlled()
    state.terminal_status = policy.RunStatus.RUNNING
    review = next(item for item in state.accepted_artifacts.values() if item.artifact_type is policy.ArtifactType.REVIEW_DECISION)
    rejected = rehash(review, payload={**review.payload, "decision": "REVIEW_FAIL"})
    state.accepted_artifacts[review.artifact_id] = rejected
    with pytest.raises(policy.PolicyError, match="COMPLETION_REVIEW_NOT_PASSED"):
        policy.validate_completion(state)


def test_review_pass_does_not_authorize_rollback():
    with pytest.raises(policy.PolicyError, match="PRODUCTION_APPROVAL_REQUIRED"):
        policy.authorize_production_action(review_decision="REVIEW_PASS", validated_approval=False)


def test_validated_approval_is_a_separate_boundary():
    assert policy.authorize_production_action(review_decision="REVIEW_PASS", validated_approval=True)


def test_prompt_injected_artifact_cannot_alter_flow():
    assert lab.prompt_injection_is_inert()


def test_only_northstar_tenant_appears_in_normal_fixture():
    assert {item.tenant_id for item in lab.build_evidence_registry().values()} == {lab.TENANT_ID}


def test_total_work_differs_from_parallel_wall_clock():
    _, metrics = lab.run_flow_controlled()
    assert metrics.total_model_work_ms == 430
    assert metrics.wall_clock_latency_ms == 220


def test_same_task_sequential_metrics_are_derived():
    run = lab.run_same_workload("DETERMINISTIC_SEQUENTIAL")
    assert run.worker_calls == len(lab.build_tasks())
    assert run.total_model_work_ms == sum(lab._DURATIONS.values())


def test_hierarchical_overhead_is_derived():
    sequential = lab.run_same_workload("CREWAI_SEQUENTIAL")
    hierarchy = lab.run_same_workload("CREWAI_HIERARCHICAL")
    assert hierarchy.manager_calls == 1
    assert hierarchy.cost_usd > sequential.cost_usd
    assert hierarchy.wall_clock_latency_ms > sequential.wall_clock_latency_ms


def test_recovery_improvement_is_measured():
    comparison = lab.compare_recovery()
    assert comparison["hierarchical"].recovery_rate > comparison["sequential"].recovery_rate
    assert lab.recovery_gate() == "ACCEPT_HIERARCHY"


def test_quality_gate_rejects_hierarchy_with_no_benefit():
    assert lab.no_benefit_gate() == "KEEP_SEQUENTIAL"


def test_bad_hierarchy_fails_regression_gate():
    baseline = lab.run_same_workload("DETERMINISTIC_SEQUENTIAL")
    assert policy.architecture_gate(baseline, lab.bad_hierarchy_metrics()) == "KEEP_SEQUENTIAL"


def test_flow_can_beat_unconstrained_manager_on_same_workload():
    flow = lab.run_same_workload("FLOW_CONTROLLED_CREWS")
    bad = lab.bad_hierarchy_metrics()
    assert flow.completed and not bad.completed
    assert flow.wall_clock_latency_ms < bad.wall_clock_latency_ms


def test_context_projection_reduces_exposure_without_fixture_quality_loss():
    result = lab.context_projection_experiment()
    assert result["projected_approx_tokens"] < result["full_approx_tokens"]
    assert result["projected_sensitive_fields"] == 0
    assert result["task_success_equal"]


def test_persisted_state_resumes_without_rerunning_completed_tasks(tmp_path):
    state = lab.build_flow_state()
    state.task_states["collect-health"] = policy.TaskStatus.SUCCEEDED
    path = tmp_path / "state.json"
    lab.save_state(state, path)
    restored = lab.load_state(path)
    assert "collect-health" not in lab.tasks_to_resume(restored)


def test_real_crewai_adapter_output_still_validated_by_policy():
    state = lab.build_flow_state()
    valid_payload = lab.build_artifact("collect-health").payload
    accepted = adapter.validate_adapter_payload(valid_payload, task_id="collect-health", state=state)
    assert accepted.artifact_type is policy.ArtifactType.HEALTH_FINDING
    invalid = {"claims": [{"claim_id": "x", "text": "unsupported", "evidence_ids": ["health"], "fact_keys": ["not-present"]}]}
    with pytest.raises(policy.PolicyError, match="UNSUPPORTED_CLAIM"):
        adapter.validate_adapter_payload(invalid, task_id="collect-health", state=state)


def test_real_crewai_adapter_instantiates_offline_when_installed():
    pytest.importorskip("crewai")
    crew = adapter.build_sequential_crew()
    assert crew.process.value == "sequential"
    assert len(crew.tasks) == len(lab.build_tasks())
    assert all(item.output_pydantic is adapter.CrewAIArtifactPayload for item in crew.tasks)


def test_real_crewai_flow_adapter_maps_application_state_when_installed():
    pytest.importorskip("crewai")
    flow = adapter.build_flow_adapter(lab.build_flow_state())
    assert flow.state.tenant_id == lab.TENANT_ID
    assert {"admit", "choose_crew", "investigation_checkpoint"}.issubset(flow._methods)


def test_tested_crewai_adapter_version_is_exact_when_installed():
    crewai = pytest.importorskip("crewai")
    assert crewai.__version__ == adapter.TESTED_CREWAI_VERSION


def test_live_adapter_is_opt_in(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert adapter.run_live_sequential_if_configured() == "SKIPPED_NO_OPENAI_API_KEY"
