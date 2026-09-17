# Deep Dive — Bounded Model Cascades

A model cascade starts with an eligible lower-cost route, evaluates its artifact, and promotes only when a versioned automated signal rejects the result. Promotion is a quality decision—not error recovery.

## The gate is a measured classifier

The fixture validator evaluates four different properties:

1. schema validity;
2. semantic constraints;
3. grounding in required evidence IDs;
4. task correctness against labelled truth.

Valid JSON proves only syntax and required fields. It does not prove the right customer, priority, citation, decision, or business outcome.

The gate can be wrong:

- **false accept:** accepts an artifact that is task-incorrect;
- **false promotion:** rejects a task-correct artifact and triggers unnecessary work.

The lab includes both. Its schema-only baseline false-accepts a valid but incorrect priority. Its confidence threshold false-promotes a correct artifact. Threshold selection therefore belongs in evaluation, not intuition.

## Bounded flow

```text
eligible fast route
→ reserve budget and deadline
→ model call
→ common typed artifact
→ schema + semantics + grounding + task gate
   ├─ accept → complete
   └─ reject → choose unused, eligible, higher-measured-quality route
                ├─ budget/deadline/cancellation permit → promote
                └─ otherwise → typed terminal state
```

Before every next call, `run_routing_case()` checks:

- cancellation;
- total attempt count;
- remaining p95 deadline feasibility;
- conservative cumulative cost reserve;
- distinct provider budget;
- fallback budget when recovery, rather than promotion, is involved.

The fixture never performs a call and then retroactively claims cancellation or budget should have prevented it.

## When to use a cascade

A cascade is appropriate when the team can build and evaluate an automated gate on representative labelled data. The gate may be deterministic code, a calibrated classifier, an independent evaluator, a sandbox test, or a combination. It need not be perfect; its error rates must be explicit.

For an open-ended task without a trustworthy signal, do not pretend schema validity proves quality. Choose an eligible tier through workload evaluation, route to review, or build an evaluator before enabling promotion.

## What to measure

Compare the cascade and baseline on exactly the same labelled workload:

- successful compliant task rate;
- false-accept and false-promotion rates;
- promotion rate;
- average calls per request;
- average cost and cost per successful compliant task;
- p50/p95 end-to-end latency;
- deadline and budget termination rates.

Do not report only token savings or schema pass rate. A cheaper system that silently accepts wrong work is not an improvement.

## Calibration and drift

Choose thresholds on training/calibration data and report results on a held-out set. Segment by workload, tenant, language, risk class, and route. Recalibrate when models, provider revisions, adapters, prompts, validators, or traffic distributions change.

The deterministic replay in this course validates mechanics: selection, gates, promotion, attempts, budgets, and metrics. It does not validate live selector intelligence or model generalization.
