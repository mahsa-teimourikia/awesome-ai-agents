# Deep Dive: The Agent Development Framework Landscape

When evaluating agent frameworks, you are fundamentally choosing how much of the runtime mechanics you want to manage yourself. This deep dive groups the current landscape by architectural philosophy rather than popularity.

## 1. What a Framework Actually Provides

Frameworks abstract away boilerplate. Common abstractions include:
- Managing the message history.
- Parsing model tool-call requests and dispatching them to Python functions.
- Serializing state.
- Emitting traces and telemetry.
- Routing control flow between steps.

They **do not** solve business rules, authorization, or factual correctness.

## 2. Raw SDK vs Managed Agent Runtime

### Raw SDK (e.g., OpenAI Responses API)
When you use a raw API, you own the loop. You write the `while` loop that calls the model, checks for tool calls, executes the tool, and calls the model again.
- **When to use:** For small systems, or when you need absolute transparency and control over the execution loop.

### Managed Agent Runtimes (e.g., OpenAI Agents SDK)
These frameworks wrap the loop in a `Runner`. You pass an `Agent` and a list of tools, and the framework executes the turns automatically until completion.
- **When to use:** When you want built-in tracing, session management, and standard guardrails without writing the loop yourself.

## 3. Typed Agent Runtimes

### PydanticAI
PydanticAI focuses on strict typing. It ensures that inputs, outputs, and dependencies match Pydantic schemas, with built-in retries for structural failures.
- **When to use:** When schema-validity and typed dependency injection (passing context to tools securely) are your primary concerns.

## 4. Graph and Workflow Runtimes

### LangGraph
LangGraph models agents as state machines. You define a global state, nodes (functions that mutate state), and edges (routing logic). It includes a checkpointer for pausing and resuming execution.
- **When to use:** When you need explicit branching, interruptible workflows, and a visualizable state path. Do not use a graph simply to hide a straight-line function.

## 5. Team and Composition Frameworks

### Google ADK, AutoGen, CrewAI, Microsoft Agent Framework
These frameworks introduce "collaboration" abstractions (teams, crews, workflows). They are designed for scenarios where specialized agents (e.g., a "Researcher" and a "Reviewer") must communicate to solve a task.
- **When to use:** When a single agent with multiple tools fails because the context window becomes too noisy, and explicit role separation improves outcomes. Always justify the added coordination cost against a single-agent baseline.

## 6. Durable Workflow Systems

### Temporal
Temporal is not an AI framework; it is durable execution infrastructure. It guarantees that code survives server crashes and can sleep for days without losing state.
- **When to use:** When an agent's workflow involves waiting for a human for 3 days, or when recovering from an infrastructure failure is critical.

## 7. Optimization and Programming Frameworks

### DSPy
DSPy is fundamentally different from orchestrators. It is a declarative programming model that optimizes prompts automatically based on metrics. You define the *signature* of the task, provide evaluation data, and DSPy finds the best prompt or few-shot examples for the model.
- **When to use:** When you want to optimize trajectory efficiency, handle model-switching (e.g., migrating from GPT-4 to a cheaper model), or replace manual prompt engineering with programmatic tuning.

## Summary: Framework Selection Guide

1. Need absolute control and zero magic? **Raw SDK**.
2. Need basic loop management and tracing? **OpenAI Agents SDK**.
3. Need typed outputs and dependencies? **PydanticAI**.
4. Need branching, state, and pause/resume? **LangGraph**.
5. Need specialist agents working together? **AutoGen / CrewAI / Google ADK / MS Agent**.
6. Need to sleep for a week and survive crashes? **Temporal**.
7. Need to optimize prompts against metrics? **DSPy**.
