# Deep Dive: Schema Contracts & Capability Boundaries

When an agent interacts with a tool, it isn't writing Python code. It is outputting a JSON string that is subsequently parsed by your orchestration framework and passed as arguments to a Python backend.

If the agent hallucinates a parameter name, provides a string instead of an integer, or injects unintended configuration data, the backend will either crash or worse, process an unsafe action.

To solve this, SOTA architectures enforce strict **Schema Contracts** between the Agent and the backend Capability.

---

## 1. Pydantic as the Universal Translator

**Pydantic** is the industry standard for defining Schema Contracts. When you define a Pydantic model, frameworks automatically translate it into a strict **JSON Schema** definition that is injected into the LLM's system prompt using `model_json_schema()`.

```python
# ✅ SOTA PATTERN: Explicit Pydantic Contracts
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class CreateUserInput(BaseModel):
    model_config = ConfigDict(extra="forbid") # Crucial for security
    
    name: str = Field(description="The full name of the user.")
    age: int = Field(ge=18, description="The user's age. Must be 18 or older.")
    role: Literal['admin', 'user'] = Field(description="The access tier.")
```

### Why this is powerful:
1. **The LLM sees a strict JSON Schema:** It explicitly knows that `age` is of type `integer` and `role` is an `enum`.
2. **Strict Isolation (`extra="forbid"`):** By forbidding extra parameters, the model is physically prevented from attempting to supply its own `tenant_id` or `actor_id` to escalate privileges.
3. **Self-Correction:** Advanced frameworks catch the `ValidationError` and automatically feed it *back* to the LLM (e.g., *"Error: Extra inputs are not permitted"*), allowing the agent to fix its own mistake without crashing the program.

---

## 2. Engineering the `Field(description=...)`

The `description` inside a Pydantic Field is **the most important prompt engineering you will do.** It is more important than the global system prompt.

When an LLM is deciding whether to use a tool or what data to put in it, it relies heavily on the parameter descriptions.

### Bad Description:
```python
user_id: int = Field(description="The user id.")
```
*Why it fails:* Which ID? The database UUID? The customer support ticket ID? The LLM will guess, and it will often guess wrong.

### SOTA Description:
```python
user_id: int = Field(description="The 6-digit numeric database ID of the user. Do NOT use the alphanumeric ticket ID here.")
```
*Why it works:* It explicitly defines the format, the source, and actively warns against the most common hallucination (confusing it with a ticket ID).

---

## 3. Schema Evolution and Versioning

As your backend APIs evolve, your tools must evolve. Tool versioning is critical because in an agentic system, old agents (or paused trajectories waiting for human approval) might still hold references to `v1` schemas.

```python
class QueryLogsArgsV1(BaseModel):
    minutes: int

class QueryLogsArgsV2(BaseModel):
    time_range: TimeRange
```

**Best Practices for Schema Evolution:**
- **Never mutate an existing tool signature in-place** if you have running workflows or approvals pending.
- **Side-by-side deployment:** Deploy `query_logs_v2`, filter it into the catalog for new executions, and deprecate `query_logs_v1` while supporting existing paused states.
- Treat your tool schemas identically to public REST API contracts. A breaking change in a schema will break the agent's ability to plan and execute successfully.
