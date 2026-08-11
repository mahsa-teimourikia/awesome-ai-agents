"""A dependency-free, LangGraph-shaped incident investigation lab.

The lesson deliberately keeps model and infrastructure calls deterministic so
learners can inspect state transitions, checkpoints, approval pauses, and
memory policy without an API key.  Port the same node contracts to a real
``StateGraph`` after understanding the execution trace.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Literal


Evidence = dict[str, object]
Event = dict[str, object]


@dataclass
class IncidentState:
    """Thread-scoped state: only facts needed for this investigation belong here."""

    thread_id: str
    request: str
    service: str = "checkout"
    evidence: list[Evidence] = field(default_factory=list)
    hypothesis: str | None = None
    confidence: float = 0.0
    attempts: int = 0
    recommendation: str | None = None
    pending_approval: bool = False
    approved: bool | None = None
    status: Literal["running", "paused", "complete", "failed"] = "running"
    events: list[Event] = field(default_factory=list)


class Checkpointer:
    """Tiny in-memory stand-in for a LangGraph checkpointer.

    A production checkpointer must be durable, access-controlled, encrypted as
    appropriate, and retained only as long as the product policy permits.
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, list[dict[str, object]]] = {}

    def save(self, state: IncidentState, node: str) -> None:
        self._snapshots.setdefault(state.thread_id, []).append(
            {"node": node, "state": asdict(state)}
        )

    def latest(self, thread_id: str) -> IncidentState:
        snapshot = self._snapshots[thread_id][-1]["state"]
        return IncidentState(**snapshot)  # type: ignore[arg-type]

    def history(self, thread_id: str) -> list[str]:
        return [str(item["node"]) for item in self._snapshots.get(thread_id, [])]


class MemoryStore:
    """Long-term, cross-thread memory with explicit namespace and verification.

    This intentionally refuses unverified diagnostic claims. Preferences can be
    useful long-term memory; an old hunch about Redis is not reliable evidence.
    """

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], list[dict[str, object]]] = {}

    def write(self, namespace: tuple[str, str], item: dict[str, object]) -> None:
        self._items.setdefault(namespace, []).append(item)

    def read_verified(self, namespace: tuple[str, str]) -> list[dict[str, object]]:
        return [item for item in self._items.get(namespace, []) if item.get("verified")]


def service_health() -> Evidence:
    return {"source": "health", "fact": "checkout API is healthy", "verified": True}


def european_logs() -> Evidence:
    return {
        "source": "logs",
        "fact": "EU payment-token validation errors rose after deploy-1842",
        "verified": True,
    }


def deployment_history() -> Evidence:
    return {
        "source": "deployments",
        "fact": "deploy-1842 enabled strict token validation at 08:42 UTC",
        "verified": True,
    }


def add_event(state: IncidentState, node: str, message: str) -> None:
    state.events.append({"node": node, "message": message})


def triage(state: IncidentState, store: MemoryStore) -> None:
    preferences = store.read_verified(("customer", "acme"))
    add_event(state, "triage", f"Classified request for {state.service}; loaded {len(preferences)} verified preference(s).")


def collect_evidence(state: IncidentState) -> None:
    catalog = [service_health, european_logs, deployment_history]
    if state.attempts >= len(catalog):
        return
    item = catalog[state.attempts]()
    state.evidence.append(item)
    state.attempts += 1
    add_event(state, "collect_evidence", str(item["fact"]))


def analyze(state: IncidentState) -> None:
    facts = " ".join(str(item["fact"]) for item in state.evidence)
    sources = {str(item["source"]) for item in state.evidence}
    if "token validation" in facts and {"logs", "deployments"}.issubset(sources):
        state.hypothesis = "The EU checkout regression is likely caused by strict token validation in deploy-1842."
        state.confidence = 0.88
    else:
        state.hypothesis = "Evidence is incomplete; collect a distinct signal before naming a cause."
        state.confidence = min(0.25 * len(state.evidence), 0.6)
    add_event(state, "analyze", f"confidence={state.confidence:.2f}; {state.hypothesis}")


def route_after_analysis(state: IncidentState) -> Literal["collect_evidence", "recommend"]:
    """A conditional edge with an explicit attempt cap prevents runaway loops."""

    return "recommend" if state.confidence >= 0.8 or state.attempts >= 3 else "collect_evidence"


def recommend(state: IncidentState) -> None:
    state.recommendation = (
        "Prepare a rollback of deploy-1842 and notify the EU support lead; "
        "do not execute either action until an incident commander approves."
    )
    state.pending_approval = True
    state.status = "paused"
    add_event(state, "recommend", state.recommendation)


def resume_approval(state: IncidentState, approved: bool) -> None:
    if not state.pending_approval:
        raise ValueError("No approval interrupt is pending for this thread.")
    state.approved = approved
    state.pending_approval = False
    state.status = "complete"
    outcome = "approved for an external operator" if approved else "rejected; no production action is taken"
    add_event(state, "approval", outcome)


def run_investigation(
    request: str,
    checkpointer: Checkpointer,
    store: MemoryStore,
    thread_id: str = "incident-eu-1842",
    fail_after: str | None = None,
) -> IncidentState:
    """Execute nodes and checkpoint after every durable boundary.

    ``fail_after`` simulates a process crash *after* a checkpoint; resume with
    :func:`resume_investigation` and no completed tool work is repeated.
    """

    state = IncidentState(thread_id=thread_id, request=request)
    triage(state, store)
    checkpointer.save(state, "triage")
    if fail_after == "triage":
        raise RuntimeError("simulated worker loss after triage checkpoint")

    while route_after_analysis(state) != "recommend":
        collect_evidence(state)
        checkpointer.save(state, "collect_evidence")
        if fail_after == "collect_evidence":
            raise RuntimeError("simulated worker loss after evidence checkpoint")
        analyze(state)
        checkpointer.save(state, "analyze")

    # Ensure final analysis is done if route was prematurely recommendable.
    if not state.evidence or state.events[-1]["node"] != "analyze":
        analyze(state)
        checkpointer.save(state, "analyze")
    recommend(state)
    checkpointer.save(state, "interrupt:approval")
    return state


def resume_investigation(checkpointer: Checkpointer, thread_id: str) -> IncidentState:
    """Resume from the last durable snapshot until the approval interrupt."""

    state = checkpointer.latest(thread_id)
    while state.status == "running" and route_after_analysis(state) != "recommend":
        collect_evidence(state)
        checkpointer.save(state, "collect_evidence")
        analyze(state)
        checkpointer.save(state, "analyze")
    if state.status == "running":
        recommend(state)
        checkpointer.save(state, "interrupt:approval")
    return state


def stream(state: IncidentState) -> list[Event]:
    """Expose simple node-level telemetry akin to streamed state updates."""

    return list(state.events)


def demo() -> None:
    store, checkpointer = MemoryStore(), Checkpointer()
    store.write(("customer", "acme"), {"kind": "preference", "value": "prioritize clear impact updates", "verified": True})
    # This must not be returned by read_verified and must never steer diagnosis.
    store.write(("customer", "acme"), {"kind": "diagnostic_hunch", "value": "checkout is usually Redis", "verified": False})

    state = run_investigation("Why are European customers failing checkout?", checkpointer, store)
    print("nodes:", checkpointer.history(state.thread_id))
    print("paused:", state.pending_approval, "hypothesis:", state.hypothesis)
    resume_approval(state, approved=False)
    checkpointer.save(state, "end")
    print("final status:", state.status, "approved:", state.approved)


if __name__ == "__main__":
    demo()
