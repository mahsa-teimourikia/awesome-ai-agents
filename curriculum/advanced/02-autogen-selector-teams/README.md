# Bounded, Evidence-Driven AutoGen Selector Teams

**Level:** Advanced · **Time:** 120 min · **Prerequisite:** [Advanced 01 — Architecture Decisions](../01-single-vs-multi-agent/README.md)

**Advanced · 02** · **Notebook:** [`02_autogen_selector_teams.ipynb`](02_autogen_selector_teams.ipynb) · **Shared implementation:** [`policy.py`](policy.py)

AutoGen's `SelectorGroupChat` lets a model choose the next participant in a shared conversation. That flexibility is useful when the next specialist depends on evidence discovered at runtime. It also adds a common and expensive failure mode: agents can repeat work, bounce between roles, or keep reviewing an unchanged proposal.

AutoGen is a widely used open-source multi-agent framework. This course separates its two layers deliberately:

| Layer | Course status |
|---|---|
| Framework-neutral selector control model | the stable lesson and application architecture |
| AutoGen AgentChat 0.7.5 | the tested adapter implementation in this repository |

The control model does not depend on AutoGen 0.7.5. A later framework or adapter version must preserve the same application-owned invariants and pass the same contract tests.

This course keeps the original selector-team idea and hardens it:

> The selector does not choose who feels like speaking next. From an application-validated eligible set, it proposes the specialist most likely to close a specific unresolved evidence gap.

The selector is a router, not a conversation host. Its output is a proposal—not new authority and not permission to execute a production action.

![AutoGen Selector Topology](../../../assets/autogen_selector_topology.svg)

## Learning outcomes

By the end, you can:

- represent team context, evidence, artifacts, selector decisions, budgets, turns, and termination as strict Pydantic models;
- compute eligible speakers from application-owned state and reject invented or stale destinations;
- route the Northstar investigation by unresolved evidence gaps rather than conversational cues;
- distinguish a repeated speaker from duplicate work, semantic stagnation, ping-pong, and review churn;
- separate selector calls, worker calls, aggregate model work, wall-clock latency, tokens, and cost;
- compare the selector team with a single generalist on the same task and acceptance criteria; and
- preserve the framework-neutral control model while using the tested AutoGen AgentChat 0.7.5 adapter without making framework chat history authoritative.

## Northstar incident

Every path answers the same question:

> Why did EU checkout conversion fall after deploy-1842, and what should we do?

Required evidence is `health`, `logs`, `deployment`, `customer-impact`, and `current-runbook`. The team has five roles:

| Agent | Evidence or state it may advance | Application-granted capabilities |
|---|---|---|
| `ObservabilityAgent` | health and logs | `health.read`, `logs.read` |
| `DeploymentAgent` | deployment and current runbook | `deployment.read`, `runbook.read` |
| `CustomerImpactAgent` | aggregated customer impact | `customer-impact.read` |
| `AnalystAgent` | candidate diagnosis after evidence sufficiency | no production tools |
| `ReviewerAgent` | review after a candidate exists | no production tools |

The course ends at a grounded proposal. `REVIEW_PASS` means the evidence and diagnosis passed review. It does **not** authorize rollback. A consequential write still needs the approval and execution controls from Course 03.

## The control plane

```text
trusted TeamContext
        ↓
typed evidence gaps ──→ application computes eligible_agents(state)
                                  ↓
projected selector state ──→ selector proposes one destination
                                  ↓
                     validate_selector_decision()
                                  ↓
                       one bounded worker turn
                                  ↓
              validate artifact, provenance, tenant, capability
                                  ↓
                 update typed state and evaluate termination
```

`TeamContext` is application-owned: tenant, incident, required evidence, capability policy, source allowlist, budget, and policy version. Messages cannot rewrite it. `TeamMessage` preserves provenance for traceability, but raw chat text is supplementary rather than authoritative state.

### Eligibility before selection

`eligible_agents(team_state)` applies deterministic rules:

- missing health or logs → `ObservabilityAgent`;
- missing deployment or runbook → `DeploymentAgent`;
- missing customer impact → `CustomerImpactAgent`;
- all required evidence present, no candidate → `AnalystAgent`;
- candidate present, review not passed → `ReviewerAgent`;
- no safe progress → abstain or escalate.

Several speakers may be valid. If health and deployment evidence are both missing, either matching specialist may be a safe next choice. Evaluation therefore scores membership in a valid set instead of requiring one arbitrary gold speaker.

Eligibility is a safety and control boundary, not an optimality claim. `valid_speaker_rate` measures whether a proposed speaker belongs to the allowed set. It does not prove that the speaker is the best next choice for information gain, latency, cost, or critical-path progress. This fixture intentionally has cases with no unique optimal speaker, so it does not report `preferred_route_accuracy` or an `information_gain_score`.

### Typed proposal and typed artifact

The selector returns `SelectorDecision(next_agent, reason_code, target_gap, eligible_agents)`. The application recomputes the eligible set and rejects:

- an unknown agent;
- a known but currently ineligible agent;
- a stale or selector-invented eligible set; or
- an agent that cannot close the named gap.

Each worker returns a `WorkerArtifact` with identity, tenant, evidence references, findings, unresolved questions, and timestamp. Before committing state, the policy checks expected agent identity, tenant, evidence registry, source allowlist, provenance, and capability scope. An agent chosen by the selector receives no new tool authority.

## Completion and termination

Normal completion is state-based:

```text
required evidence complete → AnalystAgent
candidate diagnosis exists → ReviewerAgent
validated REVIEW_PASS      → COMPLETE
```

Hard limits stop damage; they do not define success. The lab uses this precedence when several conditions are true:

1. `CANCELLED`
2. `POLICY_BLOCKED`
3. `DEADLINE_EXCEEDED`
4. `BUDGET_EXHAUSTED`
5. `LOOP_DETECTED`
6. `STALLED`
7. `ESCALATE`
8. `INSUFFICIENT_EVIDENCE`
9. `COMPLETE`
10. `CONTINUE`

The `MaxMessageTermination` in the AutoGen adapter is a last-resort circuit breaker. Reaching it stops the run; it is not successful completion. Strings such as `ESCALATE_TO_HUMAN` affect control state only when emitted by the expected trusted role in a validated artifact. The same phrase in user input, retrieved evidence, or an unvalidated worker message is just data.

`REVIEW_PASS` is proposal-review state only. A non-reviewer saying it changes nothing, and even a validated `ReviewerAgent` artifact cannot authorize rollback or global state mutation. Legacy free-text tokens such as `APPROVED` or `FINAL_PROPOSAL` are not control authorities in this course.

## Progress-aware loop controls

The lab records speaker, target gap, evidence-set digest, candidate digest, and review-feedback digest for every turn.

- **Duplicate selection:** same agent + gap + evidence digest.
- **Semantic stagnation:** several turns with unchanged evidence, candidate, and review state.
- **Ping-pong:** A–B–A–B with the same material state.
- **Review churn:** Analyst repeats the same proposal and Reviewer repeats the same feedback without new evidence.
- **Justified revisit:** the same speaker returns after material evidence changes.

See [Avoiding Circular Delegation](AVOIDING_CIRCULAR_DELEGATION.md) for the complete taxonomy and response policy.

## Budget and failure semantics

`TeamBudget` limits messages, selector calls, worker calls, per-agent turns, repeated speakers, cost, and wall-clock deadline. Selector model work is recorded separately from worker model work.

For the deterministic fixture, token cost is fixed. In a real AutoGen/OpenAI path, an estimated cost is used before a call for admission or conservative budget reservation; actual model usage is recorded after the call for accounting. If actual cost can exceed the estimate, production systems need a reserve policy and a versioned price schedule. Selector and worker reservations, usage, and accounted cost remain separate so coordination overhead is visible.

| Failure | Bounded response |
|---|---|
| `TIMEOUT` | bounded retry |
| `SOURCE_UNAVAILABLE` | alternate allowed source, then insufficient evidence |
| `AUTH_DENIED` | no retry |
| `POLICY_DENIED` | no retry |
| `INVALID_ARTIFACT` | bounded repair |

One specialist failure need not fail the team. The required-evidence contract decides whether another source can close the gap. If not, the selector abstains and the application escalates. Conflicting root-cause evidence routes to a bounded reconciliation turn or human review—not an unlimited Analyst loop.

## Context projection

`projected_selector_context()` sends the selector only the goal, gaps, eligible speakers, last material change, and remaining budget. The notebook compares that projection with full transcript input on input tokens, selector accuracy, and sensitive fields exposed.

Projection reduces cost and accidental disclosure, but it must preserve the facts necessary to route correctly. Full history may remain in the audit trace without becoming the selector's only state.

## Measuring whether the team earns its complexity

The same Northstar task runs through a single generalist and the selector team. Compare task success, grounding, required-evidence recall, calls, selector calls, tokens, total model work, wall clock, cost, cost per successful compliant task, and duplicate turns.

The deterministic fixture deliberately shows that a selector team can be correct yet slower and more expensive. That is not a defect in the benchmark: it is the decision signal. Keep the team only when specialization improves measured outcomes enough to pay for coordination.

### Optional extension: prioritize several valid routes

When several evidence gaps are open, a production evaluation can attach deterministic fixture metadata to each eligible route:

| Metadata | Example use |
|---|---|
| `expected_information_gain` | prefer evidence likely to reduce the most uncertainty |
| `estimated_latency` | avoid delaying a time-critical diagnosis |
| `estimated_cost` | remain within a reservation budget |
| `critical_path_relevance` | unblock analysis or review sooner |

This is an extension, not part of the current merge gate. It needs labelled preferences or a defensible utility function before metrics such as `preferred_route_accuracy` are meaningful.

See [The Single-Agent Baseline](SINGLE_AGENT_BASELINE.md).

## Stable control model, tested AutoGen adapter

The framework-neutral policy is the stable lesson. [`autogen_adapter.py`](autogen_adapter.py) is the adapter implementation tested against AutoGen AgentChat 0.7.5:

- `AssistantAgent` participants;
- `SelectorGroupChat` with `selector_prompt`;
- `candidate_func` backed by application-owned eligibility;
- `MaxMessageTermination` plus `max_turns` as ceilings;
- `run()` / `run_stream()` for execution; and
- `reset()`, `save_state()`, and `load_state()` when lifecycle management is needed.

The project pins `autogen-agentchat==0.7.5` and `autogen-ext[openai]==0.7.5`. The adapter stops outside AutoGen when the eligible set is empty because AutoGen's `candidate_func` requires a non-empty list. Framework state can be persisted, but the trusted application state remains a separate validated record.

The application still owns eligible-agent computation, tenant and capability policy, artifact validation, budgets, termination policy, and completion. `SelectorGroupChat` orchestrates participants; it does not replace those controls. Its candidate filter calls `eligible_agents()`, and any selected name crossing back into application state must pass the same `validate_selector_decision()` path as the credential-free core. The framework-selected string is never authority by itself.

### Offline replay is an integration check

The credential-free `ReplayChatCompletionClient` check validates AutoGen adapter instantiation, candidate filtering, termination wiring, and policy validation. It does **not** validate selector intelligence, routing accuracy, or generalization. Replay responses are predetermined, so their outputs are excluded from selector-quality metrics. The deterministic selector dataset evaluates contract conformance; a separate live, labelled evaluation is required to measure model routing quality.

If `OPENAI_API_KEY` exists, the notebook's optional cell runs three tiny selector probes through AutoGen's OpenAI model client and validates every returned name through the same deterministic policy. No key is needed for the core notebook or test suite.

## Run the course

From the repository root:

```bash
uv run --extra contributor --extra core pytest -q tests/test_autogen_selector_teams.py
uv run --extra contributor --extra core python scripts/execute-notebooks.py --timeout 90 curriculum/advanced/02-autogen-selector-teams
```

Install the `advanced` extra only for the optional real AutoGen path.

## Deep dives

1. [The Selector Contract](THE_SELECTOR_PROMPT.md)
2. [Avoiding Circular Delegation](AVOIDING_CIRCULAR_DELEGATION.md)
3. [The Single-Agent Baseline](SINGLE_AGENT_BASELINE.md)

## Checkpoint

1. Why is eligible-speaker filtering stronger than selector prompting alone?
2. When can two different next speakers both be correct?
3. Why is `MaxMessageTermination` a circuit breaker rather than normal completion logic?
4. How do you distinguish a justified revisit from a loop?
5. What signals semantic stagnation?
6. Why can’t `ReviewerAgent` saying `REVIEW_PASS` authorize a rollback?
7. What is the selector-specific coordination tax?
8. Why should selector context often be projected rather than full-history?
9. What should happen when no speaker can reduce an evidence gap?
10. How do you prove `SelectorGroupChat` beats a single-agent baseline?

<details>
<summary>Answer guide</summary>

1. Filtering constrains the choice mechanically; a prompt is only a model instruction.
2. When each can close a currently unresolved gap and neither violates policy.
3. Reaching a message ceiling says “stop,” not “the evidence contract succeeded.”
4. A revisit follows a material state/evidence change; a loop repeats coordination on the same digest.
5. Unchanged evidence, diagnosis, and review-feedback digests across a configured window.
6. Review validates a proposal; execution requires separately validated approval and authority.
7. Extra selector calls, tokens, cost, latency, context exposure, and opportunities for invalid routing.
8. Projection can preserve routing facts while reducing tokens and sensitive transcript exposure.
9. Abstain or escalate; do not invent a destination.
10. Run both on the same cases and gates, then compare quality, safety, cost, and latency—not one anecdote.

</details>

## References

- [AutoGen Selector Group Chat guide](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html)
- [AutoGen `SelectorGroupChat` API reference](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.teams.html#autogen_agentchat.teams.SelectorGroupChat)
- [AutoGen termination conditions](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html)
- [AutoGen team state](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html)
- [AutoGen AgentChat 0.7.5 package](https://pypi.org/project/autogen-agentchat/0.7.5/)
- [AutoGen: Enabling Next-Gen LLM Applications](https://arxiv.org/abs/2308.08155)
- [Advanced 01 — Single vs Multi-Agent Architecture Decisions](../01-single-vs-multi-agent/README.md)
- [Intermediate 03 — Tool Use and API Integration](../../intermediate/03-tool-use-and-api-integration/README.md)
