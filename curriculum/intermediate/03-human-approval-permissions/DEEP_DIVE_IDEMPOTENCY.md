# Deep Dive: Idempotency in Agentic Tooling

In distributed systems, networks fail. APIs time out. Servers restart. 

If an agent is executing a read-only query (`get_weather()`) and the network drops, the orchestration framework can simply retry the tool call. No harm done.

But if the agent is executing a mutative, consequential action (`rollback_deployment()`) and the HTTP response times out, the agent is left in a blind state. **Did the rollback execute, or did it fail before reaching the server?** 

If the orchestration framework retries blindly, the execution might occur twice, potentially causing catastrophic system states.

---

## 1. The SOTA Solution: Application-Owned Idempotency

An operation is **idempotent** if performing it multiple times yields the exact same result as performing it once. 

To achieve this in agentic workflows, we use **Idempotency Keys**.

### The Anti-Pattern: LLM-Generated Keys
Do **not** trust the LLM to generate the idempotency key (e.g. `generate a UUID for this action`).
1. The LLM might hallucinate a completely new UUID upon a retry, bypassing the idempotency check entirely.
2. The LLM might reuse a UUID for a completely different action.

### The SOTA Pattern: Deterministic Application Derivation
The application should derive the idempotency key logically from the exact, digest-bound intent.

```python
# The application computes this, not the LLM
idempotency_key = f"cmd_{tenant_id}_{payload.digest}"
```

Because the `digest` covers the exact region, service, evidence, and risk tier, any retry of the *exact same approved payload* yields the exact same idempotency key. Any modification yields a new key, forcing re-approval.

---

## 2. The Execution Flow

1. **Agent Reasoning:** The LLM proposes a rollback and the UI captures human approval for the exact digest.
2. **Key Derivation:** The policy engine validates the approval and derives the key `cmd_acme_a1b2c3d4`.
3. **Backend Execution (First Try):** The execution engine checks the database. Has it seen this key? No. It executes the rollback, saves the key, and begins to return a 200 OK.
4. **Network Failure:** The wifi drops. The orchestration framework receives a timeout error.
5. **Agent Retry:** The framework automatically retries the execution.
6. **Backend Execution (Second Try):** The execution engine checks the database. Has it seen `cmd_acme_a1b2c3d4`? **Yes.** It verifies the digest matches the original record, skips the execution, and immediately returns a successful "Already Executed" receipt.

## 3. Duplicate Payload Conflicts

If the execution engine detects that the `idempotency_key` matches an existing record, but the `action_digest` is different, this indicates a severe conflict (e.g., an attacker trying to reuse an approved key for a malicious payload, or a race condition). The system must hard-reject the execution as a `CONFLICT`.
