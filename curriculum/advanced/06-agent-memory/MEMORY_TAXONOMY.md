# Deep Dive — Memory Taxonomy and Authority

Taxonomy helps us reason about purpose and lifecycle. It does not determine a
storage engine, a trust level, or an authorization decision.

## Working state is not the model context

An agent's working state can contain its plan, tool receipts, temporary
artifacts, cache entries, checkpoint metadata, and scratch notes. A context
projection selects the small, safe subset required for one model call. Sending
all working state risks leaking secrets and exhausting the context window.

Task completion normally evicts working state from the active execution path.
Separate retention rules may preserve selected trace or audit artifacts. Thus:

```text
working-context eviction ≠ source-record deletion
```

## Episodic memory is not an audit log

An episode is a selected representation of prior experience that may inform a
future task. A raw transcript is source material. An audit log is an immutable
operational or compliance record. A system may link all three, but it should not
silently turn every transcript into memory or prune compliance records merely
because an episode was consolidated.

## Semantic does not mean verified

Semantic memory is structured durable knowledge: for example, a communication
preference, account tier, or project association. Each item still needs a
verification status such as `USER_STATED`, `VERIFIED`, `INFERRED`, or `DISPUTED`.
An arbitrary decimal such as `confidence=0.95` is misleading unless it is
calibrated on representative data; this course uses evidence-backed labels.

## Procedures do not create policy

Procedural memory describes how to perform a skill. It should carry an ID,
version, source, approval record, and effective time. An agent may propose a
change, but a controlled test/review/release pipeline promotes it. A procedure
that says “refund every angry customer” cannot grant refund authority or expand
tool permissions.

## Preferences are constrained semantic memory

An explicit request for concise replies is useful and low risk. “I am an
administrator” is not a preference and cannot become authorization state.
Identity, entitlements, credentials, approvals, and tool capabilities always
come from live trusted control planes.

## Memory, RAG, and current truth

RAG retrieves external source content. Memory persists selected state about
prior interactions, entities, or tasks. They overlap—both may use embeddings or
graphs—but they have different governance and lifecycle concerns. Neither is
automatically current truth. For a current account tier, payment state, or
production condition, consult the authoritative live system.

## Schema and representation evolution

Durable memory schemas change. A scalar `preferred_language` may become a list;
a new embedding model may make old vectors incomparable. Store schema, policy,
embedding-model, and index versions. Migrations should be replayable, monitored,
and reversible, with old records retained according to policy.
