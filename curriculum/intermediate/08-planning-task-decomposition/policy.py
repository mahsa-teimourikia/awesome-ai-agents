"""Framework-neutral contracts and policy for Course 08 planning labs.

The planner may propose a plan. Only this application-owned layer can validate
capabilities, budgets, graph structure, patches, and completion conditions.
"""

from __future__ import annotations

from collections import deque
from enum import Enum
import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TASK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class FailureCode(str, Enum):
    TIMEOUT = "TIMEOUT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    AUTH_DENIED = "AUTH_DENIED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class CheckpointStatus(str, Enum):
    PASS = "PASS"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONFLICT = "CONFLICT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    INVALID_PLAN = "INVALID_PLAN"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class PlanEventType(str, Enum):
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    TASK_READY = "TASK_READY"
    TASK_STARTED = "TASK_STARTED"
    TASK_SUCCEEDED = "TASK_SUCCEEDED"
    TASK_FAILED = "TASK_FAILED"
    TASK_BLOCKED = "TASK_BLOCKED"
    TASK_RETRIED = "TASK_RETRIED"
    CHECKPOINT_FAILED = "CHECKPOINT_FAILED"
    CHECKPOINT_PASSED = "CHECKPOINT_PASSED"
    REPLAN_TRIGGERED = "REPLAN_TRIGGERED"
    PLAN_PATCH_PROPOSED = "PLAN_PATCH_PROPOSED"
    PLAN_PATCH_APPLIED = "PLAN_PATCH_APPLIED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_BLOCKED = "RUN_BLOCKED"
    RUN_ESCALATED = "RUN_ESCALATED"


class ToolEffect(str, Enum):
    READ = "READ"
    ANALYZE = "ANALYZE"
    WRITE = "WRITE"


class ReplanReason(str, Enum):
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MISSING_COVERAGE = "MISSING_COVERAGE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    TASK_FAILURE = "TASK_FAILURE"
    CONSTRAINT_CHANGED = "CONSTRAINT_CHANGED"


class PolicyError(ValueError):
    """A deterministic planning or execution-policy violation."""


class ToolDefinition(FrozenModel):
    name: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    effect: ToolEffect
    allowed_task_types: tuple[str, ...] = Field(min_length=1)
    output_artifact_types: tuple[str, ...] = Field(min_length=1)
    requires_approval: bool = False


class CapabilityPolicy(FrozenModel):
    policy_version: str = Field(min_length=1, max_length=32)
    tools: tuple[ToolDefinition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_tools(self) -> "CapabilityPolicy":
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("Capability policy contains duplicate tool names")
        return self

    def tool_map(self) -> dict[str, ToolDefinition]:
        return {tool.name: tool for tool in self.tools}


class GoalContract(FrozenModel):
    goal_id: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    objective: str = Field(min_length=1, max_length=500)
    audience: str = Field(min_length=1, max_length=200)
    required_deliverables: tuple[str, ...] = Field(min_length=1)
    required_sections: tuple[str, ...] = Field(min_length=1)
    required_evidence_types: tuple[str, ...] = Field(min_length=1)
    forbidden_actions: tuple[str, ...] = ()
    allowed_capabilities: tuple[str, ...] = Field(min_length=1)
    max_tasks: int = Field(gt=0, le=100)
    max_replans: int = Field(ge=0, le=10)
    max_attempts_per_task: int = Field(gt=0, le=10)
    max_total_attempts: int = Field(gt=0, le=500)
    max_total_cost_usd: float = Field(ge=0)
    deadline_ms: float = Field(gt=0)

    @field_validator(
        "required_deliverables",
        "required_sections",
        "required_evidence_types",
        "allowed_capabilities",
        "forbidden_actions",
    )
    @classmethod
    def normalized_unique_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("Contract values must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Contract values must be unique")
        return normalized


class Task(FrozenModel):
    task_id: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    task_type: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    objective: str = Field(min_length=1, max_length=500)
    expected_artifact_type: str = Field(
        min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern
    )
    dependencies: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()
    suggested_tools: tuple[str, ...] = ()
    coverage_tags: tuple[str, ...] = ()
    evidence_types: tuple[str, ...] = ()
    output_schema: tuple[tuple[str, str], ...] = ()
    max_attempts: int = Field(default=1, gt=0, le=10)
    timeout_ms: float = Field(default=30_000.0, gt=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    risk: str = Field(default="low", pattern=r"^(low|medium|high)$")

    @field_validator("dependencies", "suggested_tools")
    @classmethod
    def unique_identifiers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Task dependencies and suggested tools must be unique")
        for value in values:
            if not TASK_ID_PATTERN.fullmatch(value):
                raise ValueError(f"Invalid identifier: {value}")
        return values

    @field_validator("required_inputs", "coverage_tags", "evidence_types")
    @classmethod
    def unique_nonempty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("Task contract values must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("Task contract values must be unique")
        return values


class TaskState(StrictModel):
    task_id: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    attempt: int = Field(default=0, ge=0)
    status: TaskStatus = TaskStatus.PENDING
    execution_key: str | None = None
    artifact_id: str | None = None
    error_code: FailureCode | None = None


class SourceRef(FrozenModel):
    source_id: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=500)
    source_version: str = Field(min_length=1, max_length=100)
    retrieved_at: str = Field(min_length=1, max_length=64)
    trust_level: str = Field(pattern=r"^(primary|official|controlled_fixture)$")


class TaskOutput(FrozenModel):
    task_id: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    plan_version: int = Field(gt=0)
    attempt: int = Field(gt=0)
    status: TaskStatus
    artifact_type: str = Field(min_length=1, max_length=64)
    artifact_id: str = Field(min_length=1, max_length=100)
    execution_key: str = Field(min_length=1, max_length=100)
    evidence_types: tuple[str, ...] = ()
    coverage_tags: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()
    content: str = Field(min_length=1)
    output_hash: str = Field(min_length=64, max_length=64)
    created_at: str = Field(min_length=1, max_length=64)
    cost_usd: float = Field(ge=0)
    elapsed_ms: float = Field(ge=0)


class Plan(FrozenModel):
    plan_id: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    version: int = Field(default=1, gt=0)
    goal_id: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    tasks: tuple[Task, ...] = Field(min_length=1)
    created_at: str = Field(min_length=1, max_length=64)
    parent_version: int | None = Field(default=None, gt=0)
    mutation_reason: ReplanReason | None = None
    patch_digest: str | None = Field(default=None, min_length=64, max_length=64)


class DependencyEdge(FrozenModel):
    prerequisite: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)
    dependent: str = Field(min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern)


class PlanPatch(FrozenModel):
    add_tasks: tuple[Task, ...] = ()
    remove_tasks: tuple[str, ...] = ()
    add_edges: tuple[DependencyEdge, ...] = ()
    remove_edges: tuple[DependencyEdge, ...] = ()
    reason: ReplanReason
    evidence_task_id: str = Field(
        min_length=1, max_length=64, pattern=TASK_ID_PATTERN.pattern
    )

    @model_validator(mode="after")
    def contains_mutation(self) -> "PlanPatch":
        if not (self.add_tasks or self.remove_tasks or self.add_edges or self.remove_edges):
            raise ValueError("Plan patch must contain at least one mutation")
        return self


class CheckpointResult(FrozenModel):
    status: CheckpointStatus
    missing_requirements: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    reason: str = Field(min_length=1, max_length=500)


class PlanEvent(FrozenModel):
    sequence: int = Field(gt=0)
    event_type: PlanEventType
    plan_version: int = Field(gt=0)
    task_id: str | None = None
    detail: str = Field(min_length=1, max_length=500)


class PlanQualityMetrics(FrozenModel):
    task_count: int = Field(ge=0)
    layer_count: int = Field(ge=0)
    parallel_task_count: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    critical_path_ms: float = Field(ge=0)
    section_coverage_rate: float = Field(ge=0, le=1)
    evidence_coverage_rate: float = Field(ge=0, le=1)


def _task_map(plan: Plan) -> dict[str, Task]:
    task_by_id: dict[str, Task] = {}
    for task in plan.tasks:
        if task.task_id in task_by_id:
            raise PolicyError(f"DUPLICATE_TASK_ID: {task.task_id}")
        task_by_id[task.task_id] = task
    return task_by_id


def validate_dag(plan: Plan) -> None:
    """Reject duplicate IDs, bad dependencies, self-edges, and cycles in O(V+E)."""

    task_by_id = _task_map(plan)
    indegree = {task_id: 0 for task_id in task_by_id}
    dependents = {task_id: [] for task_id in task_by_id}

    for task in plan.tasks:
        for dependency in task.dependencies:
            if dependency not in task_by_id:
                raise PolicyError(
                    f"MISSING_DEPENDENCY: {dependency} required by {task.task_id}"
                )
            if dependency == task.task_id:
                raise PolicyError(f"SELF_DEPENDENCY: {task.task_id}")
            indegree[task.task_id] += 1
            dependents[dependency].append(task.task_id)

    ready = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
    visited = 0
    while ready:
        task_id = ready.popleft()
        visited += 1
        for dependent in sorted(dependents[task_id]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)

    if visited != len(task_by_id):
        raise PolicyError("CYCLE_DETECTED: plan is not a DAG")


def topological_layers(plan: Plan) -> list[list[Task]]:
    validate_dag(plan)
    task_by_id = _task_map(plan)
    indegree = {task_id: len(task.dependencies) for task_id, task in task_by_id.items()}
    dependents = {task_id: [] for task_id in task_by_id}
    for task in plan.tasks:
        for dependency in task.dependencies:
            dependents[dependency].append(task.task_id)

    current = sorted(task_id for task_id, degree in indegree.items() if degree == 0)
    layers: list[list[Task]] = []
    while current:
        layers.append([task_by_id[task_id] for task_id in current])
        following: list[str] = []
        for task_id in current:
            for dependent in dependents[task_id]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    following.append(dependent)
        current = sorted(following)
    return layers


def _critical_path_ms(plan: Plan) -> float:
    longest: dict[str, float] = {}
    for layer in topological_layers(plan):
        for task in layer:
            dependency_time = max((longest[dep] for dep in task.dependencies), default=0.0)
            longest[task.task_id] = dependency_time + task.timeout_ms
    return max(longest.values(), default=0.0)


def validate_plan_coverage(plan: Plan, contract: GoalContract) -> tuple[float, float]:
    sections = {tag for task in plan.tasks for tag in task.coverage_tags}
    evidence_types = {kind for task in plan.tasks for kind in task.evidence_types}
    deliverables = {task.expected_artifact_type for task in plan.tasks}

    missing_sections = sorted(set(contract.required_sections) - sections)
    missing_evidence = sorted(set(contract.required_evidence_types) - evidence_types)
    missing_deliverables = sorted(set(contract.required_deliverables) - deliverables)
    if missing_sections:
        raise PolicyError(f"MISSING_SECTION_COVERAGE: {', '.join(missing_sections)}")
    if missing_evidence:
        raise PolicyError(f"MISSING_EVIDENCE_COVERAGE: {', '.join(missing_evidence)}")
    if missing_deliverables:
        raise PolicyError(f"MISSING_DELIVERABLE: {', '.join(missing_deliverables)}")

    section_rate = len(sections & set(contract.required_sections)) / len(
        contract.required_sections
    )
    evidence_rate = len(evidence_types & set(contract.required_evidence_types)) / len(
        contract.required_evidence_types
    )
    return section_rate, evidence_rate


def validate_plan(
    plan: Plan, contract: GoalContract, capability_policy: CapabilityPolicy
) -> PlanQualityMetrics:
    validate_dag(plan)
    task_by_id = _task_map(plan)
    if plan.goal_id != contract.goal_id:
        raise PolicyError("GOAL_ID_MISMATCH")
    if len(plan.tasks) > contract.max_tasks:
        raise PolicyError(f"PLAN_TOO_LARGE: {len(plan.tasks)} > {contract.max_tasks}")

    tools = capability_policy.tool_map()
    allowed = set(contract.allowed_capabilities)
    forbidden = set(contract.forbidden_actions)
    total_attempts = 0
    total_cost = 0.0

    for task in plan.tasks:
        dependency_types = {
            task_by_id[dependency].expected_artifact_type
            for dependency in task.dependencies
        }
        required_input_types = set(task.required_inputs)
        if dependency_types - required_input_types:
            raise PolicyError(
                f"DEPENDENCY_OUTPUT_MISMATCH: {task.task_id}: "
                f"{sorted(dependency_types - required_input_types)}"
            )
        if required_input_types - dependency_types:
            raise PolicyError(
                f"UNSATISFIED_INPUT_CONTRACT: {task.task_id}: "
                f"{sorted(required_input_types - dependency_types)}"
            )
        if task.task_type in forbidden or set(task.suggested_tools) & forbidden:
            raise PolicyError(f"FORBIDDEN_ACTION: {task.task_id}")
        if task.max_attempts > contract.max_attempts_per_task:
            raise PolicyError(f"TASK_ATTEMPT_LIMIT: {task.task_id}")
        total_attempts += task.max_attempts
        total_cost += task.estimated_cost_usd * task.max_attempts
        for tool_name in task.suggested_tools:
            if tool_name not in allowed:
                raise PolicyError(f"PLAN_TOOL_NOT_ALLOWED: {tool_name}")
            tool = tools.get(tool_name)
            if tool is None:
                raise PolicyError(f"UNKNOWN_TOOL: {tool_name}")
            if task.task_type not in tool.allowed_task_types:
                raise PolicyError(f"TOOL_TASK_MISMATCH: {tool_name} for {task.task_type}")
            if task.expected_artifact_type not in tool.output_artifact_types:
                raise PolicyError(
                    f"TOOL_OUTPUT_MISMATCH: {tool_name} cannot produce "
                    f"{task.expected_artifact_type}"
                )
            if tool.effect == ToolEffect.WRITE and tool.requires_approval:
                raise PolicyError(f"APPROVAL_REQUIRED: {tool_name}")

    if total_attempts > contract.max_total_attempts:
        raise PolicyError(
            f"TOTAL_ATTEMPT_BUDGET_EXCEEDED: {total_attempts} > "
            f"{contract.max_total_attempts}"
        )
    if total_cost > contract.max_total_cost_usd:
        raise PolicyError(
            f"BUDGET_EXCEEDED: {total_cost:.4f} > {contract.max_total_cost_usd:.4f}"
        )

    critical_path = _critical_path_ms(plan)
    if critical_path > contract.deadline_ms:
        raise PolicyError(
            f"DEADLINE_EXCEEDED: {critical_path:.0f} > {contract.deadline_ms:.0f}"
        )

    section_rate, evidence_rate = validate_plan_coverage(plan, contract)
    layers = topological_layers(plan)
    return PlanQualityMetrics(
        task_count=len(plan.tasks),
        layer_count=len(layers),
        parallel_task_count=sum(max(0, len(layer) - 1) for layer in layers),
        estimated_cost_usd=round(total_cost, 6),
        critical_path_ms=critical_path,
        section_coverage_rate=section_rate,
        evidence_coverage_rate=evidence_rate,
    )


def get_ready_tasks(plan: Plan, task_states: dict[str, TaskState]) -> list[Task]:
    ready_tasks: list[Task] = []
    for task in plan.tasks:
        state = task_states.get(task.task_id)
        status = state.status if state else TaskStatus.PENDING
        if status != TaskStatus.PENDING:
            continue
        if all(
            dependency in task_states
            and task_states[dependency].status == TaskStatus.SUCCEEDED
            for dependency in task.dependencies
        ):
            ready_tasks.append(task)
    return sorted(ready_tasks, key=lambda task: task.task_id)


def get_blocked_tasks(plan: Plan, task_states: dict[str, TaskState]) -> list[Task]:
    """Return pending tasks made unreachable by terminal prerequisite failures."""

    blocked_ids = {
        task_id
        for task_id, state in task_states.items()
        if state.status
        in {
            TaskStatus.FAILED,
            TaskStatus.BLOCKED,
            TaskStatus.SKIPPED,
            TaskStatus.CANCELLED,
        }
    }
    newly_blocked: list[Task] = []
    changed = True
    while changed:
        changed = False
        for task in plan.tasks:
            state = task_states.get(task.task_id)
            if (
                not state
                or state.status != TaskStatus.PENDING
                or task.task_id in blocked_ids
            ):
                continue
            if any(dependency in blocked_ids for dependency in task.dependencies):
                blocked_ids.add(task.task_id)
                newly_blocked.append(task)
                changed = True
    return sorted(newly_blocked, key=lambda task: task.task_id)


def validate_task_inputs(task: Task, inputs: tuple[TaskOutput, ...]) -> None:
    """Validate dependency artifacts before a task reaches an executor."""

    input_by_task = {output.task_id: output for output in inputs}
    missing_dependencies = sorted(set(task.dependencies) - set(input_by_task))
    if missing_dependencies:
        raise PolicyError(
            f"MISSING_INPUT_ARTIFACT: {task.task_id}: {missing_dependencies}"
        )

    allowed_types = set(task.required_inputs)
    unexpected = sorted(
        {
            output.artifact_type
            for output in inputs
            if allowed_types and output.artifact_type not in allowed_types
        }
    )
    if unexpected:
        raise PolicyError(f"UNEXPECTED_INPUT_TYPE: {task.task_id}: {unexpected}")

    provided_types = {output.artifact_type for output in inputs}
    missing_types = sorted(allowed_types - provided_types)
    if missing_types:
        raise PolicyError(f"MISSING_INPUT_TYPE: {task.task_id}: {missing_types}")


def validate_replan_budget(replan_count: int, contract: GoalContract) -> None:
    if replan_count >= contract.max_replans:
        raise PolicyError(
            f"REPLAN_BUDGET_EXCEEDED: {replan_count} >= {contract.max_replans}"
        )


def _patch_digest(patch: PlanPatch) -> str:
    payload = json.dumps(patch.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_plan_patch(
    plan: Plan,
    patch: PlanPatch,
    contract: GoalContract,
    capability_policy: CapabilityPolicy,
) -> Plan:
    """Apply and fully validate a patch without mutating the parent plan."""

    original = _task_map(plan)
    if patch.evidence_task_id not in original:
        raise PolicyError(f"PATCH_EVIDENCE_NOT_FOUND: {patch.evidence_task_id}")
    tasks = {task_id: task.model_copy(deep=True) for task_id, task in original.items()}

    for task_id in patch.remove_tasks:
        if task_id not in tasks:
            raise PolicyError(f"PATCH_REMOVE_TASK_NOT_FOUND: {task_id}")
        del tasks[task_id]

    for task in patch.add_tasks:
        if task.task_id in tasks:
            raise PolicyError(f"PATCH_DUPLICATE_TASK_ID: {task.task_id}")
        tasks[task.task_id] = task.model_copy(deep=True)

    for edge in patch.remove_edges:
        dependent = tasks.get(edge.dependent)
        if dependent is None or edge.prerequisite not in dependent.dependencies:
            raise PolicyError(
                f"PATCH_REMOVE_EDGE_NOT_FOUND: {edge.prerequisite}->{edge.dependent}"
            )
        dependencies = tuple(
            dependency
            for dependency in dependent.dependencies
            if dependency != edge.prerequisite
        )
        tasks[edge.dependent] = Task.model_validate(
            {**dependent.model_dump(mode="python"), "dependencies": dependencies}
        )

    for edge in patch.add_edges:
        if edge.prerequisite not in tasks or edge.dependent not in tasks:
            raise PolicyError(
                f"PATCH_EDGE_ENDPOINT_NOT_FOUND: {edge.prerequisite}->{edge.dependent}"
            )
        dependent = tasks[edge.dependent]
        if edge.prerequisite in dependent.dependencies:
            raise PolicyError(
                f"PATCH_EDGE_ALREADY_EXISTS: {edge.prerequisite}->{edge.dependent}"
            )
        tasks[edge.dependent] = Task.model_validate(
            {
                **dependent.model_dump(mode="python"),
                "dependencies": (*dependent.dependencies, edge.prerequisite),
            }
        )

    new_plan = Plan(
        plan_id=plan.plan_id,
        version=plan.version + 1,
        goal_id=plan.goal_id,
        tasks=tuple(tasks.values()),
        created_at=plan.created_at,
        parent_version=plan.version,
        mutation_reason=patch.reason,
        patch_digest=_patch_digest(patch),
    )
    validate_plan(new_plan, contract, capability_policy)
    return new_plan


def make_execution_key(plan: Plan, task: Task, attempt: int) -> str:
    payload = f"{plan.plan_id}:{plan.version}:{task.task_id}:{attempt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_output_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
