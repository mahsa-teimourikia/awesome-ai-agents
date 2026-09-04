# Deep dive: routing evidence questions to bounded sources

Semantic routing is a decision layer before retrieval. It proposes which source or sources best match an evidence question; application policy still decides whether the route is allowed. Routing does not grant database access, choose a tenant, enable public web search, or increase a budget.

## Route outcomes, not forced classification

A production router needs more than one winning label:

| Outcome | Meaning | Controller response |
| --- | --- | --- |
| `KNOWN_ROUTE` | one source is clearly justified | validate and retrieve |
| `MULTI_ROUTE` | the question spans multiple evidence sources | decompose or retrieve an approved subset |
| `AMBIGUOUS` | several interpretations remain | clarify or apply a bounded disambiguation step |
| `UNKNOWN` | no registered source fits | abstain or escalate; never invent a source |

For the Northstar incident, incident facts route to `incident_db`, procedures to `runbook_search`, and the dependency/provider question proposes both `dependency_graph` and `provider_status`. The controller initially retrieves incident plus runbook, evaluates the evidence gap, and queries the graph only when dependency evidence is missing.

## Router implementations

| Router | Strengths | Limitations | Best fit |
| --- | --- | --- | --- |
| Deterministic rules | inspectable, cheap, stable, easy to test | weak on novel phrasing | narrow high-value intents and policy-sensitive routes |
| Embedding classifier | handles paraphrase without generation | threshold calibration, dataset drift, ambiguous multi-intent queries | larger stable route sets with representative examples |
| Model-based classifier | flexible decomposition and structured rationales | added cost/latency and non-deterministic errors | complex questions after deterministic safeguards |
| Hybrid cascade | cheap path first, expensive route only for uncertainty | more operational/evaluation complexity | high-volume systems with a measured uncertainty boundary |

Do not label one class “high accuracy” and another “medium accuracy” universally. Accuracy, abstention quality, latency, and cost depend on the route set, examples, encoder/model, thresholds, hardware, deployment mode, and live query distribution.

The open-source [`semantic-router`](https://github.com/aurelio-labs/semantic-router) project is one maintained embedding/dynamic-routing option. Its API has changed across releases, so follow its current documentation and pin the version only if you adopt it. Course 09 deliberately does not depend on it: the deterministic router in `policy.py` makes the source, tenant, and budget boundaries visible and testable. No uncited sub-millisecond guarantee is assumed.

## Multi-route decomposition

“Which dependency or provider is involved?” legitimately spans graph and provider-status evidence. Three patterns are possible:

1. retrieve both immediately when both are required and budgeted;
2. retrieve the lower-cost/internal source first, evaluate the gap, then retrieve the official status source if necessary; or
3. split the compound question into two linked evidence questions.

Course 09 uses the second pattern. It demonstrates that routing opportunity is not an instruction to query everything.

## Evaluation

Build a labeled dataset containing known, unknown, ambiguous, and multi-route queries. Measure:

- exact and set-based route accuracy;
- false-positive source access;
- unknown/ambiguous abstention quality;
- tenant and authorization violations;
- evidence recall after routing, not classification accuracy alone;
- duplicate retrieval rate;
- cost and latency distributions on the target deployment.

Inspect errors by class. A route can be “correct” yet yield stale evidence, and a relevant document can still fail to support the final claim. Route evaluation therefore precedes—but never replaces—freshness, sufficiency, and citation verification.

## Production boundaries

- Bind tenant and authorization from authenticated application context.
- Deny unknown sources and validate every model-proposed route.
- Put hard limits on query rewrites, corrective retrievals, hops, web calls, cost, and time.
- Require explicit web permission, confidentiality checks, query minimization, and domain allowlists.
- Version router rules/models and retain observable route decisions without private chain-of-thought.
- Prefer a fixed path when one known source already answers the question.

The router chooses where evidence may be sought. It never decides what the evidence authorizes.
