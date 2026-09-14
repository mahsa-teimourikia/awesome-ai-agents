# Hysteresis, debounce, cooldown, and backpressure

These controls solve different problems. Treating them as synonyms creates blind spots.

| Control | Question | Course 08 behavior |
| --- | --- | --- |
| Hysteresis | when has a state recovered? | activate at `0.30`, recover at `0.10` |
| Debounce | has the condition persisted long enough? | measure event-time duration over a continuous valid streak |
| Cooldown | may another notification be sent yet? | suppress repeat same-severity notification for 15 minutes |
| Rate limit | is this recipient/channel interruption budget exhausted? | cap low-priority sends per rolling hour |
| Backpressure | can the consumer keep up? | process P1, batch moderate load, shed policy-eligible low priority |

## Stateful hysteresis

An activation threshold and a lower recovery threshold create a band in which the prior incident state is retained. Crossing below activation does not resolve an active incident. Recovery requires the lower boundary plus sustained healthy evidence.

```text
NORMAL → PENDING → ACTIVE → RECOVERY_PENDING → RESOLVED
```

`ACKNOWLEDGED` records the human response and cancels pending escalation. It does not mean the monitored condition recovered.

## Time-based debounce

Counting samples is unsafe because three readings might span three seconds or three hours. The fixture computes duration from event timestamps. Missing, stale, invalid, or below-threshold readings break the breach streak. Likewise, recovery requires a continuous good-quality healthy streak.

Sensor quality is part of the trigger decision. A missing value is not zero and cannot silently prove either breach or recovery. Out-of-order events cannot extend a streak or regress the incident.

## Fixed cooldown

Cooldown begins after notification, not after every sample. A continuing breach during cooldown stays active but does not interrupt the same recipient again. After cooldown, policy may issue a reminder. Cooldown never replaces hysteresis: recovery state still depends on evidence.

New material information bypasses older suppression where policy requires it. Course 08 always permits P1 severity escalation past a prior lower-severity cooldown. Production policies may also treat scope expansion or a newly affected service as material.

## Recipient rate limit

The delivery boundary counts confirmed messages by tenant, recipient, channel, and rolling window. P4/P3 floods can be deferred or rejected with `RATE_LIMIT`. Mandatory P1 routing bypasses that optional interruption budget; this exception is explicit and auditable.

## Stream backpressure

`evaluate_backpressure()` consumes queue depth, consumer lag, event severity, and tenant policy:

- P1: preserve and process now;
- moderate depth: batch correlated low-priority work before optional model enrichment;
- overload: shed only explicitly eligible low-priority events.

This avoids one model call per raw event. Operators should measure queue lag, shed counts, trigger recall, P1 misses, and model/notification budgets. Less noise is not success if critical-event recall declines.

## Failure cases to test

- a single spike never activates a sustained trigger;
- a sensor gap breaks the streak;
- oscillation inside the hysteresis band does not resolve/reopen;
- a continuous breach during cooldown produces no repeat notification;
- P3→P1 bypasses cooldown;
- sustained healthy values resolve;
- low-priority overload sheds while P1 remains eligible.
