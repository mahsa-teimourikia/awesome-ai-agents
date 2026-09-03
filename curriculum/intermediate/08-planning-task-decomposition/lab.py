"""Deterministic Course 08 lab: validated DAG scheduling and bounded replanning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from pydantic import Field

from policy import (
    CapabilityPolicy,
    CheckpointResult,
    CheckpointStatus,
    DependencyEdge,
    FailureCode,
    FrozenModel,
    GoalContract,
    Plan,
    PlanEvent,
    PlanEventType,
    PlanPatch,
    PlanQualityMetrics,
    PolicyError,
    ReplanReason,
    RunStatus,
    RuntimeAction,
    SourceRef,
    StrictModel,
    Task,
    TaskOutput,
    TaskState,
    TaskStatus,
    ToolDefinition,
    ToolEffect,
    apply_plan_patch,
    can_attempt,
    checkpoint_action,
    failure_action,
    get_blocked_tasks,
    get_ready_tasks,
    make_execution_key,
    make_output_hash,
    validate_plan,
    validate_replan_budget,
    validate_task_inputs,
)


FIXED_TIME = "2026-01-15T12:00:00+00:00"


class ExecutionResult(FrozenModel):
    succeeded: bool
    content: str = ""
    evidence_types: tuple[str, ...] = ()
    coverage_tags: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()
    failure_code: FailureCode | None = None
    checkpoint: CheckpointResult | None = None
    cost_usd: float = Field(default=0.0, ge=0)
    elapsed_ms: float = Field(default=0.0, ge=0)


class PlanningRunState(StrictModel):
    run_id: str = Field(min_length=1, max_length=64)
    plan_id: str = Field(min_length=1, max_length=64)
    current_plan_version: int = Field(gt=0)
    started_at: str = Field(min_length=1, max_length=64)
    terminal_status: RunStatus = RunStatus.RUNNING
    plan: Plan
    task_states: dict[str, TaskState]
    outputs: tuple[TaskOutput, ...] = ()
    events: tuple[PlanEvent, ...] = ()
    checkpoint: CheckpointResult | None = None
    replan_count: int = Field(default=0, ge=0)
    total_attempts: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0)
    elapsed_ms: float = Field(default=0.0, ge=0)


# Backwards-compatible name used by the existing notebook and external learners.
RunState = PlanningRunState


@dataclass(frozen=True)
class RunOptions:
    inject_conflict: bool = False
    inject_missing_evidence: bool = False
    transient_timeout_task: str | None = None
    transient_invalid_output_task: str | None = None


def build_capability_policy() -> CapabilityPolicy:
    return CapabilityPolicy(
        policy_version="course-08-v1",
        tools=(
            ToolDefinition(
                name="source-library",
                effect=ToolEffect.READ,
                allowed_task_types=("read-source",),
                output_artifact_types=("evidence-bundle",),
            ),
            ToolDefinition(
                name="compare-evidence",
                effect=ToolEffect.ANALYZE,
                allowed_task_types=("compare-routes", "reconcile-evidence"),
                output_artifact_types=("route-comparison", "reconciliation"),
            ),
            ToolDefinition(
                name="quality-check",
                effect=ToolEffect.ANALYZE,
                allowed_task_types=("quality-checkpoint",),
                output_artifact_types=("checkpoint-result",),
            ),
            ToolDefinition(
                name="synthesize-report",
                effect=ToolEffect.ANALYZE,
                allowed_task_types=("synthesize-report",),
                output_artifact_types=("technical-report",),
            ),
        ),
    )


def build_goal_contract(max_replans: int = 2) -> GoalContract:
    return GoalContract(
        goal_id="adaptive-rag-report",
        objective="Research adaptive RAG and produce a cited technical report.",
        audience="Technical builders evaluating retrieval architectures",
        required_deliverables=("technical-report",),
        required_sections=(
            "foundations",
            "routing-strategies",
            "security-implications",
        ),
        required_evidence_types=("primary-paper", "official-documentation"),
        forbidden_actions=("send-email", "delete-database", "execute-untrusted-code"),
        allowed_capabilities=(
            "source-library",
            "compare-evidence",
            "quality-check",
            "synthesize-report",
        ),
        max_tasks=10,
        max_replans=max_replans,
        max_attempts_per_task=2,
        max_total_attempts=16,
        max_total_cost_usd=1.00,
        deadline_ms=60_000,
    )


def _task(
    task_id: str,
    task_type: str,
    objective: str,
    artifact_type: str,
    tool: str,
    *,
    dependencies: tuple[str, ...] = (),
    required_inputs: tuple[str, ...] = (),
    coverage_tags: tuple[str, ...] = (),
    evidence_types: tuple[str, ...] = (),
    max_attempts: int = 1,
    cost: float = 0.02,
    timeout_ms: float = 4_000,
) -> Task:
    return Task(
        task_id=task_id,
        task_type=task_type,
        objective=objective,
        expected_artifact_type=artifact_type,
        dependencies=dependencies,
        required_inputs=required_inputs,
        suggested_tools=(tool,),
        coverage_tags=coverage_tags,
        evidence_types=evidence_types,
        output_schema=(
            ("content", "str"),
            ("source_refs", "tuple[SourceRef, ...]"),
        ),
        max_attempts=max_attempts,
        timeout_ms=timeout_ms,
        estimated_cost_usd=cost,
    )


def build_initial_plan() -> Plan:
    return Plan(
        plan_id="adaptive-rag-plan",
        version=1,
        goal_id="adaptive-rag-report",
        created_at=FIXED_TIME,
        tasks=(
            _task(
                "read-adaptive-rag-primary",
                "read-source",
                "Read the Adaptive-RAG primary paper and capture routing evidence.",
                "evidence-bundle",
                "source-library",
                coverage_tags=("routing-strategies",),
                evidence_types=("primary-paper",),
                max_attempts=2,
            ),
            _task(
                "read-rag-foundation",
                "read-source",
                "Read the foundational RAG paper and establish the baseline.",
                "evidence-bundle",
                "source-library",
                coverage_tags=("foundations",),
                evidence_types=("primary-paper",),
            ),
            _task(
                "read-implementation-guidance",
                "read-source",
                "Read controlled implementation guidance, including security implications.",
                "evidence-bundle",
                "source-library",
                coverage_tags=("security-implications",),
                evidence_types=("official-documentation",),
            ),
            _task(
                "compare-routes",
                "compare-routes",
                "Compare no-retrieval, one-shot, and iterative retrieval routes.",
                "route-comparison",
                "compare-evidence",
                dependencies=(
                    "read-adaptive-rag-primary",
                    "read-rag-foundation",
                    "read-implementation-guidance",
                ),
                required_inputs=("evidence-bundle",),
                coverage_tags=("routing-strategies", "security-implications"),
            ),
            _task(
                "quality-checkpoint",
                "quality-checkpoint",
                "Verify evidence coverage, provenance, and unresolved conflicts.",
                "checkpoint-result",
                "quality-check",
                dependencies=("compare-routes",),
                required_inputs=("route-comparison",),
            ),
            _task(
                "synthesize-report",
                "synthesize-report",
                "Produce the cited adaptive RAG technical report.",
                "technical-report",
                "synthesize-report",
                dependencies=("quality-checkpoint",),
                required_inputs=("checkpoint-result",),
                coverage_tags=(
                    "foundations",
                    "routing-strategies",
                    "security-implications",
                ),
            ),
        ),
    )


def source_replacement_patch() -> PlanPatch:
    replacement = _task(
        "read-replacement-guidance",
        "read-source",
        "Read alternate official implementation guidance with security controls.",
        "evidence-bundle",
        "source-library",
        coverage_tags=("security-implications",),
        evidence_types=("official-documentation",),
    )
    return PlanPatch(
        add_tasks=(replacement,),
        remove_edges=(
            DependencyEdge(
                prerequisite="read-implementation-guidance",
                dependent="compare-routes",
            ),
        ),
        add_edges=(
            DependencyEdge(
                prerequisite="read-replacement-guidance", dependent="compare-routes"
            ),
        ),
        reason=ReplanReason.SOURCE_UNAVAILABLE,
        evidence_task_id="read-implementation-guidance",
    )


def conflict_reconciliation_patch() -> PlanPatch:
    reconciliation = _task(
        "reconcile-conflicting-evidence",
        "reconcile-evidence",
        "Reconcile benchmark-scope differences and preserve stated uncertainty.",
        "reconciliation",
        "compare-evidence",
        dependencies=("compare-routes",),
        required_inputs=("route-comparison",),
        coverage_tags=("routing-strategies", "security-implications"),
    )
    recheck = _task(
        "quality-checkpoint",
        "quality-checkpoint",
        "Verify reconciled evidence coverage, provenance, and remaining conflicts.",
        "checkpoint-result",
        "quality-check",
        dependencies=("reconcile-conflicting-evidence",),
        required_inputs=("reconciliation",),
        max_attempts=2,
    )
    return PlanPatch(
        add_tasks=(reconciliation, recheck),
        remove_tasks=("quality-checkpoint",),
        reason=ReplanReason.CONFLICTING_EVIDENCE,
        evidence_task_id="quality-checkpoint",
    )


def missing_evidence_patch() -> PlanPatch:
    repair = _task(
        "read-missing-evidence",
        "read-source",
        "Read controlled official guidance to repair the checkpoint evidence gap.",
        "evidence-bundle",
        "source-library",
        coverage_tags=("security-implications",),
        evidence_types=("official-documentation",),
    )
    recheck = _task(
        "quality-checkpoint",
        "quality-checkpoint",
        "Verify repaired evidence coverage, provenance, and remaining conflicts.",
        "checkpoint-result",
        "quality-check",
        dependencies=("compare-routes", "read-missing-evidence"),
        required_inputs=("route-comparison", "evidence-bundle"),
        max_attempts=2,
    )
    return PlanPatch(
        add_tasks=(repair, recheck),
        remove_tasks=("quality-checkpoint",),
        reason=ReplanReason.MISSING_COVERAGE,
        evidence_task_id="quality-checkpoint",
    )


def _source(
    source_id: str, source_url: str, source_version: str, trust_level: str
) -> SourceRef:
    return SourceRef(
        source_id=source_id,
        source_url=source_url,
        source_version=source_version,
        retrieved_at=FIXED_TIME,
        trust_level=trust_level,
    )


def _merge(values: Iterable[tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(sorted({item for group in values for item in group}))


class DeterministicExecutor:
    """Offline fixtures with one source failure and optional evidence conflict."""

    def __init__(self, options: RunOptions = RunOptions()) -> None:
        self.options = options
        self.timeout_injected: set[str] = set()
        self.invalid_output_injected: set[str] = set()
        self.receipts: dict[str, ExecutionResult] = {}

    def execute(
        self,
        task: Task,
        execution_key: str,
        inputs: tuple[TaskOutput, ...],
        all_outputs: tuple[TaskOutput, ...],
        contract: GoalContract,
    ) -> ExecutionResult:
        if execution_key in self.receipts:
            return self.receipts[execution_key]

        if (
            self.options.transient_timeout_task == task.task_id
            and task.task_id not in self.timeout_injected
        ):
            self.timeout_injected.add(task.task_id)
            return ExecutionResult(
                succeeded=False,
                failure_code=FailureCode.TIMEOUT,
                cost_usd=0.005,
                elapsed_ms=100,
            )

        if (
            self.options.transient_invalid_output_task == task.task_id
            and task.task_id not in self.invalid_output_injected
        ):
            self.invalid_output_injected.add(task.task_id)
            return ExecutionResult(
                succeeded=False,
                failure_code=FailureCode.INVALID_OUTPUT,
                cost_usd=0.005,
                elapsed_ms=30,
            )

        if task.task_id == "read-implementation-guidance":
            return ExecutionResult(
                succeeded=False,
                failure_code=FailureCode.SOURCE_UNAVAILABLE,
                cost_usd=0.005,
                elapsed_ms=80,
            )

        if task.task_id == "read-adaptive-rag-primary":
            result = ExecutionResult(
                succeeded=True,
                content=(
                    "Adaptive-RAG routes questions by estimated complexity across "
                    "no-retrieval, single-step, and iterative retrieval strategies."
                ),
                evidence_types=("primary-paper",),
                coverage_tags=("routing-strategies",),
                source_refs=(
                    _source(
                        "adaptive-rag-2024",
                        "https://arxiv.org/abs/2403.14403",
                        "v2",
                        "primary",
                    ),
                ),
                cost_usd=0.02,
                elapsed_ms=60,
            )
        elif task.task_id == "read-rag-foundation":
            result = ExecutionResult(
                succeeded=True,
                content="RAG combines parametric generation with retrieved evidence.",
                evidence_types=("primary-paper",),
                coverage_tags=("foundations",),
                source_refs=(
                    _source(
                        "rag-2020",
                        "https://arxiv.org/abs/2005.11401",
                        "v4",
                        "primary",
                    ),
                ),
                cost_usd=0.02,
                elapsed_ms=55,
            )
        elif task.task_id == "read-replacement-guidance":
            missing_evidence = self.options.inject_missing_evidence
            result = ExecutionResult(
                succeeded=True,
                content=(
                    "Official orchestration guidance keeps retrieved content as data "
                    "and places policy checks in application code."
                ),
                evidence_types=() if missing_evidence else ("official-documentation",),
                coverage_tags=() if missing_evidence else ("security-implications",),
                source_refs=(
                    _source(
                        "langgraph-workflows",
                        "https://docs.langchain.com/oss/python/langgraph/workflows-agents",
                        "2026-01",
                        "official",
                    ),
                ),
                cost_usd=0.02,
                elapsed_ms=50,
            )
        elif task.task_id == "read-missing-evidence":
            result = ExecutionResult(
                succeeded=True,
                content="Controlled official guidance fills the recorded evidence gap.",
                evidence_types=("official-documentation",),
                coverage_tags=("security-implications",),
                source_refs=(
                    _source(
                        "controlled-security-guidance",
                        "fixture://adaptive-rag/security-guidance",
                        "v1",
                        "controlled_fixture",
                    ),
                ),
                cost_usd=0.02,
                elapsed_ms=40,
            )
        elif task.task_type == "compare-routes":
            conflict = " [CONFLICT] Iterative retrieval costs vary by benchmark scope."
            result = ExecutionResult(
                succeeded=True,
                content=(
                    "No retrieval is cheapest for simple questions; one-shot retrieval "
                    "is predictable; iterative retrieval handles evidence gaps."
                    + (conflict if self.options.inject_conflict else "")
                ),
                evidence_types=_merge(output.evidence_types for output in inputs),
                coverage_tags=("routing-strategies", "security-implications"),
                source_refs=_merge_source_refs(inputs),
                cost_usd=0.03,
                elapsed_ms=70,
            )
        elif task.task_type == "reconcile-evidence":
            result = ExecutionResult(
                succeeded=True,
                content=(
                    "[RESOLVED] The sources use different workloads; the report states "
                    "that routing benefits and coordination cost must be benchmarked."
                ),
                evidence_types=_merge(output.evidence_types for output in inputs),
                coverage_tags=("routing-strategies", "security-implications"),
                source_refs=_merge_source_refs(inputs),
                cost_usd=0.02,
                elapsed_ms=45,
            )
        elif task.task_type == "quality-checkpoint":
            checkpoint = evaluate_checkpoint(all_outputs, inputs, contract)
            result = ExecutionResult(
                succeeded=checkpoint.status == CheckpointStatus.PASS,
                content=checkpoint.reason,
                evidence_types=_merge(output.evidence_types for output in all_outputs),
                coverage_tags=_merge(output.coverage_tags for output in all_outputs),
                source_refs=_merge_source_refs(all_outputs),
                failure_code=(
                    FailureCode.CONFLICTING_EVIDENCE
                    if checkpoint.status == CheckpointStatus.CONFLICT
                    else FailureCode.INVALID_OUTPUT
                    if checkpoint.status != CheckpointStatus.PASS
                    else None
                ),
                checkpoint=checkpoint,
                cost_usd=0.01,
                elapsed_ms=25,
            )
        elif task.task_type == "synthesize-report":
            result = ExecutionResult(
                succeeded=True,
                content=(
                    "# Adaptive RAG\n\nEvidence-backed comparison of routing strategies, "
                    "foundations, and security implications. Sources: "
                    + ", ".join(ref.source_id for ref in _merge_source_refs(all_outputs))
                ),
                evidence_types=_merge(output.evidence_types for output in all_outputs),
                coverage_tags=contract.required_sections,
                source_refs=_merge_source_refs(all_outputs),
                cost_usd=0.04,
                elapsed_ms=80,
            )
        else:
            result = ExecutionResult(
                succeeded=False,
                failure_code=FailureCode.POLICY_BLOCKED,
                elapsed_ms=1,
            )

        if result.succeeded:
            self.receipts[execution_key] = result
        return result


def _merge_source_refs(outputs: Iterable[TaskOutput]) -> tuple[SourceRef, ...]:
    sources: dict[str, SourceRef] = {}
    for output in outputs:
        for source in output.source_refs:
            sources[source.source_id] = source
    return tuple(sources[source_id] for source_id in sorted(sources))


def evaluate_checkpoint(
    all_outputs: tuple[TaskOutput, ...],
    direct_inputs: tuple[TaskOutput, ...],
    contract: GoalContract,
) -> CheckpointResult:
    if any("[CONFLICT]" in output.content for output in direct_inputs) and not any(
        "[RESOLVED]" in output.content for output in direct_inputs
    ):
        return CheckpointResult(
            status=CheckpointStatus.CONFLICT,
            conflicts=("retrieval-cost-by-benchmark",),
            reason="Evidence scope conflicts; add one bounded reconciliation task.",
        )

    evidence = {kind for output in all_outputs for kind in output.evidence_types}
    coverage = {tag for output in all_outputs for tag in output.coverage_tags}
    missing = sorted(
        (set(contract.required_evidence_types) - evidence)
        | (set(contract.required_sections) - coverage)
    )
    if missing:
        return CheckpointResult(
            status=CheckpointStatus.MISSING_EVIDENCE,
            missing_requirements=tuple(missing),
            reason="Required evidence or report coverage is missing.",
        )
    return CheckpointResult(
        status=CheckpointStatus.PASS,
        reason="Required evidence, coverage, provenance, and conflict checks passed.",
    )


def _append_event(
    state: PlanningRunState,
    event_type: PlanEventType,
    detail: str,
    task_id: str | None = None,
) -> None:
    event = PlanEvent(
        sequence=len(state.events) + 1,
        event_type=event_type,
        plan_version=state.plan.version,
        task_id=task_id,
        detail=detail,
    )
    state.events = (*state.events, event)


def _inputs_for(task: Task, outputs: tuple[TaskOutput, ...]) -> tuple[TaskOutput, ...]:
    latest = {output.task_id: output for output in outputs}
    return tuple(latest[dependency] for dependency in task.dependencies if dependency in latest)


def _record_success(
    state: PlanningRunState,
    task: Task,
    task_state: TaskState,
    result: ExecutionResult,
) -> None:
    payload = {
        "task_id": task.task_id,
        "artifact_type": task.expected_artifact_type,
        "content": result.content,
        "source_ids": [source.source_id for source in result.source_refs],
    }
    output = TaskOutput(
        task_id=task.task_id,
        plan_version=state.plan.version,
        attempt=task_state.attempt,
        status=TaskStatus.SUCCEEDED,
        artifact_type=task.expected_artifact_type,
        artifact_id=f"artifact-{task.task_id}-a{task_state.attempt}",
        execution_key=task_state.execution_key or "missing-execution-key",
        evidence_types=result.evidence_types,
        coverage_tags=result.coverage_tags,
        source_refs=result.source_refs,
        content=result.content,
        output_hash=make_output_hash(payload),
        created_at=FIXED_TIME,
        cost_usd=result.cost_usd,
        elapsed_ms=result.elapsed_ms,
    )
    task_state.status = TaskStatus.SUCCEEDED
    task_state.artifact_id = output.artifact_id
    task_state.error_code = None
    state.outputs = (*state.outputs, output)
    _append_event(state, PlanEventType.TASK_SUCCEEDED, output.artifact_id, task.task_id)
    if result.checkpoint:
        state.checkpoint = result.checkpoint
        _append_event(
            state,
            PlanEventType.CHECKPOINT_PASSED,
            result.checkpoint.reason,
            task.task_id,
        )


def _apply_patch(
    state: PlanningRunState,
    patch: PlanPatch,
    contract: GoalContract,
    capability_policy: CapabilityPolicy,
) -> None:
    validate_replan_budget(state.replan_count, contract)
    _append_event(state, PlanEventType.REPLAN_TRIGGERED, patch.reason.value)
    _append_event(state, PlanEventType.PLAN_PATCH_PROPOSED, patch.reason.value)
    state.plan = apply_plan_patch(state.plan, patch, contract, capability_policy)
    state.current_plan_version = state.plan.version
    state.replan_count += 1
    for task in state.plan.tasks:
        state.task_states.setdefault(task.task_id, TaskState(task_id=task.task_id))
    _append_event(
        state,
        PlanEventType.PLAN_PATCH_APPLIED,
        f"plan v{state.plan.parent_version} -> v{state.plan.version}",
    )


def evaluate_run_status(
    state: PlanningRunState, contract: GoalContract
) -> RunStatus:
    """Evaluate verified completion separately from scheduler queue state."""

    if state.terminal_status in {
        RunStatus.INVALID_PLAN,
        RunStatus.BUDGET_EXHAUSTED,
        RunStatus.ESCALATED,
        RunStatus.CANCELLED,
    }:
        return state.terminal_status
    if not state.checkpoint or state.checkpoint.status != CheckpointStatus.PASS:
        return RunStatus.BLOCKED
    if any(
        task_state.status
        in {
            TaskStatus.PENDING,
            TaskStatus.READY,
            TaskStatus.RUNNING,
            TaskStatus.BLOCKED,
        }
        for task_state in state.task_states.values()
    ):
        return RunStatus.BLOCKED
    deliverables = [
        output
        for output in state.outputs
        if output.artifact_type in contract.required_deliverables
    ]
    if not deliverables:
        return RunStatus.BLOCKED
    final = deliverables[-1]
    if not set(contract.required_sections).issubset(final.coverage_tags):
        return RunStatus.BLOCKED
    if not set(contract.required_evidence_types).issubset(final.evidence_types):
        return RunStatus.BLOCKED
    return RunStatus.COMPLETED


# Compatibility alias for learners who used the first PR revision.
evaluate_completion = evaluate_run_status


def run_research_plan(
    options: RunOptions = RunOptions(),
    contract: GoalContract | None = None,
    capability_policy: CapabilityPolicy | None = None,
) -> PlanningRunState:
    contract = contract or build_goal_contract()
    capability_policy = capability_policy or build_capability_policy()
    plan = build_initial_plan()
    validate_plan(plan, contract, capability_policy)
    state = PlanningRunState(
        run_id="adaptive-rag-run",
        plan_id=plan.plan_id,
        current_plan_version=plan.version,
        started_at=FIXED_TIME,
        plan=plan,
        task_states={task.task_id: TaskState(task_id=task.task_id) for task in plan.tasks},
    )
    executor = DeterministicExecutor(options)
    _append_event(state, PlanEventType.PLAN_CREATED, "initial plan v1")
    _append_event(state, PlanEventType.PLAN_VALIDATED, "DAG, policy, and budgets valid")

    for _ in range(50):
        ready = get_ready_tasks(state.plan, state.task_states)
        if not ready:
            for task in get_blocked_tasks(state.plan, state.task_states):
                state.task_states[task.task_id].status = TaskStatus.BLOCKED
                _append_event(
                    state,
                    PlanEventType.TASK_BLOCKED,
                    "terminal prerequisite did not succeed",
                    task.task_id,
                )
            completion = evaluate_run_status(state, contract)
            state.terminal_status = completion
            _append_event(
                state,
                PlanEventType.RUN_COMPLETED
                if completion == RunStatus.COMPLETED
                else PlanEventType.RUN_BLOCKED,
                completion.value,
            )
            return state

        patch_applied = False
        for task in ready:
            task_state = state.task_states[task.task_id]
            task_state.status = TaskStatus.READY
            _append_event(state, PlanEventType.TASK_READY, "dependencies satisfied", task.task_id)

            if state.total_attempts >= contract.max_total_attempts:
                state.terminal_status = RunStatus.BUDGET_EXHAUSTED
                _append_event(state, PlanEventType.RUN_ESCALATED, "attempt budget exhausted")
                return state
            if not can_attempt(task, task_state, contract):
                state.terminal_status = RunStatus.BUDGET_EXHAUSTED
                _append_event(
                    state,
                    PlanEventType.RUN_ESCALATED,
                    f"task attempt budget exhausted: {task.task_id}",
                    task.task_id,
                )
                return state
            if state.total_cost_usd + task.estimated_cost_usd > contract.max_total_cost_usd:
                state.terminal_status = RunStatus.BUDGET_EXHAUSTED
                _append_event(state, PlanEventType.RUN_ESCALATED, "cost budget exhausted")
                return state

            task_state.attempt += 1
            task_state.status = TaskStatus.RUNNING
            task_state.execution_key = make_execution_key(
                state.plan, task, task_state.attempt
            )
            state.total_attempts += 1
            _append_event(state, PlanEventType.TASK_STARTED, "fixture execution", task.task_id)
            inputs = _inputs_for(task, state.outputs)
            try:
                validate_task_inputs(task, inputs)
            except PolicyError as error:
                state.terminal_status = RunStatus.ESCALATED
                _append_event(state, PlanEventType.RUN_ESCALATED, str(error), task.task_id)
                return state

            result = executor.execute(
                task,
                task_state.execution_key,
                inputs,
                state.outputs,
                contract,
            )
            state.total_cost_usd = round(state.total_cost_usd + result.cost_usd, 6)
            state.elapsed_ms += result.elapsed_ms
            if state.total_cost_usd > contract.max_total_cost_usd:
                state.terminal_status = RunStatus.BUDGET_EXHAUSTED
                _append_event(state, PlanEventType.RUN_ESCALATED, "cost budget exhausted")
                return state
            if state.elapsed_ms > contract.deadline_ms:
                state.terminal_status = RunStatus.BUDGET_EXHAUSTED
                _append_event(state, PlanEventType.RUN_ESCALATED, "deadline exhausted")
                return state

            if result.succeeded:
                _record_success(state, task, task_state, result)
                continue

            task_state.status = TaskStatus.FAILED
            task_state.error_code = result.failure_code
            _append_event(
                state,
                PlanEventType.TASK_FAILED,
                (result.failure_code or FailureCode.UNKNOWN).value,
                task.task_id,
            )
            if result.checkpoint:
                state.checkpoint = result.checkpoint
                _append_event(
                    state,
                    PlanEventType.CHECKPOINT_FAILED,
                    result.checkpoint.reason,
                    task.task_id,
                )

            action = (
                checkpoint_action(result.checkpoint.status)
                if result.checkpoint
                else failure_action(
                    result.failure_code or FailureCode.UNKNOWN,
                    can_attempt(task, task_state, contract),
                )
            )

            if action in {RuntimeAction.RETRY, RuntimeAction.REPAIR}:
                task_state.status = TaskStatus.PENDING
                _append_event(
                    state,
                    PlanEventType.TASK_RETRIED,
                    "bounded transient retry"
                    if action == RuntimeAction.RETRY
                    else "bounded invalid-output repair",
                    task.task_id,
                )
                continue

            try:
                if action == RuntimeAction.REPLAN:
                    patch = (
                        source_replacement_patch()
                        if result.failure_code == FailureCode.SOURCE_UNAVAILABLE
                        else missing_evidence_patch()
                    )
                    _apply_patch(state, patch, contract, capability_policy)
                    if result.checkpoint:
                        state.task_states["quality-checkpoint"].status = TaskStatus.PENDING
                        state.task_states["quality-checkpoint"].error_code = None
                    patch_applied = True
                    break
                if action == RuntimeAction.RECONCILE:
                    _apply_patch(
                        state,
                        conflict_reconciliation_patch(),
                        contract,
                        capability_policy,
                    )
                    state.task_states["quality-checkpoint"].status = TaskStatus.PENDING
                    state.task_states["quality-checkpoint"].error_code = None
                    patch_applied = True
                    break
            except PolicyError as error:
                state.terminal_status = RunStatus.ESCALATED
                _append_event(state, PlanEventType.RUN_ESCALATED, str(error))
                return state

            budget_stop = (
                result.failure_code == FailureCode.BUDGET_EXCEEDED
                or result.checkpoint is not None
                and result.checkpoint.status == CheckpointStatus.BUDGET_EXHAUSTED
            )
            state.terminal_status = (
                RunStatus.BUDGET_EXHAUSTED
                if budget_stop
                else RunStatus.ESCALATED
            )
            _append_event(
                state,
                PlanEventType.RUN_ESCALATED,
                "non-retryable failure"
                if action == RuntimeAction.STOP
                else "failure requires escalation",
            )
            return state

        if patch_applied:
            continue

    state.terminal_status = RunStatus.ESCALATED
    _append_event(state, PlanEventType.RUN_ESCALATED, "scheduler iteration limit")
    return state


def summarize_run(state: PlanningRunState) -> dict[str, object]:
    return {
        "status": state.terminal_status.value,
        "plan_version": state.current_plan_version,
        "replans": state.replan_count,
        "attempts": state.total_attempts,
        "cost_usd": state.total_cost_usd,
        "checkpoint": state.checkpoint.status.value if state.checkpoint else None,
        "failed_tasks": [
            task_id
            for task_id, task_state in state.task_states.items()
            if task_state.status == TaskStatus.FAILED
        ],
        "artifacts": [output.artifact_id for output in state.outputs],
    }


def plan_metrics() -> PlanQualityMetrics:
    return validate_plan(
        build_initial_plan(), build_goal_contract(), build_capability_policy()
    )
