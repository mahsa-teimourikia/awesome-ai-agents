# Deep Dive: Runtime Policy Enforcement

If Application-Layer guardrails (like NeMo) protect the *Agent*, Runtime Policy Engines protect the *Infrastructure*.

When an agent decides to call a tool (e.g., `execute_sql(query="DROP TABLE users")`), that request must be intercepted and validated *before* the tool executes. 

## Why Pydantic is Not Enough

Developers often use tools like Pydantic or JSONSchema to validate LLM outputs. 
- Pydantic can guarantee that `user_id` is a string.
- Pydantic **cannot** guarantee that the Agent is *authorized* to query that specific `user_id` at 3:00 AM from a restricted IP address.

Pydantic validates **shape**. We need to validate **policy**.

## Open Policy Agent (OPA) and Rego

[Open Policy Agent (OPA)](https://www.openpolicyagent.org/) is the industry standard for decoupling policy from code. It uses a declarative language called **Rego**.

### How it Works in an Agent Architecture
1. The LLM generates a tool call: `query_billing(tenant_id="AcmeCorp")`.
2. The Orchestration framework intercepts the call. It packages the tool arguments, the Agent's identity, and the current context into a JSON payload.
3. The framework sends this JSON to the OPA server.
4. OPA evaluates the JSON against its Rego policies.
5. OPA returns `{"allow": true}` or `{"allow": false, "reason": "Cross-tenant access denied"}`.

### Example Rego Policy

This Rego policy ensures an agent can only query data for the tenant it was assigned to at the start of the session:

```rego
package agent.tool_execution

default allow = false

# Allow the tool execution ONLY if the requested tenant matches the agent's assigned tenant
allow {
    input.tool_name == "query_billing"
    input.requested_tenant == input.agent_session_tenant
}
```

If a hijacked agent attempts to query `Globex` while assigned to `AcmeCorp`, OPA rejects it instantly. The LLM cannot talk its way out of a Rego evaluation.

## Circuit Breakers and Budgets

Runtime Policy Engines also enforce operational limits:
- **Action Budgets:** An agent might get caught in an infinite loop, calling an expensive API 10,000 times. A runtime policy can track state in Redis and enforce a rule: *Maximum 5 tool calls per session*.
- **Idempotency:** If an agent attempts to call `charge_credit_card(amount=50)` twice because it hallucinated a failure, the runtime gateway must detect the identical idempotency key and return the cached success response rather than charging the user twice.
