# Deep Dive: Structured Outputs vs Tool Calling

It is critical to distinguish between generating structured data and executing tools.

## 1. Structured Outputs

Structured Output is when you force the LLM to reply with a JSON payload that perfectly matches a specific schema, rather than free-text.

**Mechanism:** The model output is strictly constrained to the schema structure.
**Use Case:** Information extraction, text classification, data formatting.
**Action:** No external action is taken. The application simply consumes the generated data.

*Example:* A model reads a customer email and outputs:
```json
{
  "category": "refund",
  "urgency": "high"
}
```

## 2. Tool Calling (Function Calling)

Tool Calling is a multi-step orchestration process where the model requests the application to perform an action, and waits for the result before continuing.

**Mechanism:** 
1. Model proposes a tool call (JSON payload).
2. Application halts generation, validates the payload, and executes the external function.
3. Application appends the function result to the chat history.
4. Model reads the result and continues generation.

**Use Case:** Fetching live data, modifying external state, triggering workflows.
**Action:** An external function is executed by the application.

## 3. When to use which?

- Do you just need to parse the user's intent into a predictable object for your downstream code? -> **Structured Output**.
- Do you need the model to pause, look up an order in a database, and then tell the user about it? -> **Tool Calling**.

## 4. Semantic Correctness

Neither feature guarantees semantic correctness!
- **Structured Outputs** guarantees the payload is valid JSON and matches the shape of your schema, but it does *not* guarantee that the extracted data is factually true.
- **Tool Calling** guarantees the proposed arguments match your schema, but it does *not* mean the request is business-valid or authorized. Both require application-side validation.
