# Deep Dive: Model Cascades

If you use the most capable Frontier model for every task, your cloud bill will bankrupt your enterprise.
However, if you use a cheap, small model for every task, the quality of your application will plummet.

The solution is the **Model Cascade**.

## How a Cascade Works
A cascade is an optimization pattern where you try the cheapest model first, and *only* promote to a more expensive model if the cheap one fails.

1. **The Fast Path:** Route the request to a cheap, fast model (e.g., `claude-3-haiku` or `gpt-4o-mini`).
2. **The Assertion:** You MUST have a deterministic way to evaluate the output. 
   - *Example:* Did the model return a valid JSON object matching the `UserProfile` Pydantic schema?
3. **The Promotion:** If the cheap model outputs a broken JSON string (fails the assertion), you throw away the response. You then route the exact same prompt to the Frontier model (e.g., `claude-3-5-sonnet`).

## When Cascades Fail
Cascades only work if you have a programmatic, deterministic way to verify the output (like a regex match, a unit test pass, or a JSON schema validation).

If the task is open-ended (e.g., "Write a creative poem"), you cannot use a Cascade, because you have no automated way to prove the cheap model "failed" at writing the poem. In open-ended tasks, you must rely on Semantic Routing or just default to the required tier.
