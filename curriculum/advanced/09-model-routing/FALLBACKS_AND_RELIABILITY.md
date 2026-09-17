# Deep Dive — Fallbacks and Reliability

Fallback is recovery from a route/provider failure. It is not cascade promotion, and a shared client API does not make providers transparently interchangeable.

## Normalize the failure first

Provider adapters should map provider-specific responses to an application taxonomy:

| Category | Fixture codes | Default policy |
| --- | --- | --- |
| Retryable | `RATE_LIMIT`, `TRANSIENT_PROVIDER`, `TIMEOUT` | Bounded same-route retry, then compatible fallback if allowed |
| Availability fallback | `MODEL_UNAVAILABLE` | Compatible fallback without a pointless retry |
| Terminal | `INVALID_REQUEST`, `AUTH_FAILURE`, `POLICY_DENIED`, `CONTEXT_TOO_LARGE`, `CONTENT_REJECTED` | Stop and surface the typed reason |

Blindly sending authentication, policy, content, context, or invalid-request failures to another provider can leak data, evade policy, multiply cost, or repeat a deterministic error.

## Retry before fallback

For transient failures, the fixture retries the same route once with bounded exponential backoff, deterministic test jitter, and provider `retry_after_ms` when present. It retries only if the delay fits the remaining deadline.

Production jitter should be random and distributed. Retry budgets should be scoped to the route and request, respect idempotency for consequential tools, and avoid multiplying retries across application, gateway, SDK, and provider layers.

## Compatibility is explicit

A fallback route must:

1. pass a fresh evaluation of the same trusted `TaskRequirements` and `RoutingContext`;
2. satisfy current lifecycle, health, breaker, capacity, region, retention, policy, deadline, and cost constraints;
3. use a different provider;
4. share the same `equivalence_group`;
5. implement the same versioned adapter contract;
6. fit the remaining provider, attempt, cost, and deadline budgets.

The initial eligible set is historical evidence, not ongoing execution authority. An equivalence-group label is an additional registry assertion, not proof that modality, output/schema, tools, context limits, and data policy still pass.

The common `CandidateArtifact` normalizes structured data, evidence IDs, tool calls, confidence, and provenance. This creates a validation surface; it does not claim equal tool behavior, context semantics, safety filters, or model quality.

After fallback, run the same artifact validator and completion policy. Never trust the framework- or provider-selected name directly.

## Circuit breaker state

The routing runtime keeps circuit state per route and consults it before every call:

```text
CLOSED --threshold failures in window--> OPEN
OPEN --cooldown elapsed--> HALF_OPEN
HALF_OPEN --one probe succeeds--> CLOSED
HALF_OPEN --probe fails--> OPEN
```

Recoverable provider failures call `record_failure()` and successful provider responses call `record_success()`. Only one half-open probe is admitted. A production distributed system needs shared state or a lease; otherwise every process can stampede the recovering route.

## Health, freshness, and capacity

`RouteHealth` and `CapacityState` are route-specific. Eligibility rejects:

- unavailable routes and open circuits;
- stale health or capacity snapshots;
- exhausted request/token capacity;
- unavailable concurrency.

Production routing may add queue depth limits, adaptive concurrency, provider token buckets, regional quotas, hedging policy, and load shedding. Those signals need timestamps and ownership; “healthy” without freshness is not a safe fact.

The lab's mutable capacity ledger is initialized from the provider snapshot and consumes request/token headroom after calls. It demonstrates local reservation and accounting, not a globally synchronized provider quota; production must reconcile shared limits.

## Trace every attempt

`RouteAttempt` records a unique attempt ID, request ID, route, provider, fixture model ID, reason, start time, latency, tokens, reserved cost, actual cost, status, error code, and validation reasons. `RoutingRun` aggregates the final state, explicit budget overrun, and counts promotions separately from provider fallbacks.

This lets operations distinguish:

- more calls caused by gate calibration;
- more calls caused by provider reliability;
- deliberate policy reroutes;
- terminal denials that correctly made no extra calls.

## Framework boundary

Libraries such as [LiteLLM](https://docs.litellm.ai/) can normalize provider calls and expose retry, fallback, and cost mechanisms. The application must still own eligibility, tenant/data policy, route equivalence, retry classification, budgets, cancellation, artifact validation, and completion.

Use [AWS retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html), [backoff and jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/), and [idempotent API guidance](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) as production design references.
