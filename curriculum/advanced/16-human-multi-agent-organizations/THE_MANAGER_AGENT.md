# Deep Dive: The Manager Agent

One of the most debated topics in multi-agent systems is the role of the "Manager Agent" (sometimes called the Router or Orchestrator Agent).

## When to use a Manager Agent
A Manager Agent earns its place in the architecture *only* when the task requires **Context Isolation** or **Parallelization**.

### Context Isolation
If you pass the entire history of an incident (Slack logs, database dumps, customer emails) to a single agent, the LLM's context window gets polluted. The agent will become confused by conflicting information and hallucinate.

A Manager Agent solves this. It reads the master objective, and then creates isolated Work Orders. 
- It sends *only* the database logs to the Data Agent.
- It sends *only* the customer emails to the Support Agent.

By isolating context, the specialist agents remain highly focused and accurate.

### Parallelization
If an incident requires checking three different microservices, a single agent will do this sequentially (which is slow). A Manager Agent can spawn three separate specialist agents simultaneously, aggregate their results, and synthesize a final report.

## The Manager Hallucination (Anti-Pattern)
The biggest risk of using a Manager Agent is that it begins acting like a "Surrogate Executive."

If the Data Agent returns an error saying *"I cannot access the EU database,"* the Manager Agent might hallucinate a fake summary like *"The Data Agent reported the EU database is healthy,"* just to keep the task moving forward.

### Mitigation: Strict Escalation
To prevent Manager Hallucination, the Manager Agent must be stripped of its ability to "resolve uncertainty." 

If a specialist agent fails, or if there is conflicting data between two specialists, the Manager Agent must be hard-coded to **Escalate to Human**. It is a coordinator, not a decision-maker. It routes data; it does not invent it.
