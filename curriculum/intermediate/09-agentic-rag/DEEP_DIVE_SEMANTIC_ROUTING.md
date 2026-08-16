# Deep Dive: Semantic Routing in Agentic RAG

Standard Retrieval-Augmented Generation (RAG) is monolithic. If a user asks a question, the system embeds the query, hits a single Vector Database, retrieves the top-K chunks, and attempts to synthesize an answer. 

**This fails in the enterprise.** 
If a user asks, *"What was our total revenue in Q3?"*, a Vector DB will return chunks of text that happen to contain the words "total", "revenue", and "Q3". It will not perform math. 

**Agentic RAG** introduces a decision layer before retrieval: **Semantic Routing**.

---

## 1. The Core Concept

Semantic Routing is the process of analyzing the user's intent *before* committing to a retrieval strategy. Instead of a single Vector DB, an enterprise Agentic RAG system acts as a dispatcher to multiple specialized data sources:

1. **Vector Database:** Best for unstructured semantic queries (*"What is our policy on remote work?"*).
2. **SQL/Graph Database:** Best for aggregations, math, and structured relationships (*"How many customers churned last month?"*).
3. **Web Search API:** Best for real-time or external data (*"What did the Fed announce regarding interest rates today?"*).
4. **Direct Answer / Chitchat:** No retrieval needed (*"Hello, how are you?"*).

---

## 2. State of the Art (SOTA) Implementation Patterns

Routing requires a classifier. There are three primary ways to build this classifier, trading off between latency, cost, and accuracy.

### A. The LLM Router (High Accuracy, High Latency)
You pass the user's query to a fast LLM (like `gpt-4o-mini` or `claude-3-haiku`) and ask it to output an enum.

```python
from pydantic import BaseModel
from typing import Literal

class RouterDecision(BaseModel):
    destination: Literal["vector_db", "sql_db", "web_search", "chitchat"]

# System Prompt: "You are a routing agent. Analyze the user query..."
```
- **Pros:** Highly accurate. Can handle complex edge cases and ambiguous queries.
- **Cons:** Adds 300-800ms of latency before the actual retrieval even begins. Adds inference costs.

### B. The Embedding Router (Low Latency, Medium Accuracy)
Instead of an LLM, you pre-define "utterances" (example phrases) for each route. At runtime, you embed the user's query and calculate the cosine similarity against the pre-defined utterances. If it's closest to the "SQL" utterances, you route to SQL.

- **Pros:** Extremely fast (<50ms). Very cheap.
- **Cons:** Struggles with novel phrasing or complex, multi-part questions.

### C. The `semantic-router` Library (The SOTA Hybrid)
The open-source library [`semantic-router`](https://github.com/aurelio-labs/semantic-router) has emerged as the SOTA standard for this problem. It uses ultra-fast local embeddings and optimized mathematics to route queries in less than 2 milliseconds.

```python
from semantic_router import Route
from semantic_router import SemanticRouter
from semantic_router.encoders import OpenAIEncoder

# 1. Define Routes
sql_route = Route(
    name="sql_analytics",

# 2. Compile the highly-optimized routing layer
encoder = OpenAIEncoder()
router = RouteLayer(encoder=encoder, routes=[sql_route, vector_route])

# 3. Execute in < 2ms
decision = router("How much money did we make last week?")
print(decision.name) # Output: sql_analytics
```

---

## 3. Advanced Pattern: Multi-Routing

What if the user asks a compound question?
*"What is our policy on remote work, and how many employees currently work remotely?"*

A simple semantic router will fail because it must pick one destination.
SOTA Agentic RAG implements **Task Decomposition + Multi-Routing**:
1. The **Decomposer** splits the query into two sub-queries.
2. The **Router** sends Query A to the Vector DB and Query B to the SQL DB.
3. The **Synthesizer** waits for both payloads to return and generates a final, comprehensive answer.

## 4. Enterprise Recommendation
Never use a generic Vector DB for structured data. If your data lives in Postgres, route queries there. Use `semantic-router` for low-latency dispatching in production, and fall back to an LLM router only if the user query is highly ambiguous.
