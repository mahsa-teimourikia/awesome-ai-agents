"""Credential-free human approval and least-privilege lab.

Northstar's incident agent may gather evidence and prepare a rollback, but it
cannot execute a customer-visible or production-changing action.  This module
models the application-owned policy boundary; it is intentionally not a model
prompt and never contacts a real system.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal


Permission = Literal["READ", "PROPOSE", "EXECUTE_WITH_APPROVAL"]
Decision = Literal["approve", "modify", "reject", "escalate"]
RunStatus = Literal["paused", "executed", "rejected", "escalated", "expired"]


TOOL_PERMISSIONS: dict[str, Permission] = {
    "get_service_status": "READ",
    "query_region_logs": "READ",
    "inspect_deployments": "READ",
    "prepare_rollback": "PROPOSE",
    "draft_customer_notice": "PROPOSE",
    "create_incident_ticket": "PROPOSE",
    "restart_service": "EXECUTE_WITH_APPROVAL",
    "rollback_deployment": "EXECUTE_WITH_APPROVAL",
    "send_customer_notice": "EXECUTE_WITH_APPROVAL",
}

ROLE_GRANTS: dict[str, set[Permission]] = {
    "support_agent": {"READ", "PROPOSE"},
    "incident_commander": {"READ", "PROPOSE", "EXECUTE_WITH_APPROVAL"},
    "communications_reviewer": {"READ", "PROPOSE", "EXECUTE_WITH_APPROVAL"},
}

REQUIRED_REVIEWER: dict[str, str] = {
    "restart_service": "incident_commander",
    "rollback_deployment": "incident_commander",
    "send_customer_notice": "communications_reviewer",
}


@dataclass(frozen=True)
class Evidence:
    source: str
    fact: str
    observed_at: str


@dataclass(frozen=True)
class ProposedAction:
    tool: str
    arguments: dict[str, str]
    rationale: str
    risk: Literal["low", "medium", "high"]
    evidence_ids: tuple[str, ...]

    def fingerprint(self) -> str:
        return sha256(repr((self.tool, sorted(self.arguments.items()), self.evidence_ids)).encode()).hexdigest()[:16]


@dataclass
class ApprovalRequest:
    run_id: str
    tenant_id: str
    requester: str
    action: ProposedAction
    evidence: list[Evidence]
    expires_at: str
    status: RunStatus = "paused"
    action_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.action_fingerprint:
            self.action_fingerprint = self.action.fingerprint()


@dataclass(frozen=True)
class AuditEvent:
    run_id: str
    tenant_id: str
    actor: str
    decision: Decision
    original_fingerprint: str
    final_fingerprint: str | None
    reason: str
    timestamp: str


@dataclass
class ApprovalStore:
    requests: dict[str, ApprovalRequest] = field(default_factory=dict)
    executed_fingerprints: set[str] = field(default_factory=set)
    audit: list[AuditEvent] = field(default_factory=list)

    def save(self, request: ApprovalRequest) -> None:
        self.requests[request.run_id] = request

    def load(self, run_id: str, tenant_id: str) -> ApprovalRequest:
        request = self.requests[run_id]
        if request.tenant_id != tenant_id:
            raise PermissionError("Tenant mismatch: approval request is not visible to this caller.")
        return request


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def can_propose(role: str, tool: str) -> bool:
    return TOOL_PERMISSIONS[tool] in ROLE_GRANTS[role]


def get_evidence() -> list[Evidence]:
    return [
        Evidence("service_health", "checkout is degraded in eu-west", "2026-08-10T09:05:00Z"),
        Evidence("logs", "3DS callback errors rose after deploy-1842", "2026-08-10T09:06:00Z"),
        Evidence("deployments", "deploy-1842 enabled strict token validation at 08:42 UTC", "2026-08-10T09:07:00Z"),
    ]


def validate_action(action: ProposedAction, evidence: list[Evidence]) -> None:
    if action.tool not in TOOL_PERMISSIONS:
        raise ValueError("Unknown tool is denied by default.")
    if TOOL_PERMISSIONS[action.tool] != "EXECUTE_WITH_APPROVAL":
        raise ValueError("This exercise pauses only consequential execution tools.")
    if action.risk != "high" or len(action.evidence_ids) < 2:
        raise ValueError("High-impact actions require risk classification and at least two evidence references.")
    known = {item.source for item in evidence}
    if not set(action.evidence_ids).issubset(known):
        raise ValueError("Approval payload cites evidence that was not collected in this run.")
    if action.tool == "rollback_deployment" and action.arguments.get("deployment_id") != "deploy-1842":
        raise ValueError("Rollback target must be a validated deployment identifier.")
    if action.tool == "rollback_deployment" and action.arguments.get("region") != "eu-west":
        raise ValueError("Rollback scope must remain the validated eu-west region.")


def propose_rollback(store: ApprovalStore, run_id: str = "approval-eu-1842", tenant_id: str = "northstar", requester: str = "support_agent") -> ApprovalRequest:
    if not can_propose(requester, "prepare_rollback"):
        raise PermissionError("Requester cannot prepare a rollback.")
    evidence = get_evidence()
    action = ProposedAction(
        tool="rollback_deployment",
        arguments={"service": "checkout", "deployment_id": "deploy-1842", "region": "eu-west"},
        rationale="Independent logs and deployment history support a scoped rollback; service health shows customer impact.",
        risk="high",
        evidence_ids=("service_health", "logs", "deployments"),
    )
    validate_action(action, evidence)
    request = ApprovalRequest(run_id, tenant_id, requester, action, evidence, "2026-08-10T10:00:00Z")
    store.save(request)
    return request


def decide(
    store: ApprovalStore,
    run_id: str,
    tenant_id: str,
    actor: str,
    decision: Decision,
    reason: str,
    modified_action: ProposedAction | None = None,
) -> dict[str, object]:
    """Resume an exact approval request with authorization, validation, and audit.

    The returned "execution" is a deterministic record, not a real side effect.
    A real executor would use an idempotency key equal to the final fingerprint.
    """
    request = store.load(run_id, tenant_id)
    if request.status != "paused":
        raise ValueError(f"Run is not pending approval: {request.status}")
    if actor != REQUIRED_REVIEWER[request.action.tool]:
        raise PermissionError(f"{actor} cannot approve {request.action.tool}.")
    if not reason.strip():
        raise ValueError("Approval decisions require a review reason.")
    if decision in {"reject", "escalate"}:
        request.status = "rejected" if decision == "reject" else "escalated"
        event = AuditEvent(run_id, tenant_id, actor, decision, request.action_fingerprint, None, reason, now())
        store.audit.append(event)
        return {"status": request.status, "executed": False, "audit": event}

    final = modified_action if decision == "modify" else request.action
    validate_action(final, request.evidence)
    fingerprint = final.fingerprint()
    if fingerprint in store.executed_fingerprints:
        raise RuntimeError("Duplicate execution blocked by idempotency key.")
    store.executed_fingerprints.add(fingerprint)
    request.status = "executed"
    event = AuditEvent(run_id, tenant_id, actor, decision, request.action_fingerprint, fingerprint, reason, now())
    store.audit.append(event)
    return {"status": request.status, "executed": True, "execution": {"tool": final.tool, "arguments": final.arguments, "idempotency_key": fingerprint}, "audit": event}


def permission_matrix() -> list[dict[str, str]]:
    return [{"tool": tool, "level": level, "reviewer": REQUIRED_REVIEWER.get(tool, "none")} for tool, level in TOOL_PERMISSIONS.items()]


def demo_paths() -> dict[str, object]:
    approved_store = ApprovalStore()
    request = propose_rollback(approved_store)
    approved = decide(approved_store, request.run_id, "northstar", "incident_commander", "approve", "Evidence supports a scoped rollback.")

    rejected_store = ApprovalStore()
    request = propose_rollback(rejected_store, run_id="approval-reject")
    rejected = decide(rejected_store, request.run_id, "northstar", "incident_commander", "reject", "Wait for the deployment owner to verify rollback impact.")

    return {"request": request, "approved": approved, "rejected": rejected, "matrix": permission_matrix()}


if __name__ == "__main__":
    result = demo_paths()
    print("approval request:", asdict(result["request"]))
    print("approved:", result["approved"])
    print("rejected:", result["rejected"])
