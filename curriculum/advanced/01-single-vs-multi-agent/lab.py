"""Deterministic multi-agent architecture comparison for Northstar incidents."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Architecture: name:str; topology:str; roles:tuple[str,...]; cost:float; latency_ms:int; accuracy:float; coordination:int
def choose(complexity:str)->Architecture:
 if complexity=='simple': return Architecture('single investigator','single',('investigator',),.012,2500,.91,0)
 if complexity=='cross-domain': return Architecture('supervisor team','supervisor-workers',('supervisor','observability','deployment','customer-impact','risk-reviewer'),.041,6100,.96,7)
 return Architecture('blackboard team','blackboard',('planner','specialists','critic'),.055,7600,.94,11)
def compare(complexity='cross-domain'):
 single=choose('simple'); team=choose(complexity)
 winner=team.name if team.accuracy-single.accuracy>=.03 else single.name
 return {'single':single,'team':team,'recommended':winner,'reason':'add agents only when measured specialization benefit exceeds coordination cost'}
PATTERNS={
 'supervisor-workers':'central coordinator delegates bounded specialist work; easy audit, central bottleneck.',
 'router-specialists':'deterministic/model router selects one specialist; efficient when task classes are clear.',
 'planner-executors':'planner makes DAG; executors perform constrained tasks; strong for dependencies.',
 'hierarchical':'manager/submanagers reduce top-level context; requires ownership and budget boundaries.',
 'peer-to-peer':'agents negotiate directly; resilient but harder to govern and terminate.',
 'blackboard':'specialists publish attributed facts to shared state; useful for evidence synthesis.',
 'generator-critic':'generator proposes, critic challenges; quality gain can be offset by cost/confirmation bias.',
 'sequential':'handoff pipeline; predictable but serial latency.',
 'parallel-swarm':'fan-out independent work; fast but needs aggregation, rate limits, and cancellation.'}
if __name__=='__main__': print(compare())
