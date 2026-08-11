"""Credential-free registry and control-plane simulation for an agent ecosystem."""
from __future__ import annotations
from dataclasses import dataclass, field
@dataclass(frozen=True)
class AgentRecord: name:str; owner:str; capabilities:tuple[str,...]; risk:str; version:str; eval_passed:bool
@dataclass(frozen=True)
class ToolRecord: name:str; kind:str; owner:str; scopes:tuple[str,...]; trusted:bool; version:str
@dataclass
class ControlPlane:
    agents:dict[str,AgentRecord]=field(default_factory=dict); tools:dict[str,ToolRecord]=field(default_factory=dict); audit:list[str]=field(default_factory=list)
    def register_agent(self, agent:AgentRecord):
        if not agent.owner or not agent.eval_passed: raise ValueError("Agent requires an accountable owner and passing release evaluation")
        self.agents[agent.name]=agent; self.audit.append(f"agent-registered:{agent.name}:{agent.version}")
    def register_tool(self, tool:ToolRecord):
        if not tool.trusted: raise PermissionError("Unverified tool/MCP server cannot enter the enterprise registry")
        self.tools[tool.name]=tool; self.audit.append(f"tool-registered:{tool.name}:{tool.version}")
    def discover(self, agent:str, capability:str, tenant_scope:str)->list[str]:
        if agent not in self.agents: raise PermissionError("Unknown agent")
        allowed=[t.name for t in self.tools.values() if capability in t.scopes]
        self.audit.append(f"discover:{agent}:{capability}:{tenant_scope}:{','.join(allowed)}"); return allowed
    def execute(self, agent:str, tool:str, scope:str, cost_cents:int, approved:bool=False)->str:
        a,t=self.agents[agent],self.tools[tool]
        if scope not in t.scopes: raise PermissionError("Tool scope denied")
        if cost_cents>25: raise RuntimeError("FinOps budget exceeded")
        if a.risk=="high" and not approved: return "proposal-only: human approval required"
        self.audit.append(f"execute:{agent}:{tool}:{scope}:cost={cost_cents}"); return "executed-with-audit"
def run_demo()->ControlPlane:
    p=ControlPlane(); p.register_agent(AgentRecord("customer-impact","commerce-platform",("impact-analysis",),"high","1.2.0",True)); p.register_tool(ToolRecord("metrics-mcp","mcp","data-platform",("impact-analysis",),True,"4.1.0")); assert p.discover("customer-impact","impact-analysis","tenant:acme")==["metrics-mcp"]; assert p.execute("customer-impact","metrics-mcp","impact-analysis",8)=="proposal-only: human approval required"; return p
if __name__=="__main__": print("\n".join(run_demo().audit))
