# Advanced 09 — Model Routing

**Level:** Advanced · **Time:** 150 min · **Prerequisites:** Intermediate 05 Evaluation, Intermediate 06 Tool Engineering, Advanced 08 Proactive Agents

**Canonical notebook:** [`09_model_routing.ipynb`](09_model_routing.ipynb)

> Routing is a constrained decision, not a model leaderboard. First prove that a route is technically and organizationally eligible; only then optimize among the eligible routes.

This course builds a credential-free routing control plane for Northstar Commerce. The fixture names (`model-fast-v1`, `provider-a`) are deliberately fictional. They keep the lesson stable as commercial catalogs, prices, regions, and product names change.

## Learning outcomes

By the end, you can:

- turn a task into typed requirements without trusting prompt text as policy;
- separate provider-supplied capability metadata from application-owned eligibility;
- filter on modality, output, tools, context, quality, policy, residency, retention, health, capacity, cost, latency, and deadline;
- optimize cost, latency, or measured workload quality only inside the eligible set;
- build a bounded quality cascade and measure its promotion signal;
- distinguish cascade promotion, provider fallback, and policy rerouting;
- classify provider failures into retry, compatible fallback, or terminal outcomes;
- preserve a typed route-attempt history with registry, pricing, policy, and validator versions; and
- compare a governed policy with a same-task baseline using task success, false accepts, false promotions, cost, latency, and call count.

## Scenario and threat model

Northstar extracts structured support tickets containing sensitive EU customer data. An attacker can place instructions in ticket text, retrieved documents, or model output. None of those channels may alter the tenant, data classification, allowed provider or region, retention requirement, budget, deadline, or authorization context.

The application constructs two trusted objects:

- `TaskRequirements`: workload family and technical needs;
- `RoutingContext`: tenant and organizational constraints.

Provider catalogs are also untrusted inputs. They may report technical capabilities, but the application must overlay classification, residency, retention, lifecycle, pricing, health, capacity, and tenant policy before a route can become eligible.

```text
untrusted request content                 provider catalog metadata
            │                                      │
            └──────► application-owned typed requirements/context
                                      │
                        eligibility (fail closed)
                                      │
                       eligible route set only
                                      │
                    objective-specific optimization
                                      │
                bounded call → typed artifact → validator
                         │ pass                 │ fail
                         ▼                      ▼
                     complete        quality promotion / recovery
```

## The control boundary

The lesson uses four distinct decisions:

| Decision | Question | Owned by |
| --- | --- | --- |
| Eligibility | May this route process this task for this tenant now? | Application policy |
| Optimization | Which eligible route best fits this request's objective? | Application routing policy |
| Quality promotion | Did an automated gate justify a stronger route? | Versioned validator and cascade policy |
| Failure recovery | Is this failure retryable, safely equivalent elsewhere, or terminal? | Error taxonomy and bounded recovery policy |

These decisions are not interchangeable. A cheap route is irrelevant if it is ineligible. A provider error is not evidence that output quality was inadequate. A quality-gate rejection is not a provider outage. A session pin that becomes ineligible must be rerouted by policy, not silently reused.

## Course artifacts

| Artifact | Purpose |
| --- | --- |
| [`policy.py`](policy.py) | Strict Pydantic contracts and pure policy decisions |
| [`lab.py`](lab.py) | Deterministic registry, replay client, bounded runtime, circuit breaker, and evaluation |
| [`09_model_routing.ipynb`](09_model_routing.ipynb) | Canonical executable lesson |
| [`CAPABILITY_FILTERING.md`](CAPABILITY_FILTERING.md) | Eligibility and trusted routing context |
| [`MODEL_CASCADES.md`](MODEL_CASCADES.md) | Quality gates, promotion signals, and cascade measurement |
| [`FALLBACKS_AND_RELIABILITY.md`](FALLBACKS_AND_RELIABILITY.md) | Error taxonomy, compatibility, retries, health, and circuits |
| [`tests/test_model_routing.py`](../../../tests/test_model_routing.py) | Focused invariants and adversarial cases |

## Registry model

`ModelRoute` represents a deployable route, not a universal model score. A route binds a fixture model ID to a provider, deployment, region, equivalence group, adapter contract, capability set, application policy, pricing snapshot, workload measurements, health, capacity, and lifecycle.

Quality is workload-specific. `model-fast-v1` can have one measured score for support extraction and no measurement at all for architecture reasoning. Missing evidence makes the route ineligible for that workload; it does not inherit a global “good model” label.

Pricing accounts for both input and output tokens. Admission reserves the upper output bound; runtime accounting records actual tokens. A production registry should keep effective dates and conservative reserves because live usage and prices may exceed estimates.

Lifecycle states are explicit:

- `ACTIVE`: accepts new work;
- `DRAINING`: only an already pinned eligible session may continue;
- `DEPRECATED`: no new routing;
- `DISABLED`: unavailable.

## Eligibility before optimization

`evaluate_eligibility()` checks:

1. trusted context consistency and cancellation;
2. lifecycle, tenant provider allowlist, region, classification, and retention;
3. modalities, output type, structured output, tools, protocols, parallel tools, streaming, reasoning, context, and output limits;
4. route-equivalence group and measured workload quality;
5. latency SLO, upper-bound cost, deadline feasibility;
6. route-specific health, circuit state, freshness, request/token capacity, and concurrency.

Only routes with no rejection reasons enter `select_route()`. The deterministic fixture demonstrates why this order matters: `route-fast-us-cheap` has the lowest nominal price, but sensitive EU/ZDR work cannot use it.

The objective then ranks the eligible set:

- `BALANCED_COST`: lowest expected cost, with latency and quality tie-breakers;
- `QUALITY_FIRST`: highest measured workload quality;
- `LATENCY_FIRST`: lowest measured p95 latency.

The result is a typed `RoutingDecision` with the complete eligible set, per-route rejection reasons, expected and reserved cost, workload quality, p95 latency, and registry/pricing/policy versions.

## Output contracts and quality gates

Provider adapters normalize output into a common `CandidateArtifact`. A shared API shape does not make models, tool semantics, safety behavior, context handling, or outputs equivalent.

The support-ticket validator reports four separate signals:

- schema validity;
- semantic constraints;
- evidence grounding;
- task correctness against labelled fixture truth.

JSON validity alone is intentionally insufficient. The fixture includes valid JSON with the wrong priority. A schema-only baseline accepts it; the governed policy rejects it and promotes.

The automated gate is imperfect and must itself be evaluated:

- **false accept:** the gate accepts a task-incorrect artifact;
- **false promotion:** the gate rejects a task-correct artifact and spends more work.

The replay client validates routing mechanics against labelled fixture outcomes. It does not prove live-model intelligence or generalization.

## Three different route changes

| Change | Trigger | Next route requirement | Attempt reason |
| --- | --- | --- | --- |
| Cascade | Output fails an automated quality gate | Higher measured quality, still eligible | `CASCADE_PROMOTION` |
| Fallback | Retryable/unavailable provider route | Same equivalence group and adapter contract, still eligible | `PROVIDER_FALLBACK` |
| Reroute | Policy/context/health changes before work | Recompute eligibility and optimization | `POLICY_REROUTE` |

The runtime checks cancellation, remaining deadline, conservative cost reserve, attempt count, provider count, and fallback count before every next model call. A cancellation must prevent the next call, not merely discard its result.

## Reliability model

The fixture normalizes provider failures into a typed taxonomy:

- retryable: rate limit, timeout, transient provider error;
- fallback-capable after bounded retry: the retryable set plus model unavailable;
- terminal: invalid request, authentication failure, policy denial, context too large, content rejection.

Retries use bounded exponential backoff, deterministic fixture jitter, and `retry_after_ms` when supplied. They must fit the remaining deadline. Fallback is allowed only across routes that were already eligible and share both an equivalence group and adapter contract.

The route-specific circuit breaker implements `CLOSED → OPEN → HALF_OPEN`. Only one half-open probe is admitted. Health and capacity snapshots have freshness limits because stale “healthy” state is unsafe. Production systems also need distributed coordination, per-route token buckets, queue limits, and provider-specific herd control.

## Evaluation

`evaluation_fixture()` compares the same five labelled cases:

1. easy fast-path success;
2. schema-valid and constraint-valid but task-incorrect output;
3. schema-invalid output;
4. correct output rejected by an over-conservative confidence signal;
5. provider unavailability requiring a compatible fallback.

The baseline always uses the cheapest route, checks schema only, and performs no recovery. The governed policy uses the full gate and bounded recovery. Report:

- successful compliant task rate;
- false-accept and false-promotion rates;
- promotion and provider-fallback rates;
- total and average model calls;
- average cost and cost per successful compliant task;
- p95 end-to-end latency.

The deterministic fixture makes policy mechanics reproducible. Production claims require representative labelled traffic, held-out evaluation, live latency/cost measurements, calibration by workload and tenant, and monitoring for drift.

## Run locally

From the repository root:

```bash
uv sync --extra core --extra contributor
uv run --extra core python curriculum/advanced/09-model-routing/lab.py
uv run --extra core --extra contributor pytest -q tests/test_model_routing.py
uv run --extra core --extra contributor python scripts/execute-notebooks.py \
  curriculum/advanced/09-model-routing/09_model_routing.ipynb
```

The notebook and lab require no credentials and make zero production provider calls.

## Production adapter boundary

The stable lesson is framework-neutral. In production, an adapter may obtain versioned capability metadata or normalize provider APIs, but application code still owns eligibility, tenant policy, residency, retention, pricing reservations, quality gates, budgets, retries, fallback equivalence, completion, and audit history.

Useful implementation references:

- [LiteLLM documentation](https://docs.litellm.ai/) — unified provider input/output, retry/fallback, and cost-tracking mechanisms; these do not imply semantic equivalence.
- [RouteLLM](https://github.com/lm-sys/RouteLLM) — serving and evaluating learned routing policies with calibrated thresholds.
- [Semantic Router](https://github.com/aurelio-labs/semantic-router) and [vLLM Semantic Router overview](https://github.com/vllm-project/semantic-router/blob/main/website/docs/overview/semantic-router-overview.md) — semantic and model-routing implementations.
- [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html), [Exponential backoff and jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/), and [Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) — bounded retry guidance.

## Exercises

1. Add an audio task family and prove that text-only routes never enter its optimization set.
2. Calibrate two confidence thresholds on separate train and holdout fixtures. Plot task success, false accepts, false promotions, cost, and p95 latency.
3. Add a tenant whose policy permits public US work but requires sensitive EU work to remain in-region. Prove the eligible sets differ.
4. Add a `DRAINING` route and demonstrate sticky-session continuation versus new-work denial.
5. Extend the circuit breaker with a distributed lease for the half-open probe and explain the failure mode without it.

## Checkpoint

**A sensitive EU task has three routes. The cheapest route is in the US without zero-data-retention support; a second EU route passes the quality gate; a third EU route has higher measured quality. What is the correct order?**

A. Rank all three by price, then check policy after the call.
B. Ask the model which policy applies.
C. Exclude the US route through application-owned eligibility, optimize the remaining routes for the request objective, then use the quality gate only to decide bounded promotion.
D. Always use the highest-quality route.

<details>
<summary>Answer</summary>

**C.** Eligibility is a control boundary. Optimization and quality promotion operate only inside the eligible set, and prompt or model text cannot enlarge that set.

</details>

## Final principle

**First prove a route may run. Then decide whether it should run. After it runs, validate what it produced. Every additional call remains bounded by policy, deadline, cost, and cancellation.**
