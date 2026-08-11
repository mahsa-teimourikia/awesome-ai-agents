"""Deterministic layered guardrail reference implementation."""
from dataclasses import dataclass, field
@dataclass
class Request: tenant:str; text:str; tool:str; arguments:dict; risk:str="low"; actions:int=0; budget:int=3; audit:list[str]=field(default_factory=list)
ALLOWED={"read_status","search_runbook"}
def enforce(r:Request)->str:
 if "ignore previous" in r.text.lower(): r.audit.append("input:blocked"); return "blocked-input"
 if r.tool not in ALLOWED: r.audit.append("tool:deny"); return "blocked-tool"
 if r.arguments.get("tenant")!=r.tenant: r.audit.append("args:tenant-mismatch"); return "blocked-arguments"
 if r.actions>=r.budget: r.audit.append("budget:exhausted"); return "blocked-budget"
 if r.risk=="high": r.audit.append("action:approval-required"); return "approval-required"
 r.actions+=1; r.audit.append("output:audit-recorded"); return "allowed"
def run_demo():
 r=Request("acme","summarize status","read_status",{"tenant":"acme"}); assert enforce(r)=="allowed"; return r
if __name__=="__main__": print(run_demo())
