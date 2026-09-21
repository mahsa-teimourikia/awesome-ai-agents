# Evidence-bound evaluator agents

A static judge can assess explanation quality, but text alone cannot prove a refund, deployment, approval, or tenant boundary. An evaluator agent may actively collect evidence, yet it remains a fallible component inside deterministic controls—not the end of the trust chain.

## Least-privilege verification

Use narrow, typed reads such as:

```text
get_deployment(service_id, tenant_id)
get_incident_metrics(service_id, window, tenant_id)
get_refund_status(operation_id, tenant_id)
```

Avoid arbitrary SQL or generic production credentials. The evaluator's role name grants no authority. An application-owned registry must authorize each tool by capability and effect class, enforce tenant and resource scope, and reject writes or external side effects.

The evaluator identity must differ from the primary agent identity. This reduces self-attestation risk but does not by itself make the evaluator trustworthy.

## Evidence contracts

Each `EvidenceRecord` includes:

```text
evidence_id, evidence_type, source, tenant_id
observed_at, retrieved_at, source_version
digest, authority, supported_criteria, operation_id
```

A verdict cites evidence IDs. Before accepting it, the application verifies:

- the evidence exists in the trusted snapshot;
- source authority is sufficient for the criterion;
- tenant and scope match the evaluation case;
- the observation is fresh enough;
- observation and retrieval timestamps are not materially in the future;
- post-action claims use post-action observations; and
- consequential claims bind to the expected operation or provider receipt.

The application sorts the accepted evidence records and recomputes a canonical digest over their IDs, content digests, provenance, tenant, timestamps, authority, and bindings. Both request and verdict must match that computed value. Repeating the same unverified snapshot label is not integrity protection.

A database read or API response is independent evidence whose strength depends on provenance and integrity. It is not “cryptographic proof” unless an actual signature, attestation, or digest-verification mechanism supplies that property.

## Three claims, not one

Keep these separate:

1. **Action executed:** an exact operation receipt or audit event matches the proposed action.
2. **Desired state observed:** a fresh authoritative observation shows the target state.
3. **Causal attribution supported:** the evidence design supports that the evaluated action caused the outcome.

Healthy metrics after a rollback do not automatically prove that rollback caused recovery. Another operator, retry, or external event may explain the state.

## Bounded active evaluation

Active verification can become another autonomous loop. Bound model calls, tool calls, elapsed time, and cost. Check deadline/cancellation before every next call. Stop when the required evidence is collected, or when the budget ends, evidence is unavailable, or conflicts remain.

Return `INSUFFICIENT_EVIDENCE` or `ABSTAIN`; do not guess. A judge result can also be `INVALID_EVALUATION` when its schema, version bindings, evidence references, or hard-gate logic fail validation.

## Layered flow

```text
1. deterministic checks
   schema • tenant • tool policy • approval • receipt
2. evidence collection
   typed reads • provenance • freshness • operation binding
3. semantic judgment
   relevance • explanation quality • uncertainty handling
4. deterministic verdict validation
   selected judge/settings • complete criteria • recomputed snapshot • trusted hard gates
5. application aggregation
   risk policy • human review • shadow/canary/blocking mode
```

The evaluator can query the wrong data, misread a record, or hallucinate a conclusion. Tests around evidence selection and verdict validation are therefore mandatory. A model's `PASS` is a proposal to policy, never authorization to mutate state or release production.
