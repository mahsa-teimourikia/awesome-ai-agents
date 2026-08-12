"""Credential-free delegated-capability authorization example."""
from dataclasses import dataclass, field
@dataclass
class Capability: subject:str; tenant:str; action:str; resource:str; expires:int; approved:bool=False; audit:list[str]=field(default_factory=list)
def authorize(c:Capability, now:int, requested_tenant:str, requested_action:str)->str:
 if now>=c.expires: c.audit.append("deny:expired"); return "deny"
 if requested_tenant!=c.tenant or requested_action!=c.action: c.audit.append("deny:scope"); return "deny"
 if requested_action in {"restart","refund"} and not c.approved: c.audit.append("approval-required"); return "approval-required"
 c.audit.append("allow:delegated-capability"); return "allow"
def run_demo():
 c=Capability("agent:incident-adviser","acme","read-status","checkout",expires=10); assert authorize(c,1,"acme","read-status")=="allow"; return c
if __name__=="__main__": print(run_demo())
