# Deep Dive: Consolidation and Forgetting

An agent's context window is finite. If you just append every user message to a chat history, the agent will eventually crash or lose its reasoning ability (the "Lost in the Middle" phenomenon).

To solve this, advanced agents use **Reflection**.

## The Reflection Pattern
Reflection is an asynchronous background process that converts Episodic Memory (raw logs) into Semantic Memory (concrete facts).

1. **Trigger:** After 10 conversational turns, a background job kicks off.
2. **Extraction:** A cheap, fast LLM reads the 10 turns and asks: *"Are there any new, durable facts here?"*
   - Log: "Actually, I switched from Python to Go."
   - Extraction: `{"user_id": 123, "fact_type": "primary_language", "value": "Go"}`
3. **Upsert:** The agent updates the structured Semantic Database.
4. **Forgetting:** The agent deletes the 10 raw episodic turns from its working memory to free up context window space.

## Resolving Contradictions
If the user previously said they used Python, and now says they use Go, the Semantic Database must handle the contradiction.
You should not store both facts and rely on the LLM to figure out which is true. The Reflection engine must explicitly **supersede** the old fact, maintaining a single source of truth in the Semantic DB.
