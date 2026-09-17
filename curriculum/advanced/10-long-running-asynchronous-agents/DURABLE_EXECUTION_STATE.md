# Deep dive — Durable execution state

Durability is the ability to reconstruct a valid control state after process or infrastructure failure. It is not the ability to pickle a Python process.

## What the checkpoint answers

A safe checkpoint lets a new worker answer:

- Which tenant and subject own this run?
- Which workflow and schema versions interpret it?
- Which state and step are authoritative?
- Which proposal and preconditions were reviewed?
- Which budgets have already been consumed?
- Is a timer, approval, lease, or logical operation pending?
- Which transitions and external attempts already occurred?

The course stores a compact `RunRecord` and separate append-oriented ledgers. This is easier to govern than one unstructured context blob and avoids coupling execution recovery to prompt formatting.

## Persisted records

| Record | Role | Mutation rule |
| --- | --- | --- |
| `runs` | current authoritative snapshot | compare-and-swap on `state_version` |
| `transition_history` | audit trail | append |
| `inbox` | received-event dedupe and disposition | unique `event_id` |
| `outbox` | transactional publication intent | append, later publish/mark |
| `approvals` | typed receipts and consumption | consume once conditionally |
| `timers` | due time and timeout policy | pending → fired once |
| `operations` | stable logical effect identity and outcome | conditional state changes |
| `execution_receipts` | unique attempt evidence | append/update one attempt |

`DurableStore` opens a connection per operation and uses short transactions. This lab choice exposes atomic boundaries. Production PostgreSQL, workflow histories, or cloud orchestration services use different primitives but should preserve the invariants.

## Legal transitions

State names encode operational meaning. `WAITING_APPROVAL`, `READY_TO_RESUME`, `EXECUTING`, `RECONCILING`, and `VERIFYING` each admit a different set of operations.

Completion is reachable only from `VERIFYING`. A receipt must exist and match the operation request before the state can become `COMPLETED`. Cancellation, expiry, rejection, escalation, failure, and manual control are terminal in this fixture. A late event is recorded as stale rather than silently ignored or allowed to reopen work.

## Compare-and-swap and leases

State-version CAS prevents lost updates. It does not by itself prevent two workers from both starting a side effect if they read before either writes. The runtime therefore requires an expiring lease and then atomically claims the logical operation before the external call.

Lease rules:

1. claimant presents the state version it observed;
2. run must be claimable;
3. another unexpired owner blocks the claim;
4. successful claim increments state version;
5. an expired lease may be replaced by a new owner using the latest version.

Do not hold a database transaction open over a network or model call. It increases contention and still cannot make the remote system part of the local transaction.

## Versioning

Workflow version and state-schema version solve different compatibility problems. A schema migration can preserve fields while control-flow meaning changes; a control-flow patch can remain compatible with the same serialized shape.

Safe deployment strategies include:

- pin old executions to old compatible workflow code;
- use explicit workflow-version branches supported by the orchestrator;
- migrate state with a tested, observable, reversible procedure; or
- transfer incompatible runs to manual control.

The lab rejects unsupported versions to make silent replay impossible.

## Replay determinism versus explicit state persistence

Durable runtimes do not all recover the same way. Replay-based engines such as Temporal reconstruct workflow progress from history and require deterministic workflow/orchestrator code. Current time, randomness, network calls, model calls, and consequential tool calls must go through framework-approved deterministic APIs or activities so replay does not invent new effects.

This SQLite lab instead loads an explicit state record and applies guarded transitions. It does not replay Python instructions. Even so, nondeterministic model/provider work remains outside the state transaction, and its inputs, attempts, and results need durable records. Neither model is “deserialize the LLM context and continue.”

When mapping the lesson to a framework, first determine whether it uses history replay, explicit snapshots, or both; then follow that framework's determinism and versioning rules.

## Data governance

Persist only what recovery and audit require. Treat workflow storage as sensitive operational data:

- segregate tenants and enforce access outside model control;
- encrypt in transit and at rest;
- avoid secrets and reusable credentials in checkpoints;
- store artifact references and integrity digests instead of unnecessary payload copies;
- define retention, deletion, legal hold, and backup-restoration procedures; and
- redact traces while preserving reason codes and identifiers needed for audit.

SQLite is a teaching adapter. Production concurrency, replication, backup, encryption, access control, and retention must be provided by the selected database or workflow service.

## Framework boundary

Temporal, LangGraph, Step Functions, and Durable Functions can provide history, checkpoints, timers, task delivery, and replay. Application code still owns:

- tenant and subject bindings;
- legal domain transitions;
- approval semantics and current-policy validation;
- consequential operation identity;
- provider-specific reconciliation; and
- evidence required for completion.

See the official [Temporal documentation](https://docs.temporal.io/), [LangGraph checkpointed human-review example](https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph), [Step Functions callback pattern](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html), and [Durable Functions overview](https://learn.microsoft.com/en-us/azure/durable-task/durable-functions/durable-functions-overview).
