# Deep Dive: Schema Contracts

When an agent interacts with a tool, it isn't writing Python code. It is outputting a JSON string that is subsequently parsed by your orchestration framework (e.g., LangGraph or LangChain) and passed as arguments to a Python function.

If the agent hallucinates a parameter name, provides a string instead of an integer, or forgets a required argument entirely, the backend Python function will crash. 

To solve this, SOTA architectures enforce strict **Schema Contracts** between the Agent and the Tool.

---

## 1. The Death of Docstrings

In early agent frameworks, developers relied on Python docstrings to explain tools to the LLM:

```python
# ❌ ANTI-PATTERN: The LLM has to guess the types and constraints.
def create_user(name, age, role):
    \"\"\"Creates a user. Age must be > 18. Role must be 'admin' or 'user'.\"\"\"
    pass
```

This is brittle. The LLM has to parse the English text, infer that `age` is an integer, and hope it spells "admin" correctly.

## 2. Pydantic as the Universal Translator

**Pydantic** is the industry standard for defining Schema Contracts. When you define a Pydantic model, frameworks automatically translate it into a strict **JSON Schema** definition that is injected into the LLM's system prompt.

```python
# ✅ SOTA PATTERN: Explicit Pydantic Contracts
from pydantic import BaseModel, Field
from typing import Literal

class CreateUserInput(BaseModel):
    name: str = Field(description="The full name of the user.")
    age: int = Field(ge=18, description="The user's age. Must be 18 or older.")
    role: Literal['admin', 'user'] = Field(description="The access tier.")

@tool("create_user", args_schema=CreateUserInput)
def create_user(name: str, age: int, role: str):
    \"\"\"Creates a user in the database.\"\"\"
    pass
```

### Why this is powerful:
1. **The LLM sees a strict JSON Schema:** It explicitly knows that `age` is of type `integer` and `role` is an `enum`.
2. **Automatic Validation:** Before the `create_user` Python function is ever executed, Pydantic intercepts the LLM's raw JSON output. If the LLM outputs `"age": "twenty"`, Pydantic throws a `ValidationError`.
3. **Self-Correction:** Advanced frameworks catch the `ValidationError` and automatically feed it *back* to the LLM (e.g., *"Error: 'twenty' is not a valid integer for field 'age'. Try again."*), allowing the agent to fix its own mistake without crashing the program.

---

## 3. Engineering the `Field(description=...)`

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

## 4. Multi-Tool Disambiguation

As you add more tools to an agent (e.g., 10-15 tools), the LLM starts getting confused about *which* tool to use. 

If you have `get_billing_info` and `get_shipping_info`, the LLM might use the wrong one.

**The Fix:** Your tool descriptions and schema descriptions must be mutually exclusive.
- `get_billing_info`: *"Use this ONLY to check invoice history and payment methods. Do NOT use this to check delivery dates."*
- `get_shipping_info`: *"Use this ONLY to check tracking numbers and delivery dates. Do NOT use this for payment issues."*

By treating schemas as strict, documented API contracts, you drastically reduce hallucination rates and improve trajectory efficiency.
