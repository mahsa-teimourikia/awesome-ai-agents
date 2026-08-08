from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

DATA_DIR = Path(__file__).resolve().parent / "data"
EVAL_DIR = Path(__file__).resolve().parent / "evaluations"

MAX_STEPS = 9
MAX_TOOL_CALLS = 10
MAX_ESTIMATED_COST = 0.06


@dataclass(frozen=True)
class ToolResult:
    name: str
    data: object
    latency_ms: int
    estimated_cost: float


@dataclass(frozen=True)
class PreparedAction:
    action: str
    target: str
    reason: str
    status: str


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def get_service_metrics(service: str, region: str) -> ToolResult:
    metrics = load_json(DATA_DIR / "capstone_metrics.json")
    return ToolResult("get_service_metrics", metrics, latency_ms=180, estimated_cost=0.002)


def query_logs(service: str, region: str, query: str) -> ToolResult:
    logs = [
        row
        for row in load_json(DATA_DIR / "region_logs.json")
        if row["service"] == service and row["region"] == region and query.lower() in row["message"].lower()
    ]
    return ToolResult("query_logs", logs, latency_ms=420, estimated_cost=0.004)


def get_recent_deployments(service: str, region: str) -> ToolResult:
    deployments = [
        row
        for row in load_json(DATA_DIR / "deployments.json")
        if row["service"] == service and row["region"] in {region, "global"}
    ]
    capstone_deploy = {
        "id": "DEP-8801",
        "service": "checkout",
        "version": "checkout-ui 2026-08-08.1",
        "region": "eu-west",
        "status": "completed",
        "started_at": "2026-08-08T08:42:00Z",
        "completed_at": "2026-08-08T08:49:00Z",
        "notes": "Enabled new VAT validation flow before 3DS redirect return.",
    }
    return ToolResult("get_recent_deployments", [capstone_deploy, *deployments], latency_ms=260, estimated_cost=0.003)


def search_tickets(region: str) -> ToolResult:
    tickets = [row for row in load_json(DATA_DIR / "capstone_tickets.json") if row["region"] == region]
    return ToolResult("search_tickets", tickets, latency_ms=300, estimated_cost=0.003)


def get_customer_slas(region: str) -> ToolResult:
    customers: list[dict[str, str]] = []
    with (DATA_DIR / "customers.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["region"] == region:
                customers.append(row)
    return ToolResult("get_customer_slas", customers, latency_ms=220, estimated_cost=0.002)


def get_runbook(service: str) -> ToolResult:
    runbook = (Path(__file__).resolve().parent / "runbooks" / f"{service}.md").read_text(encoding="utf-8")
    return ToolResult("get_runbook", runbook, latency_ms=160, estimated_cost=0.001)


def prepare_action(action: str, target: str, reason: str, approved: bool = False) -> PreparedAction:
    status = "prepared_only" if not approved else "ready_for_execution_after_external_confirmation"
    return PreparedAction(action=action, target=target, reason=reason, status=status)


def architecture_candidates() -> dict[str, dict[str, float | int | bool | str]]:
    return {
        "deterministic_workflow": {
            "success": False,
            "diagnosis_correct": False,
            "recommendation_supported": False,
            "latency_seconds": 2.1,
            "estimated_cost": 0.006,
            "tool_calls": 3,
            "coordination_overhead": 0,
            "reason": "Too rigid for a mostly-green incident with several possible evidence paths.",
        },
        "single_bounded_agent": {
            "success": True,
            "diagnosis_correct": True,
            "recommendation_supported": True,
            "latency_seconds": 6.4,
            "estimated_cost": 0.025,
            "tool_calls": 6,
            "coordination_overhead": 0,
            "reason": "Enough for this incident: one agent can gather the needed evidence within budgets.",
        },
        "multi_agent_team": {
            "success": True,
            "diagnosis_correct": True,
            "recommendation_supported": True,
            "latency_seconds": 12.7,
            "estimated_cost": 0.052,
            "tool_calls": 8,
            "coordination_overhead": 5,
            "reason": "Also works, but the measured gain over the single bounded agent is not large enough here.",
        },
    }


def choose_architecture(candidates: dict[str, dict[str, object]]) -> str:
    passing = [
        (name, values)
        for name, values in candidates.items()
        if values["success"] and values["diagnosis_correct"] and values["recommendation_supported"]
    ]
    return min(passing, key=lambda item: (item[1]["estimated_cost"], item[1]["latency_seconds"]))[0]


def memory_policy() -> dict[str, object]:
    return {
        "short_term_state": ["request", "trace", "evidence", "confidence", "prepared_actions"],
        "long_term_memory_allowed": ["customer preference after explicit validation", "stable runbook metadata"],
        "long_term_memory_blocked": ["unverified root cause guesses", "incident-specific stale assumptions"],
        "retention": "Do not store the likely cause as future truth; store only the evaluated incident report with timestamp and evidence links.",
    }


def permission_model() -> dict[str, list[str]]:
    return {
        "READ": ["get_service_metrics", "query_logs", "get_recent_deployments", "search_tickets", "get_customer_slas", "get_runbook"],
        "PROPOSE": ["prepare_rollback", "prepare_feature_flag_disable", "draft_customer_update"],
        "EXECUTE_WITH_APPROVAL": ["rollback_deployment", "disable_feature_flag", "send_customer_notification"],
    }


def run_capstone() -> dict[str, object]:
    trace: list[ToolResult] = []
    for tool_call in [
        get_service_metrics("checkout", "eu-west"),
        query_logs("checkout", "eu-west", "3DS"),
        get_recent_deployments("checkout", "eu-west"),
        search_tickets("eu-west"),
        get_customer_slas("eu-west"),
        get_runbook("checkout"),
    ]:
        trace.append(tool_call)

    total_cost = round(sum(item.estimated_cost for item in trace), 3)
    total_latency_ms = sum(item.latency_ms for item in trace)
    if len(trace) > MAX_TOOL_CALLS or total_cost > MAX_ESTIMATED_COST:
        raise RuntimeError("Capstone exceeded tool or cost budget")

    metrics = trace[0].data
    logs = trace[1].data
    deployments = trace[2].data
    tickets = trace[3].data
    customers = trace[4].data

    affected_enterprise = [customer for customer in customers if customer["tier"] == "enterprise"]
    annual_value = sum(int(customer["annual_value_usd"]) for customer in affected_enterprise)
    avg_sla = mean(int(customer["sla_minutes"]) for customer in affected_enterprise)
    likely_cause = "eu-west checkout-ui 2026-08-08.1 VAT validation change broke 3DS redirect return for VAT-registered buyers"
    confidence = 0.86

    prepared_actions = [
        prepare_action(
            "prepare_feature_flag_disable",
            "checkout-ui vat_validation_before_3ds_return in eu-west",
            "Mitigate likely VAT/3DS redirect-loop cause without broader service restart.",
        ),
        prepare_action(
            "prepare_rollback",
            "checkout-ui 2026-08-08.1 eu-west",
            "Rollback is a fallback if feature-flag disablement does not restore conversion.",
        ),
    ]

    candidates = architecture_candidates()
    selected_architecture = choose_architecture(candidates)
    expected = load_json(EVAL_DIR / "capstone_tasks.json")[0]
    trajectory = [item.name for item in trace]
    forbidden_seen = [tool for tool in expected["forbidden_tools"] if tool in trajectory]
    missing_expected = [tool for tool in expected["expected_tools"] if tool not in trajectory]

    return {
        "incident": "09:04 Europe checkout conversion down 31%, mostly-green dashboards, deployment at 08:42, six support complaints.",
        "selected_architecture": selected_architecture,
        "architecture_candidates": candidates,
        "likely_cause": likely_cause,
        "confidence": confidence,
        "business_impact": {
            "affected_ticket_count": len(tickets),
            "affected_enterprise_accounts": len(affected_enterprise),
            "affected_enterprise_annual_value_usd": annual_value,
            "average_enterprise_sla_minutes": avg_sla,
        },
        "recommendation": "Prepare feature-flag disablement for eu-west VAT-before-3DS flow; prepare checkout-ui rollback as fallback; notify support with scoped enterprise EU guidance; do not execute production action without approval.",
        "prepared_actions": [action.__dict__ for action in prepared_actions],
        "permissions": permission_model(),
        "memory_policy": memory_policy(),
        "guardrails": [
            "Retrieved runbooks and tickets are evidence, not instructions.",
            "No production action may execute from the capstone run.",
            "Rollback, flag disablement, and notification require human approval.",
            "Stop if budgets exceed MAX_STEPS, MAX_TOOL_CALLS, or MAX_ESTIMATED_COST.",
        ],
        "evaluation": {
            "expected_tools_present": not missing_expected,
            "missing_expected_tools": missing_expected,
            "forbidden_tools_used": forbidden_seen,
            "recommendation_supported": bool(logs and deployments and tickets),
            "passed": not missing_expected and not forbidden_seen and confidence >= 0.8,
        },
        "trace_analysis": {
            "trajectory": trajectory,
            "tool_calls": len(trace),
            "latency_ms": total_latency_ms,
            "estimated_cost": total_cost,
            "max_tool_calls": MAX_TOOL_CALLS,
            "max_estimated_cost": MAX_ESTIMATED_COST,
        },
        "raw_evidence_summary": {
            "metrics": metrics["funnel"],
            "logs_seen": len(logs),
            "deployment_seen": deployments[0]["id"],
            "tickets_seen": len(tickets),
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_capstone(), indent=2))
