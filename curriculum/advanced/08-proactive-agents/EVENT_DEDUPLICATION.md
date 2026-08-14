# Deep Dive: Event Deduplication

When a proactive agent monitors a data stream (e.g., an AWS CloudWatch log stream), an anomalous event rarely happens just once. A failing database might throw 5,000 `ConnectionTimeout` errors in a single minute.

If your agent is purely reactive to the stream, it will trigger an LLM invocation and send a Slack notification for every single error. This is a catastrophic failure mode known as an **Alerting Storm**.

## The Deduplication Pattern
Before invoking the LLM, the agent infrastructure must pass the event through a Deduplication Layer (usually backed by Redis or Memcached).

1. **Signature Generation:** The agent creates a deterministic hash of the event. For example, hashing the `ErrorType` and the `DatabaseID`.
   - `signature = hash("ConnectionTimeout" + "db-prod-01")` (e.g., `sig_abc123`)
2. **TTL Check:** The agent queries Redis: `EXISTS sig_abc123`.
3. **Action:**
   - If `FALSE`: The agent processes the event, sends the alert, and writes `sig_abc123` to Redis with a Time-To-Live (TTL) of 1 hour.
   - If `TRUE`: The agent silently drops the event.

This guarantees that the on-call engineer receives exactly *one* notification per hour for that specific error, saving thousands of dollars in LLM tokens and preventing notification fatigue.
