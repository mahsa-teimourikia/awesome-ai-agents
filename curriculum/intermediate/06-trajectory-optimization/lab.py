"""Compare reliable incident-investigation trajectories without live calls."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Step: name:str; latency_ms:int; cost:float; evidence:bool=False; safe:bool=True
@dataclass(frozen=True)
class Trace: name:str; steps:tuple[Step,...]; diagnosis_supported:bool
WASTEFUL=Trace('wasteful',(
 Step('plan',900,.004),Step('search_incidents',1400,.006,True),Step('reflect',800,.004),Step('get_status',1100,.005,True),Step('search_incidents',1400,.006,True),Step('get_runbook',900,.004),Step('query_logs',1700,.008,True),Step('reflect',800,.004),Step('query_logs',1700,.008,True)),True)
OPTIMIZED=Trace('optimized',(
 Step('get_status',1100,.005,True),Step('query_logs',1700,.008,True),Step('get_runbook',900,.004)),True)
def measure(trace:Trace)->dict[str,object]:
 names=[s.name for s in trace.steps]; evidence=sum(s.evidence for s in trace.steps)
 return {'name':trace.name,'success':trace.diagnosis_supported and evidence>=2 and all(s.safe for s in trace.steps),'steps':len(trace.steps),'tool_calls':sum(n not in {'plan','reflect'} for n in names),'duplicates':len(names)-len(set(names)),'latency_ms':sum(s.latency_ms for s in trace.steps),'cost':round(sum(s.cost for s in trace.steps),3),'evidence_signals':evidence}
def release_gate(trace:Trace)->dict[str,object]:
 m=measure(trace); return {'pass':bool(m['success']) and m['duplicates']<=1 and m['latency_ms']<=6000,'metrics':m}
def choose_parallel(operations:list[Step], independent:bool, rate_limit_allows:bool)->str:
 return 'parallel' if independent and rate_limit_allows else 'sequential'
if __name__=='__main__':
 for trace in (WASTEFUL,OPTIMIZED): print(release_gate(trace))
