# Deep Dive: Public Benchmark Evidence

## A score answers a bounded question

A benchmark is a versioned measurement contract: cases, environment, allowed
interaction, evaluator, and aggregation. A result is interpretable only inside that
contract. SWE-bench, WebArena, GAIA, τ-bench, BrowserGym, OSWorld, and AgentBench
exercise different capabilities and harnesses; there is no defensible conversion such
as “one WebArena point equals some fraction of a SWE-bench point.”

Use this taxonomy:

| Type | Primary question |
| --- | --- |
| Capability benchmark | Can the system demonstrate a particular capability? |
| System benchmark | Can the full agent complete representative tasks? |
| Safety benchmark | Does behavior remain inside explicit risk boundaries? |
| Regression suite | Did a candidate break previously established behavior? |
| Load/performance benchmark | Does the system meet throughput and latency objectives? |
| Production shadow evaluation | How does a candidate behave on real inputs without controlling effects? |

## Contamination and leakage

For a public case and a model with unknown training data, the accurate claim is
**contamination risk**, not proven memorization. Record observable exposure:

- `PUBLIC_SOURCE`
- `CONTROLLED_ENVIRONMENT`
- `PRIVATE_HELD_OUT`

Then record development leakage independently. A private case may be exposed through
prompt or rubric development, few-shot examples, fine-tuning, debugging, logs,
repeated CI runs, memory, or caches. Held-out status is a process property, not a
privacy label.

Maintain three practical partitions:

- development: visible and safe to tune against;
- validation: held out from routine prompt/model development;
- challenge: adversarial or rotated, with restricted exposure.

Reset agent memory and retrieval/model/tool caches unless persistent learning is what
the case explicitly tests. Bind RAG tests to corpus, index, and embedding versions.
For changing web/search data, choose record/replay, a controlled corpus, or a dated
live-eval mode and document the reproducibility trade-off.

## Public benchmark limits do not make them irrelevant

Public scores can screen models, reveal capability changes, support research, and
provide common comparisons. Enterprise readiness additionally requires your workload,
tools, identities, data, policy, failure modes, costs, and operational SLOs. Continue
monitoring after release because neither public nor private offline cases establish
future production performance.

See the primary project documentation linked from the [course README](README.md), and
pin the dataset, environment, evaluator, model, scaffold, and run configuration used
for every result.
