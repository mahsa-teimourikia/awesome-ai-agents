# Event identity, deduplication, and correlation

At-least-once event systems may deliver the same producer event more than once. A proactive consumer must expect redelivery, reordering, retries, and crashes between state writes and external calls.

## Six identities, six jobs

| Field | Meaning |
| --- | --- |
| `event_id` | stable producer identity used for source-delivery idempotency |
| `schema_version` and `source_version` | meaning of the accepted envelope and source contract |
| versioned fingerprint | normalized fields used for a time-bounded duplicate claim |
| `correlation_key` | evidence grouping key, not a duplicate key |
| `incident_id` | one durable aggregate/state-machine occurrence |
| logical notification / attempt IDs | stable delivery intent / unique provider call |

The fingerprint includes only application-approved fields such as service, metric, region, environment, and certificate or backup identifiers. It excludes arbitrary message text, recipient instructions, and model summaries. Changing fingerprint fields changes semantics, so `fingerprint_version` is part of the hash input and audit trail.

## Why `EXISTS` then `SET` is wrong

This check-then-write sequence races:

```text
worker A: EXISTS key → false
worker B: EXISTS key → false
worker A: SET key
worker B: SET key
```

Both workers believe they won. Use one atomic conditional operation instead: a database unique key/UPSERT, Redis `SET ... NX EX ...`, a conditional write, or an equivalent stream-state primitive. `DurableProactiveStore.claim_dedupe()` uses one transactional SQLite insert after deleting only an expired claim.

## Dedupe is not exactly once

A claim can expire. A process can crash after the provider accepts a message but before the receipt is stored. A provider can time out with an unknown result. A partition can delay an event beyond the chosen window. Therefore dedupe cannot prove exactly-once side effects.

Course 08 combines:

- durable source-event uniqueness;
- atomic, tenant-scoped fingerprint claims;
- stable logical notification identity across retries;
- unique attempt identity for observability;
- provider-side idempotency where available; and
- reconciliation before retry after an unknown outcome.

## Duplicate does not mean discard all information

A source redelivery creates no new notification, but it increments duplicate-delivery and occurrence telemetry. Distinct events sharing a correlation key update the incident occurrence count and may add affected services. A materially higher severity bypasses prior cooldown/digest suppression. This preserves critical recall.

## Correlation window and incident lifecycle

The dedupe window answers “have I already claimed this normalized delivery?” The correlation window answers “does this new evidence belong to the current incident occurrence?” They need not match.

- within the window: update the incident with compare-and-set state versioning;
- beyond the window: start a new incident occurrence;
- lower/equal sequence: mark out of order, do not regress state;
- event at or before resolution: stale, do not reopen;
- timely event after resolution: start a new occurrence.

The SQLite fixture makes these boundaries executable and restart-safe. Production systems must choose windows from domain evidence and monitor collisions, expiry, and suppressed critical events.

## References

- [Redis `SET` conditional and expiry options](https://redis.io/docs/latest/commands/set/)
- [Redis data-deduplication tutorial](https://redis.io/tutorials/data-deduplication-with-redis/)
- [Apache Kafka delivery semantics](https://kafka.apache.org/08/design/design/)
- [SQLite UPSERT](https://www.sqlite.org/lang_UPSERT.html)
