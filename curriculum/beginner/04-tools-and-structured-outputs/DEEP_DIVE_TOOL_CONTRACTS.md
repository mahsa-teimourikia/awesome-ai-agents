# Deep Dive: Tool Contract Design

A tool provided to an LLM is a contract between the Model and the Application. Just like REST APIs, tools must be designed with explicit boundaries, clear semantics, and robust security.

## 1. Capability-Oriented APIs

Prefer narrow business capabilities over generic execution tools. 

**Bad:** `manage_order(order_id, action, data)`
**Good:** `get_order(order_id)` and `issue_refund(order_id, amount_cents)`

Narrow tools are easier for the model to understand, easier to type-check, and infinitely easier to authorize. 

## 2. Naming and Descriptions

The model relies entirely on the name and description to understand when to use a tool.

- **Naming:** Be specific, concise, and stable. `get_order` is better than `get_data` (too vague) and `fetch_customer_order_history_by_identifier_v2` (unnecessarily verbose).
- **Descriptions:** Use the description to carry rich instructions. Explain what the tool does, when to use it, when *not* to use it, and constraints on the parameters.

## 3. Argument and Return Schemas

- **Arguments:** Use strict types. Do not use `float` for currency; use `int` for minor units (e.g. cents) or `Decimal`. Use Enums for restricted choices (e.g., `RefundReason`). Use `ConfigDict(extra="forbid")` to reject hallucinated parameters.
- **Returns:** Return structured data (Pydantic models) rather than arbitrary strings. Structured results reduce ambiguity, are easier to test, and reduce model interpretation errors.

## 4. Effect Classification

Categorize tools by their side effects:
- **Read-Only:** Safe to execute (e.g. `get_order`).
- **Reversible Write:** Modifies state but can be easily undone (e.g. `update_ticket_tag`).
- **Consequential Write:** High-risk actions (e.g. `issue_refund`). These require idempotent design and often a deterministic human approval gate.

## 5. Authorization Boundaries

The model is fundamentally untrusted. It can propose an action, but it cannot authorize it.
Do not pass `user_id`, `tenant_id`, or `roles` as arguments for the model to generate. These must be injected directly by the application through an `ExecutionContext` when executing the tool.

## 6. Error Contracts

Normalize errors. Do not return raw stack traces or SQL exceptions to the model. Return clean, structured error codes: `{"error_code": "INVALID_AMOUNT", "message": "Refund exceeds order total."}`.

## 7. Versioning and Idempotency

Tool schemas are API contracts. Changing `amount: float` to `amount_cents: int` will break model behavior if not coordinated.

For write tools, always implement idempotency keys so that if the model accidentally calls `issue_refund` twice for the same logical request, the application only processes it once.
