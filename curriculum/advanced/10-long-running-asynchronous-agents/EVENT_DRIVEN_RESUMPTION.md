# Deep dive — Events, idempotency, and reconciliation

An event says that something was delivered. It does not prove the payload is authentic, current, authorized, unique, or still relevant.

## Admission before dispatch

The fixture verifies, in order:

1. the run exists and its workflow/state versions are supported;
2. the event ID has not already reached the durable inbox;
3. the payload matches its digest;
4. the envelope signature is valid;
5. tenant and run bindings match authoritative state;
6. the run is not terminal; and
7. the event type is legal for the current state.

Accepted, rejected, duplicate, and stale deliveries all produce explicit dispositions. A production gateway should also enforce source identity, allowed event types, timestamp/replay windows, key rotation, and payload-size limits.

## Three independent identities

`event_id` deduplicates message delivery. `state_version` serializes state transitions. `logical_operation_id` identifies a consequential external effect. Reusing one of these for all three collapses different failure domains.

The logical operation ID is derived from trusted tenant, run, proposal, action, and target identity. Its request digest binds the effect parameters. Retries keep both stable while generating a new attempt ID:

```text
operation:abc...             stable logical effect
├── attempt:operation:abc:1  timed out after possible commit
├── reconcile:operation:abc  confirmed no effect
└── attempt:operation:abc:2  safe retry
```

## At-least-once without an exactly-once promise

No local database transaction can atomically commit both its row update and an arbitrary remote API call. Failure can occur after either side commits.

The course therefore uses:

- durable inbox dedupe for repeated events;
- CAS and legal transitions for repeated or competing state changes;
- short atomic claims before external calls;
- stable provider idempotency keys where supported;
- unique attempt receipts;
- explicit `UNKNOWN_OUTCOME`; and
- provider query/reconciliation before retry.

This produces safe behavior under the fixture's contract. It is not a universal exactly-once guarantee.

## Failure taxonomy

| Failure | Automatic retry? | Next control |
| --- | --- | --- |
| transient dependency before commit | bounded | new attempt, same logical operation |
| timeout with possible commit | no | reconcile |
| authentication/permission denial | no | terminal or operator |
| application policy denial | no | terminal |
| invalid/stale event | no | reject/stale inbox record |
| precondition changed | no | repropose/reapprove |
| state-version conflict | no blind retry | reload and reevaluate |
| cancellation/manual takeover | no | stop automated work |

A production provider adapter must classify failures based on the provider's documented semantics. The same HTTP status can have different commit guarantees across APIs.

## Claim/call/record crash windows

| Crash point | Durable observation | Recovery |
| --- | --- | --- |
| before claim commit | no attempt exists | another worker may claim |
| after claim, before call | `IN_FLIGHT`, no provider result | lease expiry plus provider query or policy-defined recovery |
| after provider commit, before record | local result unknown | reconcile by stable operation ID |
| after success record, before message publish | operation succeeded, outbox pending | outbox publisher retries delivery |

The outbox prevents “state committed but notification disappeared.” This lab records pending messages but does not implement a publisher; production needs a publisher lease, delivery retries, dedupe at consumers, and monitoring of old pending rows.

## Observability

Trace with identifiers, not raw sensitive payloads:

- run, tenant, workflow version, and state version;
- event ID/type/source and inbox disposition;
- from/to state and reason code;
- logical operation and attempt IDs;
- lease owner/expiry;
- provider operation ID and reconciliation outcome;
- budget counters; and
- retry/failure classification.

Alerts should include stuck waits, old leases, repeated version conflicts, budget exhaustion, approval failures, reconciliation age, terminal failures, and outbox backlog.
