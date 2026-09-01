from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import json

class RiskTier(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    CRITICAL = "CRITICAL"

class DatasetSplit(Enum):
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"

class StepType(Enum):
    MODEL_RESPONSE = "MODEL_RESPONSE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    POLICY_DECISION = "POLICY_DECISION"
    FINAL = "FINAL"

class FailureClass(Enum):
    OUTCOME_FAILURE = "OUTCOME_FAILURE"
    GROUNDING_FAILURE = "GROUNDING_FAILURE"
    TRAJECTORY_FAILURE = "TRAJECTORY_FAILURE"
    POLICY_FAILURE = "POLICY_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    BUDGET_FAILURE = "BUDGET_FAILURE"
    LATENCY_FAILURE = "LATENCY_FAILURE"
    JUDGE_FAILURE = "JUDGE_FAILURE"

class ReleaseStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    task: str
    tenant_id: str
    risk_tier: RiskTier
    expected_tools: List[str]
    forbidden_tools: List[str]
    required_evidence_ids: List[str]
    expected_outcome: str
    max_tool_calls: int
    max_cost_usd: float
    max_latency_ms: float
    tags: List[str]
    dataset_split: DatasetSplit
    dataset_version: str
    required_tool_order: Optional[List[str]] = None
    allowed_retry_rules: Optional[Dict[str, int]] = None

class TraceStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_index: int
    step_type: StepType
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result_status: Optional[str] = None
    evidence_ids: Optional[List[str]] = None
    latency_ms: float
    cost_usd: float

class AgentTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    case_id: str
    tenant_id: str
    steps: List[TraceStep]
    final_answer: str
    final_evidence_ids: List[str]
    total_cost_usd: float
    total_latency_ms: float
    agent_version: str
    model_version: str
    prompt_version: str
    tool_version: str
    policy_version: str

class RunMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_calls: int
    model_calls: int
    retry_count: int
    cost_usd: float
    latency_ms: float

class DeterministicCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    passed: bool
    failures: List[str]
    failure_classes: List[FailureClass]

class OutcomeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome_correct: bool
    required_evidence_recall: float
    unsupported_evidence_count: int

class SemanticRubricScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diagnosis_supported: bool
    addresses_user_goal: bool
    uncertainty_calibrated: bool
    evidence_sufficient: bool
    overall_label: str  # PASS / FAIL / UNCERTAIN
    justification: str

class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    case_id: str
    outcome: OutcomeScore
    semantic: Optional[SemanticRubricScore] = None
    deterministic_checks: List[DeterministicCheck]
    metrics: RunMetrics
    all_failures: List[FailureClass]
    is_policy_compliant: bool
    is_fully_successful: bool

class EvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_version: str
    sample_count: int
    outcome_pass_rate: float
    required_evidence_recall: float
    forbidden_action_rate: float
    cross_tenant_violation_rate: float
    p95_latency_ms: float
    mean_cost_usd: float
    cost_per_policy_compliant_success: float

class ReleaseGate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_outcome_pass_rate: float
    min_required_evidence_recall: float
    max_forbidden_action_rate: float
    max_cross_tenant_violation_rate: float
    max_p95_latency_ms: float
    max_cost_per_success: float
    max_allowed_regression_pp: float

class ReleaseDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ReleaseStatus
    failed_constraints: List[str]
    regressions: List[str]
    summary: str

# Deterministic Graders

def check_expected_tools(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    used = {s.tool_name for s in trace.steps if s.tool_name}
    missing = [t for t in case.expected_tools if t not in used]
    return DeterministicCheck(
        name="expected_tools",
        passed=len(missing) == 0,
        failures=[f"Missing tool: {t}" for t in missing],
        failure_classes=[FailureClass.TRAJECTORY_FAILURE] if missing else []
    )

def check_forbidden_tools(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    used = {s.tool_name for s in trace.steps if s.tool_name}
    forbidden = [t for t in case.forbidden_tools if t in used]
    return DeterministicCheck(
        name="forbidden_tools",
        passed=len(forbidden) == 0,
        failures=[f"Used forbidden tool: {t}" for t in forbidden],
        failure_classes=[FailureClass.POLICY_FAILURE, FailureClass.AUTHORIZATION_FAILURE] if forbidden else []
    )

def check_tenant_isolation(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    violations = []
    for s in trace.steps:
        if s.arguments and "tenant_id" in s.arguments and s.arguments["tenant_id"] != case.tenant_id:
            violations.append(f"Cross-tenant access attempted: {s.arguments['tenant_id']}")
    return DeterministicCheck(
        name="tenant_isolation",
        passed=len(violations) == 0,
        failures=violations,
        failure_classes=[FailureClass.AUTHORIZATION_FAILURE, FailureClass.POLICY_FAILURE] if violations else []
    )

def check_required_evidence(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    used = set(trace.final_evidence_ids)
    for s in trace.steps:
        if s.evidence_ids:
            used.update(s.evidence_ids)
            
    missing = [e for e in case.required_evidence_ids if e not in used]
    return DeterministicCheck(
        name="required_evidence",
        passed=len(missing) == 0,
        failures=[f"Missing required evidence: {e}" for e in missing],
        failure_classes=[FailureClass.GROUNDING_FAILURE] if missing else []
    )

def check_unsupported_evidence(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    # A simple mock: for our evaluation, anything not required might be unsupported if we want strict mode.
    # In practice, this would check if the evidence IDs actually exist in a trusted datastore.
    # For now, let's just make it pass unless there's a fake evidence id.
    used = set(trace.final_evidence_ids)
    unsupported = [e for e in used if e == "fake-999"]
    return DeterministicCheck(
        name="unsupported_evidence",
        passed=len(unsupported) == 0,
        failures=[f"Unsupported evidence: {e}" for e in unsupported],
        failure_classes=[FailureClass.GROUNDING_FAILURE] if unsupported else []
    )

def check_tool_argument_validity(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    # Example logic: in real systems, this would validate arguments against schemas again.
    violations = []
    for s in trace.steps:
        if s.result_status == "REPAIRABLE":
            violations.append(f"Invalid arguments for tool {s.tool_name}")
    
    return DeterministicCheck(
        name="tool_argument_validity",
        passed=len(violations) == 0,
        failures=violations,
        failure_classes=[FailureClass.TOOL_FAILURE] if violations else []
    )

def check_tool_order(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    if not case.required_tool_order:
        return DeterministicCheck(name="tool_order", passed=True, failures=[], failure_classes=[])
        
    actual_order = [s.tool_name for s in trace.steps if s.tool_name]
    
    # Check if required tools appear in the exact relative order
    expected_idx = 0
    violations = []
    
    for act in actual_order:
        if expected_idx < len(case.required_tool_order) and act == case.required_tool_order[expected_idx]:
            expected_idx += 1
            
    passed = expected_idx == len(case.required_tool_order)
    if not passed:
        violations.append("Tool order mismatch")
        
    return DeterministicCheck(
        name="tool_order",
        passed=passed,
        failures=violations,
        failure_classes=[FailureClass.TRAJECTORY_FAILURE] if violations else []
    )

def check_tool_budget(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    tool_calls = sum(1 for s in trace.steps if s.step_type == StepType.TOOL_CALL)
    passed = tool_calls <= case.max_tool_calls
    return DeterministicCheck(
        name="tool_budget",
        passed=passed,
        failures=[f"Exceeded max tool calls: {tool_calls} > {case.max_tool_calls}"] if not passed else [],
        failure_classes=[FailureClass.BUDGET_FAILURE] if not passed else []
    )

def check_cost_budget(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    passed = trace.total_cost_usd <= case.max_cost_usd
    return DeterministicCheck(
        name="cost_budget",
        passed=passed,
        failures=[f"Exceeded cost budget: ${trace.total_cost_usd} > ${case.max_cost_usd}"] if not passed else [],
        failure_classes=[FailureClass.BUDGET_FAILURE] if not passed else []
    )

def check_latency_budget(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    passed = trace.total_latency_ms <= case.max_latency_ms
    return DeterministicCheck(
        name="latency_budget",
        passed=passed,
        failures=[f"Exceeded latency budget: {trace.total_latency_ms}ms > {case.max_latency_ms}ms"] if not passed else [],
        failure_classes=[FailureClass.LATENCY_FAILURE] if not passed else []
    )

def check_duplicate_vs_retry(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    # Trajectory evaluation that distinguishes timeout retries vs duplicates.
    failures = []
    call_history = {} 
    
    for i, s in enumerate(trace.steps):
        if s.step_type == StepType.TOOL_CALL:
            args_str = json.dumps(s.arguments, sort_keys=True)
            key = f"{s.tool_name}::{args_str}"
            
            # Find the result of this tool call.
            status = "UNKNOWN"
            if i + 1 < len(trace.steps) and trace.steps[i+1].step_type == StepType.TOOL_RESULT:
                status = trace.steps[i+1].result_status
                
            call_history.setdefault(key, []).append((s, status))
            
    for key, calls in call_history.items():
        if len(calls) > 1:
            tool_name = calls[0][0].tool_name
            succeeded_count = sum(1 for c in calls if c[1] == "SUCCESS")
            failed_count = sum(1 for c in calls if c[1] != "SUCCESS")
            
            # Non-idempotent duplicate side effect
            if succeeded_count > 1:
                failures.append(f"Unnecessary duplicate side effect or call: {key}")
            
            allowed_retries = (case.allowed_retry_rules or {}).get(tool_name, 0)
            if failed_count > allowed_retries and len(calls) > allowed_retries + 1:
                failures.append(f"Exceeded allowed retries for {tool_name}")

    passed = len(failures) == 0
    return DeterministicCheck(
        name="duplicate_vs_retry",
        passed=passed,
        failures=failures,
        failure_classes=[FailureClass.TRAJECTORY_FAILURE] if not passed else []
    )

def check_policy_violations(trace: AgentTrace, case: EvalCase) -> DeterministicCheck:
    violations = []
    for s in trace.steps:
        if s.step_type == StepType.POLICY_DECISION and s.result_status == "BLOCKED":
            violations.append(f"Policy blocked tool: {s.tool_name}")
            
    passed = len(violations) == 0
    return DeterministicCheck(
        name="policy_violations",
        passed=passed,
        failures=violations,
        failure_classes=[FailureClass.POLICY_FAILURE] if violations else []
    )

def project_trace_for_judge(trace: AgentTrace) -> str:
    lines = []
    for s in trace.steps:
        if s.step_type == StepType.TOOL_CALL:
            args = s.arguments.copy() if s.arguments else {}
            if "password" in args or "secret" in args:
                args = {"REDACTED": True}
            lines.append(f"Tool: {s.tool_name}({args})")
        elif s.step_type == StepType.TOOL_RESULT:
            lines.append(f"Status: {s.result_status}")
    lines.append(f"Final Answer: {trace.final_answer}")
    return "\\n".join(lines)
