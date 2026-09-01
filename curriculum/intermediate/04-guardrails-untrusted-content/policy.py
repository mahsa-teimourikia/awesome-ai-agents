from enum import Enum
from typing import List, Dict, Optional, Literal, Set
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TrustLevel(Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"
    QUARANTINED = "QUARANTINED"

class Sensitivity(Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"

class SourceType(Enum):
    USER = "USER"
    RAG_DOCUMENT = "RAG_DOCUMENT"
    WEB = "WEB"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    MEMORY = "MEMORY"
    SUBAGENT = "SUBAGENT"

class ContentDisposition(Enum):
    ALLOW_AS_DATA = "ALLOW_AS_DATA"
    QUARANTINE = "QUARANTINE"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"

class ToolEffect(Enum):
    READ = "READ"
    PROPOSE = "PROPOSE"
    WRITE = "WRITE"

class GuardrailStatus(Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    REPAIRABLE = "REPAIRABLE"
    ABSTAIN = "ABSTAIN"

class ContentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    item_id: str
    tenant_id: str
    source_type: SourceType
    source_id: str
    source_version: str
    observed_at: datetime
    trust: TrustLevel
    sensitivity: Sensitivity
    payload: str

class InjectionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    detected: bool
    markers: List[str]

class ContentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    disposition: ContentDisposition
    signal: InjectionSignal
    reason: str

class ExecutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    tenant_id: str
    user_id: str
    roles: List[str]
    environment: str
    approved_capabilities: List[str]
    allowed_destinations: List[str]
    request_id: str

class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str
    arguments: dict
    tenant_id: Optional[str] = None # Some tools specify a tenant target

class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str
    effect: ToolEffect
    required_permissions: List[str]
    requires_approval: bool
    allowed_environments: List[str]

# --- Authoritative Tool Registry ---
TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    "query_logs": ToolDefinition(
        name="query_logs",
        effect=ToolEffect.READ,
        required_permissions=["logs:read"],
        requires_approval=False,
        allowed_environments=["production", "staging"]
    ),
    "get_service_health": ToolDefinition(
        name="get_service_health",
        effect=ToolEffect.READ,
        required_permissions=["health:read"],
        requires_approval=False,
        allowed_environments=["production", "staging"]
    ),
    "get_deployment": ToolDefinition(
        name="get_deployment",
        effect=ToolEffect.READ,
        required_permissions=["deployment:read"],
        requires_approval=False,
        allowed_environments=["production", "staging"]
    ),
    "prepare_restart_proposal": ToolDefinition(
        name="prepare_restart_proposal",
        effect=ToolEffect.PROPOSE,
        required_permissions=["deployment:propose"],
        requires_approval=False,
        allowed_environments=["production", "staging"]
    ),
    "restart_service": ToolDefinition(
        name="restart_service",
        effect=ToolEffect.WRITE,
        required_permissions=["deployment:write"],
        requires_approval=True,
        allowed_environments=["production"]
    ),
    "export_customer_records": ToolDefinition(
        name="export_customer_records",
        effect=ToolEffect.WRITE,
        required_permissions=["customer_data:export"],
        requires_approval=True,
        allowed_environments=["production"]
    )
}

class ToolDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    status: GuardrailStatus
    reason: str

# --- Detection & Containment logic ---

def detect_injection_signals(item: ContentItem) -> InjectionSignal:
    """
    NOT a production-complete prompt injection detector.
    Demonstrates deterministic fallback.
    """
    known_markers = [
        "ignore previous instructions",
        "restart production",
        "export customer records",
        "ignore policy"
    ]
    
    found = []
    text = item.payload.lower()
    for marker in known_markers:
        if marker in text:
            found.append(marker)
            
    return InjectionSignal(
        detected=len(found) > 0,
        markers=found
    )

def classify_content(item: ContentItem) -> ContentDecision:
    signal = detect_injection_signals(item)
    
    if signal.detected:
        return ContentDecision(
            disposition=ContentDisposition.QUARANTINE,
            signal=signal,
            reason="Injection markers detected in untrusted content."
        )
        
    if item.trust == TrustLevel.TRUSTED:
        return ContentDecision(
            disposition=ContentDisposition.ALLOW_AS_DATA,
            signal=signal,
            reason="Trusted internal content."
        )
        
    return ContentDecision(
        disposition=ContentDisposition.ALLOW_AS_DATA,
        signal=signal,
        reason="Untrusted data; no known injection markers detected. Safe for delimited inclusion."
    )

def validate_tool_call(call: ToolCall, context: ExecutionContext, approved: bool = False) -> ToolDecision:
    if call.name not in TOOL_REGISTRY:
        return ToolDecision(status=GuardrailStatus.BLOCKED, reason=f"UNKNOWN_TOOL: {call.name}")
        
    definition = TOOL_REGISTRY[call.name]
    
    if call.tenant_id and call.tenant_id != context.tenant_id:
        return ToolDecision(status=GuardrailStatus.BLOCKED, reason="WRONG_TENANT")
        
    for perm in definition.required_permissions:
        if perm not in context.approved_capabilities:
            return ToolDecision(status=GuardrailStatus.BLOCKED, reason="UNAUTHORIZED_CAPABILITY")
            
    if context.environment not in definition.allowed_environments:
        return ToolDecision(status=GuardrailStatus.BLOCKED, reason="ENVIRONMENT_NOT_ALLOWED")
        
    if definition.requires_approval and not approved:
        return ToolDecision(status=GuardrailStatus.APPROVAL_REQUIRED, reason="APPROVAL_REQUIRED")
        
    return ToolDecision(status=GuardrailStatus.ALLOWED, reason="ALLOW")

class EgressPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: GuardrailStatus
    reason: str

def validate_egress(destination: str, tenant: str, sensitivity: Sensitivity, purpose: str, context: ExecutionContext) -> EgressPolicy:
    if destination not in context.allowed_destinations:
        return EgressPolicy(status=GuardrailStatus.BLOCKED, reason="EGRESS_DENIED")
        
    return EgressPolicy(status=GuardrailStatus.ALLOWED, reason="EGRESS_ALLOWED")

class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    evidence_ids: List[str]
    recommended_action: Literal["restart", "export", "monitor", "escalate"]
    confidence: float
    
class OutputValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: GuardrailStatus
    reason: str

def validate_investigation_response(response: InvestigationResponse, valid_evidence_ids: Set[str]) -> OutputValidationResult:
    for eid in response.evidence_ids:
        if eid not in valid_evidence_ids:
            return OutputValidationResult(status=GuardrailStatus.ABSTAIN, reason="UNSUPPORTED_EVIDENCE")
            
    return OutputValidationResult(status=GuardrailStatus.ALLOWED, reason="VALID")
