# Deep dive — Events, idempotency, and reconciliation

An event says that something was delivered. It does not prove the payload is authentic, current, authorized, unique, or still relevant.

## Admission before dispatch

The fixture verifies, in order:

1. the run exists and its workflow/state versions are supported;
2. neither the envelope ID nor the stable `(source, source_event_id)` delivery has already reached the durable inbox;
3. the payload matches its digest;
4. the envelope signature is valid;
5. tenant and run bindings match authoritative state;
6. the authenticated source is allowed to emit that event type;
7. the event names the current wait generation and is not older than the persisted wait start or implausibly far in the future;
8. the run is not terminal; and
9. the event type is legal for the current state.

Accepted, rejected, duplicate, and stale deliveries all produce explicit dispositions. In the fixture, `approval-gateway`, `scheduler`, `integration-gateway`, and `operator-control` each have a narrow event-type allowlist. Production gateways also need authenticated source identity, key rotation, payload-size limits, and a domain-appropriate replay/freshness policy.

## Three independent identities

`event_id` deduplicates one envelope, while `(source, source_event_id)` deduplicates a delivery that may be rewrapped with another envelope ID. `wait_generation` prevents an authentic event for wait 1 from waking wait 2. `state_version` serializes state transitions. `logical_operation_id` identifies a consequential external effect. Reusing one of these for all boundaries collapses different failure domains.

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
| cancellation/manual takeover before dispatch | no | stop automated work |
| cancellation/manual takeover after dispatch | no | preserve reconciliation/verification obligation, block new calls, then finish with the requested control outcome |

A production provider adapter must classify failures based on the provider's documented semantics. The same HTTP status can have different commit guarantees across APIs.

## Claim/call/record crash windows

| Crash point | Durable observation | Recovery |
| --- | --- | --- |
| before claim commit | no attempt exists | another worker may claim |
| after claim, before dispatch | `IN_FLIGHT`, no dispatch marker | lease expiry plus policy-defined recovery |
| after dispatch marker, before call/result | `IN_FLIGHT`, call may have happened | lease expiry → unknown outcome → reconciliation |
| after provider commit, before record | local result unknown | reconcile by stable operation ID |
| after success record, before message publish | operation succeeded, outbox pending | outbox publisher retries delivery |

The operation's `active_attempt_id` and owner prevent a late result from an obsolete attempt from mutating the current attempt. The outbox prevents “state committed but notification disappeared.” This lab records pending messages but does not implement a publisher; production needs a publisher lease, delivery retries, dedupe at consumers, and monitoring of old pending rows.

## Reconciliation and independent verification

Reconciliation produces one of three typed outcomes: `CONFIRMED_EFFECT`, `CONFIRMED_NO_EFFECT`, or `STILL_UNKNOWN`. A receipt binds that finding to the logical operation and request digest. Confirmed absence permits another attempt only after current approval, policy, preconditions, and retry budget are revalidated.

Provider reconciliation is not the final completion check. The lab separately queries a deterministic business read model, `RefundLedger`. Only matching provider evidence plus matching business-state evidence can complete the normal workflow. If cancellation or manual takeover arrived while the effect was in flight, the same verification obligation is preserved, but the final control state reflects that durable intent.

## Observability

Trace with identifiers, not raw sensitive payloads:

- run, tenant, workflow version, and state version;
- envelope ID, source event ID, wait generation, type/source, and inbox disposition;
- from/to state and reason code;
- logical operation and attempt IDs;
- lease owner/expiry;
- active attempt, dispatch marker, provider operation ID, typed reconciliation outcome, and business verification;
- budget counters; and
- retry/failure classification.

Alerts should include stuck waits, old leases, repeated version conflicts, budget exhaustion, approval failures, reconciliation age, terminal failures, and outbox backlog.
