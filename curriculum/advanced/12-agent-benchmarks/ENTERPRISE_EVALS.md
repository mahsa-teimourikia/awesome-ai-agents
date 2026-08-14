# Deep Dive: Custom Enterprise Evaluations

You cannot trust an agent in production based on its SWE-bench score. You must build a **Custom Enterprise Evaluation Suite** and attach it to your CI/CD pipeline as a Release Gate.

If an engineer modifies a prompt or adds a new tool, the PR cannot merge until the agent passes the Eval Suite.

## Building the Golden Dataset
An evaluation suite requires a "Golden Dataset" of test cases. Do not ask an LLM to generate synthetic test cases; they will be too easy and won't reflect reality.

**How to build it:**
1. Export the last 500 traces from your production system (e.g., actual customer support chats).
2. **Anonymize** the data (strip PII).
3. Have human engineers label the "Expected Outcome" for each trace.
4. Categorize them into: *Routine* (easy), *Ambiguous* (hard), and *Adversarial* (prompt injection attempts).

## The Test Fixture
An agent in an evaluation suite cannot be allowed to hit the production database. You must build a **Mock Environment** (a Sandbox).
- If the test case requires looking up a customer, the `get_customer` tool must return a hardcoded JSON response for that specific test case, not a live API call.

## The Three Layers of Evaluation

1. **Outcome Evaluation:** Did the agent achieve the goal? (e.g., Did the generated JSON match the expected schema and data?)
2. **Trajectory Evaluation:** How did the agent get there? (e.g., Did it hallucinate a tool? Did it try to delete a user?)
3. **Operational Evaluation:** How much did it cost? (e.g., Did it burn $4 in tokens for a task that should cost $0.02?)
