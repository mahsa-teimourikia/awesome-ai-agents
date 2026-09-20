# Deep Dive: Observable Trajectory Analysis

## Outcome and path are independent criteria

An agent may reach the correct state through an unauthorized attempt; platform IAM may
contain the effect. Report both facts:

```text
authoritative outcome: correct
agent policy adherence: failed
platform containment: succeeded
compliant success: false
```

Do not fold them into an arbitrary weighted score. Cross-tenant access, unauthorized
mutation, approval bypass, and secret exposure are hard gates in the Northstar fixture.

## Evaluate observable events

The course records typed tool calls/results, proposals, evidence IDs, approvals,
execution receipts, state transitions, and final artifacts. It does not request or
depend on private chain-of-thought. Explicit plans can be evaluated when the product
deliberately exposes them as artifacts.

Tool behavior is specified as:

- required actions;
- allowed optional actions;
- forbidden actions;
- tool-call budgets; and
- partial-order constraints where order is meaningful.

This accepts valid alternative paths. Fewer calls are not automatically better: report
missing required, unnecessary, forbidden, and duplicate calls alongside outcome, cost,
and latency.

## Evidence-bound grounding

A trajectory is grounded only when the claims it relies on cite known evidence that is
authorized for the case, bound to the right tenant/source/version/digest, and supports
the claim. An agent-set `grounded: true` flag proves nothing.

Semantic judges can evaluate nuance after deterministic controls, but Course 11's
reliability rules still apply: version the evaluator, measure it against independent
human labels, preserve abstention/disagreement, and prevent it from overriding hard
facts. When evaluator logic changes, rerun old and new evaluators over frozen outputs
to separate measurement changes from agent changes.

## Operational trajectory

Record wall-clock time separately from model, tool, and queue work; parallel work can
lower latency while increasing total work. Include model/tool/evaluator cost, calls,
tokens, retries, handoffs, and duplicate work. The product chooses its quality-safety-
cost-latency frontier explicitly rather than hiding trade-offs in one score.
