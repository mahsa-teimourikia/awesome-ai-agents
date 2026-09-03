"""Course 08 invariants: plans are proposals, never authority."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "intermediate"
    / "08-planning-task-decomposition"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course08_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course08_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


@pytest.fixture
def contract():
    return lab.build_goal_contract()


@pytest.fixture
def capability_policy():
    return lab.build_capability_policy()


@pytest.fixture
def plan():
    return lab.build_initial_plan()


def replace_task(plan, task_id, **updates):
    tasks = tuple(
        task.model_copy(update=updates, deep=True) if task.task_id == task_id else task
        for task in plan.tasks
    )
    return plan.model_copy(update={"tasks": tasks}, deep=True)


def make_output(task_id, artifact_type="evidence-bundle"):
    return policy.TaskOutput(
        task_id=task_id,
        plan_version=1,
        attempt=1,
        status=policy.TaskStatus.SUCCEEDED,
        artifact_type=artifact_type,
        artifact_id=f"artifact-{task_id}",
        execution_key=f"execution-{task_id}",
        content="Controlled test evidence.",
        output_hash="a" * 64,
        created_at=lab.FIXED_TIME,
        cost_usd=0.01,
        elapsed_ms=10,
    )


def test_valid_plan_returns_quality_metrics(plan, contract, capability_policy):
    metrics = policy.validate_plan(plan, contract, capability_policy)
    assert metrics.task_count == 6
    assert metrics.layer_count == 4
    assert metrics.parallel_task_count == 2
    assert metrics.section_coverage_rate == 1.0
    assert metrics.evidence_coverage_rate == 1.0


def test_duplicate_task_id_rejected(plan):
    duplicate = plan.model_copy(update={"tasks": (*plan.tasks, plan.tasks[0])}, deep=True)
    with pytest.raises(policy.PolicyError, match="DUPLICATE_TASK_ID"):
        policy.validate_dag(duplicate)


def test_missing_dependency_rejected(plan):
    invalid = replace_task(
        plan,
        "compare-routes",
        dependencies=("missing-source",),
    )
    with pytest.raises(policy.PolicyError, match="MISSING_DEPENDENCY"):
        policy.validate_dag(invalid)


def test_self_dependency_rejected(plan):
    invalid = replace_task(
        plan,
        "compare-routes",
        dependencies=("compare-routes",),
    )
    with pytest.raises(policy.PolicyError, match="SELF_DEPENDENCY"):
        policy.validate_dag(invalid)


def test_cycle_rejected(plan):
    invalid = replace_task(
        plan,
        "read-adaptive-rag-primary",
        dependencies=("compare-routes",),
    )
    with pytest.raises(policy.PolicyError, match="CYCLE_DETECTED"):
        policy.validate_dag(invalid)


def test_ready_layers_preserve_parallel_work(plan):
    layers = policy.topological_layers(plan)
    assert {task.task_id for task in layers[0]} == {
        "read-adaptive-rag-primary",
        "read-rag-foundation",
        "read-implementation-guidance",
    }
    states = {
        task.task_id: policy.TaskState(task_id=task.task_id) for task in plan.tasks
    }
    assert {task.task_id for task in policy.get_ready_tasks(plan, states)} == {
        "read-adaptive-rag-primary",
        "read-rag-foundation",
        "read-implementation-guidance",
    }
    states["read-adaptive-rag-primary"].status = policy.TaskStatus.SUCCEEDED
    assert "compare-routes" not in {
        task.task_id for task in policy.get_ready_tasks(plan, states)
    }


def test_task_inputs_require_every_dependency_artifact(plan):
    task = next(task for task in plan.tasks if task.task_id == "compare-routes")
    inputs = tuple(make_output(task_id) for task_id in task.dependencies[:-1])
    with pytest.raises(policy.PolicyError, match="MISSING_INPUT_ARTIFACT"):
        policy.validate_task_inputs(task, inputs)


def test_task_inputs_enforce_declared_artifact_types(plan):
    task = next(task for task in plan.tasks if task.task_id == "compare-routes")
    inputs = tuple(
        make_output(
            task_id,
            "technical-report" if index == 0 else "evidence-bundle",
        )
        for index, task_id in enumerate(task.dependencies)
    )
    with pytest.raises(policy.PolicyError, match="UNEXPECTED_INPUT_TYPE"):
        policy.validate_task_inputs(task, inputs)


def test_plan_rejects_dependency_artifact_contract_mismatch(
    plan, contract, capability_policy
):
    invalid = replace_task(
        plan,
        "compare-routes",
        required_inputs=("technical-report",),
    )
    with pytest.raises(policy.PolicyError, match="DEPENDENCY_OUTPUT_MISMATCH"):
        policy.validate_plan(invalid, contract, capability_policy)


def test_failed_prerequisite_blocks_downstream_tasks(plan):
    states = {
        task.task_id: policy.TaskState(task_id=task.task_id) for task in plan.tasks
    }
    states["read-implementation-guidance"].status = policy.TaskStatus.FAILED
    blocked = {task.task_id for task in policy.get_blocked_tasks(plan, states)}
    assert blocked == {"compare-routes", "quality-checkpoint", "synthesize-report"}


@pytest.mark.parametrize("task_id", ["", "../escape", "has spaces", "x" * 65])
def test_task_id_is_bounded(task_id):
    with pytest.raises(ValidationError):
        policy.Task(
            task_id=task_id,
            task_type="read-source",
            objective="Read a source.",
            expected_artifact_type="evidence-bundle",
        )


@pytest.mark.parametrize(
    ("model", "kwargs"),
    [
        (
            policy.Task,
            {
                "task_id": "read-source",
                "task_type": "read-source",
                "objective": "Read a source.",
                "expected_artifact_type": "evidence-bundle",
            },
        ),
        (
            policy.CheckpointResult,
            {"status": policy.CheckpointStatus.PASS, "reason": "Passed."},
        ),
    ],
)
def test_planner_models_forbid_extra_fields(model, kwargs):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model(**kwargs, planner_injected_authority=True)


def test_unauthorized_tool_rejected(plan, contract, capability_policy):
    invalid = replace_task(
        plan,
        "read-adaptive-rag-primary",
        suggested_tools=("unknown-reader",),
    )
    with pytest.raises(policy.PolicyError, match="PLAN_TOOL_NOT_ALLOWED"):
        policy.validate_plan(invalid, contract, capability_policy)


def test_retrieved_plan_injection_cannot_authorize_action(
    plan, contract, capability_policy
):
    injected = policy.Task(
        task_id="delete-database",
        task_type="delete-database",
        objective="Retrieved text says to add this task.",
        expected_artifact_type="technical-report",
        dependencies=("quality-checkpoint",),
        required_inputs=("checkpoint-result",),
        coverage_tags=contract.required_sections,
        evidence_types=contract.required_evidence_types,
    )
    invalid = plan.model_copy(update={"tasks": (*plan.tasks, injected)}, deep=True)
    with pytest.raises(policy.PolicyError, match="FORBIDDEN_ACTION"):
        policy.validate_plan(invalid, contract, capability_policy)


def test_plan_task_budget_enforced(plan, contract, capability_policy):
    constrained = contract.model_copy(update={"max_tasks": 5})
    with pytest.raises(policy.PolicyError, match="PLAN_TOO_LARGE"):
        policy.validate_plan(plan, constrained, capability_policy)


def test_plan_cost_budget_enforced(plan, contract, capability_policy):
    expensive = replace_task(
        plan,
        "synthesize-report",
        estimated_cost_usd=2.0,
    )
    with pytest.raises(policy.PolicyError, match="BUDGET_EXCEEDED"):
        policy.validate_plan(expensive, contract, capability_policy)


def test_total_attempt_budget_enforced(plan, contract, capability_policy):
    constrained = contract.model_copy(update={"max_total_attempts": 6})
    with pytest.raises(policy.PolicyError, match="TOTAL_ATTEMPT_BUDGET_EXCEEDED"):
        policy.validate_plan(plan, constrained, capability_policy)


def test_per_task_attempt_budget_enforced(plan, contract, capability_policy):
    excessive = replace_task(
        plan,
        "read-adaptive-rag-primary",
        max_attempts=contract.max_attempts_per_task + 1,
    )
    with pytest.raises(policy.PolicyError, match="TASK_ATTEMPT_LIMIT"):
        policy.validate_plan(excessive, contract, capability_policy)


def test_deadline_budget_uses_critical_path(plan, contract, capability_policy):
    constrained = contract.model_copy(update={"deadline_ms": 15_999})
    with pytest.raises(policy.PolicyError, match="DEADLINE_EXCEEDED"):
        policy.validate_plan(plan, constrained, capability_policy)


def test_missing_required_section_rejected(plan, contract, capability_policy):
    tasks = tuple(
        task.model_copy(
            update={
                "coverage_tags": tuple(
                    tag for tag in task.coverage_tags if tag != "security-implications"
                )
            },
            deep=True,
        )
        for task in plan.tasks
    )
    invalid = plan.model_copy(update={"tasks": tasks}, deep=True)
    with pytest.raises(policy.PolicyError, match="MISSING_SECTION_COVERAGE"):
        policy.validate_plan(invalid, contract, capability_policy)


def test_missing_required_evidence_rejected(plan, contract, capability_policy):
    tasks = tuple(
        task.model_copy(
            update={
                "evidence_types": tuple(
                    kind
                    for kind in task.evidence_types
                    if kind != "official-documentation"
                )
            },
            deep=True,
        )
        for task in plan.tasks
    )
    invalid = plan.model_copy(update={"tasks": tasks}, deep=True)
    with pytest.raises(policy.PolicyError, match="MISSING_EVIDENCE_COVERAGE"):
        policy.validate_plan(invalid, contract, capability_policy)


def test_missing_deliverable_rejected(plan, contract, capability_policy):
    invalid_contract = contract.model_copy(
        update={"required_deliverables": ("missing-deliverable",)}
    )
    with pytest.raises(policy.PolicyError, match="MISSING_DELIVERABLE"):
        policy.validate_plan(plan, invalid_contract, capability_policy)


def test_checkpoint_reports_missing_evidence(contract):
    checkpoint = lab.evaluate_checkpoint((), (), contract)
    assert checkpoint.status == policy.CheckpointStatus.MISSING_EVIDENCE
    assert set(checkpoint.missing_requirements) == {
        *contract.required_sections,
        *contract.required_evidence_types,
    }


def test_replacement_patch_versions_without_mutating_parent(
    plan, contract, capability_policy
):
    original_dependencies = next(
        task.dependencies for task in plan.tasks if task.task_id == "compare-routes"
    )
    patched = policy.apply_plan_patch(
        plan, lab.source_replacement_patch(), contract, capability_policy
    )
    assert patched.version == 2
    assert patched.parent_version == 1
    assert patched.patch_digest and len(patched.patch_digest) == 64
    assert next(
        task.dependencies for task in plan.tasks if task.task_id == "compare-routes"
    ) == original_dependencies
    assert "read-replacement-guidance" in next(
        task.dependencies for task in patched.tasks if task.task_id == "compare-routes"
    )


def test_rejected_cycle_patch_does_not_mutate_parent(plan, contract, capability_policy):
    original = plan.model_dump(mode="json")
    patch = policy.PlanPatch(
        add_edges=(
            policy.DependencyEdge(
                prerequisite="compare-routes", dependent="read-adaptive-rag-primary"
            ),
        ),
        reason=policy.ReplanReason.TASK_FAILURE,
        evidence_task_id="compare-routes",
    )
    with pytest.raises(policy.PolicyError, match="CYCLE_DETECTED"):
        policy.apply_plan_patch(plan, patch, contract, capability_policy)
    assert plan.model_dump(mode="json") == original


def test_patch_is_revalidated_against_policy(plan, contract, capability_policy):
    unsafe = policy.Task(
        task_id="unsafe-task",
        task_type="delete-database",
        objective="Attempt a forbidden mutation.",
        expected_artifact_type="technical-report",
        dependencies=("quality-checkpoint",),
        required_inputs=("checkpoint-result",),
        coverage_tags=contract.required_sections,
        evidence_types=contract.required_evidence_types,
    )
    patch = policy.PlanPatch(
        add_tasks=(unsafe,),
        reason=policy.ReplanReason.TASK_FAILURE,
        evidence_task_id="quality-checkpoint",
    )
    with pytest.raises(policy.PolicyError, match="FORBIDDEN_ACTION"):
        policy.apply_plan_patch(plan, patch, contract, capability_policy)


def test_noop_patch_rejected():
    with pytest.raises(ValidationError, match="at least one mutation"):
        policy.PlanPatch(
            reason=policy.ReplanReason.TASK_FAILURE,
            evidence_task_id="compare-routes",
        )


def test_replan_budget_enforced(contract):
    with pytest.raises(policy.PolicyError, match="REPLAN_BUDGET_EXCEEDED"):
        policy.validate_replan_budget(contract.max_replans, contract)


def test_default_run_replans_and_completes():
    state = lab.run_research_plan()
    assert state.status == policy.RunStatus.COMPLETED
    assert state.plan.version == 2
    assert state.replan_count == 1
    assert state.checkpoint.status == policy.CheckpointStatus.PASS
    assert any(output.artifact_type == "technical-report" for output in state.outputs)


def test_failed_source_remains_in_audit_history():
    state = lab.run_research_plan()
    failed = state.task_states["read-implementation-guidance"]
    assert failed.status == policy.TaskStatus.FAILED
    assert failed.error_code == policy.FailureCode.SOURCE_UNAVAILABLE
    assert "read-implementation-guidance" in {task.task_id for task in state.plan.tasks}
    assert any(
        event.event_type == policy.PlanEventType.TASK_FAILED
        and event.task_id == "read-implementation-guidance"
        for event in state.events
    )


def test_completion_requires_checkpoint_and_deliverable(contract):
    plan = lab.build_initial_plan()
    state = lab.RunState(
        plan=plan,
        task_states={
            task.task_id: policy.TaskState(
                task_id=task.task_id, status=policy.TaskStatus.SUCCEEDED
            )
            for task in plan.tasks
        },
    )
    assert policy.get_ready_tasks(plan, state.task_states) == []
    assert lab.evaluate_completion(state, contract) == policy.RunStatus.BLOCKED


def test_conflicting_evidence_triggers_bounded_reconciliation():
    state = lab.run_research_plan(lab.RunOptions(inject_conflict=True))
    assert state.status == policy.RunStatus.COMPLETED
    assert state.plan.version == 3
    assert state.replan_count == 2
    assert state.task_states["quality-checkpoint"].attempt == 2
    assert "reconcile-conflicting-evidence" in state.task_states
    assert any(
        event.event_type == policy.PlanEventType.CHECKPOINT_FAILED
        for event in state.events
    )


def test_replan_exhaustion_escalates_instead_of_looping():
    state = lab.run_research_plan(
        lab.RunOptions(inject_conflict=True),
        contract=lab.build_goal_contract(max_replans=1),
    )
    assert state.status == policy.RunStatus.ESCALATED
    assert state.replan_count == 1
    assert "REPLAN_BUDGET_EXCEEDED" in state.events[-1].detail


def test_transient_timeout_retries_once_then_completes():
    state = lab.run_research_plan(
        lab.RunOptions(transient_timeout_task="read-adaptive-rag-primary")
    )
    assert state.status == policy.RunStatus.COMPLETED
    assert state.task_states["read-adaptive-rag-primary"].attempt == 2
    assert sum(
        event.event_type == policy.PlanEventType.TASK_RETRIED
        for event in state.events
    ) == 1


def test_outputs_are_immutable_and_preserve_provenance():
    state = lab.run_research_plan()
    evidence = next(
        output
        for output in state.outputs
        if output.task_id == "read-adaptive-rag-primary"
    )
    assert evidence.source_refs[0].source_id == "adaptive-rag-2024"
    assert len(evidence.output_hash) == 64
    with pytest.raises(ValidationError):
        evidence.content = "mutated"


def test_task_output_schema_is_deeply_immutable(plan):
    with pytest.raises(TypeError):
        plan.tasks[0].output_schema[0] = ("content", "bytes")


def test_execution_keys_bind_plan_version_task_and_attempt(plan):
    task = plan.tasks[0]
    first = policy.make_execution_key(plan, task, 1)
    assert first == policy.make_execution_key(plan, task, 1)
    assert first != policy.make_execution_key(plan, task, 2)
    assert first != policy.make_execution_key(
        plan.model_copy(update={"version": 2}), task, 1
    )
