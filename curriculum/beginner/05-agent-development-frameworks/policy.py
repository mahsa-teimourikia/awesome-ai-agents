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

class IncidentRecommendation(BaseModel):
    summary: str
    cited_evidence_ids: list[str]
    suspected_deployment_id: str | None
    attribution_strength: Literal["unknown", "correlated", "strong_evidence", "verified"]
    recommended_action: Literal["observe", "investigate", "consider_rollback", "escalate"]

class ModelDecision(BaseModel):
    decision_summary: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    final_answer: IncidentRecommendation | None = None

class AgentRunResult(BaseModel):
    recommendation: IncidentRecommendation
    evidence_retrieved: List[Any]
    evidence_ids: List[str]
    steps: int
    tool_calls: int

def verify_grounding(result: AgentRunResult):
    """Enforce structured grounding invariants on the final recommendation."""
    rec = result.recommendation
    retrieved_ev_ids = [getattr(ev, 'evidence_id', None) for ev in result.evidence_retrieved]
    
    # 1. Every cited_evidence_id exists in evidence_retrieved
    for cite_id in rec.cited_evidence_ids:
        assert cite_id in retrieved_ev_ids, f'GROUNDING VIOLATION: Cited evidence {cite_id} was never retrieved.'
        
    # 2. Suspected deployment was actually retrieved
    if rec.suspected_deployment_id:
        has_deployment = any(isinstance(ev, DeploymentResult) and ev.latest_deployment_id == rec.suspected_deployment_id for ev in result.evidence_retrieved)
        assert has_deployment, f'GROUNDING VIOLATION: Suspected deployment {rec.suspected_deployment_id} was not retrieved.'
        
    # 3 & 4. attribution_strength="verified" requires verification evidence (temporal correlation alone cannot become "verified")
    if rec.attribution_strength == "verified":
        raise AssertionError("GROUNDING VIOLATION: Temporal correlation (health & deployment) cannot establish 'verified' causality.")
        
    # 5. rollback recommendation requires the expected prerequisite evidence
    if rec.recommended_action == "consider_rollback":
        assert rec.suspected_deployment_id is not None, "GROUNDING VIOLATION: Rollback recommended without a suspected deployment."
        has_health_degradation = any(isinstance(ev, HealthResult) and ev.status in ['DEGRADED', 'DOWN'] for ev in result.evidence_retrieved)
        assert has_health_degradation, "GROUNDING VIOLATION: Rollback recommended but no health degradation evidence retrieved."

    print('\nGrounding Invariant Verified: Recommendation uses structured evidence constraints correctly.')
