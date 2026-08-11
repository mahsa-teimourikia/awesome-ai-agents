"""Deterministic design comparison for Northstar multi-agent architectures."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Architecture:
    name: str; topology: str; roles: tuple[str, ...]
    cost: float; latency_ms: int; accuracy: float; coordination: int


@dataclass(frozen=True)
class Artifact:
    owner: str; claim: str; evidence_id: str; tenant: str; confidence: float


@dataclass
class Board:
    tenant: str = "northstar-eu"
    artifacts: list[Artifact] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)

    def publish(self, item: Artifact) -> None:
        if item.tenant != self.tenant: raise ValueError("cross-tenant artifact")
        if not item.evidence_id or not 0 <= item.confidence <= 1: raise ValueError("invalid artifact")
        self.artifacts.append(item); self.trace.append(f"publish:{item.owner}:{item.evidence_id}")


def choose(complexity: str) -> Architecture:
    if complexity == "simple":
        return Architecture("single investigator", "single", ("investigator",), .012, 2500, .91, 0)
    if complexity == "cross-domain":
        return Architecture("supervisor team", "supervisor-workers", ("supervisor", "observability", "deployment", "customer-impact", "risk-reviewer"), .041, 6100, .96, 7)
    return Architecture("blackboard team", "blackboard", ("planner", "specialists", "critic"), .055, 7600, .94, 11)


def allocate(task: str) -> tuple[str, ...]:
    """Form the smallest team; simple work remains a generalist workflow."""
    return ("observability", "deployment", "customer-impact") if "conversion" in task.lower() else ("investigator",)


def critic(board: Board) -> str:
    """A critic requires independently attributable, agreeing evidence—not majority prose."""
    roles = {a.owner for a in board.artifacts}
    if roles != {"observability", "deployment", "customer-impact"}:
        return "escalate:missing-specialist"
    if min(a.confidence for a in board.artifacts) < .7:
        return "escalate:low-confidence"
    if len({a.claim for a in board.artifacts}) != 1:
        return "escalate:conflicting-evidence"
    return "proposal:source-supported"


def compare(complexity: str = "cross-domain") -> dict:
    single = choose("simple"); team = choose(complexity)
    winner = team.name if team.accuracy - single.accuracy >= .03 else single.name
    return {"single": single, "team": team, "recommended": winner,
            "reason": "add agents only when measured specialization benefit exceeds coordination cost"}


PATTERNS = {
 "supervisor-workers":"Central owner delegates bounded specialist work; audit-friendly but can bottleneck.",
 "router-specialists":"Classify and dispatch clear domains; measure misroutes and constrain fan-out.",
 "planner-executors":"Validated DAG plan with constrained executors; version plans and bound replans.",
 "manager-subagents":"Layered ownership reduces context; cap delegation depth and retain source artifacts.",
 "hierarchical":"Nested teams for decomposable programs; avoid summary loss and authority expansion.",
 "peer-to-peer":"Authenticated peer negotiation; needs TTL, quorum, ownership, and termination protocol.",
 "blackboard":"Versioned/provenance-tagged shared artifacts; ACLs and conflict policy are essential.",
 "debate":"Bounded counterarguments; only useful with diverse evidence and a verifier.",
 "generator-critic":"Proposal challenged against a rubric; critic cannot authorize action.",
 "sequential":"Validated deterministic handoffs; predictable but serially slow.",
 "parallel-swarm":"Bounded fan-out/fan-in independent work; needs cancellation and aggregation policy.",
}


if __name__ == "__main__":
    board = Board()
    for role, evidence in [("observability", "metrics-42"), ("deployment", "deploy-842"), ("customer-impact", "sla-eu")]:
        board.publish(Artifact(role, "rollback deploy-842", evidence, "northstar-eu", .88))
    assert critic(board) == "proposal:source-supported"
    print(compare())
