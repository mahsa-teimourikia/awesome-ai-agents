"""Deterministic containment checks for agent-security attack surfaces."""
from dataclasses import dataclass, field
@dataclass
class Attempt: tenant:str; content:str; tool:str; target:str; trusted:bool=False; audit:list[str]=field(default_factory=list)
def contain(a:Attempt)->str:
 if "ignore previous" in a.content.lower(): a.audit.append("quarantine:injection"); return "blocked-context"
 if not a.trusted and a.tool in {"send_email","export_data","shell"}: a.audit.append("deny:untrusted-to-powerful-tool"); return "blocked-tool"
 if a.target!=a.tenant: a.audit.append("deny:cross-tenant"); return "blocked-tenant"
 if a.tool not in {"search_runbook","read_status"}: a.audit.append("deny:allowlist"); return "blocked-tool"
 a.audit.append("allow:read-only"); return "allowed"
def run_demo():
 a=Attempt("acme","status request","read_status","acme",True); assert contain(a)=="allowed"; return a
if __name__=="__main__": print(run_demo())
