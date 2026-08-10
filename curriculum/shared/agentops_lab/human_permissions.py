from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentops_lab.loop_yourself import get_runbook, get_service_status
from agentops_lab.tool_engineering import RestartRequest, restart_service
from agentops_lab.workflow_or_agent import get_recent_deployments, query_region_logs


PermissionLevel = Literal["READ", "PROPOSE", "EXECUTE_WITH_APPROVAL"]
HumanDecision = Literal["approve", "modify", "reject"]


APPROVAL_POLICY = {
    "query_logs": False,
    "get_status": False,
    "retrieve_runbook": False,
    "inspect_deployments": False,
    "prepare_rollback": False,
    "draft_notification": False,
    "prepare_ticket": False,
    "restart_service": True,
    "rollback_deployment": True,
    "send_notification": True,
}


TOOL_PERMISSIONS: dict[str, PermissionLevel] = {
    "query_logs": "READ",
    "get_status": "READ",
    "retrieve_runbook": "READ",
    "inspect_deployments": "READ",
    "prepare_rollback": "PROPOSE",
    "draft_notification": "PROPOSE",
    "prepare_ticket": "PROPOSE",
    "restart_service": "EXECUTE_WITH_APPROVAL",
    "rollback_deployment": "EXECUTE_WITH_APPROVAL",
    "send_notification": "EXECUTE_WITH_APPROVAL",
}


@dataclass
class ProposedAction:
    tool: str
    arguments: dict
    rationale: str
    risk: Literal["low", "medium", "high"]


@dataclass
class PausedRun:
    run_id: str
    proposed_action: ProposedAction
    evidence: list[dict]
    status: Literal["paused_for_approval"] = "paused_for_approval"


@dataclass
class ApprovalAuditEvent:
    actor: str
    decision: HumanDecision
    original_action: ProposedAction
    final_action: ProposedAction | None
    reason: str


@dataclass
class ApprovalResult:
    status: Literal["executed", "modified_and_executed", "rejected"]
    message: str
    audit: ApprovalAuditEvent


@dataclass
class InMemoryCheckpointStore:
    paused_runs: dict[str, PausedRun] = field(default_factory=dict)

    def save(self, run: PausedRun) -> None:
        self.paused_runs[run.run_id] = run

    def load(self, run_id: str) -> PausedRun:
        return self.paused_runs[run_id]

    def clear(self, run_id: str) -> None:
        self.paused_runs.pop(run_id, None)


def query_logs(service: str) -> dict:
    return query_region_logs(service, "eu-west", "ERROR")


def get_status(service: str) -> dict:
    return get_service_status(service)


def retrieve_runbook(service: str) -> dict:
    return get_runbook(service)


def inspect_deployments(service: str) -> dict:
    return get_recent_deployments(service, "eu-west")


def prepare_rollback(service: str, deployment_id: str, reason: str) -> dict:
    return {"prepared": True, "service": service, "deployment_id": deployment_id, "reason": reason}


def draft_notification(audience: str, message: str) -> dict:
    return {"draft": True, "audience": audience, "message": message}


def prepare_ticket(title: str, evidence: list[str]) -> dict:
    return {"draft": True, "title": title, "evidence": evidence}


def propose_restart_after_investigation(store: InMemoryCheckpointStore, run_id: str = "run-approval-001") -> PausedRun:
    evidence = [
        {"tool": "get_status", "result": get_status("checkout")},
        {"tool": "query_logs", "result": query_logs("checkout")},
        {"tool": "inspect_deployments", "result": inspect_deployments("checkout")},
    ]
    action = ProposedAction(
        tool="restart_service",
        arguments={
            "service": "checkout",
            "reason": "Restart checkout after eu-west 3DS callback errors and degraded checkout health.",
            "incident_id": "INC-1042",
        },
        rationale="Checkout is degraded and regional logs show repeated 3DS callback failures.",
        risk="high",
    )
    paused = PausedRun(run_id=run_id, proposed_action=action, evidence=evidence)
    store.save(paused)
    return paused


def requires_approval(action: ProposedAction) -> bool:
    return APPROVAL_POLICY.get(action.tool, True)


def execute_approved_action(action: ProposedAction) -> dict:
    if action.tool == "restart_service":
        request = RestartRequest(
            service=action.arguments["service"],
            reason=action.arguments["reason"],
            incident_id=action.arguments["incident_id"],
        )
        return restart_service(request, approved=True)
    if action.tool == "send_notification":
        return {"status": "sent", **action.arguments}
    if action.tool == "rollback_deployment":
        return {"status": "rolled_back", **action.arguments}
    raise ValueError(f"Unsupported executable action: {action.tool}")


def resume_with_human_decision(
    store: InMemoryCheckpointStore,
    run_id: str,
    decision: HumanDecision,
    actor: str = "incident-commander",
    modified_action: ProposedAction | None = None,
    reason: str = "",
) -> ApprovalResult:
    paused = store.load(run_id)
    original = paused.proposed_action

    if decision == "reject":
        audit = ApprovalAuditEvent(actor, decision, original, None, reason or "Rejected by human reviewer.")
        store.clear(run_id)
        return ApprovalResult("rejected", "Restart rejected; continue investigation or escalate with evidence.", audit)

    action = modified_action if decision == "modify" and modified_action else original
    execution = execute_approved_action(action)
    store.clear(run_id)

    audit = ApprovalAuditEvent(actor, decision, original, action, reason or f"{decision.title()}d by human reviewer.")
    status = "modified_and_executed" if decision == "modify" else "executed"
    return ApprovalResult(status, f"{action.tool} completed: {execution}", audit)


def permission_matrix() -> list[dict[str, str]]:
    return [{"tool": tool, "permission": permission, "requires_approval": str(APPROVAL_POLICY[tool])} for tool, permission in TOOL_PERMISSIONS.items()]


def demo_approval_paths() -> dict:
    store = InMemoryCheckpointStore()
    paused = propose_restart_after_investigation(store)

    approve_store = InMemoryCheckpointStore()
    approve_store.save(paused)
    approved = resume_with_human_decision(approve_store, paused.run_id, "approve", reason="Evidence supports restart and incident commander approved.")

    modify_store = InMemoryCheckpointStore()
    modify_store.save(paused)
    modified_action = ProposedAction(
        tool="restart_service",
        arguments={
            "service": "checkout",
            "reason": "Restart only checkout-api workers in eu-west after 3DS callback errors.",
            "incident_id": "INC-1042",
        },
        rationale="Limit blast radius to eu-west checkout workers.",
        risk="high",
    )
    modified = resume_with_human_decision(modify_store, paused.run_id, "modify", modified_action=modified_action, reason="Scope narrowed before approval.")

    reject_store = InMemoryCheckpointStore()
    reject_store.save(paused)
    rejected = resume_with_human_decision(reject_store, paused.run_id, "reject", reason="Need deployment owner confirmation before restart.")

    return {"paused": paused, "approved": approved, "modified": modified, "rejected": rejected, "permissions": permission_matrix()}


if __name__ == "__main__":
    demo = demo_approval_paths()
    print(demo["paused"])
    print(demo["approved"].status, demo["approved"].message)
    print(demo["modified"].status, demo["modified"].message)
    print(demo["rejected"].status, demo["rejected"].message)
    print(demo["permissions"])
