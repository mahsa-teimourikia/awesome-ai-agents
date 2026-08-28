import hashlib
import json
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

class UIAction(BaseModel):
    action_type: Literal['click', 'type', 'scroll', 'wait', 'navigate', 'submit_commit']
    target_id: Optional[str] = None
    value: Optional[str] = None

class ControllerState(BaseModel):
    allowed_origins: List[str]
    current_origin: str = "https://internal-portal.example"
    snapshot_id: str = "snap_1"

def compute_action_digest(action: UIAction) -> str:
    canon = json.dumps(action.model_dump(exclude_none=True), sort_keys=True)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()

class Approval(BaseModel):
    action_digest: str
    approver_id: str
    expires_at_unix: float

def grant_human_approval(action: UIAction, approver_id: str = "sec-lead-1", duration_sec: float = 60.0, decision: Literal["approve", "reject"] = "approve") -> Approval:
    import time
    if decision == "reject":
        raise ValueError("Human rejected the action.")
    return Approval(
        action_digest=compute_action_digest(action),
        approver_id=approver_id,
        expires_at_unix=time.time() + duration_sec
    )

def validate_policy(
    action: UIAction, 
    agent_snapshot_id: str,
    controller: ControllerState
) -> None:
    """Phase 1: Zero-Trust Runtime Validation."""
    # 1. Origin Allowlist Validation
    if controller.current_origin not in controller.allowed_origins:
        raise PermissionError(f"Action blocked: Origin '{controller.current_origin}' is not in the allowlist.")
    
    # 2. Synchronous State Validation (Snapshot matching)
    if agent_snapshot_id != controller.snapshot_id:
        raise ValueError(f"Action blocked: Stale state. Agent used snapshot {agent_snapshot_id}, but current DOM is {controller.snapshot_id}. The page has mutated.")

def validate_approval(
    action: UIAction,
    approval_token: Optional[Approval]
) -> None:
    """Phase 2: Cryptographic Human Approval Check."""
    import time
    if not approval_token:
        raise PermissionError(f"ACTION INTERCEPTED: '{action.action_type}' requires an explicit human approval token.")
        
    if time.time() > approval_token.expires_at_unix:
        raise PermissionError("Human approval token has expired.")
        
    current_digest = compute_action_digest(action)
    if current_digest != approval_token.action_digest:
        raise PermissionError(f"Approval digest mismatch! The payload was mutated.\nExpected: {approval_token.action_digest}\nActual: {current_digest}")
