"""Deterministic coordination controls for evidence-backed multi-agent work."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Artifact:
    role: str
    claim: str
    source: str
    confidence: float


@dataclass
class TeamRun:
    required_roles: set[str] = field(default_factory=lambda: {"observability", "deployment", "impact"})
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    trace: list[str] = field(default_factory=list)
    budget: int = 6
    status: str = "routed"


def assign(task: str) -> list[str]:
    """Deterministic router: create a team only for cross-domain incidents."""
    return ["observability", "deployment", "impact"] if "conversion" in task.lower() else ["generalist"]


def publish(run: TeamRun, artifact: Artifact) -> None:
    """Blackboard accepts one scoped, attributable artifact per authorized role."""
    if artifact.role not in run.required_roles:
        raise ValueError("unauthorized role")
    if not artifact.source or not 0 <= artifact.confidence <= 1:
        raise ValueError("artifact requires source and calibrated confidence")
    run.artifacts[artifact.role] = artifact
    run.trace.append(f"publish:{artifact.role}:{artifact.source}")


def converge(run: TeamRun) -> str:
    """A critic blocks disagreement; no majority vote can erase missing evidence."""
    if run.budget <= 0:
        run.status = "escalated"; run.trace.append("budget-exhausted"); return run.status
    if set(run.artifacts) != run.required_roles:
        run.status = "waiting"; run.trace.append("missing-artifact"); return run.status
    claims = [a.claim for a in run.artifacts.values()]
    if len(set(claims)) != 1 or min(a.confidence for a in run.artifacts.values()) < .7:
        run.status = "conflict"; run.trace.append("critic:request-evidence-or-human"); return run.status
    run.status = "proposal"; run.trace.append("consensus:proposal-only"); return run.status


def run_demo() -> TeamRun:
    run = TeamRun()
    for role, source in [("observability", "metrics-42"), ("deployment", "deploy-842"), ("impact", "sla-eu")]:
        publish(run, Artifact(role, "rollback deploy-842", source, .88))
    assert converge(run) == "proposal"
    return run


if __name__ == "__main__": print(run_demo())
