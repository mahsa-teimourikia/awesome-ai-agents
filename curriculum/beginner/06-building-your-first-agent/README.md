# 06 — Building Your First Complete Agent

**Level:** Beginner · **Primary notebook:** [`06_building_your_first_agent.ipynb`](06_building_your_first_agent.ipynb) 

**Scenario:** We need to synthesize everything learned so far into a single, cohesive, and robust bounded agent. Northstar, our fictional SaaS support team, needs an agent that can safely review escalated tickets, query the customer's billing status, and propose a resolution.

## Outcomes

After completing the notebook and lab, you can:

1. Synthesize concepts from previous modules (Agent Loop, Workflows, Tools, and Frameworks).
2. Write a raw, un-abstracted Agent Loop using only the OpenAI API.
3. Rewrite the same agent using **LangGraph** to understand state machines and cyclic graphs.
4. Rewrite the same agent using **PydanticAI** to understand type-safe, developer-friendly orchestration.
5. Contrast the Developer Experience (DX) of manual loops, graphs, and structured frameworks.

## 1. The Goal: The Northstar Escalation Agent

Our agent needs to solve a specific problem: "Handle an escalated ticket from a frustrated customer whose billing failed."

To do this, the agent must be provided with tools:
1. `get_ticket_details(ticket_id)`: Fetches the text of the complaint.
2. `get_billing_status(customer_id)`: Checks if the customer's credit card is valid.
3. `issue_refund(customer_id, amount)`: A sensitive action that refunds the customer.

## 2. Approach 1: The Raw Agent Loop

Before relying on magic frameworks, you must understand the underlying loop. A raw agent is simply a `while` loop that calls the LLM, checks if the LLM wants to use a tool, executes the tool, and feeds the result back into the LLM.

**Pros:** Total control, zero magic, explicit dependencies.
**Cons:** You must write all the routing, JSON parsing, error handling, message history management, and retry logic yourself.

## 3. Approach 2: LangGraph

LangGraph forces you to think of your agent as a State Machine. You define nodes (e.g., "Call Model", "Execute Tool") and edges (e.g., "If model requests tool, go to Execute Tool"). 

**Pros:** Extremely explicit control flow, built-in persistence (memory), and easy human-in-the-loop pausing. Perfect for enterprise applications that need auditability.
**Cons:** High boilerplate. You are writing graph orchestration code, not just agent logic.

## 4. Approach 3: PydanticAI

PydanticAI represents the modern, Pythonic wave of agent frameworks. Instead of graphs, it relies on strict Python types (`Pydantic`) and simple decorators.

**Pros:** Extremely lightweight, type-safe, zero boilerplate. It feels like writing normal Python code.
**Cons:** Hides the underlying loop. Less suitable for complex, multi-agent orchestrations where you need strict, graph-based routing between different AI personas.

## Guided Lab

1. Open `06_building_your_first_agent.ipynb` from this directory.
2. Run the **Raw Agent Loop** cell. Watch how we manually append `tool_calls` and `tool_responses` to the message array.
3. Run the **LangGraph** cell. Notice how the agent's behavior is identical, but the code structure uses `StateGraph` and compiles into a runnable app.
4. Run the **PydanticAI** cell. Observe how the same tools are simply decorated with `@agent.tool` and executed in a single line: `agent.run_sync()`.

## Evaluation and production checklist

- [ ] Does your agent have a strict system prompt defining its persona and boundaries?
- [ ] Are sensitive tools (like `issue_refund`) protected by a human-in-the-loop confirmation before execution?
- [ ] Have you chosen the right framework for the job? (e.g., Don't use LangGraph for a simple CLI tool, don't use Raw Loops for a complex enterprise workflow).
- [ ] Does your agent handle tool failures gracefully? (e.g., What happens if `get_billing_status` times out?)

## Checkpoint

**1. Which framework relies on defining Nodes and Edges to orchestrate the agent loop?**
- A) PydanticAI
- B) OpenAI Raw API
- C) LangGraph
- D) Browser-Use

**2. Why might you choose a Raw Agent Loop over a framework?**
- A) Because it has built-in memory management.
- B) Because it provides type-safe schemas out of the box.
- C) To have total control with zero abstraction magic and explicit dependencies.
- D) To easily orchestrate multiple agents.

## Watch For

- **Framework Lock-in:** Don't let a framework dictate your architecture. The LLM is the engine; the framework is just the chassis.
- **Over-engineering:** Don't use a massive graph framework if a simple script will do.
