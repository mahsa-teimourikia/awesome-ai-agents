import time
import urllib.parse
import hashlib
import json
from typing import Literal, List, Optional, Any, Union, Tuple, Dict
from pydantic import BaseModel, Field, ConfigDict

# Centralized model configuration (Model/API capabilities evolve over time;
# official documentation at https://platform.openai.com/docs is the source of truth).
OPENAI_MODEL = "gpt-4o-mini"

# Action Types & Risk Classification
ActionType = Literal["navigate", "click", "type", "scroll", "submit", "stop"]
RiskLevel = Literal["OBSERVE", "DRAFT", "COMMIT", "SENSITIVE"]

class BaseAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str
    action_type: ActionType
    risk_level: RiskLevel = "OBSERVE"
    decision_summary: Optional[str] = Field(None, description="Observable action rationale")

class NavigateAction(BaseAction):
    action_type: Literal["navigate"] = "navigate"
    url: str

class ClickAction(BaseAction):
    action_type: Literal["click"] = "click"
    target_role: str
    target_name: str
    target_id: Optional[str] = None
    fallback_coordinates: Optional[Tuple[float, float]] = None

class TypeAction(BaseAction):
    action_type: Literal["type"] = "type"
    target_role: str
    target_name: str
    text: str
    target_id: Optional[str] = None

class SubmitAction(BaseAction):
    action_type: Literal["submit"] = "submit"
    target_role: str = "button"
    target_name: str = "Submit Escalation"
    case_id: str
    escalation_note: str = Field(..., description="The exact payload content of the escalation note being submitted")
    risk_level: Literal["COMMIT"] = "COMMIT"

UIAction = Union[NavigateAction, ClickAction, TypeAction, SubmitAction]

class Approval(BaseModel):
    proposal_digest: str
    snapshot_id: str
    case_id: str
    action_type: str
    target_name: str
    approver_id: str
    expires_at: float
    decision: Literal["approve", "reject"]

ALLOWED_APPROVERS = {'sec-lead-1', 'sec-lead-2'}

def compute_action_digest(action: UIAction) -> str:
    """Produces a deterministic SHA-256 digest of the proposed action payload."""
    note = getattr(action, "escalation_note", "") or getattr(action, "text", "")
    payload_repr = f"{action.snapshot_id}|{action.action_type}|{getattr(action, 'target_name', '')}|{getattr(action, 'case_id', '')}|{note}"
    return hashlib.sha256(payload_repr.encode('utf-8')).hexdigest()

class ControllerState:
    def __init__(self, allowed_origins: List[str]):
        self.allowed_origins = allowed_origins
        self.snapshot_counter = 0
        self.latest_snapshot_id: Optional[str] = None
        self.action_history: List[Dict[str, Any]] = []
        self.action_count = 0
        self.max_actions = 10
        self.recovery_count = 0
        self.max_recoveries = 3

    def new_snapshot_id(self) -> str:
        self.snapshot_counter += 1
        self.latest_snapshot_id = f"snap-{self.snapshot_counter:03d}"
        return self.latest_snapshot_id

class ValidationResult(BaseModel):
    allowed: bool
    status: Literal["ALLOWED", "ORIGIN_DISALLOWED", "STALE_SNAPSHOT", "APPROVAL_REQUIRED", "APPROVAL_INVALID", "APPROVAL_EXPIRED", "BUDGET_EXHAUSTED"]
    reason: str

def validate_policy(
    action: UIAction, 
    current_url: str, 
    controller: ControllerState
) -> ValidationResult:
    # 1. Action Budget Check
    if controller.action_count >= controller.max_actions:
        return ValidationResult(allowed=False, status="BUDGET_EXHAUSTED", reason=f"Max action budget of {controller.max_actions} exhausted.")
    # 2. Strict Origin Allowlist Verification (Parsed URL comparison)
    if action.action_type == "navigate":
        target_url = getattr(action, 'url', current_url)
    else:
        target_url = current_url
        
    parsed = urllib.parse.urlparse(target_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in controller.allowed_origins:
        return ValidationResult(
            allowed=False, 
            status="ORIGIN_DISALLOWED", 
            reason=f"Security Policy Violation: Target origin '{origin}' is not in allowed origins {controller.allowed_origins}."
        )
    # 3. Observation Freshness Check
    if action.snapshot_id != controller.latest_snapshot_id:
        return ValidationResult(
            allowed=False, 
            status="STALE_SNAPSHOT", 
            reason=f"Stale Observation: Action snapshot '{action.snapshot_id}' does not match latest snapshot '{controller.latest_snapshot_id}'."
        )
    return ValidationResult(allowed=True, status="ALLOWED", reason="Action passed policy and envelope checks.")

def validate_approval(
    action: UIAction, 
    controller: ControllerState, 
    approval: Optional[Approval] = None
) -> ValidationResult:
    """
    Approver authentication/authorization is assumed to be enforced by the application identity layer.
    This function validates the digest-bound approval against the proposed action and checks the authorized approver set.
    """
    if action.risk_level == "COMMIT":
        if approval is None:
            return ValidationResult(
                allowed=False, 
                status="APPROVAL_REQUIRED", 
                reason="High-risk COMMIT action requires explicit human approval."
            )
        
        expected_digest = compute_action_digest(action)
        if approval.proposal_digest != expected_digest:
            return ValidationResult(
                allowed=False, 
                status="APPROVAL_INVALID", 
                reason="Approval digest mismatch: approval does not match proposed action payload (mutated payload or target)."
            )
        
        if approval.case_id != getattr(action, 'case_id', ''):
            return ValidationResult(
                allowed=False,
                status="APPROVAL_INVALID",
                reason="Approval case_id mismatch."
            )
            
        if approval.action_type != action.action_type:
            return ValidationResult(
                allowed=False,
                status="APPROVAL_INVALID",
                reason="Approval action_type mismatch."
            )
            
        if approval.target_name != getattr(action, 'target_name', ''):
            return ValidationResult(
                allowed=False,
                status="APPROVAL_INVALID",
                reason="Approval target_name mismatch."
            )

        if approval.snapshot_id != controller.latest_snapshot_id:
            return ValidationResult(
                allowed=False, 
                status="APPROVAL_INVALID", 
                reason="Approval bound to stale snapshot."
            )
        if time.time() > approval.expires_at:
            return ValidationResult(
                allowed=False, 
                status="APPROVAL_EXPIRED", 
                reason="Digest-bound approval has expired."
            )
        if approval.decision != "approve":
            return ValidationResult(
                allowed=False, 
                status="APPROVAL_INVALID", 
                reason="Human approver rejected the action."
            )
            
        if approval.approver_id not in ALLOWED_APPROVERS:
            return ValidationResult(
                allowed=False,
                status="APPROVAL_INVALID",
                reason=f"Approver {approval.approver_id} is not authorized."
            )
            
    return ValidationResult(allowed=True, status="ALLOWED", reason="Approval verified.")

def grant_human_approval(action: UIAction, approver_id: str = "sec-lead-1", duration_sec: float = 60.0, decision: Literal["approve", "reject"] = "approve") -> Approval:
    """Simulates the out-of-band human confirmation step producing a digest-bound approval."""
    digest = compute_action_digest(action)
    return Approval(
        proposal_digest=digest,
        snapshot_id=action.snapshot_id,
        case_id=getattr(action, "case_id", "CASE-123"),
        action_type=action.action_type,
        target_name=getattr(action, "target_name", ""),
        approver_id=approver_id,
        expires_at=time.time() + duration_sec,
        decision=decision
    )

class GroundingResult(BaseModel):
    success: bool
    status: Literal["GROUNDED", "TARGET_NOT_FOUND", "AMBIGUOUS_TARGET", "DISABLED", "OUT_OF_BOUNDS"]
    locator: Optional[Any] = None
    bounding_box: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
