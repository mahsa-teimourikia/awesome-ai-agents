"""Deterministic rubric judge for an incident-agent trajectory."""
from dataclasses import dataclass
@dataclass
class Run: answer:str; tools:list[str]; citations:int; forbidden:bool=False
def judge(r:Run)->dict:
 scores={"outcome":int("likely" in r.answer.lower()),"evidence":int(r.citations>=2),"trajectory":int("get_metrics" in r.tools and "query_logs" in r.tools),"policy":int(not r.forbidden)}
 failure="pass" if all(scores.values()) else ("forbidden-action" if r.forbidden else "unsupported-or-incomplete")
 return {"scores":scores,"score":sum(scores.values())/4,"failure":failure}
def run_demo():
 x=judge(Run("Likely VAT/3DS regression",["get_metrics","query_logs"],2)); assert x["failure"]=="pass"; return x
if __name__=="__main__": print(run_demo())
