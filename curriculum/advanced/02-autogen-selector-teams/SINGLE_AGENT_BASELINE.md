# Deep Dive: The Single-Agent Baseline

Before deploying a five-agent selector team, ask: does it beat a single generalist on the same governed task?

## Hold the workload constant

Both candidates answer the Northstar question, use the same five required evidence types, share the same no-production-execution boundary, and face the same success and grounding criteria. Changing the task, tools, evidence, or rubric between runs invalidates the comparison.

## Measure the complete coordination tax

| Dimension | Why it matters |
|---|---|
| Task success | did the system produce the required outcome? |
| Grounding | does the diagnosis cite validated evidence? |
| Required-evidence recall | how much of the evidence contract was satisfied? |
| Model calls | total model invocations |
| Selector calls | routing-only coordination work |
| Tokens | selector and worker tokens, separately and together |
| Total work | sum of all model-call elapsed work |
| Wall clock | user-perceived elapsed time; do not blindly sum concurrent calls |
| Cost | selector plus worker cost |
| Cost per successful compliant task | cost normalized by outcomes that pass all gates |
| Duplicate turns | work repeated on unchanged state |

“Token tax” is too narrow. A team can add latency, operational failure points, context exposure, and invalid-route risk even when token prices are low.

For deterministic fixtures, costs are fixed inputs. For live models, use estimated cost before execution for admission or reservation and actual reported token usage after execution for accounting under a versioned price schedule. Track selector and worker usage separately; otherwise routing cost disappears inside the team total.

## Interpret the deterministic fixture

The lab's selector team and single generalist both succeed. The team makes more calls and costs more because every worker turn also needs a selector turn. That result says the team has not yet earned its complexity on this fixture.

In a broader evaluation, the selector team may win if specialization materially improves evidence recall, grounding, safety, or success on cases a single agent misses. Use repeated cases and uncertainty estimates for real model comparisons; do not generalize from one deterministic example.

## Decision gate

Keep `SelectorGroupChat` only when it provides a measured structural benefit and remains within safety, cost, and latency limits. Otherwise keep the smaller architecture from Advanced Course 01.

> A selector team is warranted only if it beats the measured single-agent baseline on outcomes that matter, not because a multi-agent diagram looks more sophisticated.
