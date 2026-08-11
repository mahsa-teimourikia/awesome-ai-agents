"""Deterministic evidence-first Agentic RAG harness for the learning module."""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Evidence:
    id:str; source:str; text:str; topics:tuple[str,...]; trust:float; tenant:str="acme"
@dataclass
class Run:
    question:str; plan:list[str]=field(default_factory=list); evidence:list[Evidence]=field(default_factory=list); trace:list[str]=field(default_factory=list); citations:list[str]=field(default_factory=list)

CORPUS=[
 Evidence("paper","Adaptive-RAG paper","Routes questions among no retrieval, one-step retrieval, and iterative retrieval using question complexity.",("adaptive","routing"),.96),
 Evidence("runbook","Checkout runbook","For EU payment errors, collect provider error IDs and compare region configuration before proposing rollback.",("payments","eu","procedure"),.93),
 Evidence("graph","Service graph","checkout-api depends on payment-gateway; payment-gateway uses EU provider configuration.",("payments","dependency","graph"),.9),
 Evidence("sql","Incident table","Incident 418 recorded EU payment authorization failures after a configuration rollout.",("payments","eu","incident"),.91),
 Evidence("noise","Old catalog note","Catalog cache latency was investigated last quarter.",("catalog",),.5),
]
def plan_query(question:str)->list[str]:
    return ["classify retrieval route","retrieve operational evidence","follow dependency edge","evaluate coverage","synthesize cited answer","verify citations"]
def search(query:str, tags:set[str])->list[Evidence]:
    return [e for e in CORPUS if tags.intersection(e.topics)]
def run_agentic_rag(question="Why did EU checkout payments fail and what should we do?")->Run:
    r=Run(question); r.plan=plan_query(question); r.trace.append("route: complex operational question → iterative multi-hop retrieval")
    first=search(question,{"payments","eu"}); r.evidence.extend(first); r.trace.append("search: operational runbook + incident record")
    if any("payment-gateway" in e.text for e in first) is False:
        r.evidence.extend(search(question,{"dependency","graph"})); r.trace.append("multi-hop: follow checkout → payment-gateway dependency")
    else: r.evidence.extend(search(question,{"dependency","graph"})); r.trace.append("multi-hop: graph lookup")
    r.evidence=[e for e in r.evidence if e.trust>=.8]
    r.citations=[e.id for e in r.evidence]
    r.trace.append("evidence gate: trusted sources cover incident, procedure, and dependency")
    r.trace.append("grounded action: propose validation; do not execute rollback")
    return r
def answer(run:Run)->str:
    assert {"runbook","sql","graph"}.issubset(run.citations)
    return "EU payment authorization failures followed a configuration rollout. Verify EU provider configuration and collect provider error IDs; propose, but do not execute, rollback without approval. Citations: " + ", ".join(run.citations)
if __name__=="__main__":
 r=run_agentic_rag(); print("\n".join(r.trace)); print(answer(r))
