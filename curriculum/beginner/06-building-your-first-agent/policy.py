import hashlib
import json
from typing import Literal, Set
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

# Domain Errors
class DomainValidationError(Exception):
    """Raised when business domain rules fail."""
    pass

class AuthorizationError(Exception):
    """Raised when role or tenant scope validation fails."""
    pass

# Mock Database Fixtures
DB = {
    'tickets': {
        'T-102': {'tenant_id': 'Northstar', 'customer_id': 'C-55', 'text': 'I was charged twice for my subscription. Please fix it.', 'status': 'open'},
        'T-999': {'tenant_id': 'AcmeCorp', 'customer_id': 'C-99', 'text': 'Acme cross-tenant ticket.', 'status': 'open'}
    },
    'transactions': {
        'C-55': [
            {'tenant_id': 'Northstar', 'tx_id': 'TX-901', 'amount_cents': 10000, 'date': '2026-08-01', 'note': 'initial subscription charge'},
            {'tenant_id': 'Northstar', 'tx_id': 'TX-902', 'amount_cents': 10000, 'date': '2026-08-01', 'note': 'system duplicate charge'}
        ],
        'C-99': [
            {'tenant_id': 'AcmeCorp', 'tx_id': 'TX-801', 'amount_cents': 5000, 'date': '2026-08-01', 'note': 'acme single charge'}
        ]
    },
    'refunds': []
}

ALLOWED_APPROVERS: Set[str] = {'MGR-1', 'MGR-2', 'COMPLIANCE-LEAD'}

class ApprovalDecision(str, Enum):
    APPROVE = 'approve'
    REJECT = 'reject'

class RefundProposal(BaseModel):
    customer_id: str = Field(..., description="The customer ID")
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
    decision: ApprovalDecision = Field(..., description="The decision of the approver")
    expires_at: float = Field(..., description="Unix timestamp of approval expiration")

class IssueRefundArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    customer_id: str = Field(..., description="The customer ID")
    transaction_id: str = Field(..., description="The transaction to refund")
    amount_cents: int = Field(..., description="Amount to refund in cents")
    idempotency_key: str = Field(..., description="Client-provided idempotency key")

class RefundCommand(BaseModel):
    tenant_id: str
    customer_id: str
    transaction_id: str
    amount_cents: int
    idempotency_key: str

class RefundResult(BaseModel):
    status: Literal['success', 'already_processed']
    amount_cents: int
    transaction_id: str

class ErrorResult(BaseModel):
    error_type: str
    message: str

def validate_approval(proposal: RefundProposal, approval: Approval, current_time_unix: float) -> None:
    """Strictly validates the digest-bound approval token against the current proposal and clock."""
    if current_time_unix > approval.expires_at:
        raise ValueError("Approval has expired.")
    
    if approval.decision != ApprovalDecision.APPROVE:
        raise ValueError("Approval decision was not to approve.")

    if approval.approver_id not in ALLOWED_APPROVERS:
        raise AuthorizationError(f"Unauthorized approver ID: {approval.approver_id}")

    current_digest = hash_proposal(proposal)
    if current_digest != approval.proposal_digest:
        raise ValueError(f"Approval digest mismatch! The proposal was mutated after approval.\nExpected: {approval.proposal_digest}\nActual: {current_digest}")

def _issue_refund_impl(cmd: RefundCommand) -> RefundResult:
    # 5. Core Business/Database Logic

    # 5a. Cross-Tenant Verification
    customer_txs = DB['transactions'].get(cmd.customer_id, [])
    tx = next((t for t in customer_txs if t['tx_id'] == cmd.transaction_id), None)
    if not tx:
        raise DomainValidationError("Transaction not found for this customer.")
    
    if tx['tenant_id'] != cmd.tenant_id:
        raise AuthorizationError("Cross-tenant refund denied: transaction belongs to another organization.")
    
    if tx['amount_cents'] != cmd.amount_cents:
        raise DomainValidationError("Refund amount must match transaction amount strictly.")

    # 5b. Idempotency Check
    if any(r['idempotency_key'] == cmd.idempotency_key for r in DB['refunds']):
        return RefundResult(status="already_processed", transaction_id=cmd.transaction_id, amount_cents=cmd.amount_cents)

    # 5c. Execution
    DB['refunds'].append({
        'tenant_id': cmd.tenant_id,
        'customer_id': cmd.customer_id,
        'transaction_id': cmd.transaction_id,
        'amount_cents': cmd.amount_cents,
        'idempotency_key': cmd.idempotency_key
    })
    return RefundResult(status="success", transaction_id=cmd.transaction_id, amount_cents=cmd.amount_cents)

