# Deep Dive: Event-Driven Resumption

If the agent process was killed, how does it wake up when the human finally clicks "Approve"?

You must use an **Event-Driven Architecture**.

## The Webhook Wakeup
When the human clicks the Approve button in your UI, your backend fires a Webhook or publishes an event to a Message Queue (like AWS SQS or Kafka).

This event triggers a Serverless Function (like AWS Lambda) which:
1. Receives the `job_id`.
2. Fetches the Agent's state from the Database using the `job_id`.
3. Deserializes the state back into the LLM's context window.
4. Resumes execution right where it left off.

## The Idempotency Requirement
Message queues often have "at-least-once" delivery guarantees. This means your webhook might fire *twice* due to a network hiccup.

If the agent wakes up twice, it might execute the approved transaction twice (e.g., refunding a customer $100 twice).

**Mitigation:** You must use **Idempotency Keys**. 
When the agent proposes the action, it generates a unique UUID (the idempotency key). When it wakes up and calls the target API, it passes that UUID. If the API is called twice with the same UUID, the API simply returns the cached success response rather than repeating the action.
