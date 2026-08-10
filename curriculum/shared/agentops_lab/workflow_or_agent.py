from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentops_lab.loop_yourself import DATA_DIR, get_runbook, get_service_status, search_incidents


@dataclass
class ArchitectureRun:
    task: str
    architecture: str
    reason: str
    steps: list[str]
    result: str
    evidence: list[dict[str, Any]] = field(default_factory=list)


def _load_json(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text())


def get_recent_deployments(service_name: str, region: str | None = None) -> dict[str, Any]:
    deployments = []
    for deployment in _load_json("deployments.json"):
        if deployment["service"] != service_name.lower():
            continue
        if region and deployment["region"] not in {region.lower(), "global"}:
            continue
        deployments.append(deployment)
    return {"service": service_name.lower(), "region": region, "count": len(deployments), "deployments": deployments}


def query_region_logs(service_name: str, region: str, query: str) -> dict[str, Any]:
    query_terms = query.lower().split()
    matches = []
    for log in _load_json("region_logs.json"):
        if log["service"] != service_name.lower() or log["region"] != region.lower():
            continue
        searchable = f"{log['level']} {log['message']} {log['customer_segment']}".lower()
        if any(term in searchable for term in query_terms):
            matches.append(log)
    return {"service": service_name.lower(), "region": region.lower(), "query": query, "count": len(matches), "matches": matches}


def task_a_status_report(service_name: str = "checkout") -> ArchitectureRun:
    status = get_service_status(service_name)
    if not status["found"]:
        report = f"No status found for {service_name}."
    else:
        report = (
            f"{service_name.title()} status report: health={status['health']}; "
            f"owner={status['owner']}; tier={status['sla_tier']}; "
            f"dependencies={', '.join(status['dependencies'])}; latest_deploy={status['last_deploy']}."
        )
    return ArchitectureRun(
        task="A: Retrieve checkout status and format a report",
        architecture="deterministic workflow",
        reason="The steps are known in advance: read status, then format the result. A model-controlled loop would add cost and failure paths without improving the outcome.",
        steps=["get_service_status", "format_status_report"],
        result=report,
        evidence=[status],
    )


def summarize_runbook_response(service_name: str, status: dict[str, Any], runbook: dict[str, Any]) -> str:
    if not runbook["found"]:
        return f"{service_name.title()} is {status['health']}, but no runbook was found. Escalate to {status['owner']}."
    return (
        f"{service_name.title()} is {status['health']}. Follow the runbook: confirm evidence before declaring an incident, "
        "check active incidents and payment error signals, prioritize affected SLA tiers, and escalate to the service owner if evidence is incomplete."
    )


def task_b_bounded_workflow(service_name: str = "checkout") -> ArchitectureRun:
    status = get_service_status(service_name)
    steps = ["get_service_status", "branch_on_health"]
    evidence = [status]

    if not status["found"]:
        result = f"No status found for {service_name}; escalate to operations."
    elif status["health"] == "healthy":
        result = f"{service_name.title()} is healthy. No incident runbook is needed."
    else:
        runbook = get_runbook(service_name)
        evidence.append(runbook)
        steps.extend(["get_runbook", "summarize_runbook_response"])
        result = summarize_runbook_response(service_name, status, runbook)

    return ArchitectureRun(
        task="B: If checkout is unhealthy, retrieve runbook and summarize response",
        architecture="bounded workflow",
        reason="The control path is still mostly known. One conditional branch decides whether a summary is needed, so code should own the path and the model should only summarize bounded material.",
        steps=steps,
        result=result,
        evidence=evidence,
    )


class EuropeCheckoutInvestigator:
    """Small deterministic planner for an open-ended incident question."""

    def choose_next_tool(self, evidence: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
        tool_names = {item["tool"] for item in evidence}
        if "get_service_status" not in tool_names:
            return "get_service_status", {"service_name": "checkout"}
        if "search_incidents" not in tool_names:
            return "search_incidents", {"query": "active checkout payment eu europe 3ds vat failures"}
        if "get_recent_deployments" not in tool_names:
            return "get_recent_deployments", {"service_name": "checkout", "region": "eu-west"}
        if "query_region_logs" not in tool_names:
            return "query_region_logs", {"service_name": "checkout", "region": "eu-west", "query": "3DS VAT checkout error enterprise"}
        if "get_runbook" not in tool_names:
            return "get_runbook", {"service_name": "checkout"}
        return None


def task_c_dynamic_investigation(max_steps: int = 6) -> ArchitectureRun:
    planner = EuropeCheckoutInvestigator()
    evidence: list[dict[str, Any]] = []
    steps: list[str] = []
    tool_map = {
        "get_service_status": get_service_status,
        "search_incidents": search_incidents,
        "get_recent_deployments": get_recent_deployments,
        "query_region_logs": query_region_logs,
        "get_runbook": get_runbook,
    }

    for _ in range(max_steps):
        call = planner.choose_next_tool(evidence)
        if call is None:
            break
        name, arguments = call
        result = tool_map[name](**arguments)
        steps.append(name)
        evidence.append({"tool": name, "arguments": arguments, "result": result})

    result = (
        "European checkout failures need a dynamic investigation. Evidence shows checkout is degraded, there is an active checkout/payment incident, "
        "a recent eu-west checkout UI deployment changed VAT and 3DS handling, and eu-west logs show 3DS callback rejections for enterprise customers. "
        "Recommended response: acknowledge regional checkout impact, prioritize enterprise SLA customers, keep fallback payment routing available, "
        "and ask checkout owners to inspect the VAT/3DS deployment before claiming root cause."
    )
    return ArchitectureRun(
        task="C: Investigate reports that some European customers cannot complete checkout",
        architecture="single bounded agent",
        reason="The path is not obvious up front. The system must choose which evidence to inspect next based on observations, while still staying within a max-step budget.",
        steps=steps,
        result=result,
        evidence=evidence,
    )


def classify_task(problem_shape: str) -> str:
    normalized = problem_shape.lower()
    if "known" in normalized:
        return "Workflow"
    if "few model" in normalized or "bounded" in normalized:
        return "Agentic workflow"
    if "dynamic" in normalized or "open" in normalized:
        return "Agent"
    if "specialized" in normalized or "separable" in normalized:
        return "Multi-agent"
    return "Start with a workflow, then justify added autonomy with evaluation evidence"


if __name__ == "__main__":
    for run in [task_a_status_report(), task_b_bounded_workflow(), task_c_dynamic_investigation()]:
        print(f"\n{run.task}")
        print(f"architecture={run.architecture}")
        print(f"steps={' -> '.join(run.steps)}")
        print(run.result)
