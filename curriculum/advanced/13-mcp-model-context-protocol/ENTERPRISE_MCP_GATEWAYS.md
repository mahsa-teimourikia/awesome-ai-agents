# Deep Dive: Enterprise MCP Gateways

A gateway can centralize policy, routing, credential isolation, budgets, and audit. It
is a control point—not a universal trust oracle. A compromised gateway has broad blast
radius, so production designs need least privilege, segmentation, high availability,
policy versioning, and independent backend enforcement.

## Request path

```text
host identity and user intent
  -> gateway admission
  -> tenant-specific approved server route
  -> short-lived server-audience credential
  -> MCP client/transport
  -> server-side authorization
  -> narrowly scoped backend identity
  -> backend system
```

The model never sees backend credentials. The gateway retrieves or uses narrowly scoped
credentials through the organization's identity/secret system; it is not one giant
static-secret vault.

## Capability snapshots and races

An expiring snapshot binds server artifact, registry/policy versions, principal, tenant,
subject, purpose, credential ID/expiry/scope digest, and capability descriptor digests.
It captures what was eligible at discovery time, not permanent authority; call-time
authorization remains definitive.

The gateway tests three important races:

- permission revoked after discovery → `DENY_SCOPE`;
- server quarantined after discovery → `DENY_SERVER_QUARANTINED`;
- descriptor changed after discovery → `DENY_DESCRIPTOR_CHANGED`.

New tools and changed schemas/descriptions are `PENDING_REVIEW`. Capability-list change
notifications prompt a fresh diff; they do not approve the change.

## Resilience and execution

Calls have deadlines, cancellation, bounded retries, response-size limits, and budgets
for tools, servers, bytes, elapsed time, and cost. Retry policy distinguishes transport,
protocol, server, application, authorization, validation, and unknown-outcome failures.
Authorization and validation denials are terminal.

The gateway separates `prepare_tool_call()` from adapter dispatch and
`complete_tool_call()`. Preparation atomically persists an attempt, claims any approval,
and reserves estimated tool/server/byte/time/cost capacity. Completion releases the
reservation and accounts actual usage. Estimates can be lower than actuals, so
production may require conservative reserves or hard provider limits.

Cancellation before dispatch stops the next call. Cancellation after dispatch does not
roll back an external effect; an absent/invalid response remains an unknown outcome and
must be reconciled. Reconciliation is authorized/audited and distinguishes confirmed
effect, confirmed no effect, and still unknown.

Rate limiting is atomic and multidimensional across principal, tenant, and capability.
The fixture permits exactly N calls and rejects N+1, including under concurrent access.
A production gateway needs a distributed atomic store rather than an in-process lock.

Lifecycle is the governance state (`DISCOVERED` through `ACTIVE`, `QUARANTINED`, or
`RETIRED`); health is operational availability (`HEALTHY`, `DEGRADED`, `QUARANTINED`,
or `DISABLED`). The fixture permits degraded reads but denies approval-gated/high-risk
writes. Quarantine and restoration are governed events recording actor, reason, time,
and policy version.

## Supply-chain review

Enterprise admission covers publisher identity, endpoint, package/container version and
digest, provenance, vulnerability posture, network destinations, data retention,
subprocessors, and capability namespaces. A public registry entry is useful discovery
metadata, not evidence that these controls passed.

## Audit

Audit records allowed and denied requests, schema failures, approval failures, rate
limits, descriptor drift, and quarantine. Log identifiers, reason codes, policy version,
and canonical digests—not credentials, raw sensitive arguments, or full tool results.
The deterministic fixture hash-chains events to make local edits observable; this does
not authenticate a mutable chain. Local sequential IDs are not globally unique, and raw
hashes of low-entropy sensitive values can be guessable. Production requires durable,
tamper-resistant/externally anchored storage, selective or keyed digests, access
control, retention, and monitoring.
