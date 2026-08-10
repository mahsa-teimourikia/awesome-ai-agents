from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentops_lab.loop_yourself import get_runbook, get_service_status, search_incidents
from agentops_lab.workflow_or_agent import get_recent_deployments, query_region_logs


class IncidentState(TypedDict):
    request: str
    service: str | None
    evidence: list[dict]
    suspected_cause: str | None
    confidence: float
    attempts: int
    recommendation: str | None


@dataclass
class MemoryRecord:
    customer: str
    key: str
    value: str
    source: Literal["preference", "verified_fact", "unverified_fact"]
    active: bool = True


@dataclass
class MemoryStore:
    records: list[MemoryRecord] = field(default_factory=list)

    def add(self, customer: str, key: str, value: str, source: Literal["preference", "verified_fact", "unverified_fact"]) -> None:
        self.records.append(MemoryRecord(customer=customer, key=key, value=value, source=source))

    def search(self, customer: str) -> list[MemoryRecord]:
        return [record for record in self.records if record.customer == customer and record.active]

    def deactivate(self, customer: str, key: str) -> None:
        for record in self.records:
            if record.customer == customer and record.key == key:
                record.active = False


def new_state(request: str) -> IncidentState:
    return {
        "request": request,
        "service": None,
        "evidence": [],
        "suspected_cause": None,
        "confidence": 0.0,
        "attempts": 0,
        "recommendation": None,
    }


def triage(state: IncidentState) -> IncidentState:
    service = "checkout" if "checkout" in state["request"].lower() else "unknown"
    return {**state, "service": service, "attempts": state["attempts"] + 1}


def need_evidence(state: IncidentState) -> bool:
    return len(state["evidence"]) < 2


def collect_evidence(state: IncidentState, memory: MemoryStore | None = None, customer: str = "Acme") -> IncidentState:
    service = state["service"] or "checkout"
    evidence = list(state["evidence"])
    collected = {item["tool"] for item in evidence}

    if "memory" not in collected and memory:
        evidence.append({"tool": "memory", "result": [record.__dict__ for record in memory.search(customer)]})
    elif "get_service_status" not in collected:
        evidence.append({"tool": "get_service_status", "result": get_service_status(service)})
    elif "search_incidents" not in collected:
        evidence.append({"tool": "search_incidents", "result": search_incidents(f"active {service} payment failures")})
    elif "get_recent_deployments" not in collected:
        evidence.append({"tool": "get_recent_deployments", "result": get_recent_deployments(service, "eu-west")})
    elif "query_region_logs" not in collected:
        evidence.append({"tool": "query_region_logs", "result": query_region_logs(service, "eu-west", "ERROR 3DS VAT")})
    elif "get_runbook" not in collected:
        evidence.append({"tool": "get_runbook", "result": get_runbook(service)})

    return {**state, "evidence": evidence, "attempts": state["attempts"] + 1}


def analyze(state: IncidentState, trust_unverified_memory: bool = False) -> IncidentState:
    evidence_by_tool = {item["tool"]: item["result"] for item in state["evidence"]}
    suspected_cause = state["suspected_cause"]
    confidence = 0.15

    status = evidence_by_tool.get("get_service_status")
    if status and status.get("health") == "degraded":
        confidence += 0.2

    incidents = evidence_by_tool.get("search_incidents", {}).get("matches", [])
    if any(incident["status"] == "active" for incident in incidents):
        confidence += 0.25
        suspected_cause = "payment gateway timeout spike"

    deployments = evidence_by_tool.get("get_recent_deployments", {}).get("deployments", [])
    if any("3DS" in deployment["notes"] or "VAT" in deployment["notes"] for deployment in deployments):
        confidence += 0.2
        suspected_cause = "eu-west checkout UI validation or 3DS redirect change"

    logs = evidence_by_tool.get("query_region_logs", {}).get("matches", [])
    if any("3DS" in log["message"] for log in logs):
        confidence += 0.2
        suspected_cause = "eu-west 3DS callback rejection"

    memories = evidence_by_tool.get("memory", [])
    for record in memories:
        if record["source"] == "unverified_fact" and trust_unverified_memory:
            suspected_cause = record["value"]
            confidence += 0.15

    return {
        **state,
        "suspected_cause": suspected_cause,
        "confidence": min(confidence, 0.95),
        "attempts": state["attempts"] + 1,
    }


def decide_next_step(state: IncidentState) -> Literal["investigate", "finish"]:
    if state["confidence"] >= 0.75:
        return "finish"
    if state["attempts"] >= 10:
        return "finish"
    return "investigate"


def recommend(state: IncidentState) -> IncidentState:
    if state["confidence"] >= 0.75:
        recommendation = (
            f"Recommend acknowledging checkout impact, prioritizing SLA customers, and investigating {state['suspected_cause']}. "
            "Treat this as a suspected cause, not confirmed root cause, until engineering validates the evidence."
        )
    else:
        recommendation = (
            "Evidence is insufficient for a confident diagnosis. Escalate to checkout owners with the collected evidence and avoid guessing root cause."
        )
    return {**state, "recommendation": recommendation}


def run_state_graph(request: str, memory: MemoryStore | None = None, trust_unverified_memory: bool = False) -> tuple[IncidentState, list[str]]:
    state = new_state(request)
    path = ["START", "triage"]
    state = triage(state)

    if need_evidence(state):
        while True:
            path.append("collect_evidence")
            state = collect_evidence(state, memory=memory)
            path.append("analyze")
            state = analyze(state, trust_unverified_memory=trust_unverified_memory)
            decision = decide_next_step(state)
            path.append(f"decide:{decision}")
            if decision == "finish":
                break
    path.append("recommend")
    state = recommend(state)
    path.append("END")
    return state, path


def memory_bias_experiment() -> dict:
    memory = MemoryStore()
    memory.add("Acme", "preference", "Always prioritize fast resolution", "preference")
    baseline, baseline_path = run_state_graph("Acme European users report checkout failures.", memory=memory)

    memory.add("Acme", "fact", "Checkout problems are usually caused by Redis.", "unverified_fact")
    biased, biased_path = run_state_graph("Acme European users report checkout failures.", memory=memory, trust_unverified_memory=True)

    memory.deactivate("Acme", "fact")
    repaired, repaired_path = run_state_graph("Acme European users report checkout failures.", memory=memory, trust_unverified_memory=True)

    return {
        "baseline": {"state": baseline, "path": baseline_path},
        "biased": {"state": biased, "path": biased_path},
        "repaired": {"state": repaired, "path": repaired_path},
        "lesson": "Long-term memory should be scoped, validated, auditable, and reversible; unverified facts can bias new incident diagnosis.",
    }


if __name__ == "__main__":
    final_state, graph_path = run_state_graph("Acme European users report checkout failures.")
    print(graph_path)
    print(final_state["recommendation"])
    experiment = memory_bias_experiment()
    print(experiment["biased"]["state"]["suspected_cause"])
    print(experiment["repaired"]["state"]["suspected_cause"])
