"""Credential-free event-driven proactive agent with consent and notification controls."""
from dataclasses import dataclass, field
@dataclass
class Goal: tenant:str; metric:str; threshold:float; notify:bool; active:bool=True
@dataclass
class Worker: goal:Goal; seen:set[str]=field(default_factory=set); events:list[str]=field(default_factory=list)
def handle(w:Worker, event_id:str, conversion:float, hour:int)->str:
 if not w.goal.active or event_id in w.seen: return "ignore"
 w.seen.add(event_id)
 if conversion>=w.goal.threshold: return "no-action"
 w.events.append("evidence:conversion-below-threshold")
 if not w.goal.notify or hour<8 or hour>18: return "queue-for-review"
 w.events.append("notify:ops-oncall")
 return "notified"
def run_demo():
 w=Worker(Goal("acme","eu_conversion",.85,True)); assert handle(w,"evt-1",.69,10)=="notified"; assert handle(w,"evt-1",.69,10)=="ignore"; return w
if __name__=="__main__": print(run_demo().events)
