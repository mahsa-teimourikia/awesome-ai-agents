# Deep Dive: Human Approval Timeouts and Stale State

Durable execution solves the compute problem, but it introduces a new logical problem: **Stale State**.

Imagine this scenario:
1. **Monday:** The Agent analyzes a database and proposes deleting table `temp_logs_2023`. It pauses and asks for human approval.
2. **Tuesday - Sunday:** The human manager is on vacation.
3. **Next Monday:** The human returns and clicks "Approve".
4. The Agent wakes up and executes the deletion.

**The Danger:** During those 7 days, another engineer might have repurposed `temp_logs_2023` to hold critical production data. Because the agent's memory was frozen on Monday, it is unaware of the change. It executes a catastrophic deletion based on *stale* assumptions.

## Mitigation 1: Timeouts (TTL)
Every proposal must have a **Time To Live (TTL)**. 
If the human does not respond within 24 hours, the job is marked as `EXPIRED`. If the human clicks approve on day 7, the system rejects the approval.

## Mitigation 2: Revalidation on Wake
If the TTL is long, the agent must be programmed to **Revalidate** its assumptions upon waking up.
Before executing the approved action, the agent runs a quick check: *"Does the `temp_logs_2023` table still have the same schema and row count as it did when I made the proposal 7 days ago?"* 
If the state has mutated, the agent aborts the action and requests a new review.
