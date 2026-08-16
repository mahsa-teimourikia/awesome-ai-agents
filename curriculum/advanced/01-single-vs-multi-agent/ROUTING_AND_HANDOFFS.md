# Deep Dive: Routing and Handoffs

Once you decide you *must* use multiple agents, you have to decide how they communicate. 

## Pattern 1: The Blackboard (Shared State)
In this pattern, agents do not talk directly to each other. They read and write to a shared database (the "Blackboard").
- **Example:** `Analyst_Agent` writes a hypothesis to a Redis key. `Reviewer_Agent` is triggered by a cron job, reads the Redis key, and writes a score.
- **Pros:** Highly decoupled, very scalable.
- **Cons:** High latency, complex infrastructure.

## Pattern 2: The Direct Handoff (Tool Calling)
In this pattern, the multi-agent system is just a tree of tools. Agent A has a tool called `ask_agent_b(query)`.
- **Example:** OpenAI's Swarm framework uses this. The `Triage_Agent` calls `transfer_to_billing()`, which instantly swaps the system prompt and tools to the `Billing_Agent`.
- **Pros:** Extremely fast, low token overhead.
- **Cons:** Agents are tightly coupled.

## Pattern 3: Deterministic Routing (The State Machine)
In this pattern, agents do not choose who they talk to. A deterministic Python script (like LangGraph) controls the flow.
- **Example:** The script runs `Agent A`. When `Agent A` finishes, the script forces the output into `Agent B`.
- **Pros:** Guaranteed execution order, very safe for enterprise.
- **Cons:** Rigid. If `Agent A` fails, the pipeline breaks unless explicitly coded to recover.
