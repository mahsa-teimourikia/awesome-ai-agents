# Advanced 10 — Long-Running & Asynchronous Agents

**Level:** Advanced · **Time:** 165 min · **Prerequisites:** Intermediate 10 Durable State, Advanced 04 Hybrid Production Architecture, Advanced 05 Incident Response

**Canonical notebook:** [`10_long_running_agents.ipynb`](10_long_running_agents.ipynb)

> A long-running agent is a durable, versioned state machine. A callback can wake it, but only current application policy and validated authority may let it act.

This course builds a credential-free refund workflow for Northstar Commerce. It can wait without holding a worker, survive process death, admit duplicate and untrusted events, coordinate competing workers, enforce a single-use approval, and reconcile an external effect whose result is unknown.

The lesson is framework-neutral. SQLite makes the transactional boundaries visible; it is not presented as the production scaling answer.

## Learning outcomes

By the end, you can:

- persist the minimal authoritative execution state and reopen it in another process;
- distinguish event delivery, state-transition, and side-effect idempotency;
- use legal transitions and compare-and-swap state versions to reject stale writers;
- validate an approval receipt against tenant, subject, proposal, digest, action, target, policy, role, expiry, and current preconditions;
- release a worker while waiting for a signed event or durable timer;
- claim work with an expiring lease before calling an external system;
- keep a logical operation ID stable while attempt IDs remain unique;
- treat a timeout-after-commit as `UNKNOWN_OUTCOME`, reconcile it, and only then retry or complete;
- persist retry, action, model-call, and cost budgets across restarts;
- pin workflow and state-schema versions rather than replaying incompatible code silently; and
- evaluate the governed runtime against a same-task naive baseline.

## Scenario and threat model

Northstar proposes a refund and waits for review. During that wait or later execution:

- the process may terminate and another process may resume the run;
- a queue may deliver one event more than once;
- an attacker may replay or alter a callback, or use another tenant's identifier;
- approval may race with expiry, cancellation, or manual takeover;
- two workers may receive the same ready item;
- a worker lease may expire;
- current policy, permissions, or the order version may change after approval;
- a provider may apply the refund and lose its response; and
- a deployment may contain workflow code that cannot safely replay old state.

The workflow therefore trusts neither prose nor mere delivery. An event is data to validate. A resume signal is not authorization. An approval receipt is not permanent permission. Model output may propose work, but application-owned policy admits events, validates authority, owns transitions, claims effects, and declares completion.

```text
model proposal
      │
      ▼
persist typed state ──► WAITING_APPROVAL ── release worker
                              │
              signed event + durable inbox/dedupe
                              │
              current policy + receipt validation
                              │
                              ▼
                      READY_TO_RESUME
                              │ lease + CAS
                              ▼
                         EXECUTING
                     ┌────────┴────────┐
                  result known      result unknown
                     │                  │
                     ▼                  ▼
                 VERIFYING         RECONCILING
                     │                  │ query by stable ID
                     └────────┬─────────┘
                              ▼
                         COMPLETED
```

## Course artifacts

| Artifact | Purpose |
| --- | --- |
| [`policy.py`](policy.py) | Strict contracts, state machine, approval/event validation, budgets, and stable operation identity |
| [`lab.py`](lab.py) | File-backed SQLite store, inbox/outbox, timers, leases, runtime, provider fixture, and evaluation |
| [`10_long_running_agents.ipynb`](10_long_running_agents.ipynb) | Canonical executable lesson |
| [`DURABLE_EXECUTION_STATE.md`](DURABLE_EXECUTION_STATE.md) | Checkpoints, versions, CAS, leases, histories, and framework mapping |
| [`EVENT_DRIVEN_RESUMPTION.md`](EVENT_DRIVEN_RESUMPTION.md) | Event admission, three idempotency boundaries, retries, and reconciliation |
| [`HUMAN_APPROVAL_TIMEOUTS.md`](HUMAN_APPROVAL_TIMEOUTS.md) | Typed authority, current-policy revalidation, durable timers, cancellation, and races |
| [`tests/test_long_running_agents.py`](../../../tests/test_long_running_agents.py) | Focused invariants and adversarial regression tests |

## Persist authority, not an entire prompt context

The durable record stores what the application needs to resume correctly:

- run, tenant, and subject identifiers;
- workflow version and state-schema version;
- current state, step, and monotonically increasing state version;
- typed proposal and immutable precondition snapshot;
- persistent budget counters;
- pending timer and validated approval identifiers;
- worker lease owner and expiry; and
- timestamps.

Supporting ledgers store the inbox, outbox, transition history, approval receipts, timers, logical operations, and execution attempts. Large retrieved documents, formatted prompts, credentials, and arbitrary process objects do not belong in authoritative workflow state. Store references plus provenance where possible; classify, encrypt, retain, and delete persisted content under organizational policy.

The lab uses a file-backed database. `happy_path_demo()` writes the waiting run with one `DurableStore` instance and reopens the same file through another runtime before processing approval. An in-memory database would not demonstrate process-death recovery.

## State machine and optimistic concurrency

`RunStatus` makes waiting, readiness, execution, reconciliation, verification, terminal outcomes, and manual control explicit. `ALLOWED_TRANSITIONS` rejects illegal jumps such as `WAITING_APPROVAL → COMPLETED`.

Every mutation uses a compare-and-swap update:

```sql
UPDATE runs
SET state_version = :next_version, record_json = :next_record
WHERE run_id = :run_id AND state_version = :expected_version
```

If another worker advanced the run first, zero rows change and the stale writer fails. The lab deliberately avoids `INSERT OR REPLACE`: replacing a row can erase concurrent state and bypass transition semantics.

## Events wake work; they do not authorize it

An `EventEnvelope` binds a unique event ID, source, tenant, run, event type, occurrence time, payload digest, and HMAC signature. The durable inbox enforces one record per event ID. Admission checks the signature, payload digest, run and tenant bindings, and terminal state before dispatch.

For approval, the event only names a separately stored `ApprovalReceipt`. The receipt must be valid and unused, then it is consumed in the same transaction that moves the run to `READY_TO_RESUME`. A string like `APPROVED`, a queue delivery, or a truthy `approved` field has no authority by itself.

Production event authentication may use asymmetric signatures, mTLS, workload identity, a verified webhook gateway, or a cloud event bus. The exact mechanism changes; the boundary does not.

## Typed, single-use approval

The receipt binds:

- approval, run, tenant, and subject;
- proposal ID and proposal digest;
- precondition digest;
- action and target;
- approver identity and role at issuance;
- policy version; and
- issue and expiry times.

Execution revalidates current policy, permitted action and target, current approver role, and the exact precondition digest. If the order version, evidence, deployment, account state, policy, permission, or role changed, the old approval cannot authorize the new world. A reviewer approves one known proposal under known conditions—not “whatever the agent eventually decides.”

## Waiting and timeout races

Waiting does not require a busy process. The workflow persists `WAITING_APPROVAL`, schedules a durable timer, commits, and releases the worker. Later, approval or timer delivery attempts one legal compare-and-swap transition. Whichever valid transition commits first wins; the loser is recorded as stale.

The fixture exposes three explicit timeout policies:

- `EXPIRE`: approval window ended;
- `ESCALATE`: transfer to a higher-level workflow or operator queue;
- `CANCEL`: stop the run.

Other domains may define `REMIND`, `REASSIGN`, or `REPLAN`; each still needs a persisted policy and an explicit state transition rather than ad hoc timer code.

Cancellation and manual takeover are durable terminal control states. Late callbacks cannot resurrect them. “Resume” never means “ignore cancellation.”

Long process-local sleeps are the anti-pattern because a process can disappear and consume worker capacity. Polling is not universally forbidden: managed orchestrators may use durable internal polling or event integrations. The design requirement is durable state and bounded resource use, not a slogan about one transport.

## Three idempotency boundaries

These controls solve different problems:

| Boundary | Stable identity | Prevents |
| --- | --- | --- |
| Event delivery | `event_id` | applying one delivery twice |
| State transition | `run_id + expected state_version` | stale or competing writers advancing the same state |
| External effect | `logical_operation_id + request_digest` | repeating a consequential provider operation |

The logical operation ID stays stable across retries. Each attempt receives a unique attempt ID and receipt. This supports audit and recovery without pretending the whole distributed workflow runs exactly once. Queues and workers are commonly at-least-once; safety comes from dedupe, conditional writes, stable operation identity, provider support, and reconciliation.

## Claim, call, record

The side-effect boundary is deliberately three-phase:

1. **Claim:** in a short transaction, validate current authority and budgets; create or claim the stable logical operation; create a unique attempt receipt; commit.
2. **Call:** outside the database transaction, invoke the provider with the stable operation ID.
3. **Record:** in a new transaction, record success, retryable failure, terminal failure, or unknown outcome and transition accordingly.

The database lock is never held during the external call. A worker must hold an unexpired lease before claiming. Another worker can reclaim after expiry using the latest state version.

## Unknown outcomes are first-class

A timeout does not prove failure. If the provider may have committed the refund before the response was lost, the run enters `RECONCILING`. A new execution claim returns `RECONCILE_REQUIRED`; it cannot blindly retry.

The reconciler queries the provider with the stable logical operation ID:

- confirmed effect → record provider receipt, enter `VERIFYING`;
- confirmed absence → enter `READY_TO_RESUME`, retaining the same logical operation ID for a new attempt;
- still unknown → remain paused or escalate under production policy.

Only an independently observed provider record with the matching request digest permits completion. This is stronger than treating a worker's return value as truth.

## Attempts, failures, and budgets

Workflow attempts and activity attempts are different. A process restart may replay orchestration logic without justifying another external call. Every external attempt consumes a persistent activity-attempt and cost budget. The first logical external action also consumes the action budget; retries do not create a new logical action.

The fixture classifies only `TRANSIENT_DEPENDENCY` as automatically retryable. Policy denial, authentication/permission failure, invalid/stale input, version conflicts, cancellation, precondition changes, and unknown outcomes are not generic retries. Unknown outcomes route to reconciliation.

For real providers, estimated cost supports admission or reservation; actual usage supports accounting. Conservative reserves are needed when actual cost can exceed an estimate. A production runtime should persist both and stop subsequent work when a hard budget is exhausted.

## Versioning and migration

The record carries both:

- `workflow_version`: control-flow semantics;
- `state_schema_version`: serialized state shape.

`WorkflowRuntime.load_compatible()` rejects unsupported versions. Production systems typically pin old executions to compatible code, apply a tested schema migration, or use a framework's workflow-versioning mechanism. Deploying new code and hoping old histories replay correctly is not a migration plan.

## Evaluation

`evaluate_same_cases()` applies one fixed four-case fixture to both systems:

1. duplicate approval delivery;
2. correctly signed but cross-tenant event;
3. cancellation followed by a late approval;
4. timeout after a provider commit.

The naive baseline trusts approval-shaped deliveries, has no durable dedupe, forgets cancellation, and retries an unknown result. The governed runtime uses the same inputs with its durable controls. Report safe-outcome rate, unsafe resumes, duplicate effects, provider calls, and reconciliations.

This deterministic fixture validates control mechanics, not live provider reliability, database scalability, or model intelligence. Production claims require representative failure injection, concurrency tests against the chosen database, provider idempotency/reconciliation verification, load and recovery tests, and monitored real-world outcomes.

## Framework mapping

The stable architecture is not tied to SQLite or a particular orchestrator:

| Course concept | Common production mapping |
| --- | --- |
| durable run and history | workflow execution/history or database-backed state machine |
| external event | authenticated signal/callback/task token |
| durable timer | orchestrator timer or scheduled message |
| activity attempt | worker/activity/task invocation |
| lease and CAS | orchestrator task ownership or database conditional update |
| operation ledger | idempotency/reconciliation record around the target system |

- [Temporal](https://docs.temporal.io/) documents durable workflow execution that resumes after failures. Its workflow history and activity semantics can implement the orchestration layer; application code still owns approval meaning, tenant policy, side-effect contracts, and completion evidence.
- [LangGraph persistence and interrupts](https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph) support checkpointed agent graphs and human pauses. A checkpointer persists graph state; it does not make arbitrary resume data trustworthy.
- [AWS Step Functions service integration patterns](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html) include request/response, job synchronization, and callback task tokens. IAM, token handling, business authorization, and effect reconciliation remain application concerns.
- [Azure Durable Functions](https://learn.microsoft.com/en-us/azure/durable-task/durable-functions/durable-functions-overview) manages checkpoints, retries, recovery, timers, and external events for stateful serverless workflows. Application policy still decides what an event is allowed to mean.

These platforms can replace parts of `DurableStore` and `WorkflowRuntime`. They do not replace domain authorization, current-policy checks, tenant isolation, artifact validation, or target-system reconciliation.

## Run locally

From the repository root:

```bash
uv sync --extra core --extra contributor
uv run --extra core python curriculum/advanced/10-long-running-asynchronous-agents/lab.py
uv run --extra core --extra contributor pytest -q tests/test_long_running_agents.py
uv run --extra core --extra contributor python scripts/execute-notebooks.py \
  curriculum/advanced/10-long-running-asynchronous-agents/10_long_running_agents.ipynb
```

The course requires no API key and makes no production provider calls.

## Exercises

1. Add an encrypted event payload reference and a retention job without placing credentials or full retrieved context in the run record.
2. Add a second effect that requires compensation. Define which failures retry, reconcile, compensate, or transfer to manual control.
3. Replace SQLite with PostgreSQL and test two real worker processes competing under conditional updates.
4. Add a schema-v2 migration and prove both a pinned v1 run and a migrated v2 run resume safely.
5. Model a provider that cannot query by idempotency key. Design an operator-assisted reconciliation path and explain why automatic retry is unsafe.

## Final principles

**A callback is not authority.**

**A timeout is not proof of failure.**

**A durable checkpoint is not a dump of all agent memory.**

**At-least-once delivery requires idempotency and reconciliation, not an “exactly once” claim.**

**The orchestrator resumes work; the application still owns authorization, policy, effects, and completion.**
