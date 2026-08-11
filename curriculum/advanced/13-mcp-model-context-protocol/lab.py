"""Credential-free MCP boundary simulator for Northstar deployment analysis."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Capability:
    name: str; kind: str; scopes: frozenset[str]; side_effect: bool = False

CATALOG = (
    Capability("deployment://842", "resource", frozenset({"deployments.read"})),
    Capability("investigate-release", "prompt", frozenset({"incidents.read"})),
    Capability("get_deployment", "tool", frozenset({"deployments.read"})),
    Capability("rollback_deployment", "tool", frozenset({"deployments.write"}), True),
)

def negotiate(scopes: set[str]) -> list[Capability]:
    """Authorization-aware capability negotiation: least privilege changes the catalogue."""
    return [c for c in CATALOG if c.scopes <= scopes]

def invoke(name: str, args: dict, scopes: set[str], approved: bool = False) -> dict:
    cap = next((c for c in CATALOG if c.name == name and c.kind == "tool"), None)
    if not cap or not cap.scopes <= scopes: raise PermissionError("tool unavailable for delegated scope")
    if cap.side_effect and not approved: raise PermissionError("side effect requires human-approved action fingerprint")
    if name == "get_deployment":
        if args != {"deployment_id": "842"}: raise ValueError("strict tool schema rejected arguments")
        return {"deployment_id": "842", "version": "2026.08.10", "trusted_as": "untrusted-data"}
    return {"status": "proposal-submitted", "idempotency_key": args.get("idempotency_key")}

def run_demo() -> list[Capability]:
    visible = negotiate({"deployments.read", "incidents.read"})
    assert {c.name for c in visible} == {"deployment://842", "investigate-release", "get_deployment"}
    assert invoke("get_deployment", {"deployment_id": "842"}, {"deployments.read"})["deployment_id"] == "842"
    return visible

if __name__ == "__main__": print(run_demo())
