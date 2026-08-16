# Deep Dive: The Selector Prompt

In AutoGen's `SelectorGroupChat`, the **Selector** is an LLM that reads the shared conversation history and decides which agent should speak next.

## The Default Behavior Trap
If you do not explicitly prompt the Selector, it will fall back to conversational norms. 
If the `Database_Agent` says "Here is the data", the Selector might pass the mic to the `Analyst_Agent` to say "Thank you!", and then back to the `Database_Agent` to say "You're welcome!"

## Engineering the Selector Prompt
You must program the Selector to behave like a strict routing algorithm.

**Bad Prompt:**
> "Choose the next speaker based on the conversation."

**Good Prompt:**
> "You are a strict routing coordinator. Review the shared context. 
> 1. If we lack database metrics, select the `Database_Agent`.
> 2. If we lack logs, select the `Log_Agent`.
> 3. If we have both, but lack a hypothesis, select the `Analyst_Agent`.
> 4. Do not select an agent just to say 'Thank you' or acknowledge receipt. If the required artifacts are present, select the `Review_Agent` to finalize.
> 5. Do not select the same agent twice in a row."

By defining explicit evidence gaps, the Selector stops acting like a conversational participant and starts acting like a state machine router.
