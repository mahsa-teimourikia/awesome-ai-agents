# Deep Dive: Dynamic Context Windows

In early Agent architectures, the agent's "Memory" was just a single, ever-growing array of `messages`. Every user prompt, every tool call, every JSON API response, and every LLM thought was appended to the end of the array.

This approach scales poorly in production due to three reasons:
1. **Cost:** LLM APIs charge per token. If step 10 of a trajectory sends the entire history of steps 1-9 to the API, you are paying roughly quadratic costs under simple ever-growing-history assumptions.
2. **Latency:** Processing 30,000 tokens of context takes significantly longer than processing 500 tokens.
3. **"Lost in the Middle":** Research shows that LLMs suffer from severe recall degradation when context windows get too large. 

---

## 1. Context Compaction, Routing, and Phase-Scoped Views

Modern architectures do not use a single, monolithic chat history. Instead, they dynamically build a **ContextPacket** representing only the data necessary for the *current phase* of the task.

### The Phased Context Architecture

Imagine an incident response agent tasked with debugging a checkout issue.

1. **Phase 1: TRIAGE** 
   - *Needs:* The user's original request, system policy, current task state.
   - *Doesn't Need:* Raw server logs, full retrieved runbooks, or deep technical chat history.
   - *Action:* Understands the issue and sets the plan.

2. **Phase 2: INVESTIGATE**
   - *Needs:* Strict tool evidence (e.g., the 500-line server log), a highly-relevant runbook excerpt.
   - *Doesn't Need:* The user's original request or old conversational pleasantries.
   - *Action:* Synthesizes the log against the runbook to find the root cause.

3. **Phase 3: RECOMMEND**
   - *Needs:* Verified evidence, policy/risk constraints, approval state.
   - *Doesn't Need:* Unverified raw payloads.
   - *Action:* Recommends an actionable fix.

4. **Phase 4: RESUME**
   - *Needs:* Structured checkpoint, unresolved questions, and evidence handles.
   - *Doesn't Need:* The entire historic transcript.
   - *Action:* Picks up where a previous session left off.

By defining explicit `ContextRequest` budgets and phase rules, you ensure the LLM only ever sees the exact tokens it needs.

---

## 2. Advanced Techniques

### Pruning
Pruning removes stale or off-task content (e.g., older conversation turns) to keep the context window focused on the active problem, ensuring strict token budgets are met.

### Structured Summaries & Checkpointing
Instead of relying on the LLM to randomly "summarize the conversation," use a rigorous schema to compress context. A structured summary preserves invariants like constraints, required evidence IDs, and approval states, without the overhead of verbatim conversation history.

### JIT (Just-in-Time) Retrieval
Rather than loading all external memory into the prompt, rely on JIT retrieval. Bring in memory and documents only when relevance scoring and Phase constraints demand it.

### External Memory
Distinguish between the active context window and long-term external memory. The context window is finite and immediate. External memory must be persisted safely (respecting tenant scopes) and retrieved only via deliberate action.

---

## 3. Implementation: The Context Pipeline

To safely assemble these dynamic context windows, you must build a deterministic pipeline that runs *before* prompt assembly:

1. **Tenant Authorization:** Is this piece of evidence owned by the current tenant? (e.g., drop `Globex` logs from an `Acme` incident).
2. **Trust boundaries:** Is the document poisoned or quarantined by a security scanner? 
3. **Freshness:** Has this metric expired?
4. **Phase Relevance:** Does the current phase actually require raw tool evidence?
5. **Token Budgeting:** Rank the remaining items by composite score and drop anything that exceeds the current phase's token limit.

This deterministic pipeline ensures that context building is secure, auditable, and decoupled from the actual LLM string manipulation.
