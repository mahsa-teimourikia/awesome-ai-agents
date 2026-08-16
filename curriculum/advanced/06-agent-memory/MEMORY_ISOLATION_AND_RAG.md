# Deep Dive: Memory Isolation and RAG

Vector Databases are notorious for causing catastrophic data leaks in multi-tenant agent systems.

## The Semantic Leak Anti-Pattern
Imagine you dump all company documents into a single Vector DB.
- Tenant A uploads: "Acme Corp Q3 Revenue: $1M"
- Tenant B (a competitor) asks the agent: "What is Acme Corp's revenue?"
- The agent performs a semantic vector search for "Acme Corp revenue".
- The Vector DB returns Tenant A's document because the vector distance is incredibly close.
- Tenant B just stole Tenant A's private data.

## The Solution: Hybrid Retrieval
You can **never** use semantic similarity as an access control mechanism.

When querying memory, you must use **Hybrid Retrieval** (Hard Pre-filtering + Vector Search).
1. **Pre-Filter:** The database query explicitly includes a hard constraint: `WHERE tenant_id = 'tenant_b'`.
2. **Vector Search:** Only *after* the dataset is isolated to Tenant B's data does the semantic vector search execute.

If a memory system does not support hard namespace isolation at the database level, it is not safe for enterprise agents.
