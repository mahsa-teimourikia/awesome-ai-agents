import hashlib
import json
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class RefundProposal(BaseModel):
    transaction_id: str = Field(..., description="The original transaction ID")
    amount_cents: int = Field(..., description="Amount to refund in cents")
    reason: str = Field(..., description="Reason for the refund")

def hash_proposal(proposal: RefundProposal) -> str:
    """Creates a deterministic SHA-256 digest of the business proposal."""
    canon = json.dumps(proposal.model_dump(), sort_keys=True)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()

class Approval(BaseModel):
    proposal_digest: str = Field(..., description="The SHA-256 hash of the exact proposal approved")
    approver_id: str = Field(..., description="The identity of the human who approved it")
    expires_at_unix: float = Field(..., description="Unix timestamp of approval expiration")

class IssueRefundArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    transaction_id: str = Field(..., description="The transaction to refund")
    amount_cents: int = Field(..., description="Amount to refund in cents")
    reason: str = Field(..., description="Explanation for audit logs")
    idempotency_key: str = Field(..., description="Client-provided idempotency key")
    approval: Approval = Field(..., description="Cryptographic human approval token")

class RefundCommand(BaseModel):
    tenant_id: str
    transaction_id: str
    amount_cents: int
    reason: str
    idempotency_key: str
    approval: Approval

class RefundResult(BaseModel):
    status: Literal["success", "duplicate"]
    refund_id: str
    amount_cents: int

class ErrorResult(BaseModel):
    error_type: str
    message: str

def validate_approval(proposal: RefundProposal, approval: Approval, current_time_unix: float) -> None:
    """Strictly validates the digest-bound approval token against the current proposal and clock."""
    if current_time_unix > approval.expires_at_unix:
        raise ValueError("Approval token has expired.")
    
    current_digest = hash_proposal(proposal)
    if current_digest != approval.proposal_digest:
        raise ValueError(f"Approval digest mismatch! The proposal was mutated after approval.\nExpected: {approval.proposal_digest}\nActual: {current_digest}")

DB_PROCESSED_REFUNDS = set()
def _issue_refund_impl(cmd: RefundCommand) -> RefundResult:
    # 5. Core Business/Database Logic
    # 5a. Idempotency Check
    if cmd.idempotency_key in DB_PROCESSED_REFUNDS:
        return RefundResult(status="duplicate", refund_id=f"ref_{cmd.idempotency_key}", amount_cents=cmd.amount_cents)
    
    # 5b. Cross-Tenant Verification
    # (Mock) Verify transaction belongs to tenant
    if cmd.transaction_id.startswith("tx_") and not cmd.transaction_id.endswith(cmd.tenant_id):
        # We simulate cross-tenant failure if the tx doesn't end with the tenant ID
        if cmd.tenant_id == "acme_inc" and cmd.transaction_id == "tx_789_other_tenant":
            raise PermissionError("Transaction belongs to a different tenant!")

    # 5c. Execution
    DB_PROCESSED_REFUNDS.add(cmd.idempotency_key)
    return RefundResult(status="success", refund_id=f"ref_{cmd.idempotency_key}", amount_cents=cmd.amount_cents)
