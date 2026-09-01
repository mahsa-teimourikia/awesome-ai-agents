import datetime
import hashlib
import json
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContextKind(str, Enum):
    SYSTEM_POLICY = "SYSTEM_POLICY"
    TASK_STATE = "TASK_STATE"
    CONVERSATION = "CONVERSATION"
    TOOL_EVIDENCE = "TOOL_EVIDENCE"
    RETRIEVED_DOCUMENT = "RETRIEVED_DOCUMENT"
    MEMORY = "MEMORY"
    SUMMARY = "SUMMARY"


class TrustLevel(str, Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"
    QUARANTINED = "QUARANTINED"


class Sensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class Phase(str, Enum):
    TRIAGE = "TRIAGE"
    INVESTIGATE = "INVESTIGATE"
    RECOMMEND = "RECOMMEND"
    RESUME = "RESUME"


class ContextItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    item_id: str
    kind: ContextKind
    tenant_id: str
    user_id: Optional[str] = None
    source_id: str
    source_type: str
    observed_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    trust: TrustLevel
    sensitivity: Sensitivity
    relevance_score: float
    token_estimate: int
    payload: Any


class ContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    request_id: str
    tenant_id: str
    user_id: Optional[str] = None
    task_id: str
    phase: Phase
    token_budget: int
    required_evidence_ids: List[str]
    policy_version: str


class SelectionTraceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    item_id: str
    decision: str  # INCLUDED, DROPPED, QUARANTINED
    reason: str


class ContextPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    request_id: str
    tenant_id: str
    phase: Phase
    
    system_policy: Optional[ContextItem] = None
    task_state: Optional[ContextItem] = None
    
    selected_items: List[ContextItem]
    quarantined_items: List[ContextItem]
    dropped_items: List[ContextItem]
    
    structured_summary: Optional[ContextItem] = None
    
    estimated_tokens: int
    cache_key: str
    
    selection_trace: List[SelectionTraceItem]


def build_context(request: ContextRequest, candidates: List[ContextItem]) -> ContextPacket:
    """
    Authoritative Context Builder Pipeline.
    Enforces strict authorization, trust isolation, freshness, and budget ranking.
    """
    trace = []
    selected = []
    quarantined = []
    dropped = []
    
    sys_policy = None
    task_state = None
    summary = None
    
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Pipeline filtering BEFORE relevance ranking
    valid_candidates = []
    
    for item in candidates:
        # Authorization check: strict tenant isolation
        if item.tenant_id != "global" and item.tenant_id != request.tenant_id:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="WRONG_TENANT"))
            dropped.append(item)
            continue
            
        # Trust check: quarantine poisoned or explicitly untrusted items
        if item.trust == TrustLevel.QUARANTINED:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="QUARANTINED", reason="POISONED"))
            quarantined.append(item)
            continue
            
        # Freshness check
        if item.expires_at and item.expires_at < current_time:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="STALE"))
            dropped.append(item)
            continue
            
        # Phase relevance check
        if request.phase == Phase.TRIAGE and item.kind in [ContextKind.RETRIEVED_DOCUMENT, ContextKind.TOOL_EVIDENCE]:
            if item.item_id not in request.required_evidence_ids:
                trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="WRONG_PHASE"))
                dropped.append(item)
                continue
                
        valid_candidates.append(item)
        
    # 2. Assign absolute categories (Policy, State, Summary)
    pool = []
    for item in valid_candidates:
        if item.kind == ContextKind.SYSTEM_POLICY:
            sys_policy = item
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="MANDATORY_POLICY"))
        elif item.kind == ContextKind.TASK_STATE:
            task_state = item
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="MANDATORY_STATE"))
        elif item.kind == ContextKind.SUMMARY:
            summary = item
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="MANDATORY_SUMMARY"))
        else:
            pool.append(item)

    # 3. Required Evidence Preservation
    budget_pool = []
    for item in pool:
        if item.item_id in request.required_evidence_ids:
            selected.append(item)
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="REQUIRED_EVIDENCE"))
        else:
            budget_pool.append(item)
            
    # 4. Token-budget ranking (sort by relevance descending)
    budget_pool.sort(key=lambda x: x.relevance_score, reverse=True)
    
    current_tokens = sum(i.token_estimate for i in selected)
    if sys_policy: current_tokens += sys_policy.token_estimate
    if task_state: current_tokens += task_state.token_estimate
    if summary: current_tokens += summary.token_estimate
    
    for item in budget_pool:
        if item.relevance_score < 0.3:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="LOW_RELEVANCE"))
            dropped.append(item)
            continue
            
        if current_tokens + item.token_estimate <= request.token_budget:
            selected.append(item)
            current_tokens += item.token_estimate
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="BUDGET_OK"))
        else:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="TOKEN_BUDGET"))
            dropped.append(item)
            
    # 5. Cache Key Generation
    # A safe cache key must bind the exact task, policy version, and selected evidence.
    evidence_fingerprint = hashlib.sha256(
        ",".join(sorted(i.item_id for i in selected)).encode()
    ).hexdigest()[:8]
    
    cache_key = f"{request.tenant_id}::{request.task_id}::pol_{request.policy_version}::ev_{evidence_fingerprint}"
    
    return ContextPacket(
        request_id=request.request_id,
        tenant_id=request.tenant_id,
        phase=request.phase,
        system_policy=sys_policy,
        task_state=task_state,
        structured_summary=summary,
        selected_items=selected,
        quarantined_items=quarantined,
        dropped_items=dropped,
        estimated_tokens=current_tokens,
        cache_key=cache_key,
        selection_trace=trace
    )
