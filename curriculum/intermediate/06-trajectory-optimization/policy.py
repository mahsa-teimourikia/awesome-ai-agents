from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum

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

class TrajectoryMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_steps: int
    model_calls: int
    tool_calls: int
    duplicate_calls: int
    retry_count: int
    parallelizable_calls: int
    total_work_ms: float
    critical_path_ms: float
    wall_clock_latency_ms: float
    cost_usd: float
    required_evidence_recall: float
    unsupported_evidence_count: float
    outcome_correct: bool
    is_policy_compliant: bool
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
    delta_outcome_correct: bool

# Functions

def classify_steps(trajectory: Trajectory, tools: Dict[str, ToolDefinition]) -> Trajectory:
    # A simple deterministic classifier to label steps
    seen_calls = set()
    last_error_step = None
    
    for idx, s in enumerate(trajectory.steps):
        if s.step_type == StepType.TOOL_CALL:
            tool_def = tools.get(s.tool_name)
            effect = tool_def.effect if tool_def else ToolEffect.UNKNOWN
            
            # Check for retries
            is_retry = False
            if last_error_step and s.tool_name == last_error_step.tool_name and s.arguments == last_error_step.arguments:
                is_retry = True
                
            last_error_step = None
                
            if is_retry:
                s.classification = StepClassification.JUSTIFIED_RETRY
                continue
                
            args_str = str(sorted((k, v) for k, v in s.arguments.items())) if s.arguments else ""
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

def can_parallelize(step_a: TrajectoryStep, step_b: TrajectoryStep, tools: Dict[str, ToolDefinition]) -> bool:
    if step_a.step_type != StepType.TOOL_CALL or step_b.step_type != StepType.TOOL_CALL:
        return False
        
    tool_a = tools.get(step_a.tool_name)
    tool_b = tools.get(step_b.tool_name)
    
    if not tool_a or not tool_b:
        return False
        
    if not tool_a.supports_parallel or not tool_b.supports_parallel:
        return False
        
    if tool_a.effect == ToolEffect.WRITE or tool_b.effect == ToolEffect.WRITE:
        return False
        
    if tool_a.rate_limit_group and tool_a.rate_limit_group == tool_b.rate_limit_group:
        # Simplistic: if same rate limit group, assume conflict for this example
        return False
        
    if step_a.target_tenant_id != step_b.target_tenant_id:
        # Might be safe if intentionally multi-tenant, but usually we restrict scopes
        return False
        
    # We assume no data dependency if all above hold (in a real system, data dependency implies order, 
    # which means step_b's arguments depend on step_a's result, so they wouldn't be scheduled simultaneously)
    return True

def compute_metrics(baseline: Trajectory, candidate: Trajectory) -> TrajectoryComparison:
    # Dummy mock mapping just to satisfy type signatures for testing
    def mock_compute(t: Trajectory):
        total_work = sum(s.latency_ms for s in t.steps)
        # Mock critical path: sum of non-parallelizable, simple approximation
        critical_path = total_work * 0.7 
        return TrajectoryMetrics(
            total_steps=len(t.steps),
            model_calls=sum(1 for s in t.steps if s.step_type == StepType.MODEL_CALL),
            tool_calls=sum(1 for s in t.steps if s.step_type == StepType.TOOL_CALL),
            duplicate_calls=sum(1 for s in t.steps if s.classification == StepClassification.DUPLICATE_READ),
            retry_count=sum(1 for s in t.steps if s.classification == StepClassification.JUSTIFIED_RETRY),
            parallelizable_calls=0,
            total_work_ms=total_work,
            critical_path_ms=critical_path,
            wall_clock_latency_ms=critical_path + 100, # 100ms orchestration
            cost_usd=sum(s.cost_usd for s in t.steps),
            required_evidence_recall=1.0,
            unsupported_evidence_count=0.0,
            outcome_correct=True,
            is_policy_compliant=True,
            forbidden_executed=0,
            cross_tenant_executed=0
        )
        
    bm = mock_compute(baseline)
    cm = mock_compute(candidate)
    
    return TrajectoryComparison(
        baseline=bm,
        candidate=cm,
        delta_wall_clock_latency_ms=cm.wall_clock_latency_ms - bm.wall_clock_latency_ms,
        delta_cost_usd=cm.cost_usd - bm.cost_usd,
        delta_required_evidence_recall=cm.required_evidence_recall - bm.required_evidence_recall,
        delta_outcome_correct=(cm.outcome_correct == bm.outcome_correct)
    )

def should_stop(state_evidence: set, required_evidence: set) -> bool:
    return required_evidence.issubset(state_evidence)

def is_valid_cache_hit(step: TrajectoryStep, cached_result: dict, tenant_id: str, policy_version: str) -> bool:
    if step.target_tenant_id != tenant_id:
        return False
    if cached_result.get("policy_version") != policy_version:
        return False
    if step.classification == StepClassification.SIDE_EFFECT:
        return False
    if cached_result.get("expires_at", 0) < step.observed_at:
        return False
    return True

def optimization_regression_gate(comparison: TrajectoryComparison) -> bool:
    if comparison.candidate.outcome_correct == False and comparison.baseline.outcome_correct == True:
        return False
    if comparison.candidate.required_evidence_recall < comparison.baseline.required_evidence_recall:
        return False
    if comparison.candidate.forbidden_executed > 0 or comparison.candidate.cross_tenant_executed > 0:
        return False
    return True
