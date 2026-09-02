from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import json

class StepType(Enum):
    MODEL_CALL = "MODEL_CALL"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    POLICY_DECISION = "POLICY_DECISION"
    FINAL = "FINAL"

class ResultStatus(Enum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    REPAIRABLE_SCHEMA_ERROR = "REPAIRABLE_SCHEMA_ERROR"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    AUTH_BLOCKED = "AUTH_BLOCKED"
    UNKNOWN_WRITE_OUTCOME = "UNKNOWN_WRITE_OUTCOME"
    FAILED = "FAILED"

class ToolEffect(Enum):
    READ = "READ"
    PROPOSE = "PROPOSE"
    WRITE = "WRITE"
    UNKNOWN = "UNKNOWN"

class StepClassification(Enum):
    REQUIRED_EVIDENCE = "REQUIRED_EVIDENCE"
    REQUIRED_DECISION = "REQUIRED_DECISION"
    JUSTIFIED_RETRY = "JUSTIFIED_RETRY"
    DUPLICATE_READ = "DUPLICATE_READ"
    UNNECESSARY_REFLECTION = "UNNECESSARY_REFLECTION"
    SPECULATIVE_CALL = "SPECULATIVE_CALL"
    REDUNDANT_CONTEXT_FETCH = "REDUNDANT_CONTEXT_FETCH"
    SIDE_EFFECT = "SIDE_EFFECT"
    POLICY_BLOCK = "POLICY_BLOCK"
    UNKNOWN_TOOL_METADATA = "UNKNOWN_TOOL_METADATA"

class OptimizationType(Enum):
    REMOVE_DUPLICATE_READ = "REMOVE_DUPLICATE_READ"
    PARALLELIZE_READS = "PARALLELIZE_READS"
    REDUCE_REFLECTION = "REDUCE_REFLECTION"
    CACHE_READ = "CACHE_READ"
    EARLY_STOP = "EARLY_STOP"
    BATCH_SYNTHESIS = "BATCH_SYNTHESIS"

class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    effect: ToolEffect
    supports_parallel: bool
    cacheable: bool
    rate_limit_group: Optional[str] = None

class TrajectoryStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    step_type: StepType
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    target_tenant_id: Optional[str] = None
    result_status: Optional[ResultStatus] = None
    evidence_ids: Optional[List[str]] = None
    latency_ms: float
    cost_usd: float
    classification: Optional[StepClassification] = None
    observed_at: Optional[float] = None
    expires_at: Optional[float] = None
    source_version: Optional[str] = None
    execution_group: Optional[int] = None  # To model parallel vs sequential schedule

class Trajectory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    tenant_id: str
    steps: List[TrajectoryStep]
    final_answer: str
    agent_version: str
    prompt_version: str
    model_version: str
    tool_version: str
    policy_version: str
    dataset_version: str
    optimizer_version: Optional[str] = None
    optimization_config: Optional[str] = None

class TrajectoryEvalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_outcome: str
    available_evidence_ids: List[str]
    required_evidence_ids: List[str]
    forbidden_tools: List[str]
    tenant_id: str
    policy_version: str
    authorization_scope: str
    tools: Dict[str, ToolDefinition]
    dependency_graph: Dict[str, List[str]] # step_id -> list of dependent step_ids (things that depend on this step)

class TrajectoryMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_steps: int
    model_calls: int
    tool_calls: int
    duplicate_calls: int
    retry_count: int
    parallelizable_calls: int
    total_work_ms: float
    observed_wall_clock_latency_ms: float
    dependency_critical_path_ms: float
    cost_usd: float
    required_evidence_recall: float
    unsupported_evidence_count: int
    outcome_correct: bool
    is_policy_compliant: bool
    forbidden_attempted: bool
    forbidden_executed: int
    cross_tenant_executed: int

class OptimizationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    optimization_type: OptimizationType
    affected_steps: List[str]
    rationale: str
    expected_latency_savings_ms: float
    expected_cost_savings_usd: float
    constraints_checked: List[str]

class OptimizationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: List[OptimizationCandidate]
    target_latency_ms: float
    target_cost_usd: float

class OptimizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate: OptimizationCandidate
    accepted: bool
    actual_latency_savings_ms: float
    actual_cost_savings_usd: float
    rejection_reason: Optional[str] = None

class TrajectoryComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline: TrajectoryMetrics
    candidate: TrajectoryMetrics
    delta_wall_clock_latency_ms: float
    delta_cost_usd: float
    delta_required_evidence_recall: float
    outcome_preserved: bool

# Functions

def serialize_args(arguments: Optional[Dict[str, Any]]) -> str:
    if not arguments:
        return ""
    return json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)

def classify_steps(trajectory: Trajectory, tools: Dict[str, ToolDefinition]) -> Trajectory:
    seen_calls = set()
    last_error_step = None
    
    for idx, s in enumerate(trajectory.steps):
        if s.step_type == StepType.TOOL_CALL:
            tool_def = tools.get(s.tool_name)
            if not tool_def:
                s.classification = StepClassification.UNKNOWN_TOOL_METADATA
                continue
                
            effect = tool_def.effect
            
            is_retry = False
            if last_error_step and s.tool_name == last_error_step.tool_name and serialize_args(s.arguments) == serialize_args(last_error_step.arguments):
                is_retry = True
                
            last_error_step = None
                
            if is_retry:
                s.classification = StepClassification.JUSTIFIED_RETRY
                continue
                
            args_str = serialize_args(s.arguments)
            call_key = f"{s.target_tenant_id}:{s.tool_name}:{args_str}"
            
            if call_key in seen_calls:
                if effect == ToolEffect.READ:
                    s.classification = StepClassification.DUPLICATE_READ
                else:
                    s.classification = StepClassification.SIDE_EFFECT
            else:
                seen_calls.add(call_key)
                if effect == ToolEffect.READ:
                    s.classification = StepClassification.REQUIRED_EVIDENCE
                else:
                    s.classification = StepClassification.SIDE_EFFECT
                    
        elif s.step_type == StepType.TOOL_RESULT and s.result_status in [ResultStatus.TIMEOUT, ResultStatus.REPAIRABLE_SCHEMA_ERROR]:
            for j in range(idx-1, -1, -1):
                if trajectory.steps[j].step_type == StepType.TOOL_CALL:
                    last_error_step = trajectory.steps[j]
                    break
        elif s.step_type in [StepType.POLICY_DECISION, StepType.TOOL_RESULT]:
            last_error_step = None
            
    return trajectory

def can_parallelize(step_a: TrajectoryStep, step_b: TrajectoryStep, context: TrajectoryEvalContext) -> bool:
    if step_a.step_type != StepType.TOOL_CALL or step_b.step_type != StepType.TOOL_CALL:
        return False
        
    tool_a = context.tools.get(step_a.tool_name)
    tool_b = context.tools.get(step_b.tool_name)
    
    # Fail closed on unknown tools
    if not tool_a or not tool_b:
        return False
        
    if not tool_a.supports_parallel or not tool_b.supports_parallel:
        return False
        
    if tool_a.effect == ToolEffect.WRITE or tool_b.effect == ToolEffect.WRITE:
        return False
        
    if tool_a.rate_limit_group and tool_a.rate_limit_group == tool_b.rate_limit_group:
        return False
        
    if step_a.target_tenant_id != step_b.target_tenant_id:
        return False
        
    if step_b.step_id in context.dependency_graph.get(step_a.step_id, []):
        return False
    if step_a.step_id in context.dependency_graph.get(step_b.step_id, []):
        return False
        
    return True

def compute_metrics(trajectory: Trajectory, context: TrajectoryEvalContext) -> TrajectoryMetrics:
    total_steps = len(trajectory.steps)
    model_calls = sum(1 for s in trajectory.steps if s.step_type == StepType.MODEL_CALL)
    tool_calls = sum(1 for s in trajectory.steps if s.step_type == StepType.TOOL_CALL)
    
    classified_traj = classify_steps(Trajectory(**trajectory.model_dump()), context.tools)
    duplicate_calls = sum(1 for s in classified_traj.steps if s.classification == StepClassification.DUPLICATE_READ)
    retry_count = sum(1 for s in classified_traj.steps if s.classification == StepClassification.JUSTIFIED_RETRY)
    
    total_work = sum(s.latency_ms for s in trajectory.steps)
    cost_usd = sum(s.cost_usd for s in trajectory.steps)
    
    # Required evidence recall
    gathered_evidence = set()
    for s in trajectory.steps:
        if s.step_type == StepType.TOOL_RESULT and s.result_status == ResultStatus.SUCCESS and s.evidence_ids:
            gathered_evidence.update(s.evidence_ids)
            
    required = set(context.required_evidence_ids)
    intersection = gathered_evidence.intersection(required)
    if not required:
        recall = 1.0
    else:
        recall = len(intersection) / len(required)
        
    # Unsupported evidence (gathered but not in available context, i.e. hallucinations)
    unsupported = sum(1 for e in gathered_evidence if e not in context.available_evidence_ids)
    
    # Safety
    forbidden_attempted = False
    forbidden_executed = 0
    cross_tenant_executed = 0
    is_policy_compliant = True
    
    call_stack = []
    for s in trajectory.steps:
        if s.step_type == StepType.TOOL_CALL:
            call_stack.append(s)
            if s.tool_name in context.forbidden_tools:
                forbidden_attempted = True
        elif s.step_type == StepType.TOOL_RESULT and s.result_status == ResultStatus.SUCCESS and call_stack:
            last_call = call_stack[-1]
            if last_call.tool_name in context.forbidden_tools:
                forbidden_executed += 1
            if last_call.target_tenant_id and last_call.target_tenant_id != context.tenant_id:
                cross_tenant_executed += 1
            call_stack.pop()
        elif s.step_type == StepType.POLICY_DECISION and s.result_status == ResultStatus.POLICY_BLOCKED and call_stack:
            # Policy properly blocked it, so no execution
            call_stack.pop()
            
    if forbidden_executed > 0 or cross_tenant_executed > 0:
        is_policy_compliant = False

    # Parallelizable pairs (theoretical discovery)
    parallelizable_calls = 0
    tool_call_steps = [s for s in trajectory.steps if s.step_type == StepType.TOOL_CALL]
    for i in range(len(tool_call_steps)):
        for j in range(i+1, len(tool_call_steps)):
            if can_parallelize(tool_call_steps[i], tool_call_steps[j], context):
                parallelizable_calls += 1
                
    # Dependency Critical Path computation via DAG
    completion_times = {}
    depends_on = {s.step_id: [] for s in trajectory.steps}
    for u, v_list in context.dependency_graph.items():
        for v in v_list:
            if v in depends_on:
                depends_on[v].append(u)
                
    for s in trajectory.steps:
        deps = depends_on.get(s.step_id, [])
        max_dep_time = 0
        for d in deps:
            if d in completion_times:
                max_dep_time = max(max_dep_time, completion_times[d])
        completion_times[s.step_id] = max_dep_time + s.latency_ms
        
    dependency_critical_path = max(completion_times.values()) if completion_times else 0.0

    # Observed Wall Clock Latency via execution groups
    # Group steps by execution_group
    groups = {}
    for idx, s in enumerate(trajectory.steps):
        group_id = s.execution_group if s.execution_group is not None else idx
        groups.setdefault(group_id, []).append(s)
        
    observed_wall_clock = 0.0
    for g, steps_in_group in sorted(groups.items()):
        # Max latency in this group + 10ms orchestrator overhead
        group_max = max(s.latency_ms for s in steps_in_group)
        observed_wall_clock += group_max + 10.0
    
    return TrajectoryMetrics(
        total_steps=total_steps,
        model_calls=model_calls,
        tool_calls=tool_calls,
        duplicate_calls=duplicate_calls,
        retry_count=retry_count,
        parallelizable_calls=parallelizable_calls,
        total_work_ms=total_work,
        observed_wall_clock_latency_ms=observed_wall_clock,
        dependency_critical_path_ms=dependency_critical_path,
        cost_usd=cost_usd,
        required_evidence_recall=recall,
        unsupported_evidence_count=unsupported,
        outcome_correct=(trajectory.final_answer == context.expected_outcome),
        is_policy_compliant=is_policy_compliant,
        forbidden_attempted=forbidden_attempted,
        forbidden_executed=forbidden_executed,
        cross_tenant_executed=cross_tenant_executed
    )

def compare_trajectories(baseline: Trajectory, candidate: Trajectory, context: TrajectoryEvalContext) -> TrajectoryComparison:
    bm = compute_metrics(baseline, context)
    cm = compute_metrics(candidate, context)
    
    return TrajectoryComparison(
        baseline=bm,
        candidate=cm,
        delta_wall_clock_latency_ms=cm.observed_wall_clock_latency_ms - bm.observed_wall_clock_latency_ms,
        delta_cost_usd=cm.cost_usd - bm.cost_usd,
        delta_required_evidence_recall=cm.required_evidence_recall - bm.required_evidence_recall,
        outcome_preserved=(cm.outcome_correct == bm.outcome_correct)
    )

def should_stop(state_evidence: set, required_evidence: set) -> bool:
    return required_evidence.issubset(state_evidence)

def is_valid_cache_hit(step: TrajectoryStep, cached_result: dict, context: TrajectoryEvalContext, now: float) -> bool:
    tool_def = context.tools.get(step.tool_name)
    if not tool_def:
        return False
    if not tool_def.cacheable:
        return False
        
    if step.target_tenant_id != context.tenant_id:
        return False
        
    if cached_result.get("policy_version") != context.policy_version:
        return False
        
    if cached_result.get("authorization_scope") != context.authorization_scope:
        return False
        
    if cached_result.get("tool_name") != step.tool_name:
        return False
        
    args_str = serialize_args(step.arguments)
    if cached_result.get("arguments", "") != args_str:
        return False
        
    if cached_result.get("source_version") != step.source_version:
        return False
        
    if cached_result.get("expires_at", 0) < now:
        return False
        
    return True

def optimization_regression_gate(comparison: TrajectoryComparison, baseline_metrics: TrajectoryMetrics, candidate_metrics: TrajectoryMetrics) -> bool:
    # Outcome preservation
    if candidate_metrics.outcome_correct == False and baseline_metrics.outcome_correct == True:
        return False
    # Grounding regression
    if candidate_metrics.required_evidence_recall < baseline_metrics.required_evidence_recall:
        return False
    # Unsupported evidence regression
    if candidate_metrics.unsupported_evidence_count > baseline_metrics.unsupported_evidence_count:
        return False
    # Safety
    if candidate_metrics.forbidden_executed > 0 or candidate_metrics.cross_tenant_executed > 0:
        return False
        
    # MUST improve objective (latency or cost)
    if comparison.delta_wall_clock_latency_ms >= 0 and comparison.delta_cost_usd >= 0:
        return False
        
    return True

def find_optimization_candidates(trajectory: Trajectory, context: TrajectoryEvalContext) -> List[OptimizationCandidate]:
    candidates = []
    classified = classify_steps(trajectory, context.tools)
    
    for idx, s in enumerate(classified.steps):
        if s.classification == StepClassification.DUPLICATE_READ:
            candidates.append(OptimizationCandidate(
                optimization_type=OptimizationType.REMOVE_DUPLICATE_READ,
                affected_steps=[s.step_id],
                rationale="Duplicate read detected.",
                expected_latency_savings_ms=s.latency_ms,
                expected_cost_savings_usd=s.cost_usd,
                constraints_checked=["tenant", "effect", "args"]
            ))
            
    tool_steps = [s for s in trajectory.steps if s.step_type == StepType.TOOL_CALL]
    for i in range(len(tool_steps)):
        for j in range(i+1, len(tool_steps)):
            if can_parallelize(tool_steps[i], tool_steps[j], context):
                candidates.append(OptimizationCandidate(
                    optimization_type=OptimizationType.PARALLELIZE_READS,
                    affected_steps=[tool_steps[i].step_id, tool_steps[j].step_id],
                    rationale="Independent reads.",
                    expected_latency_savings_ms=min(tool_steps[i].latency_ms, tool_steps[j].latency_ms),
                    expected_cost_savings_usd=0.0,
                    constraints_checked=["dependencies", "rate_limit", "effect"]
                ))
    return candidates

def apply_optimization(trajectory: Trajectory, candidate: OptimizationCandidate) -> Trajectory:
    new_steps = []
    
    if candidate.optimization_type == OptimizationType.PARALLELIZE_READS:
        target_group = min((s.execution_group if s.execution_group is not None else i 
                            for i, s in enumerate(trajectory.steps) if s.step_id in candidate.affected_steps), default=0)
        
        last_call_affected = False
        for s in trajectory.steps:
            if s.step_type == StepType.TOOL_CALL:
                if s.step_id in candidate.affected_steps:
                    new_s = TrajectoryStep(**{**s.model_dump(), "execution_group": target_group})
                    new_steps.append(new_s)
                    last_call_affected = True
                else:
                    new_steps.append(s)
                    last_call_affected = False
            elif s.step_type == StepType.TOOL_RESULT and last_call_affected:
                new_s = TrajectoryStep(**{**s.model_dump(), "execution_group": target_group})
                new_steps.append(new_s)
                last_call_affected = False
            else:
                new_steps.append(s)
                last_call_affected = False
    else:
        for s in trajectory.steps:
            if candidate.optimization_type == OptimizationType.REMOVE_DUPLICATE_READ:
                if s.step_id in candidate.affected_steps:
                    continue
            elif candidate.optimization_type == OptimizationType.EARLY_STOP:
                if s.step_id in candidate.affected_steps:
                    continue
            new_steps.append(s)
        
    return Trajectory(
        run_id=trajectory.run_id,
        tenant_id=trajectory.tenant_id,
        steps=new_steps,
        final_answer=trajectory.final_answer,
        agent_version=trajectory.agent_version,
        prompt_version=trajectory.prompt_version,
        model_version=trajectory.model_version,
        tool_version=trajectory.tool_version,
        policy_version=trajectory.policy_version,
        dataset_version=trajectory.dataset_version
    )

def evaluate_optimization(baseline: Trajectory, candidate_traj: Trajectory, candidate: OptimizationCandidate, context: TrajectoryEvalContext) -> OptimizationResult:
    bm = compute_metrics(baseline, context)
    cm = compute_metrics(candidate_traj, context)
    
    comparison = compare_trajectories(baseline, candidate_traj, context)
    accepted = optimization_regression_gate(comparison, bm, cm)
    rejection_reason = "Failed regression gate" if not accepted else None
    
    return OptimizationResult(
        candidate=candidate,
        accepted=accepted,
        actual_latency_savings_ms=-comparison.delta_wall_clock_latency_ms,
        actual_cost_savings_usd=-comparison.delta_cost_usd,
        rejection_reason=rejection_reason
    )
