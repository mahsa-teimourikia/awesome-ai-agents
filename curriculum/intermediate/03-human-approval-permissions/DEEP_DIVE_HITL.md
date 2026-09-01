# Deep Dive: Human-in-the-Loop (HITL) Architectures

Consequential actions—such as modifying production infrastructure, executing financial transactions, or sending mass communications—often require a **Human-in-the-Loop (HITL)** depending on strict, risk-based policies.

However, LLMs and HTTP requests are synchronous. You cannot block an HTTP thread for 3 days while waiting for an Incident Commander to approve a rollback.

---

## 1. The Asynchronous Pause (e.g., LangGraph)

State-of-the-Art (SOTA) HITL requires a persistent state machine for durable orchestration.

1. **The Plan:** The agent analyzes evidence and proposes a business intent (e.g., `RollbackProposal`).
2. **The Interrupt:** The orchestration graph (e.g., LangGraph) hits a breakpoint using `interrupt(review_payload)`.
3. **The Sleep:** The state is serialized and saved to a checkpointer (e.g., Postgres, Redis). The Python process gracefully terminates. Zero compute is wasted while waiting.
4. **The Wake:** Days later, a reviewer makes a decision on a dashboard. The dashboard invokes the graph with `Command(resume=ApprovalDecision)`, waking the exact paused state.

---

## 2. Orchestration != Authorization

A critical enterprise mistake is assuming the orchestration framework handles security. 

**LangGraph's `interrupt()` is a durable pause/resume mechanism, not an authorization barrier.** If your graph does this:

```python
# ❌ INSECURE: Do not do this.
decision = interrupt(payload)
if decision == "approve":
    execute(payload)
```

You are vulnerable to a compromised UI, session hijacking, or spoofed `resume` commands. 

**The SOTA Pattern:** 
1. The orchestration framework provides the durable pause.
2. The application's deterministic **Policy Engine** intercepts the resume.
3. The engine verifies the identity of the resume caller, checks their roles against the risk tier, validates the expiration, and verifies the digest of the payload.

```python
# ✅ SECURE: Deterministic re-validation
decision = interrupt(payload)

# The deterministic application layer strictly validates the session and digest
# before generating the execution command.
command = validate_approval(payload, decision, reviewer_session)
execute(command)
```

## 3. Digest-Bound Approvals

A human does not approve a "vague intent to rollback". They approve an exact, immutable state.

If a reviewer modifies a proposal (e.g., changing the target region from `eu-west` to `global`), the application must treat this as a **completely new proposal**. The SHA-256 digest of the payload changes, invalidating previous approvals and forcing the policy engine to re-evaluate risk and required roles.

This ensures a reviewer cannot approve a low-risk action and subsequently edit it into a critical-risk action before execution.
