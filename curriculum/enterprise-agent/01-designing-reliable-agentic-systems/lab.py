"""Credential-free architecture decision harness for reliable agentic systems."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Architecture(str, Enum):
    WORKFLOW = "deterministic_workflow"
    AGENT = "bounded_single_agent"
    TEAM = "specialist_team"


@dataclass(frozen=True)
class TaskProfile:
    name: str
    known_path: bool
    ambiguity: int
    risk: int
    data_sensitivity: int
    domains: int
    reversibility: int
    quality_target: float = 0.9


@dataclass
class Decision:
    architecture: Architecture
    controls: list[str]
    rationale: list[str]
    budgets: dict[str, int]
    approved: bool = False
    trace: list[str] = field(default_factory=list)


def select_architecture(task: TaskProfile) -> Decision:
    """Choose the least autonomous design that meets the task profile."""
    controls = ["tenant scope", "typed tool contracts", "trace IDs", "outcome + trajectory evaluation"]
    rationale: list[str] = []
    if task.known_path and task.ambiguity <= 2:
        architecture = Architecture.WORKFLOW
        rationale.append("The path is known: deterministic code is more auditable and predictable.")
    elif task.domains >= 3 and task.ambiguity >= 6:
        architecture = Architecture.TEAM
        rationale.append("Independent domains may benefit from bounded specialist work and evidence contracts.")
    else:
        architecture = Architecture.AGENT
        rationale.append("Evidence selection is dynamic, but one bounded investigator preserves a simple baseline.")

    if task.risk >= 6 or task.reversibility <= 3:
        controls += ["human approval for exact write action", "idempotency key", "rollback plan"]
        rationale.append("The action is high-impact or hard to reverse; policy and human approval own the commit.")
    if task.data_sensitivity >= 6:
        controls += ["minimized context packet", "redaction", "retention policy", "per-tenant memory namespace"]
        rationale.append("Sensitive context requires isolation, minimization, retention, and audit controls.")
    if architecture is Architecture.AGENT:
        controls += ["max steps", "max tool calls", "allowed-tool list", "abstain/escalate terminal state"]
    if architecture is Architecture.TEAM:
        controls += ["role ownership", "artifact contracts", "per-agent turn cap", "team message cap", "single-agent comparison"]
    return Decision(architecture, controls, rationale, {"max_steps": 6, "max_tool_calls": 8, "max_cost_cents": 25})


def execute_safely(task: TaskProfile, request_approval: bool = False) -> Decision:
    """Simulate a read-only investigation and approval-gated remediation proposal."""
    decision = select_architecture(task)
    decision.trace += [f"route:{decision.architecture.value}", "read:status", "read:deployment", "validate:evidence"]
    if task.risk >= 6:
        decision.trace += ["propose:rollback-eu-checkout", "pause:human-approval"]
        decision.approved = request_approval
        decision.trace.append("execute:idempotent-rollback" if request_approval else "terminal:proposal-only")
    else:
        decision.trace.append("terminal:recommendation")
    return decision


def evaluate_candidates(task: TaskProfile) -> list[dict[str, object]]:
    """Compare a simple baseline with more autonomous candidates before promotion."""
    candidates = [
        (Architecture.WORKFLOW, 0.72, 1.2, 2, 0.002),
        (Architecture.AGENT, 0.89, 4.3, 5, 0.012),
        (Architecture.TEAM, 0.92 if task.domains >= 3 else 0.87, 8.1, 11, 0.034),
    ]
    return [
        {"architecture": a.value, "quality": q, "latency_seconds": latency, "tool_calls": tools,
         "estimated_cost_usd": cost, "meets_quality_target": q >= task.quality_target}
        for a, q, latency, tools, cost in candidates
    ]


def run_demo() -> tuple[Decision, list[dict[str, object]]]:
    incident = TaskProfile("EU checkout conversion drop", False, 7, 8, 7, 3, 2, 0.9)
    decision = execute_safely(incident, request_approval=False)
    assert decision.architecture is Architecture.TEAM
    assert not decision.approved and decision.trace[-1] == "terminal:proposal-only"
    return decision, evaluate_candidates(incident)


if __name__ == "__main__":
    selected, comparison = run_demo()
    print(selected.architecture.value)
    print("\n".join(selected.trace))
    for candidate in comparison:
        print(candidate)
