"""Credential-free scenarios for the Agent Development Frameworks course.

Each function deliberately separates deterministic policy from a framework-shaped
agent decision. The notebooks use these functions as executable fixtures before
showing optional real SDK implementations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class Evidence:
    source_id: str
    claim: str
    confidence: float


@dataclass(frozen=True)
class ComplianceDecision:
    case_id: str
    decision: Literal["approve", "escalate", "reject"]
    evidence_ids: list[str]
    rationale: str
    requires_human_review: bool


INCIDENT_EVIDENCE = {
    "status": Evidence("status-checkout", "checkout is degraded in eu-west", 0.96),
    "incident": Evidence("inc-482", "payment-token validation errors increased after release 2026.08.10.1", 0.92),
    "runbook": Evidence("runbook-checkout", "collect evidence and propose rollback; do not execute it", 0.99),
}


def openai_sdk_shaped_triage(request: str) -> dict:
    """A deterministic trace mirroring a managed tool-using incident agent."""
    trace = [
        {"kind": "session", "detail": "incident-eu-482"},
        {"kind": "tool", "name": "get_service_status", "detail": asdict(INCIDENT_EVIDENCE["status"])},
        {"kind": "tool", "name": "search_incidents", "detail": asdict(INCIDENT_EVIDENCE["incident"])},
        {"kind": "tool", "name": "get_runbook", "detail": asdict(INCIDENT_EVIDENCE["runbook"])},
        {"kind": "guardrail", "name": "evidence_required", "detail": {"passed": True}},
    ]
    return {
        "request": request,
        "answer": "Evidence supports a checkout degradation after the release. Prepare a rollback proposal; do not execute it.",
        "citations": [item.source_id for item in INCIDENT_EVIDENCE.values()],
        "trace": trace,
    }


def pydanticai_shaped_compliance_case(case_id: str, amount_usd: int, country: str) -> ComplianceDecision:
    """Return a schema-shaped decision; policy, not a model, determines escalation."""
    high_risk = amount_usd >= 10_000 or country.upper() in {"IR", "KP"}
    evidence = ["kyc-verified", "transaction-screening"]
    if high_risk:
        return ComplianceDecision(case_id, "escalate", evidence, "High-risk threshold requires analyst review.", True)
    return ComplianceDecision(case_id, "approve", evidence, "Required checks passed below the escalation threshold.", False)


def langgraph_shaped_approval(action: str, approved: bool = False) -> dict:
    """Model a durable workflow that may stop at a human approval boundary."""
    if action not in {"prepare_rollback", "restart_checkout"}:
        return {"state": "rejected", "reason": "Unknown action"}
    if action == "prepare_rollback":
        return {"state": "complete", "artifact": "Rollback plan prepared; no production action executed."}
    if not approved:
        return {"state": "interrupt", "proposal": "restart_checkout", "reason": "Production restart needs named human approval."}
    return {"state": "complete", "artifact": "Restart command authorized for audited execution."}


def adk_shaped_customer_impact() -> dict:
    """Compose bounded specialist outputs instead of an open-ended group chat."""
    findings = {
        "observability": {"evidence": "EU checkout errors increased 31%", "source": "metrics-eu"},
        "deployment": {"evidence": "release 2026.08.10.1 preceded the increase", "source": "deploy-2026.08.10.1"},
        "customer_impact": {"evidence": "six enterprise complaints; Gold SLA at risk", "source": "support-queue"},
    }
    return {
        "findings": findings,
        "plan": "Open an incident, notify on-call, and prepare a rollback for approval. Do not restart services automatically.",
        "coordination_cost": {"specialists": 3, "tool_calls": 3, "handoffs": 0},
    }


def microsoft_agent_framework_shaped_operations_workflow() -> dict:
    return {"workflow": ["triage", "retrieve_customer_context", "draft_escalation", "human_review"], "tools": ["get_service_status", "search_tickets"], "result": "Draft escalation for Gold customer impact; waiting for on-call review.", "major_features": ["agents", "function tools", "workflow builder", "stateful execution", "middleware/observability seam"]}


def crewai_shaped_incident_crew() -> dict:
    return {"roles": ["Observability Engineer", "Release Engineer", "Incident Commander"], "tasks": ["collect telemetry", "inspect deployment", "synthesize approved response"], "process": "sequential with explicit task context", "result": "Rollback proposal prepared with evidence; no production action executed.", "major_features": ["agents", "tasks", "crews", "processes", "flows", "tools", "memory/knowledge boundary", "guardrails/observability seam"]}


if __name__ == "__main__":
    print(openai_sdk_shaped_triage("European customers cannot complete checkout."))
    print(pydanticai_shaped_compliance_case("case-17", 12_500, "CA"))
    print(langgraph_shaped_approval("restart_checkout"))
    print(adk_shaped_customer_impact())
    print(microsoft_agent_framework_shaped_operations_workflow())
    print(crewai_shaped_incident_crew())
