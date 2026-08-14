# Deep Dive: When to Use Teams (And When Not To)

Multi-agent teams (like AutoGen or CrewAI) are highly popular in demos. They look impressive: "Agent A talks to Agent B to solve the problem!"

In production, multi-agent teams are often a massive liability.

## The Multi-Agent Tax
If a user asks "What is my account balance?", a single agent can call `get_balance()` and answer in 2 seconds for $0.001.

If you use a team:
1. `ManagerAgent` receives the request.
2. `ManagerAgent` delegates to `BillingAgent`.
3. `BillingAgent` calls the tool.
4. `BillingAgent` passes the result to `ReviewerAgent`.
5. `ReviewerAgent` passes it back to `ManagerAgent`.

This takes 45 seconds, costs $0.05, and vastly increases the surface area for hallucinations (e.g., the agents get stuck in an infinite polite loop: "Thank you BillingAgent!" "You're welcome ManagerAgent!").

## When Teams Actually Add Value
You should only use a multi-agent team when the workload is **Asymmetric**.

*Example: Generating Secure Code.*
- Agent 1: `CoderAgent` (Prompted to be fast and creative).
- Agent 2: `SecurityAgent` (Prompted to be adversarial and strict).

Because their system prompts and goals are fundamentally at odds, splitting them into two agents that debate each other produces a better result than trying to prompt a single agent to be "creative but also strict."
