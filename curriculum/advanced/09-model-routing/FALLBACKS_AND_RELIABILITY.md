# Deep Dive: Fallbacks and Reliability

Agents are entirely dependent on upstream API providers. If OpenAI goes down, and your agent is hardcoded to `gpt-4o`, your entire enterprise application goes down with it.

This is unacceptable for production systems. You must design for High Availability (HA) using **Cross-Provider Fallbacks**.

## Standard Errors to Catch
Your router must catch the following standard HTTP errors from API providers:
- `429 Too Many Requests`: You hit a rate limit.
- `503 Service Unavailable`: The provider is experiencing an outage.
- `529 Site Overloaded`: The provider's servers are too busy.

## The Fallback Pattern
When the Router catches one of these errors, it should not crash the agent. Instead, it should immediately route the request to a secondary provider.

* **Primary Route:** `anthropic/claude-3-5-sonnet`
* **Trigger:** Returns `503 Service Unavailable`.
* **Fallback Route:** `openai/gpt-4o`

### LiteLLM
Building this manually is tedious because every provider uses a different API schema. The industry standard for handling this is **LiteLLM**. 

LiteLLM provides a unified API format (it translates Anthropic, Google, and Cohere APIs into the OpenAI format), and allows you to configure Fallbacks with a single line of code. If Provider A fails, LiteLLM automatically translates the prompt and sends it to Provider B, completely transparently to the Agent.
