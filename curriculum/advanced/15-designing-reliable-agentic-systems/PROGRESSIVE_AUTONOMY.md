# Deep Dive: Progressive Autonomy

A massive anti-pattern in the current AI landscape is defaulting to a Multi-Agent System (MAS) for every problem. 

If a task can be solved with a simple Python script, using a 7-agent swarm to solve it is architectural negligence. It introduces non-determinism, skyrockets latency (from milliseconds to minutes), and burns API credits unnecessarily.

Reliable enterprise engineering demands **Progressive Autonomy**: start at the lowest possible tier of autonomy, and only promote to the next tier when mathematical evidence proves the current tier is failing.

## The Autonomy Ladder

### Tier 1: The Deterministic Baseline (Code)
**When to use:** The inputs are structured, the logic is fixed, and the output is predictable.
**Example:** Fetching a user's recent orders from a database.
**Why:** Zero hallucination risk, sub-100ms latency, zero API token cost.

### Tier 2: The Bounded Single Agent
**When to use:** The inputs are ambiguous (e.g., natural language), but the task is narrow and doesn't require long-running memory.
**Example:** Taking a messy customer email and extracting the `order_id` and the `sentiment` into a structured JSON object.
**Why:** It bridges the gap between unstructured human data and your deterministic internal APIs.

### Tier 3: The Stateful Graph
**When to use:** The task requires pausing for human approval, hitting an external API that might timeout, or looping over a retry logic with state persistence.
**Example:** Drafting a refund proposal, pausing execution for a manager to click "Approve", and resuming execution to hit the Stripe API.
**Why:** You need the system to "remember" where it was if the server crashes mid-execution.

### Tier 4: The Specialist Team (Multi-Agent)
**When to use:** The context window is too large for one agent, or the task requires vastly different personas to debate a solution.
**Example:** Resolving a P0 Sev-1 outage where you need one agent querying Datadog, one agent querying GitHub commits, and one agent drafting the post-mortem.
**Why:** Context isolation prevents hallucination in extremely complex scenarios.

> [!WARNING]  
> If you are at Tier 4, constantly ask yourself: "Did we over-engineer this? Can we push this logic back down to Tier 1?"
