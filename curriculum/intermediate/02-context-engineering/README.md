# 02 — Context Engineering for Agents

**Level:** Intermediate · **Primary notebook:** **Notebook:** [`02_context_engineering.ipynb`](02_context_engineering.ipynb) 

**Scenario:** Northstar, a SaaS support team, is integrating this concept into their agentic workflow.

An agent is only as capable as the information available at the instant it chooses its next action. Context engineering is the system discipline of selecting, structuring, refreshing, compressing, and isolating that information. It is broader than prompt writing: system instructions, conversation, task state, tool results, retrieved documents, user-scoped memory, and metadata all compete for a finite attention budget.

This module uses a Northstar Commerce incident assistant. It must investigate EU checkout payment failures for **Acme** without leaking another tenant’s data, treating a poisoned runbook as untrusted, or drowning the model in old chat history. The default lab is deterministic and needs no provider credentials.

## Outcomes

You will be able to:

1. Design a context contract around the smallest high-signal information set for one decision.
2. Separate system instructions, dynamic context, tool context, environment state, conversation state, and external memory.
3. Route context just in time by task phase, tenant, source trust, relevance, freshness, and token budget.
4. Compress and prune context without losing decisions, evidence provenance, constraints, or unresolved questions.
5. Cache safe context artifacts with keys that include identity, task, policy, and source version.
6. Defend against context poisoning, stale state, cross-tenant leakage, and long-window distraction.

## Why context engineering matters

The model does not “see the whole application.” It sees the token packet constructed for this turn. A stronger model can still make a weak decision if it receives an irrelevant transcript, stale tool result, wrong tenant’s data, or a document that tries to manipulate its behavior. A larger context window is capacity—not automatic relevance, truth, authorization, or memory.

![Diagram](https://kroki.io/mermaid/svg/eNpVUMtOAzEMvPMVvsOWP0CiLfQB4kDpKeohZF0aNWsvjndLhfh33GyRSi6O7JnxjLeJD2HnReH59Qrs3bt1RoEP9gmuIdZIGvW4gaq6g7GbMCl-KQh3irIpjIlbHbNiAy2nGP6gZTQ9EXqU7DUymR5SH4WpMVXI6hUv0Q_uTTpTqkGZUwZPNQiqROx9ugQ-ulXg1nBmBYXMaYMNy7_V4_KffRfJG1AkT1a3gnlHmLO1eI8EYYdhn38KZ1Y4c7dqfDJNrjFBOCdufdijDonnBbdwUwwxn4LdFsfQCreczWtBLQpq6V7wAPxuR-3LFYbh8sLqk1uTnpOzQBDOuRoMD-tJLdkIPjsv1ouEMDpl-wU6Mov9)

## 1. Context anatomy

| Component | What it is | Example in the scenario | Rule |
| --- | --- | --- | --- |
| System instructions | stable behavioral contract | evidence-first, no remediation, document trust boundary | developer/application owned; never overridden by retrieved text |
| Dynamic context | data chosen for this decision | current incident phase and EU symptoms | route at runtime; expire quickly |
| Tool context | result of a bounded call | payment authorization error count | schema/freshness/provenance required |
| Environment state | task machine state | `phase=investigate`, budget, approvals | application owned and versioned |
| Conversation state | relevant thread turns | user report and confirmed constraints | prune stale/off-topic messages |
| External memory | persisted facts across threads | Acme premium SLA | namespace by tenant/user; validate and revoke |
| Retrieved documents | evidence, not instructions | payments runbook | untrusted by default; quote/cite, do not execute |

**Context windows vs external memory:** the context window is the finite prompt sent on this inference. External memory is data stored outside it. Memory becomes useful only after selection, authorization, freshness, and a purposeful retrieval policy. Do not dump all memory into every turn.

## 2. System instructions and tool context

System instructions should be clear, stable, and minimal enough to remain useful. They specify role, evidence standard, boundaries, tool-use rules, output contract, and escalation/stop behavior. They should not become a giant rules dump; move deterministic logic (authorization, math, tenant filtering, retries, billing limits) into code.

Tool context is part of the prompt surface. Good tool results are small, typed, attributable, and decision-oriented:

```json
{
  "source_id": "health-1",
  "observed_at": "2026-08-10T08:44:00Z",
  "tenant": "acme",
  "metric": "payment_authorization_errors",
  "region": "EU",
  "value": 47,
  "trust": "trusted"
}
```

Do not return a 40-page raw log to the model when a compact aggregate plus an opaque evidence handle can answer the current question. Retain the raw artifact outside the prompt for audit and targeted follow-up.

## 3. Dynamic routing and just-in-time context

An agent’s phase changes what it needs:

| Phase | Include now | Defer |
| --- | --- | --- |
| Triage | user goal, identity, current constraints, small thread summary | broad logs/runbooks/history |
| Investigate | fresh service/tool evidence, relevant runbook excerpt, task state | unrelated tenant data and old chat |
| Recommend | verified evidence, policy, risk/approval state, required output schema | raw intermediate tool payloads |
| Resume | compact checkpoint, current plan, unresolved gaps, source handles | entire historic transcript |

This is **just-in-time context**: keep lightweight identifiers and retrieve only what the next decision needs. It reduces token cost and stale information but adds runtime retrieval risk, so use source metadata, bounded tools, result validation, and fallbacks. A practical hybrid loads a small stable “starter pack” (policy + task + identity) then requests evidence progressively.

## 4. Compression, pruning, summarization, and caching

These techniques solve different problems:

| Technique | Keep | Drop | Main risk |
| --- | --- | --- | --- |
| Pruning | recent/relevant turns | stale, off-task content | discarding a hidden dependency |
| Summarization | meaning in a compact narrative | verbatim details | unsupported or lossy summary |
| Structured compression | decisions, evidence IDs, constraints, open questions | redundant tool payloads | schema misses an important field |
| Caching | stable, safe context artifact | repeat construction | using data under the wrong tenant/policy/version |

The lab uses a structured summary with a decision, evidence IDs, current state, scoped memory, and an open gap. This is safer than “summarize the conversation” because a reviewer can evaluate its required fields. Cache keys must include tenant/user scope, task/phase, policy version, source versions, and—where relevant—model/prompt version. Never share a cached packet across tenants just because its text looks similar.

## 5. Context isolation and poisoning

**Isolation** is an access-control property. Route only items whose tenant/user namespace and authorization match the request. State, conversation, tool results, and memory should each carry a scope; filtering after prompt assembly is too late.

**Poisoning** occurs when untrusted content attempts to change the agent’s behavior: a retrieved runbook says “ignore policy,” a web page asks for secrets, an old summary embeds malicious instructions, or a tool result includes attacker-controlled text. Treat external content as data with provenance and delimiters; never allow it to author system instructions, tool permissions, or approval decisions. Use input/document scanning as a signal, but rely on deterministic trust/authorization boundaries rather than a classifier alone.

The lab quarantines an Acme document containing an instruction injection and drops a high-relevance Globex document before it reaches the context packet. This illustrates a crucial point: relevance does not override isolation or trust.

## 6. Guided lab

1. Open `02_context_engineering.ipynb`. Inspect the selected items, token estimate, dropped items, quarantine list, cache key, and structured summary.
2. Compare `triage` and `investigate` requests. Why should raw tool/document evidence appear only in the latter?
3. Add a huge old conversation turn. Confirm it is pruned under the budget rather than displacing current incident state.
4. Add a trusted but stale source. Extend the routing policy with freshness and show how the packet changes.
5. Change the request tenant to `globex`. Confirm Acme data and cache keys never cross the namespace.
6. Replace the deterministic router with model-assisted selection only after preserving hard tenant/trust filters, budgets, schema validation, traceability, and a safe fallback.

## Production checklist

- [ ] Treat context construction as a versioned, tested component—not string concatenation.
- [ ] Separate stable system policy from untrusted documents and tool outputs.
- [ ] Attach tenant/user scope, provenance, freshness, sensitivity, and version metadata to every context item.
- [ ] Select the minimal sufficient context per phase; enforce a token budget before model invocation.
- [ ] Preserve decisions, evidence IDs, constraints, open questions, and stop state during compression.
- [ ] Include scope/policy/source versions in cache keys; expire/revalidate sensitive caches.
- [ ] Keep raw artifacts outside the context window and cite evidence handles in outputs.
- [ ] Evaluate retrieval/context selection, cross-tenant blocking, poison quarantine, summary recall, cache isolation, token cost, and outcome quality.

## Exercises

1. Add an `approval` state item and prove a recommendation cannot claim permission without it.
2. Implement a freshness score and compare relevance-only routing with relevance-plus-freshness routing.
3. Add a document that is highly relevant but from an unauthorized project; write an assertion that it is excluded.
4. Design a summary schema for a 100-turn incident investigation; which fields cannot be compressed away?
5. Compare “full transcript,” “recent messages,” “structured summary + just-in-time evidence,” and “external memory only” on accuracy, latency, cost, and failure modes.

## Watch For

- **Assumption failure:** The model hallucinates an unsupported parameter.
- **State leak:** Context is incorrectly preserved across runs.
- **Timeout:** The tool takes too long and the agent loops.
- **Auth bypass:** The agent attempts an action it shouldn't.

## Checkpoint

**1. What is the primary purpose of this module?**
- A) To understand the core concept.
- B) To write complex boilerplate.
- C) To ignore system errors.
- D) To bypass security.

**2. How do we mitigate the primary failure mode?**
- A) Retries.
- B) Human approval.
- C) Logging.
- D) Idempotency keys.

## References

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — context as a finite resource, just-in-time retrieval, compaction, and long-horizon strategies.
- [LangGraph memory overview](https://docs.langchain.com/oss/python/concepts/memory) — thread-scoped state versus long-term namespaced memory.
- [OpenAI context-engineering personalization cookbook](https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization) — state and memory considerations for agents.
- [A Survey on Large Language Model based Autonomous Agents](https://arxiv.org/abs/2308.11432) — agent components including planning, memory, and tool use.
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — prompt-injection risks and defenses.

## Deep Dives & State of the Art

- **[Dynamic Context & Vector DBs](DEEP_DIVE_DYNAMIC_CONTEXT.md)**
- **[Prompt Injection & XML Tagging](DEEP_DIVE_PROMPT_INJECTION.md)**


## SOTA Deep Dives
Explore industry-standard architectural patterns and enterprise implementation details:

- [Dynamic Context](DEEP_DIVE_DYNAMIC_CONTEXT.md)
- [Prompt Injection](DEEP_DIVE_PROMPT_INJECTION.md)
