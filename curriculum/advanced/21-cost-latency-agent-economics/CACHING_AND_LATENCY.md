# Deep Dive: Caching, Latency, and TTFT

Latency is the silent killer of agentic workflows. If a user asks a question and the agent takes 15 seconds to reply, the user will abandon the session. 

You must optimize for three things: **Semantic Caching**, **Parallel Execution**, and **Time to First Token (TTFT)**.

## 1. Semantic Caching

Traditional caching uses exact string matching. If user A asks `"How do I reset my password?"` and user B asks `"I forgot my password!"`, a traditional Redis cache treats them as a cache miss, forcing you to pay for two expensive LLM calls.

**Semantic Caching** solves this using Vector Embeddings.
1. The user's query is embedded into a vector.
2. We query a Vector Database (like Pinecone or pgvector) using Cosine Similarity.
3. If the similarity score is extremely high (e.g., > 0.95), we return the cached response instantly. 

**Cost:** $0.00. **Latency:** 50ms.

*Warning:* Never cache dynamic tools or personalized data. Cache only operational FAQs, static runbooks, or broad intent classifications. Always include the Tenant ID in the cache key to prevent data leakage across organizations.

## 2. Parallel Tool Execution

If an agent decides it needs to check the Weather in New York, London, and Tokyo, doing so sequentially could take 6 seconds (3 API calls * 2 seconds each).

Modern agent architectures enforce **Parallel Execution**. If the LLM returns an array of three tool calls, the orchestrator must execute them concurrently using `asyncio` or goroutines. The wall-clock latency drops from 6 seconds down to 2 seconds.

## 3. Time To First Token (TTFT)

When an agent is performing complex reasoning, it might take 10 seconds to decide which tool to call. 
To the user, the app looks frozen.

**Time to First Token (TTFT)** is the most critical metric for perceived performance. You must stream the agent's internal monologue or intermediate steps back to the UI immediately. 

Even if the final answer takes 15 seconds, if the user sees *"I am querying the database..."* after 1 second, they will wait. If they see nothing for 15 seconds, they will refresh the page and trigger a duplicate, expensive request.
