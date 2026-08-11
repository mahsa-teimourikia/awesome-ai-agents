"""Deterministic orchestration graph for an incident proposal."""
from dataclasses import dataclass,field
@dataclass
class Run: state:str="route"; trace:list[str]=field(default_factory=list); approved:bool=False
def step(r:Run,event:str=""):
 if r.state=="route": r.state="parallel-evidence"; r.trace.append("route:bounded-agent")
 elif r.state=="parallel-evidence": r.state="approval"; r.trace.append("join:evidence")
 elif r.state=="approval" and event=="approve": r.state="complete";r.approved=True;r.trace.append("approval:approved")
 elif r.state=="approval": r.trace.append("checkpoint:waiting-approval")
 return r.state
def run_demo():
 r=Run();step(r);step(r);assert step(r)=="approval";assert step(r,"approve")=="complete";return r
if __name__=="__main__":print(run_demo())
