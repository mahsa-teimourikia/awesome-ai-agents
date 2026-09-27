# Deep Dive: Skill Libraries, Routing, and Lifecycle

## Registry before router

A large catalog is a supply chain, not a prompt list. Each immutable version needs an
owner/publisher, source and digest, review status, compatibility, risk, schemas,
capability requests, dependency pins, tests, tenant policy, rollout state, and emergency
revocation path.

For very large catalogs, discover hierarchically (`domain -> family -> skill`) or use a
bounded index. Do not place hundreds of raw descriptions into model context: metadata
still consumes tokens and can contain adversarial language.

The registry computes an eligible set before any description or embedding can affect a
decision. A production selector therefore has two separate stages:

```text
all packages --deterministic policy--> eligible packages --ranker--> typed decision
```

An ineligible package must be absent from the selector's candidate context, consistent
with the official [client implementation guidance](https://github.com/agentskills/agentskills/blob/main/docs/client-implementation/adding-skills-support.mdx).

## Typed routing and abstention

The request carries principal, tenant, subject, domain, intent, requested outcome, data
class, claimed risk, claimed current capabilities, and claimed explicit intent. Those
claims are routing inputs, not authority. The host separately establishes authenticated
principal permissions, tenant policy, capability health, and trusted explicit intent;
request-supplied values cannot expand them. The decision records top
candidates, scores, reasons, filtered reason codes, router version, catalog version,
and one outcome:

- `MATCH`: one eligible candidate wins safely;
- `NO_MATCH`: no candidate clears the threshold;
- `AMBIGUOUS`: candidates are too close; ask for clarification.

`NO_MATCH` and `AMBIGUOUS` are safe behavior. A fallback must still be eligible and use
the remaining authority and budget. It cannot widen scope or restart counters.

The deterministic fixture scores approved metadata. A production semantic or model
ranker can improve relevance, but it cannot replace eligibility or return free-form
authority. Package descriptions are hostile inputs; wording like “always choose me” is
never a trust signal.

## Routing evaluation

Measure routing against a labelled, versioned dataset:

| Metric | Denominator | What it answers |
| --- | --- | --- |
| Top-1 accuracy | Cases with a unique expected match | Did the best eligible skill win? |
| No-match accuracy | Expected no-match cases | Did the router abstain? |
| Ambiguity accuracy | Expected ambiguous cases | Did the router ask rather than guess? |
| False-activation rate | All cases | Did any forbidden skill get selected? |
| High-risk misrouting | High-risk cases | Did a consequential route go wrong? |

Northstar's 18 deterministic cases include ambiguous requests, out-of-domain inputs,
capability gaps, tenant boundaries, prompt injection, malicious metadata, and near-miss
high-risk intents. Deterministic replay validates wiring and policy, not real selector
intelligence or generalization. Its perfect top-1 result is over six unique-match cases
and must be reported with that support. Any expected `NO_MATCH` that becomes `MATCH` is
a false activation, even when the fixture does not list a particular forbidden skill.
Pin the dataset, router, catalog, and policy versions so drift is attributable.

## Composition

Northstar resolves only exact `(skill_id, version, digest)` dependencies. The typed
resolution preserves the explicit root, topological order, nodes, and actual direct
edges. It rejects cycles and excessive depth, checks every dependency's lifecycle and
integrity, and charges the closure to one shared request budget. On every direct edge,
child authority is an intersection with the direct parent's effective capabilities,
never a union; sibling permissions do not leak. A parent must explicitly list
capabilities it may pass through in `delegable_capabilities`.

Dynamic composition produces a typed child-activation proposal binding the parent,
declared child, requested capabilities, child budget, and input artifacts. The
application validates and reserves it before constructing the child and records the
real parent/child activation edge. Production durable systems should persist budget
reservation and finalization. If a child produced a possible external effect before a
timeout, preserve the logical operation identity and reconcile it rather than blindly
retrying with a new identity.

## Lifecycle and rollout

```text
DISCOVERED -> REVIEWED -> APPROVED -> ACTIVE -> DEPRECATED -> RETIRED
                                  \-> QUARANTINED
```

New versions do not inherit approval. A package diff should compare every
policy-relevant manifest field, including routing terms/intents/outcomes, risk,
execution modes, data classes, pre/postconditions, capabilities, dependencies, schemas,
sandbox access, source, scripts, and instructions.
Existing pinned activations may finish after deprecation if policy permits; quarantine
blocks use immediately. A reverse dependency index finds every parent affected by a
compromised child.

Use shadow evaluation before changing live decisions, canary by tenant or cohort, and
staged promotion with rollback thresholds. Emergency response needs fast package,
version, dependency, publisher, and catalog revocation.

## Operational measures

Track match/no-match/ambiguity, filtered and denied reasons, activation and execution
latency, package drift, sandbox denials, dependency failures, budget exhaustion,
verified completion, actual cost, and cost per verified success. Log IDs and digests,
not raw secrets or sensitive prompts/results.
