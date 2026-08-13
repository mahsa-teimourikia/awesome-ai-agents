# Deep Dive: Control Planes and Escalation

No matter how advanced an LLM is, **an LLM cannot guarantee idempotency or a safe database commit.**

If you give an agent a tool called `refund_customer(amount: int)`, and the LLM experiences a retry-loop due to a network timeout, it might call `refund_customer(50)` three times in a row, refunding the customer $150.

Reliability belongs to the application layer surrounding the LLM, not the LLM itself.

## Application-Layer Safety Wrappers

### 1. Enforcing Idempotency
Never expose raw destructive tools to an agent. Always wrap them in an application layer that enforces an **Idempotency Key**.

When the agent decides to issue a refund, the tool wrapper generates a hash based on the `ticket_id`. If the agent loops and calls the tool again, the application layer sees the same hash, intercepts the call, and returns: *"Refund already processed."*

### 2. Validating Tool Arguments
If a tool expects an integer (e.g., `refund_customer(amount: int)`), and the agent hallucinates a string (`refund_customer(amount: "fifty bucks")`), the application layer must catch the type error and return a strict, typed error message to the agent so it can self-correct. Do not let the raw error crash the system.

### 3. Escalation as a First-Class Citizen
Agents are trained to be helpful, which means they will often guess or hallucinate rather than admit they are stuck.

You must explicitly design your system to allow the agent to "give up." 
- Give the agent an `escalate_to_human(reason: str)` tool.
- Tell the agent in the system prompt: *"If you do not have enough evidence to proceed, you MUST use the escalate tool. Guessing is a critical failure."*
