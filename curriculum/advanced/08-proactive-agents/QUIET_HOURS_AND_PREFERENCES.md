# Quiet hours, preferences, and durable delivery

Notification wording and delivery authority belong to different components. A detector produces a typed `NotificationProposal`; an application-owned router decides whether, when, where, and to whom it may be delivered.

## Routing precedence

Course 08 applies:

```text
tenant and recipient-scope authorization
→ current on-call assignment
→ mandatory organizational policy
→ IANA timezone and workday
→ optional user preference
→ interruption budget and provider result
```

Mandatory P1 policy can override quiet hours and category opt-out. Optional policy must not. The override should be narrow, versioned, observable, and owned by accountable operators.

## Time zones and daylight saving time

Fixed offsets such as `UTC-8` are wrong when daylight-saving rules change. `RecipientPreference.timezone` accepts an IANA name such as `America/Vancouver`, and Python `zoneinfo` calculates the next local workday. The regression suite includes the 2026 spring-forward transition.

## Current recipient, not cached recipient

A proposal stores an authorized recipient **scope** such as `on_call_primary`, not an email address copied from model output. The router resolves that scope from a current schedule. Delivery resolves it again, because a rotation can change after proposal creation. A stale assignment or a preference belonging to another tenant/recipient fails closed.

## Durable digest lifecycle

A P4 signal outside working hours becomes a persisted digest item with a UTC delivery time. It survives process restart; the service does not sleep in memory until morning. Correlated occurrences update the incident, while the logical item remains stable.

Before dispatch:

- resolved incident → summarize as “occurred and resolved”;
- superseded/escalated/cancelled item → do not send as active;
- open incident → summarize current occurrence state.

Digest queries are tenant- and recipient-scoped.

## Idempotent delivery and unknown outcomes

Retries reuse the logical notification ID but receive unique attempt IDs. A confirmed receipt makes repeat delivery a no-op. A timeout is `UNKNOWN`: the system blocks another send until it reconciles provider state. Treating unknown as failure can duplicate a page.

Transient P1 failure can use an authorized fallback channel. Lower-priority retries remain bounded. Exhausted work moves to a dead-letter table with an auditable reason.

## Acknowledgment and escalation

P1 policy schedules durable escalation roles. An authorized acknowledgment transitions incident state and cancels pending timers. Without acknowledgment, each due role escalates in order. Resolution also cancels escalation and updates deferred digest state.

The notification provider cannot authorize remediation. A delivered page may prompt a human decision or an independently authorized workflow, but text such as `APPROVED` or `restart now` carries no capability.

## References

- [Python `zoneinfo`](https://docs.python.org/3/library/zoneinfo.html)
- [AWS EventBridge documentation](https://docs.aws.amazon.com/eventbridge/)
