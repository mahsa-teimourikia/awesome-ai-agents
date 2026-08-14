# Deep Dive: Evidence Gathering

The first phase of Incident Command is **Evidence Gathering**. 
Agents are prone to hallucination, especially during stressful, high-context scenarios like production outages. If an agent tells you "Redis is down," you must ask: *"Show me the query that proves Redis is down."*

## The Read-Only Boundary
During the Evidence Gathering phase, the agent must be strictly restricted to **Read-Only Tools**.
- `query_datadog_metrics(query)`
- `search_sentry_logs(service_name)`
- `get_recent_github_deployments()`
- `list_active_zendesk_tickets()`

If the agent has access to `restart_service()` or `flush_redis()` during this phase, it might panic and mutate state before it understands the problem.

## Building the Timeline
The agent's objective is not to solve the problem, but to construct a chronological timeline linking cause and effect.
1. **08:42:** A deployment for `Checkout UI v2.1` begins.
2. **08:49:** The deployment completes.
3. **08:55:** Datadog reports a 31% drop in checkout conversion.
4. **09:00:** Zendesk receives 6 tickets regarding checkout failures.

By enforcing a Read-Only Evidence Gathering phase, the agent builds a grounded, factual hypothesis rather than an LLM hallucination.
