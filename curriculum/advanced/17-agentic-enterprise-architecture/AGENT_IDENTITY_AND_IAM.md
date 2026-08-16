# Deep Dive: Agent Identity and IAM

In a traditional web application, a human logs in, receives a session token, and uses that token to perform actions. 

When deploying autonomous agents, the worst security mistake an enterprise can make is **Inherited Authority**—giving the agent the exact same session token as the human who triggered it.

## The Problem with Inherited Authority
Imagine an HR Manager (Alice) triggers an agent to "Summarize the vacation policy." 
If the agent inherits Alice's blanket API key, and the agent hallucinates (or is prompt-injected), it could execute a query to "Download all employee salary data." Because Alice has HR Admin rights, the database accepts the query. The agent just caused a massive data breach.

## Workload Identity (The Solution)

An agent must be treated as a distinct non-human entity (a Workload). It must be assigned its own **Workload Identity**.

When Alice asks the orchestrator to run the "Vacation Summarizer Agent," the orchestrator does *not* pass Alice's token to the agent. Instead, it contacts the IAM provider (like AWS IAM or Okta) and requests a **Narrowly Scoped, Time-Bound Token**.

### Anatomy of an Agent Token
An agent's JWT (JSON Web Token) should contain:
- `sub`: The Agent's unique ID (`agent_vacation_summarizer_v1`).
- `tenant_id`: The specific workspace the agent is allowed to query.
- `scopes`: `["read:confluence_hr_policies"]`. (Notice it does *not* have `read:employee_salaries`).
- `exp`: An expiration time of 15 minutes.

### Privilege Escalation Prevention
If the agent is hijacked via prompt injection and tries to hit the `/api/salaries` endpoint, the downstream Resource Server will inspect the agent's JWT, see that the scope is missing, and reject the request with a `403 Forbidden`. 

The agent is mathematically prevented from performing actions outside its defined, narrow scope, regardless of what the LLM decides to do.
