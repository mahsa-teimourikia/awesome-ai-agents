"""Deterministic write → manage → read memory subsystem for the Agent Memory lesson."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

class MemoryType(str, Enum): WORKING="working"; EPISODIC="episodic"; SEMANTIC="semantic"; PROCEDURAL="procedural"

@dataclass
class Memory:
    id: str; type: MemoryType; namespace: tuple[str, str]; text: str; confidence: float; importance: int
    created_at: str; source: str; expires: bool=False; supersedes: str|None=None; tags: tuple[str,...]=()

@dataclass
class MemoryStore:
    records: dict[str, Memory]=field(default_factory=dict); audit: list[str]=field(default_factory=list)
    def write(self, item: Memory) -> None:
        if item.namespace[0] != "tenant": raise PermissionError("Memory must be tenant scoped")
        if "ignore policy" in item.text.casefold(): raise ValueError("Untrusted instruction cannot become memory")
        self.records[item.id]=item; self.audit.append(f"write:{item.id}")
    def retrieve(self, namespace: tuple[str,str], query_tags: set[str], limit: int=5) -> list[Memory]:
        candidates=[m for m in self.records.values() if m.namespace==namespace and not m.expires and query_tags.intersection(m.tags)]
        ranked=sorted(candidates,key=lambda m:(m.importance,m.confidence,m.created_at),reverse=True)[:limit]
        self.audit.append("read:"+",".join(m.id for m in ranked)); return ranked
    def forget(self, memory_id: str, reason: str) -> None:
        self.records[memory_id].expires=True; self.audit.append(f"forget:{memory_id}:{reason}")
    def consolidate(self, old_id: str, new: Memory) -> None:
        self.forget(old_id, "superseded by verified fact"); new.supersedes=old_id; self.write(new)

def now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def seed_store() -> MemoryStore:
    s=MemoryStore(); ns=("tenant","acme")
    for m in [
      Memory("work-1",MemoryType.WORKING,ns,"Current task: investigate EU payment errors; no remediation approval.",1,10,now(),"run-state",tags=("payments","eu","current")),
      Memory("episode-1",MemoryType.EPISODIC,ns,"On 2026-07-01, region mismatch was resolved by verifying provider configuration.",.8,7,now(),"incident-418",tags=("payments","eu","incident")),
      Memory("fact-1",MemoryType.SEMANTIC,ns,"Acme premium SLA requires escalation within 15 minutes after confirmation.",.95,9,now(),"contract",tags=("sla","payments")),
      Memory("procedure-1",MemoryType.PROCEDURAL,ns,"Collect evidence, verify config, propose only; require commander approval for rollback.",.98,9,now(),"policy",tags=("payments","procedure")),
      Memory("wrong-old",MemoryType.SEMANTIC,ns,"Checkout problems are always Redis failures.",.2,2,now(),"unverified-chat",tags=("payments","eu")),
    ]: s.write(m)
    return s
def run_demo() -> MemoryStore:
    s=seed_store(); ns=("tenant","acme")
    before=s.retrieve(ns,{"payments","eu"}, limit=5); assert "wrong-old" in [m.id for m in before]
    s.consolidate("wrong-old",Memory("fact-2",MemoryType.SEMANTIC,ns,"EU payment incidents require evidence from provider errors and region configuration; do not assume one cause.",.95,8,now(),"postmortem",tags=("payments","eu")))
    after=s.retrieve(ns,{"payments","eu"}, limit=5); assert "wrong-old" not in [m.id for m in after]
    return s
if __name__=="__main__":
 s=run_demo(); print("\n".join(s.audit))
