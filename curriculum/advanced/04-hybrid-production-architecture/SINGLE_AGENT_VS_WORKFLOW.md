# Deep Dive: Bounded Agent vs Governed Workflow

Choose a workflow when important state transitions are known or governable. Choose a bounded agent when the evidence-gathering path is genuinely ambiguous and model-driven adaptation earns its cost.

## Governed workflow

A workflow is not merely a linear list. It can include conditional branches, parallel work and joins, bounded retries and loops, durable waits, timeouts, cancellation, and compensation.

The password reset fixture demonstrates end-to-end authenticated subject binding, explicit identity verification, OTP expiry, attempt limits, persisted state, and a stable per-reset logical idempotency key. A retry of one reset preserves its ID; a later reset for the same user receives a new ID. A restart cannot erase failed attempts or extend expiry. The final write cannot run before the `PASSWORD_UPDATE_AUTHORIZED` state.

This improves inspectability and control; it does not make the system “100% reliable.” Dependencies, persistence, workers, networks, and operators still fail. Reliability comes from defined invariants, retries, recovery, and evidence—not from the workflow label.

## Bounded agent

The Northstar diagnostic request cannot know its evidence path in advance. A bounded agent may decide which read source to inspect next, but its contract still fixes:

- allowed read capabilities;
- required evidence;
- maximum model and tool calls;
- cost, deadline, and replan budgets;
- tenant and data scope;
- structured output and safe failure behavior.

It can propose “prepare a rollback,” but cannot execute rollback. If the evidence gap requires a different architecture, the agent emits an `ARCHITECTURE_ESCALATION_REQUEST`. Application policy—not the worker—decides whether a separately budgeted transition is allowed.

## Practical selection test

Ask two questions:

1. Can we govern the important transitions and failure branches explicitly?
2. Does dynamic evidence selection materially improve the outcome?

Use the smallest compliant option that passes those tests. Avoid replacing clear state with hidden conversational memory, but also avoid encoding an unbounded diagnostic world as a brittle maze of branches.
