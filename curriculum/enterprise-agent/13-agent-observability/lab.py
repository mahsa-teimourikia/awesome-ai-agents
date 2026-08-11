"""OpenTelemetry-shaped, credential-free trace for an incident agent trajectory."""
from dataclasses import dataclass, asdict
@dataclass
class Span: name:str; kind:str; latency_ms:int; tokens:int=0; cost_cents:float=0; error:str=""; attrs:dict=None
def incident_trace():
 return [Span("route","internal",12,attrs={"route":"single-agent","tenant":"acme"}),Span("model.triage","llm",540,620,.11,attrs={"prompt_version":"v3","context_items":3}),Span("tool.metrics","tool",180,attrs={"tool":"get_service_metrics"}),Span("tool.logs","tool",420,attrs={"tool":"query_logs"}),Span("policy.proposal","internal",15,attrs={"decision":"approval-required"})]
def summarize(spans): return {"latency_ms":sum(s.latency_ms for s in spans),"tokens":sum(s.tokens for s in spans),"cost_cents":round(sum(s.cost_cents for s in spans),2),"errors":[s.error for s in spans if s.error],"trajectory":[s.name for s in spans]}
def run_demo():
 s=incident_trace(); x=summarize(s); assert x["trajectory"][-1]=="policy.proposal" and x["cost_cents"]==.11; return x
if __name__=="__main__": print(run_demo())
