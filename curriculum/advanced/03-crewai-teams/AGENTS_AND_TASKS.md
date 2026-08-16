# Deep Dive: Agents and Tasks

The most common mistake when building multi-agent systems is letting agents "chat" with each other like humans in a Slack channel. This leads to infinite polite loops ("Thanks Bob!" "You're welcome Alice!") and lost context.

CrewAI solves this by strictly separating the **Agent** (the Who) from the **Task** (the What).

## The Agent (Who)
The `Agent` class defines the persona, the goal, and the allowed tools.
- **Role:** Senior Database Reliability Engineer
- **Goal:** Diagnose slow queries without dropping tables.
- **Tools:** `[query_pg_stat_statements]`

## The Task (What)
The `Task` class defines the specific deliverable and the expected schema. 
Agents do not pass conversational strings to each other. They pass the completed *output* of a Task.
- **Description:** Find the top 3 slowest queries in the last hour.
- **Expected Output:** A JSON array containing `[{"query_id": "...", "duration_ms": ...}]`.

When the Database Agent completes its Task, it hands that JSON array directly to the next Task in the graph. There is no conversational "chatter", drastically reducing token costs and hallucination risks.
