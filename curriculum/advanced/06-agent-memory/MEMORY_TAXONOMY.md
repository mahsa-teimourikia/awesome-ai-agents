# Deep Dive: Memory Taxonomy

Dumping everything into a single Vector Database is an anti-pattern. Agent memory requires distinct cognitive layers with different lifecycles and storage engines.

## 1. Working Memory (Short-Term)
* **What it is:** The agent's current scratchpad. The immediate context window.
* **Storage:** In-memory variables or a fast KV store (Redis) scoped to the current thread.
* **Lifecycle:** Cleared immediately after the task/thread completes.

## 2. Episodic Memory
* **What it is:** The raw logs of what happened. (e.g., "At 2 PM, the user asked for a refund. I called the stripe API. It failed.")
* **Storage:** A time-series database or blob storage. Vector databases are useful here for semantic search over past events.
* **Lifecycle:** Retained for audits, but heavily aggressively pruned/summarized over time.

## 3. Semantic Memory
* **What it is:** Concrete, verified facts. (e.g., "User's tier is Premium", "User is allergic to peanuts").
* **Storage:** Structured Relational Database (Postgres) or Knowledge Graph (Neo4j).
* **Lifecycle:** Durable. Requires strict schemas. You cannot query a vector database and hope the LLM extracts the correct billing tier from a fuzzy string match.

## 4. Procedural Memory
* **What it is:** Instructions and skills. How the agent knows to do things.
* **Storage:** Code repositories, prompt templates, or skill registries.
* **Lifecycle:** Version-controlled by engineers. Not modified by the agent itself.
