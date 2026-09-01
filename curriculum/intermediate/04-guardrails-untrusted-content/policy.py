from enum import Enum
from typing import List, Dict, Optional, Literal, Set, Type, Any
from pydantic import BaseModel, ConfigDict, ValidationError
from datetime import datetime
import re

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
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"
    QUARANTINE = "QUARANTINE"
    PII_OR_SECRET_DETECTED = "PII_OR_SECRET_DETECTED"
    POLICY_CHECK_REQUIRED = "POLICY_CHECK_REQUIRED"

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
    ambiguous: bool = False

class ContentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    disposition: ContentDisposition
    signal: InjectionSignal
    reason: str

class ExecutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    tenant_id: str
    user_id: str
    environment: str
    approved_capabilities: List[str]
    allowed_destinations: List[str]
    request_id: str

class ValidatedApprovalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    action: str
    tenant: str
    target_digest: str
    expiry: datetime
    policy_version: str

class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str
    arguments: dict
    requested_tenant_id: Optional[str] = None # Model-proposed scope; can only narrow, never expand trusted authority.

class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str
    effect: ToolEffect
    required_permissions: List[str]
    requires_approval: bool
    allowed_environments: List[str]
    input_model: Type[BaseModel]

# --- Strict Per-Tool Input Schemas ---
class QueryLogsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str

class HealthArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: str

class DeploymentArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster: str

class RestartProposalArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster: str
    reason: str

class RestartServiceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster: str

class ExportCustomerRecordsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination: str

# --- Authoritative Tool Registry ---
TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    "query_logs": ToolDefinition(
        name="query_logs",
        effect=ToolEffect.READ,
        required_permissions=["logs:read"],
        requires_approval=False,
        allowed_environments=["production", "staging"],
        input_model=QueryLogsArgs
    ),
    "get_service_health": ToolDefinition(
        name="get_service_health",
        effect=ToolEffect.READ,
        required_permissions=["health:read"],
        requires_approval=False,
        allowed_environments=["production", "staging"],
        input_model=HealthArgs
    ),
    "get_deployment": ToolDefinition(
        name="get_deployment",
        effect=ToolEffect.READ,
        required_permissions=["deployment:read"],
        requires_approval=False,
        allowed_environments=["production", "staging"],
        input_model=DeploymentArgs
    ),
    "prepare_restart_proposal": ToolDefinition(
        name="prepare_restart_proposal",
        effect=ToolEffect.PROPOSE,
        required_permissions=["deployment:propose"],
        requires_approval=False,
        allowed_environments=["production", "staging"],
        input_model=RestartProposalArgs
    ),
    "restart_service": ToolDefinition(
        name="restart_service",
        effect=ToolEffect.WRITE,
        required_permissions=["deployment:write"],
        requires_approval=True,
        allowed_environments=["production"],
        input_model=RestartServiceArgs
    ),
    "export_customer_records": ToolDefinition(
        name="export_customer_records",
        effect=ToolEffect.WRITE,
        required_permissions=["customer_data:export"],
        requires_approval=True,
        allowed_environments=["production"],
        input_model=ExportCustomerRecordsArgs
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
        "export customer records"
    ]
    
    ambiguous_markers = [
        "ignore policy" # Could be legitimate in some internal documents
    ]
    
    found = []
    text = item.payload.lower()
    
    detected_definitive = False
    for marker in known_markers:
        if marker in text:
            found.append(marker)
            detected_definitive = True
            
    ambiguous = False
    for marker in ambiguous_markers:
        if marker in text:
            found.append(marker)
            if not detected_definitive:
                ambiguous = True
            
    return InjectionSignal(
        detected=len(found) > 0,
        markers=found,
        ambiguous=ambiguous
    )

def classify_content(item: ContentItem) -> ContentDecision:
    signal = detect_injection_signals(item)
    
    if signal.detected:
        if signal.ambiguous or item.trust == TrustLevel.TRUSTED:
            return ContentDecision(
                disposition=ContentDisposition.REQUIRE_REVIEW,
                signal=signal,
                reason="Ambiguous injection markers or markers found in trusted content. Requires human review."
            )
        else:
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
        reason="Untrusted data; no known injection markers detected. Eligible for delimited inclusion under downstream containment controls."
    )

def validate_tool_call(call: ToolCall, context: ExecutionContext, validated_approval: Optional[ValidatedApprovalContext] = None) -> ToolDecision:
    if call.name not in TOOL_REGISTRY:
        return ToolDecision(status=GuardrailStatus.BLOCKED, reason=f"UNKNOWN_TOOL: {call.name}")
        
    definition = TOOL_REGISTRY[call.name]
    
    # Structural Validation
    try:
        definition.input_model.model_validate(call.arguments)
    except ValidationError as e:
        return ToolDecision(status=GuardrailStatus.REPAIRABLE, reason=f"INVALID_ARGUMENT: {str(e)}")
    
    # Authority Validation
    if call.requested_tenant_id and call.requested_tenant_id != context.tenant_id:
        return ToolDecision(status=GuardrailStatus.BLOCKED, reason="WRONG_TENANT")
        
    for perm in definition.required_permissions:
        if perm not in context.approved_capabilities:
            return ToolDecision(status=GuardrailStatus.BLOCKED, reason="UNAUTHORIZED_CAPABILITY")
            
    if context.environment not in definition.allowed_environments:
        return ToolDecision(status=GuardrailStatus.BLOCKED, reason="ENVIRONMENT_NOT_ALLOWED")
        
    if definition.requires_approval and not validated_approval:
        return ToolDecision(status=GuardrailStatus.APPROVAL_REQUIRED, reason="APPROVAL_REQUIRED")
        
    return ToolDecision(status=GuardrailStatus.ALLOWED, reason="ALLOW")

class EgressPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: GuardrailStatus
    reason: str

def validate_egress(destination: str, tenant: str, sensitivity: Sensitivity, purpose: str, context: ExecutionContext) -> EgressPolicy:
    if tenant != context.tenant_id:
        return EgressPolicy(status=GuardrailStatus.BLOCKED, reason="WRONG_TENANT")
        
    if destination not in context.allowed_destinations:
        return EgressPolicy(status=GuardrailStatus.BLOCKED, reason="EGRESS_DENIED: Unapproved destination")
        
    if purpose not in ["alerting", "reporting", "exfiltration_test"]:
        return EgressPolicy(status=GuardrailStatus.BLOCKED, reason="EGRESS_DENIED: Invalid purpose")
        
    if sensitivity == Sensitivity.RESTRICTED and destination not in ["secure-vault@northstar.internal"]:
        return EgressPolicy(status=GuardrailStatus.BLOCKED, reason="EGRESS_DENIED: Restricted data destination mismatch")
        
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

def detect_pii(text: str) -> bool:
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    cc_pattern = r'\b(?:\d{4}[ -]?){3}\d{4}\b'
    if re.search(ssn_pattern, text) or re.search(cc_pattern, text):
        return True
    return False

def validate_investigation_response(response: InvestigationResponse, valid_evidence_ids: Set[str]) -> OutputValidationResult:
    if detect_pii(response.summary):
        return OutputValidationResult(status=GuardrailStatus.PII_OR_SECRET_DETECTED, reason="PII detected in output summary")
        
    for eid in response.evidence_ids:
        if eid not in valid_evidence_ids:
            return OutputValidationResult(status=GuardrailStatus.NEED_MORE_EVIDENCE, reason="UNSUPPORTED_EVIDENCE")
            
    if response.recommended_action in ["restart", "export"]:
        return OutputValidationResult(status=GuardrailStatus.POLICY_CHECK_REQUIRED, reason="Write recommendation requires policy approval")
            
    return OutputValidationResult(status=GuardrailStatus.ALLOWED, reason="VALID")
