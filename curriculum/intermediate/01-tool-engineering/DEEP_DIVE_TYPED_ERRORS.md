# Deep Dive: Typed Error Taxonomies & Recovery

When a standard Python script hits an API error (e.g., an HTTP 404), it throws an Exception, prints a massive stack trace to `stderr`, and the program terminates.

In Agentic Engineering, **an error is not a fatal crash; it is an Observation.**

If a tool throws an unhandled exception, returning a raw 500-line HTML stack trace to the LLM will bloat the context window, cost thousands of tokens, and severely confuse the reasoning engine. Worse, it exposes internal infrastructure details to the agent.

---

## 1. The Anti-Pattern: Raw Exceptions

```python
# ❌ ANTI-PATTERN: Letting the LLM see raw system errors
@tool
def check_inventory(sku: str):
    response = requests.get(f"https://api.warehouse.com/inventory/{sku}")
    response.raise_for_status() # Throws HTTPError on 404
    return response.json()
```
If the user provides an invalid SKU, `requests` throws a traceback. The LLM sees a wall of Python stack trace garbage. It might hallucinate an answer to escape the confusion, or get stuck in an infinite loop retrying the exact same bad SKU.

---

## 2. The SOTA Pattern: Error Taxonomies

SOTA tool engineering requires mapping raw backend exceptions into a strict taxonomy of **Typed Errors**. We treat the LLM like a junior developer: we tell it *what* went wrong and *how* to recover, without exposing internal backend tracebacks.

```python
# ✅ SOTA PATTERN: Typed Error Classification
class ToolError(Exception):
    def __init__(self, code: ErrorCode, safe_message: str, retryable: bool):
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable

@tool("check_inventory")
def check_inventory(sku: str):
    try:
        response = requests.get(f"https://api.warehouse.com/inventory/{sku}")
        if response.status_code == 404:
            raise ToolError(ErrorCode.NOT_FOUND, f"SKU '{sku}' does not exist.", retryable=False)
        if response.status_code == 429:
            raise ToolError(ErrorCode.RATE_LIMITED, "API rate limited.", retryable=True)
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        # Hiding internal infrastructure failures
        raise ToolError(ErrorCode.UNAVAILABLE, "Warehouse system is down.", retryable=True)
```

---

## 3. Independent Retry Policies

Not all errors should trigger an LLM loop. A sophisticated agent runtime maintains a `RetryPolicy` per tool.

- **TIMEOUT / RATE_LIMITED**: The runtime automatically intercepts these and performs bounded exponential backoff *without* burning LLM tokens to ask the agent to try again.
- **INVALID_ARGUMENT / NOT_FOUND**: These are returned to the agent as an observation so it can repair its arguments or halt.
- **PERMISSION_DENIED**: The runtime intercepts this and immediately halts the tool execution. The agent is informed it lacks authorization, and it must never retry.
- **POISONED_RESULT**: If the result validation pipeline detects prompt injection, it quarantines the payload and halts.

By defining independent retry behaviors, we prevent the agent from infinitely looping over deterministic failures (like authorization denials) while gracefully recovering from transient infrastructure issues.
