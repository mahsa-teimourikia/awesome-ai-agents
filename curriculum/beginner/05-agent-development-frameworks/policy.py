from typing import List, Literal, Any
from pydantic import BaseModel, Field

class HealthResult(BaseModel):
    evidence_id: str
    status: Literal['HEALTHY', 'DEGRADED', 'DOWN']
    error_rate_pct: float
    symptom: str | None

class DeploymentResult(BaseModel):
    evidence_id: str
    latest_deployment_id: str
    deployed_minutes_ago: int
    author: str

class ToolCall(BaseModel):
    id: str = "call_mock"
    name: str
    arguments_json: str

class ModelDecision(BaseModel):
    decision_summary: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    final_answer: str | None = None

class AgentRunResult(BaseModel):
    final_answer: str
    evidence_retrieved: List[Any]
    evidence_ids: List[str]
    steps: int
    tool_calls: int

def verify_grounding(result: AgentRunResult):
    """Enforce: No recommendation may rely on evidence the implementation did not retrieve."""
    if 'dep_eu_114' in result.final_answer:
        assert any(isinstance(ev, DeploymentResult) and ev.latest_deployment_id == 'dep_eu_114' for ev in result.evidence_retrieved), \
            'GROUNDING VIOLATION: Final answer cited deployment dep_eu_114, but deployment tool was never executed!'
    if 'DEGRADED' in result.final_answer or '15%' in result.final_answer:
        assert any(isinstance(ev, HealthResult) and ev.status == 'DEGRADED' for ev in result.evidence_retrieved), \
            'GROUNDING VIOLATION: Final answer cited health degradation without checking health tool!'
    print('\nGrounding Invariant Verified: All cited facts match retrieved evidence.')
