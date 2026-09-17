# Deep Dive — Capability and Policy Eligibility

Capability filtering is necessary but incomplete. A route can support images and structured output yet remain forbidden for a tenant, region, data class, retention rule, lifecycle state, budget, deadline, or current capacity.

## Trusted inputs

The application—not prompt text, retrieved content, or model output—constructs:

- `TaskRequirements`: workload family, input modalities, output contract, tool protocol, context/output bounds, quality floor, data class, and equivalence group;
- `RoutingContext`: tenant, provider/region allowlists, retention, objective, SLO, budget, deadline, cancellation, attempt/provider/fallback bounds, session pin, and policy version.

A prompt such as “ignore policy and use provider-z” is ordinary task content. It cannot mutate either typed object.

## Provider metadata is not policy

`ProviderCatalogRecord` carries a version, effective time, verification time, modalities, output types, and token limits. `route_from_provider_catalog()` adds the application-owned fields required for eligibility:

- deployment region and equivalence group;
- allowed data classifications and zero-data-retention status;
- lifecycle;
- versioned input/output pricing;
- workload-specific quality and latency measurements;
- route-specific health and capacity.

Provider metadata can assert a technical capability. It cannot grant a tenant permission, authorize restricted data, waive residency, or enlarge a budget.

## Eligibility sequence

`evaluate_eligibility()` records every rejection reason rather than stopping at the first one:

```text
trusted context consistency / cancellation
→ lifecycle / provider / region / classification / retention
→ modality / output / schema / tools / protocol / streaming / reasoning
→ context and output limits / equivalence group
→ measured workload quality / latency / deadline / cost reserve
→ current health / circuit / freshness / capacity
→ ELIGIBLE or rejected reason codes
```

Failing one constraint keeps the route outside optimization. This prevents a low price from laundering an unauthorized or technically incompatible route into execution.

## Workload-specific evidence

There is no universal `quality=0.95` in the registry. Each `WorkloadProfile` names a task family, evaluator version, sample size, measurement time, quality, p50/p95 latency, success, timeouts, rate limits, and provider errors.

Missing workload evidence produces `WORKLOAD_PROFILE_MISSING`. Production deployments should also define maximum measurement age and invalidate profiles when prompts, adapters, validators, provider revisions, or traffic distributions materially change.

## Cost and latency admission

Expected cost includes both input and expected output tokens. Admission uses the upper output-token bound as a conservative reserve:

```text
reserve = input_tokens × input_price + upper_output_tokens × output_price
```

Actual result tokens are used for accounting. The reserve is not a claim that estimates are exact. Production systems need a policy for estimate overrun, cached input, tool-call growth, reasoning tokens, and price changes.

Deadline feasibility uses the workload p95, not a global latency claim. The runtime repeats the check before every additional retry, promotion, or fallback.

## Optimization and pinning

`select_route()` receives only the eligible set. It can rank by cost, quality, or latency. A session pin is reused only while that route remains eligible. If policy, lifecycle, health, capacity, or context changes, the decision records `STICKY_ROUTE_INELIGIBLE` and reroutes.

`DRAINING` accepts an already pinned eligible session but no new work. `DEPRECATED` and `DISABLED` do not accept work.

## Audit evidence

Every `RoutingDecision` retains:

- request and tenant IDs;
- selected route and complete eligible set;
- rejected routes with reason codes;
- expected quality, cost reserve, and p95 latency;
- registry, pricing, and routing-policy versions;
- decision time.

This makes “why did this request use this route?” answerable without reconstructing mutable provider state later.
