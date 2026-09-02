from enum import Enum
from typing import List, Optional, Set, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
import hashlib
import json

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
    CYCLE_INTRODUCED = "CYCLE_INTRODUCED"
    UNKNOWN = "UNKNOWN"

class CheckpointStatus(str, Enum):
    PASS = "PASS"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONFLICT = "CONFLICT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class RunStatus(str, Enum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    INVALID_PLAN = "INVALID_PLAN"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"

class PlanEvent(str, Enum):
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    TASK_READY = "TASK_READY"
    TASK_STARTED = "TASK_STARTED"
    TASK_SUCCEEDED = "TASK_SUCCEEDED"
    TASK_FAILED = "TASK_FAILED"
    CHECKPOINT_FAILED = "CHECKPOINT_FAILED"
    REPLAN_TRIGGERED = "REPLAN_TRIGGERED"
    PLAN_PATCH_PROPOSED = "PLAN_PATCH_PROPOSED"
    PLAN_PATCH_APPLIED = "PLAN_PATCH_APPLIED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_ESCALATED = "RUN_ESCALATED"

class ToolEffect(str, Enum):
    READ = "READ"
    WRITE = "WRITE"

class ToolDefinition(BaseModel):
    name: str
    effect: ToolEffect
    allowed_task_types: List[str]
    requires_approval: bool = False
    output_schema: Optional[Dict[str, Any]] = None

class GoalContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal_id: str
    objective: str
    audience: str
    required_deliverables: List[str]
    required_sections: List[str]
    required_evidence_types: List[str]
    forbidden_actions: List[str]
    max_tasks: int
    max_replans: int
    max_attempts_per_task: int
    max_total_cost_usd: float
    deadline_ms: float
    allowed_capabilities: List[str]

class Task(BaseModel):
    task_id: str
    task_type: str
    objective: str
    expected_artifact_type: str
    dependencies: List[str] = Field(default_factory=list)
    suggested_tools: List[str] = Field(default_factory=list)
    required_inputs: List[str] = Field(default_factory=list)
    max_attempts: int = 1
    timeout_ms: float = 30000.0
    status: TaskStatus = TaskStatus.PENDING
    estimated_cost: Optional[float] = None
    risk: Optional[str] = None

class TaskState(BaseModel):
    task_id: str
    attempt: int = 1
    status: TaskStatus = TaskStatus.PENDING
    artifact_id: Optional[str] = None
    artifact_type: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    source_refs: List[str] = Field(default_factory=list)
    output_hash: Optional[str] = None
    created_at: float = 0.0
    error_code: Optional[FailureCode] = None

class Plan(BaseModel):
    plan_id: str
    version: int = 1
    goal_id: str
    tasks: List[Task] = Field(default_factory=list)
    created_at: float = 0.0
    parent_version: Optional[int] = None
    mutation_reason: Optional[str] = None

class PlanPatch(BaseModel):
    add_tasks: List[Task] = Field(default_factory=list)
    remove_tasks: List[str] = Field(default_factory=list)
    add_edges: List[Tuple[str, str]] = Field(default_factory=list) # (from, to)
    remove_edges: List[Tuple[str, str]] = Field(default_factory=list) # (from, to)
    reason: str

class CheckpointResult(BaseModel):
    status: CheckpointStatus
    missing_requirements: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    reason: str


class PolicyError(Exception):
    pass


def validate_dag(plan: Plan) -> None:
    # 1. Unique IDs
    task_ids = set()
    for t in plan.tasks:
        if t.task_id in task_ids:
            raise PolicyError(f"Duplicate task ID: {t.task_id}")
        task_ids.add(t.task_id)

    # 2. Dependencies exist and no self-dependency
    for t in plan.tasks:
        for dep in t.dependencies:
            if dep not in task_ids:
                raise PolicyError(f"Missing dependency: {dep} for task {t.task_id}")
            if dep == t.task_id:
                raise PolicyError(f"Self dependency: {t.task_id}")

    # 3. Acyclic graph
    visited = set()
    path = set()

    def visit(tid: str):
        if tid in path:
            raise PolicyError("Cycle detected in plan DAG")
        if tid in visited:
            return
        path.add(tid)
        t = next(x for x in plan.tasks if x.task_id == tid)
        for dep in t.dependencies:
            visit(dep)
        path.remove(tid)
        visited.add(tid)

    for t in plan.tasks:
        visit(t.task_id)


def topological_layers(plan: Plan) -> List[List[Task]]:
    validate_dag(plan)
    
    layers = []
    task_by_id = {t.task_id: t for t in plan.tasks}
    in_degree = {t.task_id: len(t.dependencies) for t in plan.tasks}
    
    # Track nodes whose dependencies are satisfied
    ready = [tid for tid, deg in in_degree.items() if deg == 0]
    
    # Build forward edges
    adj = {t.task_id: [] for t in plan.tasks}
    for t in plan.tasks:
        for dep in t.dependencies:
            adj[dep].append(t.task_id)

    while ready:
        next_ready = []
        layer_tasks = []
        for tid in ready:
            layer_tasks.append(task_by_id[tid])
            for dependent in adj[tid]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    next_ready.append(dependent)
        
        # Sort layer by ID for determinism
        layer_tasks.sort(key=lambda t: t.task_id)
        layers.append(layer_tasks)
        ready = next_ready

    return layers


def validate_plan_coverage(plan: Plan, contract: GoalContract) -> None:
    # E.g. make sure there's at least one task covering required sections / evidence types
    # In a simplified implementation, we check that every required section is mentioned in an objective
    plan_text = " ".join(t.objective.lower() for t in plan.tasks)
    
    for req in contract.required_sections:
        if req.lower() not in plan_text:
            raise PolicyError(f"Required coverage missing: {req}")


def validate_plan(plan: Plan, contract: GoalContract) -> None:
    validate_dag(plan)
    
    if len(plan.tasks) > contract.max_tasks:
        raise PolicyError(f"Max tasks exceeded: {len(plan.tasks)} > {contract.max_tasks}")
        
    for t in plan.tasks:
        if t.max_attempts > contract.max_attempts_per_task:
            raise PolicyError(f"Task {t.task_id} exceeds max attempts: {t.max_attempts} > {contract.max_attempts_per_task}")
            
        for tool in t.suggested_tools:
            if tool not in contract.allowed_capabilities:
                raise PolicyError(f"Unauthorized tool requested: {tool}")

    validate_plan_coverage(plan, contract)


def get_ready_tasks(plan: Plan, task_states: Dict[str, TaskState]) -> List[Task]:
    # Task is ready if its state is PENDING and all dependencies are SUCCEEDED
    ready_tasks = []
    
    for t in plan.tasks:
        state = task_states.get(t.task_id)
        status = state.status if state else TaskStatus.PENDING
        
        if status != TaskStatus.PENDING:
            continue
            
        deps_satisfied = True
        for dep in t.dependencies:
            dep_state = task_states.get(dep)
            if not dep_state or dep_state.status != TaskStatus.SUCCEEDED:
                deps_satisfied = False
                break
                
        if deps_satisfied:
            ready_tasks.append(t)
            
    # Sort for deterministic execution
    ready_tasks.sort(key=lambda x: x.task_id)
    return ready_tasks


def apply_plan_patch(plan: Plan, patch: PlanPatch) -> Plan:
    tasks = plan.tasks.copy()
    task_by_id = {t.task_id: t for t in tasks}
    
    # Remove edges
    for frm, to in patch.remove_edges:
        if to in task_by_id:
            if frm in task_by_id[to].dependencies:
                task_by_id[to].dependencies.remove(frm)
                
    # Add tasks
    for t in patch.add_tasks:
        tasks.append(t)
        task_by_id[t.task_id] = t
        
    # Remove tasks
    tasks = [t for t in tasks if t.task_id not in patch.remove_tasks]
    task_by_id = {t.task_id: t for t in tasks}
    
    # Add edges
    for frm, to in patch.add_edges:
        if to in task_by_id:
            if frm not in task_by_id[to].dependencies:
                task_by_id[to].dependencies.append(frm)
                
    new_plan = Plan(
        plan_id=plan.plan_id,
        version=plan.version + 1,
        goal_id=plan.goal_id,
        tasks=tasks,
        created_at=plan.created_at,
        parent_version=plan.version,
        mutation_reason=patch.reason
    )
    
    # Will raise if invalid
    validate_dag(new_plan)
    return new_plan

