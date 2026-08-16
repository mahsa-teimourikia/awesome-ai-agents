# Deep Dive: Durable Execution and State

One of the most dangerous patterns in early agent development is the **Polling Anti-Pattern**. 

Developers will write a Python script that asks an LLM for a plan. The LLM decides it needs human approval. The developer's code then enters a `while True:` loop, running `time.sleep(60)` and checking a database every minute to see if the human clicked approve.

## Why Polling is Illegal in Production
1. **Compute Waste:** You are keeping a server running for days just to wait for a boolean flag.
2. **Fragility:** If the server restarts (e.g., a Kubernetes pod eviction), the in-memory Python script dies. The agent's context window is lost forever. The task will never complete.

## The Solution: Durable Execution
In an enterprise, when an agent reaches a stopping point (like waiting for a human), you must **Checkpoint and Kill**.

1. **Checkpoint:** Serialize the agent's entire context window (chat history, tool outputs, pending proposals) into a JSON blob.
2. **Persist:** Save this blob to a durable database (e.g., PostgreSQL or a specialized graph database like LangGraph's checkpointer).
3. **Kill:** Physically terminate the Python process running the agent.

The agent is now "frozen" in the database. It consumes zero compute. It is immune to server crashes.
