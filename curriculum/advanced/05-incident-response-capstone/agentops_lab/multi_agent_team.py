from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentops_lab.workflow_or_agent import get_recent_deployments, query_region_logs


@dataclass
class AgentFinding:
    agent: str
    finding: str
    evidence: list[str]
    confidence: float


@dataclass
class IncidentRunComparison:
    architecture: str
    accuracy: float
    cost: float
    latency_seconds: float
    tool_calls: int
    tokens: int
    coordination_overhead: int
    recommendation: str


def query_metrics() -> dict:
    return {
        "checkout_conversion_drop": 0.35,
        "region": "eu-west",
        "payment_authorization_errors": "normal",
        "cart_to_checkout_clicks": "normal",
        "checkout_to_payment_redirect": "down 38%",
    }


def query_customer_reports() -> dict:
    return {
        "affected_segments": ["enterprise", "vat_registered_buyers"],
        "top_report": "EU customers see 3DS redirect loop after entering VAT ID.",
        "ticket_count": 91,
    }


def observability_agent() -> AgentFinding:
    metrics = query_metrics()
    logs = query_region_logs("checkout", "eu-west", "ERROR 3DS VAT")
    return AgentFinding(
        agent="ObservabilityAgent",
        finding="Conversion drop is concentrated in eu-west checkout redirect flow; logs show 3DS callback errors.",
        evidence=[str(metrics), str(logs)],
        confidence=0.82,
    )


def deployment_agent() -> AgentFinding:
    deployments = get_recent_deployments("checkout", "eu-west")
    return AgentFinding(
        agent="DeploymentAgent",
        finding="A eu-west checkout UI deployment changed VAT validation and 3DS redirect handling before the drop.",
        evidence=[str(deployments)],
        confidence=0.78,
    )


def customer_impact_agent() -> AgentFinding:
    reports = query_customer_reports()
    return AgentFinding(
        agent="CustomerImpactAgent",
        finding="Enterprise VAT-registered EU customers are disproportionately affected.",
        evidence=[str(reports)],
        confidence=0.75,
    )


def incident_analyst_agent(findings: list[AgentFinding]) -> AgentFinding:
    return AgentFinding(
        agent="IncidentAnalystAgent",
        finding="Likely cause is the eu-west VAT/3DS checkout UI change causing redirect-loop failures for enterprise buyers.",
        evidence=[finding.finding for finding in findings],
        confidence=0.84,
    )


def risk_reviewer_agent(analysis: AgentFinding) -> AgentFinding:
    return AgentFinding(
        agent="RiskReviewerAgent",
        finding="Recommendation is supported if phrased as likely cause and paired with rollback plus monitored fallback, not a confirmed root cause.",
        evidence=[analysis.finding, "Payment gateway errors are normal, so avoid blaming payments."],
        confidence=0.8,
    )


def run_multi_agent_team() -> tuple[list[AgentFinding], IncidentRunComparison]:
    specialist_findings = [observability_agent(), deployment_agent(), customer_impact_agent()]
    analysis = incident_analyst_agent(specialist_findings)
    risk = risk_reviewer_agent(analysis)
    findings = specialist_findings + [analysis, risk]
    recommendation = (
        "Roll back or disable the eu-west checkout UI VAT/3DS change, keep fallback payment routing available, "
        "notify enterprise support teams, and monitor checkout-to-payment redirect recovery. Present this as a likely cause until validated."
    )
    return findings, IncidentRunComparison(
        architecture="multi-agent team",
        accuracy=0.9,
        cost=0.046,
        latency_seconds=11.8,
        tool_calls=6,
        tokens=11800,
        coordination_overhead=5,
        recommendation=recommendation,
    )


def run_single_agent_baseline(simple_incident: bool = False) -> IncidentRunComparison:
    if simple_incident:
        return IncidentRunComparison(
            architecture="single agent",
            accuracy=0.86,
            cost=0.014,
            latency_seconds=4.9,
            tool_calls=3,
            tokens=4200,
            coordination_overhead=0,
            recommendation="Use a single agent for simple incidents with obvious outage signals.",
        )
    return IncidentRunComparison(
        architecture="single agent",
        accuracy=0.68,
        cost=0.022,
        latency_seconds=6.2,
        tool_calls=5,
        tokens=7100,
        coordination_overhead=0,
        recommendation="Suspects checkout issue but misses customer segmentation and underweights deployment evidence.",
    )


def compare_single_vs_team(simple_incident: bool = False) -> dict:
    single = run_single_agent_baseline(simple_incident=simple_incident)
    findings, team = run_multi_agent_team()
    return {
        "single_agent": single.__dict__,
        "multi_agent_team": team.__dict__,
        "findings": [finding.__dict__ for finding in findings],
        "decision": "single_agent" if simple_incident else "multi_agent_team",
        "lesson": "Add agents only when specialization improves accuracy or risk handling enough to justify coordination overhead.",
    }


if __name__ == "__main__":
    print(compare_single_vs_team())
    print(compare_single_vs_team(simple_incident=True)["decision"])
