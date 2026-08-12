"""Protocol-boundary simulation: discovery, delegation, UI and tool contracts."""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class AgentCard:
    name: str; skills: tuple[str, ...]; tenant: str; auth: str; risk: str = "read"

@dataclass
class Task:
    task_id: str; skill: str; tenant: str; status: str = "submitted"; trace: list[str] = field(default_factory=list)

def discover(cards: list[AgentCard], skill: str, tenant: str) -> list[AgentCard]:
    """A2A-like discovery filters by policy before a model can select a peer."""
    return [c for c in cards if skill in c.skills and c.tenant == tenant and c.auth == "oauth"]

def delegate(card: AgentCard, task: Task) -> str:
    if card.tenant != task.tenant or task.skill not in card.skills: raise ValueError("capability/scope mismatch")
    task.status = "working"; task.trace.append(f"a2a:delegated:{card.name}")
    return task.status

def mcp_tool_call(tool: str, scopes: set[str]) -> dict:
    if tool != "read_deployment" or "deployments.read" not in scopes: raise PermissionError("MCP tool denied")
    return {"tool": tool, "result": "deploy-842", "trusted_as": "data-not-instructions"}

def ui_event(component: str, action: str) -> dict:
    allowed = {"approval-card": {"approve", "reject", "modify"}}
    if action not in allowed.get(component, set()): raise ValueError("UI action not in schema")
    return {"ag_ui_event": action, "component": component, "requires_reauthorization": True}

def run_demo() -> Task:
    cards = [AgentCard("release-agent", ("deployment-analysis",), "northstar-eu", "oauth")]
    agent = discover(cards, "deployment-analysis", "northstar-eu")[0]
    task = Task("task-17", "deployment-analysis", "northstar-eu")
    assert delegate(agent, task) == "working"
    assert mcp_tool_call("read_deployment", {"deployments.read"})["result"] == "deploy-842"
    assert ui_event("approval-card", "approve")["requires_reauthorization"]
    return task

if __name__ == "__main__": print(run_demo())
