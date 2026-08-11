"""Deterministic agent-economics lab with explicit tokens, tool calls, retries, and latency."""
from dataclasses import dataclass, field

@dataclass
class Budget:
    tokens: int = 6_000; actions: int = 12; spend_cents: float = 8.0; latency_ms: int = 7_000

@dataclass
class Trace:
    tokens: int = 0; actions: int = 0; spend_cents: float = 0; latency_ms: int = 0; events: list[str] = field(default_factory=list)

def charge(trace: Trace, budget: Budget, label: str, tokens: int, actions: int, cents: float, latency: int) -> bool:
    proposed = (trace.tokens + tokens, trace.actions + actions, trace.spend_cents + cents, trace.latency_ms + latency)
    if proposed[0] > budget.tokens or proposed[1] > budget.actions or proposed[2] > budget.spend_cents or proposed[3] > budget.latency_ms:
        trace.events.append(f"stop:{label}:budget-exceeded")
        return False
    trace.tokens, trace.actions, trace.spend_cents, trace.latency_ms = proposed
    trace.events.append(f"run:{label}")
    return True

def investigate(cache_hit: bool, uncertain: bool, parallel_reads: bool = True) -> Trace:
    budget, trace = Budget(), Trace()
    if cache_hit:
        charge(trace, budget, "cache", 80, 0, .01, 30); return trace
    charge(trace, budget, "fast-classify", 350, 1, .08, 350)
    # Parallel reads reduce wall-clock latency, not total cost or authorization requirements.
    if parallel_reads:
        charge(trace, budget, "parallel-status-and-incidents", 0, 2, .12, 600)
    else:
        charge(trace, budget, "status", 0, 1, .06, 600); charge(trace, budget, "incidents", 0, 1, .06, 600)
    if uncertain:
        charge(trace, budget, "reasoning-synthesis", 2_400, 2, 1.45, 2_500)
    else:
        charge(trace, budget, "fast-synthesis", 700, 1, .18, 650)
    return trace

def run_demo() -> tuple[Trace, Trace]:
    cached = investigate(cache_hit=True, uncertain=False)
    complex_case = investigate(cache_hit=False, uncertain=True)
    assert cached.events == ["run:cache"]
    assert complex_case.latency_ms == 3_450 and complex_case.spend_cents == 1.65
    return cached, complex_case

if __name__ == "__main__":
    for trace in run_demo(): print(trace.events, trace.__dict__)
