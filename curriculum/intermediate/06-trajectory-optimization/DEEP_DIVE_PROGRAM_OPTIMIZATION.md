# Deep Dive: DSPy & LM Program Optimization

While trajectory optimization fundamentally involves restructuring the execution path—removing duplicate reads, parallelizing independent fetches, caching safely, and bounding retries—you can also influence the trajectory programmatically by tuning the underlying Language Model calls.

**DSPy** is a widely used open-source framework for LM program optimization. 

Instead of manually crafting complex zero-shot prompts or manually injecting "Gold Standard" few-shot examples into your system prompts, DSPy allows you to declare *what* you want (the Signature) and a metric. It then automatically compiles the prompt by simulating the agent against your dataset and extracting successful traces.

## DSPy in Practice

DSPy can optimize LM programs, prompts, and demonstrations against a metric and dataset. Results depend heavily on:
- model
- dataset
- metric
- optimizer
- task
- budget

### Example Workflow

1. **Define the Signature**: Map inputs (e.g., `order_id`) to outputs (e.g., `final_response`).
2. **Define the Module**: The logic flow, such as `dspy.ChainOfThought(Signature)`.
3. **Define the Metric**: A function that evaluates whether a prediction is successful (e.g., outcome match, evidence match, policy compliant).
4. **Compile**: Use an optimizer (e.g., `BootstrapFewShot`) to simulate, score, and extract optimal trajectories for few-shot learning.

## Demonstration Governance

When using few-shot examples (whether manually crafted or automatically compiled by DSPy), you must govern them strictly:
- **Example Provenance**: Where did the gold trace come from? Was it synthesized or real?
- **Dataset Contamination**: Ensure evaluation holdouts aren't leaked into few-shot compilation.
- **Staleness**: If tool schemas or egress policies change, the compiled prompt containing stale examples MUST be invalidated.
- **Tenant Leakage**: Ensure few-shot examples injected into the prompt don't leak one tenant's PII/data to another tenant's agent session.

Use structured logs for demonstrations. Replace private reasoning chains (`Thought: ... Observation: ...`) with observable system events (`Decision: ... Result: ...`) to ground the optimizer in reality.
