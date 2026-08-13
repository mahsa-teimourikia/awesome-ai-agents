# Deep Dive: Model Routing and Cascades

When engineers build prototype agents, they typically default to the most powerful model available (e.g., GPT-4o or Claude 3.5 Sonnet) for every single step.

In a production system, this is an economic disaster. If an agent receives the user prompt *"Hello, can you help me?"*, using GPT-4o to classify that intent is a massive waste of money and time. 

Production architectures use **Model Routing** and **LLM Cascades** (often popularized by the FrugalGPT paper).

## 1. Intent Classification (The Fast Route)
The first layer of any agent should be an **Intent Classifier** powered by a very small, extremely fast, and cheap model (e.g., `gpt-4o-mini`, `Claude 3 Haiku`, or even a fine-tuned local `Llama 3 8B`).

This model's only job is to decide:
1. Is this a casual greeting? (Return a pre-canned response).
2. Is this asking to run a specific, simple tool? (Extract the JSON arguments and execute).
3. Is this a complex, ambiguous problem? (Route to the Reasoning Agent).

## 2. LLM Cascades (The Rescue Pattern)
Even when a small model tries to execute a tool, it might fail. It might hallucinate a JSON parameter or fail a strict Pydantic validation check.

Instead of crashing the workflow or immediately returning an error to the user, you use an **LLM Cascade**.

### How a Cascade Works:
1. **Attempt 1 (Cheap):** The system asks `gpt-4o-mini` to extract the required JSON arguments to call `refund_customer`.
2. **Validation Failure:** The Pydantic model throws a `ValidationError` because the cheap model forgot to include the required `currency` field.
3. **Attempt 2 (Expensive Fallback):** The orchestrator catches the exception. It automatically falls back to `gpt-4o`, passing it the exact same prompt *plus* the `ValidationError` stack trace.
4. **Rescue:** The expensive model easily understands the error, fixes the JSON, and the tool executes successfully.

By cascading, you run 80% of your workloads on a model that is 50x cheaper, while maintaining the reliability of the flagship models for the 20% of edge cases that actually need them.
