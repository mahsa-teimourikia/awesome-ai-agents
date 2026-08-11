"""Deterministic skill discovery, progressive loading, and composition controls."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Skill:
    name: str; description: str; allowed_tools: frozenset[str]; references: tuple[str, ...]

LIBRARY = (
    Skill("incident-analysis", "Use for evidence-backed incident triage and proposals.", frozenset({"read_metrics", "read_deployment"}), ("runbook.md",)),
    Skill("customer-impact", "Use for SLA-safe customer-impact assessment.", frozenset({"read_customer_segments"}), ("sla-policy.md",)),
)

def discover(task: str, permitted_tools: set[str]) -> list[Skill]:
    """Metadata-only selection; full instructions load only after policy-filtered match."""
    words = set(task.lower().split())
    return [s for s in LIBRARY if words & set(s.description.lower().split()) and s.allowed_tools <= permitted_tools]

def activate(skill: Skill, permitted_tools: set[str]) -> dict:
    if not skill.allowed_tools <= permitted_tools: raise PermissionError("skill requests unavailable tool")
    return {"skill": skill.name, "load": ["SKILL.md", *skill.references], "tools": sorted(skill.allowed_tools)}

def compose(skills: list[Skill]) -> frozenset[str]:
    """Composition intersects policy outside skills; it never unions privileges by default."""
    return frozenset.intersection(*(s.allowed_tools for s in skills)) if skills else frozenset()

def run_demo() -> dict:
    skill = discover("incident triage with evidence", {"read_metrics", "read_deployment"})[0]
    active = activate(skill, {"read_metrics", "read_deployment"})
    assert active["skill"] == "incident-analysis"
    return active

if __name__ == "__main__": print(run_demo())
