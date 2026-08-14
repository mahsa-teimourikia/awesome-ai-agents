# Deep Dive: Single Agent vs Workflow

How do you know when to use an Agent versus a State Machine (Workflow)?

## The Workflow (State Machine)
Use a Workflow when the path to success is **Known and Linear**.

*Example: "Reset my password."*
1. Ask for email.
2. Send OTP.
3. Verify OTP.
4. Update DB.

If you use an LLM Agent for this, it might decide to skip step 2 because it hallucinates that the user is already verified. This is dangerous. Use a strict LangGraph state machine where nodes execute in a guaranteed order.

## The Bounded Single Agent
Use an Agent when the path to success is **Ambiguous**.

*Example: "Why is the database slow?"*
The system cannot know the answer in advance. It needs an entity that can loop:
1. Call `check_cpu_metrics()`.
2. Observe high CPU.
3. Call `check_active_queries()`.
4. Observe a rogue `SELECT *` query.
5. Formulate a response.

A workflow fails here because you cannot hardcode every possible diagnostic branch. The Agent thrives because it can use evidence to choose the next tool dynamically.
