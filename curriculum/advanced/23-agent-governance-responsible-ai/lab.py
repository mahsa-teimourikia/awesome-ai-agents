"""Credential-free governance gate for a registered agent release."""
from dataclasses import dataclass, field
@dataclass
class AgentRecord: name:str; owner:str; risk:str; autonomy:str; tools:set[str]; data:str; approved:bool=False; audit:list[str]=field(default_factory=list)
def release_gate(a:AgentRecord)->str:
 missing=[]
 if not a.owner: missing.append("owner")
 if a.risk not in {"low","medium","high"}: missing.append("risk")
 if a.autonomy not in {"assist","propose","execute-with-approval"}: missing.append("autonomy")
 if a.risk=="high" and a.autonomy=="execute-with-approval" and "approval" not in a.tools: missing.append("approval-control")
 if not a.data: missing.append("data-classification")
 if missing: a.audit.append("blocked:"+",".join(missing)); return "blocked"
 a.approved=True; a.audit.append("approved:versioned-evidence"); return "approved"
def run_demo():
 a=AgentRecord("incident-advisor","ops-owner","high","execute-with-approval",{"read-logs","approval"},"internal"); assert release_gate(a)=="approved"; return a
if __name__=="__main__": print(run_demo())
