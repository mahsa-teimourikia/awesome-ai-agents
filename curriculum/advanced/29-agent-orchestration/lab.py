"""Credential-free, deterministic orchestration controls for the Northstar case.

The model may synthesize a proposal, but it never advances durable state or grants
itself authority.  Those transitions belong to this application-owned controller.
"""
from dataclasses import dataclass, field


TERMINAL = {"complete", "cancelled", "escalated"}


@dataclass
class Run:
    run_id: str = "inc-eu-104"
    state: str = "route"
    trace: list[str] = field(default_factory=list)
    evidence: set[str] = field(default_factory=set)
    approved: bool = False
    attempts: int = 0
    budget_remaining: int = 4
    action_fingerprint: str = "proposal:rollback:checkout:deploy-842"
    processed_events: set[str] = field(default_factory=set)


def record(run: Run, item: str) -> None:
    run.trace.append(f"{run.state}:{item}")


def step(run: Run, event: str = "", event_id: str = "") -> str:
    """Advance one safe state transition; duplicate events have no side effect."""
    if event_id and event_id in run.processed_events:
        record(run, f"duplicate-event:{event_id}")
        return run.state
    if event_id:
        run.processed_events.add(event_id)
    if run.state in TERMINAL:
        record(run, "terminal-noop")
    elif event == "cancel":
        run.state = "cancelled"
        record(run, "cancelled")
    elif run.budget_remaining <= 0:
        run.state = "escalated"
        record(run, "budget-exhausted")
    elif run.state == "route":
        run.state = "parallel-evidence"
        run.budget_remaining -= 1
        record(run, "route:bounded-agent")
    elif run.state == "parallel-evidence":
        if event in {"metrics", "logs", "deployments"}:
            run.evidence.add(event)
            record(run, f"evidence:{event}")
        if {"metrics", "logs", "deployments"} <= run.evidence:
            run.state = "approval"
            record(run, "join:proposal-checkpointed")
    elif run.state == "approval" and event == "approve":
        run.approved = True
        run.state = "complete"
        record(run, f"approval:{run.action_fingerprint}")
    elif run.state == "approval" and event in {"reject", "expired"}:
        run.state = "escalated"
        record(run, f"approval-{event}")
    elif run.state == "approval":
        record(run, "checkpoint:waiting-approval")
    return run.state


def retry_read(run: Run, error: str) -> str:
    """Retry only bounded, idempotent reads; escalate all other failures."""
    run.attempts += 1
    if error == "timeout" and run.attempts <= 2:
        record(run, f"retry-read:{run.attempts}")
        return "retry"
    run.state = "escalated"
    record(run, f"escalate:{error}")
    return "escalate"


def run_demo() -> Run:
    run = Run()
    step(run)
    for source in ("metrics", "logs", "deployments"):
        step(run, source, f"evidence-{source}")
    assert run.state == "approval"
    step(run, "approve", "approval-1")
    step(run, "approve", "approval-1")
    assert run.state == "complete" and run.approved
    return run


if __name__ == "__main__":
    print(run_demo())
