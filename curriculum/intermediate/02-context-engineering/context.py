import datetime
import hashlib
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
    """
    TRUSTED -> normal context
    UNTRUSTED -> may enter as data with explicit provenance/delimiting; never grants authority
    QUARANTINED -> excluded from model context
    """
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


class ContextStatus(str, Enum):
    READY = "READY"
    MISSING_REQUIRED_CONTEXT = "MISSING_REQUIRED_CONTEXT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    AUTHORIZATION_BLOCKED = "AUTHORIZATION_BLOCKED"
    TRUST_BLOCKED = "TRUST_BLOCKED"
    AMBIGUOUS_AUTHORITY = "AMBIGUOUS_AUTHORITY"


class ContextItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    item_id: str
    kind: ContextKind
    tenant_id: str
    user_id: Optional[str] = None
    source_id: str
    source_type: str
    source_version: Optional[str] = None
    observed_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    trust: TrustLevel
    sensitivity: Sensitivity
    relevance_score: float
    token_estimate: int
    payload: Any


class ContextRequest(BaseModel):
    """
    tenant_id, user_id, allowed_sensitivity, policy_version, and 
    context_builder_version are application-owned trusted context.
    The model must not be able to choose or expand them.
    """
    model_config = ConfigDict(extra="forbid")
    
    request_id: str
    tenant_id: str
    user_id: Optional[str] = None
    task_id: str
    phase: Phase
    token_budget: int
    required_evidence_ids: List[str]
    allowed_sensitivity: List[Sensitivity]
    policy_version: str
    context_builder_version: str


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


class ContextBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    status: ContextStatus
    packet: Optional[ContextPacket] = None
    missing_required_ids: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def classify_context_trust(item: ContextItem) -> TrustLevel:
    """
    Deterministic trust classification fixture.
    Real scanners or classifier models provide signals, not authorization boundaries.
    The output of those scanners sets the TrustLevel that the pipeline enforces.
    """
    if "IGNORE SYSTEM POLICY" in str(item.payload):
        return TrustLevel.QUARANTINED
    if item.source_type == "web" or item.kind == ContextKind.RETRIEVED_DOCUMENT:
        return TrustLevel.UNTRUSTED
    return TrustLevel.TRUSTED


def build_context(request: ContextRequest, candidates: List[ContextItem]) -> ContextBuildResult:
    """
    Authoritative Context Builder Pipeline.
    Enforces strict authorization, trust isolation, freshness, and budget ranking.
    """
    trace = []
    selected = []
    quarantined = []
    dropped = []
    warnings = []
    
    sys_policy = None
    task_state = None
    summary = None
    
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Pipeline filtering BEFORE relevance ranking
    valid_candidates = []
    
    for item in candidates:
        # User Scope check
        if item.user_id is not None and item.user_id != request.user_id:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="WRONG_USER"))
            dropped.append(item)
            continue
            
        # Tenant Isolation check
        if item.tenant_id != "global" and item.tenant_id != request.tenant_id:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="WRONG_TENANT"))
            dropped.append(item)
            continue
            
        # Sensitivity check
        if item.sensitivity not in request.allowed_sensitivity:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="RESTRICTED_ACCESS"))
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
            
        valid_candidates.append(item)
        
    # 2. Required Evidence Check
    valid_ids = {i.item_id for i in valid_candidates}
    missing_required = [req_id for req_id in request.required_evidence_ids if req_id not in valid_ids]
    if missing_required:
        auth_blocked = False
        trust_blocked = False
        
        for dropped_item in dropped + quarantined:
            if dropped_item.item_id in missing_required:
                # Find the reason this required item was dropped
                reasons = [t.reason for t in trace if t.item_id == dropped_item.item_id]
                for reason in reasons:
                    if reason in ["WRONG_TENANT", "WRONG_USER", "RESTRICTED_ACCESS"]:
                        auth_blocked = True
                    elif reason in ["POISONED", "QUARANTINED"]:
                        trust_blocked = True
        
        if auth_blocked:
            return ContextBuildResult(
                status=ContextStatus.AUTHORIZATION_BLOCKED,
                missing_required_ids=missing_required,
                warnings=["Required evidence blocked by authorization boundaries."]
            )
        elif trust_blocked:
            return ContextBuildResult(
                status=ContextStatus.TRUST_BLOCKED,
                missing_required_ids=missing_required,
                warnings=["Required evidence blocked by trust/quarantine boundaries."]
            )
        else:
            return ContextBuildResult(
                status=ContextStatus.MISSING_REQUIRED_CONTEXT,
                missing_required_ids=missing_required,
                warnings=["Required evidence missing, stale, or dropped by non-security filters."]
            )
            
    # 3. Assign absolute categories (Policy, State, Summary) with ambiguity check
    pool = []
    ambiguous = False
    for item in valid_candidates:
        if item.kind == ContextKind.SYSTEM_POLICY:
            if sys_policy is not None: ambiguous = True
            sys_policy = item
        elif item.kind == ContextKind.TASK_STATE:
            if task_state is not None: ambiguous = True
            task_state = item
        elif item.kind == ContextKind.SUMMARY:
            # Summary is derived, not mandatory authoritative. We just select one (or the latest).
            # If multiple exist, we can just use the first or add all to pool. For this, we just set it.
            if summary is None:
                summary = item
            else:
                pool.append(item)
        else:
            pool.append(item)
            
    if ambiguous:
        warnings.append("Ambiguous authoritative items. Expected 0 or 1, got multiple.")
        return ContextBuildResult(
            status=ContextStatus.AMBIGUOUS_AUTHORITY,
            warnings=warnings
        )

    if sys_policy:
        trace.append(SelectionTraceItem(item_id=sys_policy.item_id, decision="INCLUDED", reason="MANDATORY_POLICY"))
    if task_state:
        trace.append(SelectionTraceItem(item_id=task_state.item_id, decision="INCLUDED", reason="MANDATORY_STATE"))
    if summary:
        # Check conflict with task_state
        if task_state and hasattr(task_state, "payload") and hasattr(summary, "payload"):
            if "APPROVED" in str(summary.payload) and "NO_APPROVAL" in str(task_state.payload):
                warnings.append("Summary conflicts with Task State. Task State overrides.")
                trace.append(SelectionTraceItem(item_id=summary.item_id, decision="DROPPED", reason="CONFLICTS_WITH_AUTHORITATIVE_STATE"))
                dropped.append(summary)
                summary = None
                
        if summary is not None:
            trace.append(SelectionTraceItem(item_id=summary.item_id, decision="INCLUDED", reason="DERIVED_SUMMARY"))

    # 4. Required Evidence Preservation
    budget_pool = []
    for item in pool:
        if item.item_id in request.required_evidence_ids:
            selected.append(item)
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="REQUIRED_EVIDENCE"))
        else:
            budget_pool.append(item)
            
    current_tokens = sum(i.token_estimate for i in selected)
    if sys_policy: current_tokens += sys_policy.token_estimate
    if task_state: current_tokens += task_state.token_estimate
    if summary: current_tokens += summary.token_estimate
    
    if current_tokens > request.token_budget:
        return ContextBuildResult(
            status=ContextStatus.BUDGET_EXCEEDED,
            warnings=["Token budget exceeded by mandatory and required items alone."]
        )
            
    # 5. Composite Token-budget ranking
    # Baseline composite: relevance + freshness + phase suitability
    def composite_score(x: ContextItem) -> float:
        score = x.relevance_score
        
        # freshness bonus
        if x.expires_at:
            delta = (x.expires_at - current_time).total_seconds()
            if delta > 3600: score += 0.1
        
        # phase suitability / Phase Policy
        if request.phase == Phase.TRIAGE:
            pass
        elif request.phase == Phase.INVESTIGATE:
            if x.kind == ContextKind.TOOL_EVIDENCE:
                score += 0.2
        elif request.phase == Phase.RECOMMEND:
            if x.kind == ContextKind.TOOL_EVIDENCE and x.trust == TrustLevel.TRUSTED:
                score += 0.4
            elif x.kind == ContextKind.SYSTEM_POLICY:
                score += 0.3
        elif request.phase == Phase.RESUME:
            if x.kind in [ContextKind.TASK_STATE, ContextKind.SUMMARY]:
                score += 0.5
            elif x.kind in [ContextKind.CONVERSATION, ContextKind.TOOL_EVIDENCE]:
                score -= 0.5
            
        # cost penalty
        score -= (x.token_estimate / 10000.0)
        return score
        
    budget_pool.sort(key=composite_score, reverse=True)
    
    for item in budget_pool:
        if current_tokens + item.token_estimate <= request.token_budget:
            selected.append(item)
            current_tokens += item.token_estimate
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="INCLUDED", reason="BUDGET_OK"))
        else:
            trace.append(SelectionTraceItem(item_id=item.item_id, decision="DROPPED", reason="TOKEN_BUDGET"))
            dropped.append(item)
            
    # 6. Cache Key Generation
    # Ensure tenant, user, task, phase, policy, cb ver, and items/versions are all bound.
    all_selected = selected.copy()
    if sys_policy: all_selected.append(sys_policy)
    if task_state: all_selected.append(task_state)
    if summary: all_selected.append(summary)
    
    selected_components = []
    for i in all_selected:
        if i.source_version:
            v = i.source_version
        else:
            v = hashlib.sha256(str(i.payload).encode()).hexdigest()[:8]
        selected_components.append(f"{i.item_id}:{v}")
    selected_components.sort()
    
    evidence_fingerprint = hashlib.sha256(
        ",".join(selected_components).encode()
    ).hexdigest()[:8]
    
    user_str = request.user_id or "no_user"
    cache_key = (f"{request.tenant_id}::{user_str}::{request.task_id}::{request.phase.value}::"
                 f"pol_{request.policy_version}::cb_{request.context_builder_version}::"
                 f"items_{evidence_fingerprint}")
    
    packet = ContextPacket(
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
    
    return ContextBuildResult(
        status=ContextStatus.READY,
        packet=packet,
        warnings=warnings
    )
