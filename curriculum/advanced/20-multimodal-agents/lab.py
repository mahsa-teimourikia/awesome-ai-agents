"""Credential-free multimodal evidence router; it processes metadata only."""
from dataclasses import dataclass, field
@dataclass(frozen=True)
class Evidence: modality:str; source_id:str; timestamp:str; trusted:bool; tenant:str; finding:str
@dataclass
class Case: evidence:list[Evidence]=field(default_factory=list); trace:list[str]=field(default_factory=list)
def run_demo():
 c=Case([Evidence("image","camera:12","09:04",True,"acme","conveyor stopped"),Evidence("audio","alarm:7","09:04",True,"acme","jam alarm"),Evidence("document","manual:conveyor","09:00",True,"acme","reset requires technician"),Evidence("sensor","rpm:12","09:04",True,"acme","RPM=0")]); c.trace=["see:image+document+ui", "hear:alarm", "read:sensor", "align:tenant+timestamp+provenance", "plan:technician-escalation", "act:create-read-only-incident"]; assert all(x.trusted and x.tenant=="acme" for x in c.evidence); return c
if __name__=="__main__": print("\n".join(run_demo().trace))
