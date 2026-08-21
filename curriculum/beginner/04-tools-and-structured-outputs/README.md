# 04 — Tools & Structured Outputs Fundamentals

**Level:** Beginner · **Time:** 60 min · **Prerequisites:** [Workflows vs Agentic Workflows vs Agents](../03-workflow-or-agent/README.md)

**Scenario:** To make our support agent useful, it needs to query the `orders` database and issue a `refund`. We must guarantee that the agent asks for the correct parameters (Order ID, Amount, Reason) exactly as the backend API expects them.
**Notebook:** [`04_tools_and_structured_outputs.ipynb`](04_tools_and_structured_outputs.ipynb)

## Overview

Until now, we've discussed agent loops conceptually. This module covers the actual mechanism that gives models agency: **Tool Calling** (or Function Calling) and **Structured Outputs**.

Without structured outputs, connecting an LLM to a database requires brittle Regex parsing. With modern tool calling, models are natively trained to output strictly validated JSON payloads that map directly to your backend functions.

## 1. JSON Schema & Typed Validation

When you provide a tool to an LLM, you are providing a **JSON Schema**. The model uses this schema to understand:
- The name of the function
- The purpose of the function
- The expected arguments, their data types, and whether they are required.

Instead of writing raw JSON schemas by hand, modern Python development relies on **Pydantic**. Pydantic allows you to define Python classes with type hints, and automatically generates the JSON Schema for the LLM.

## 2. Tool Descriptions as Instructions

A tool description is just as important as the system prompt.
If you name a tool `get_data`, the model will struggle. 
If you name a tool `fetch_customer_order_history_by_id`, the model knows exactly when to use it.

**Best Practices:**
- Use highly descriptive function names.
- Document every parameter explicitly.
- State when *not* to use the tool.

## 3. The Tool-Calling Lifecycle

1. **User Request:** The user asks a question ("Refund order 123 for $50").
2. **Model Selection:** The model recognizes a tool is needed. It halts text generation and emits a `tool_call` payload.
3. **Execution:** Your application intercepts the payload, validates it, and executes the actual Python function.
4. **Tool-Result Message:** Your application appends the result of the function back to the conversation history as a `tool_result` (or `tool_message`).
5. **Final Answer:** The model reads the result and generates a final human-readable response.

## 4. Handling Errors and Retries

Models make mistakes. They hallucinate parameters or omit required fields.
A robust agentic system expects errors. When validation fails (e.g., Pydantic raises a `ValidationError`), you do not crash the program. Instead, you catch the error and send the error message *back* to the model as a `tool_result`. The model will read its mistake and retry the tool call correctly.

## 5. Tool Safety and Multiple Tools

- **Multiple Tools:** You can pass dozens of tools in a single array. The model's attention mechanism routes the intent to the correct tool.
- **Safety:** Providing a tool to a model does not grant authorization. The application must enforce user identity and permissions inside the function implementation itself. (e.g., "Is the current user allowed to refund $50?").

## Checkpoint

1. **Why do we use Pydantic for tool calling?**
   - A) Because models only speak Python.
   - B) To enforce strict type validation and automatically generate JSON Schemas.
   - C) Because it speeds up model inference.
   
2. **What should your application do if the model hallucinates a parameter during a tool call?**
   - A) Crash and return a 500 error to the user.
   - B) Silently drop the parameter and execute the tool anyway.
   - C) Catch the error and pass the error message back to the model so it can retry.

## Implementations

In the companion notebook, we will implement tool calling across several paradigms:
- Raw Provider Tool Calling
- Pydantic Schemas
- OpenAI Function Calling
- Anthropic Tools
- PydanticAI (The structured output framework)
