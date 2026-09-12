# Deep Dive — Consolidation, Supersession, and Forgetting

Consolidation turns source events into candidate memories. It may run at a
conversation boundary, under token pressure, after an important event, on an
explicit correction, on a schedule, or after human review. “Every ten turns” is
only one implementation choice.

## A safe consolidation job

```text
selected sources
→ immutable source digest
→ typed candidate extraction
→ schema and provenance validation
→ optional verification or review
→ atomic durable write
```

Store a job ID, extractor version, policy version, source IDs, and source digest.
The job must be idempotent: replaying it after a timeout or process failure
must not duplicate a truth. If extraction succeeds but persistence fails, a
retry uses the same logical job identity.

The extractor can hallucinate. “I might switch to Go” must not become
`preferred_language=Go`; quoted third-party text, sarcasm, temporary state, and
malicious instructions require rejection or an ephemeral decision. A summary
cannot become more trusted than its least-trusted supporting source without an
independent verifier.

Admission itself is also replay-safe: the decision records the candidate digest
and policy version. The durable builder recomputes policy before persisting, so a
decision for candidate A cannot be attached to candidate B or to a mutated value.

## Supersession instead of overwrite

When an admissible value changes, close the prior record's valid-time interval
and write a new version in one transaction:

```text
v1: New York  ACTIVE      effective_to=2026-02-10
v2: London    ACTIVE      supersedes=v1
```

The old record remains available to authorized historical queries. `effective_*`
describes when the fact was true; `recorded_at` describes when the system learned
it. Optimistic `expected_version` rejects two concurrent writers that both read
the same prior version.

Conflicts are key-specific. Latest explicit user input may win for a preference.
An account API wins for billing data. A high-risk or equally authoritative
disagreement may require human review rather than silent selection.

## Forgetting is a policy decision

Different operations have different meanings:

- **Expiry:** stop retrieving a time-bounded fact after `expires_at`.
- **Supersession:** retain history but exclude the prior version from current use.
- **Dispute:** quarantine a challenged record while it is reviewed.
- **Soft deletion:** exclude content while retaining a governed record.
- **Hard deletion:** remove content and optionally retain a minimal tombstone.
- **Source invalidation:** revoke or reverify derived memories when provenance is
  deleted, corrected, or loses authority.
- **Legal hold/audit retention:** prevent deletion where policy requires it.

The schema, not the candidate, supplies mandatory expiry for session, short-term,
and time-bound records. Candidate expiry may shorten that lifetime but cannot
remove or extend the policy bound. Verification freshness is separate: dynamic
account facts can require a short-lived exact-source receipt even when the memory
record itself has a longer retention period.

Data minimization happens before storage: persist `communication_style=concise`,
not the full personal explanation, when the extra text is unnecessary. A memory
review interface should explain what is remembered, why, and from which safe
source handles, and should support correction, dispute, and deletion.
