# Deep Dive: Typed Error Handling & Recovery Loops

When a standard Python script hits an API error (e.g., an HTTP 404), it throws an Exception, prints a massive stack trace to `stderr`, and the program terminates.

In Agentic Engineering, **an error is not a fatal crash; it is an Observation.**

If a tool throws an unhandled exception, the orchestration framework will often crash, ending the entire agent trajectory. Even if the framework catches it, returning a raw 500-line HTML stack trace to the LLM will bloat the context window, cost thousands of tokens, and severely confuse the reasoning engine.

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

## 2. The SOTA Pattern: Semantic Error Strings

SOTA tool engineering requires you to `try/except` everything, and return **Semantic Instructions** back to the LLM as standard string output.

You treat the LLM like a junior developer. When they make a mistake, you don't scream binary code at them; you tell them *what* they did wrong and *how* to fix it.

```python
# ✅ SOTA PATTERN: Catching and typing errors
@tool
def check_inventory(sku: str):
    try:
        response = requests.get(f"https://api.warehouse.com/inventory/{sku}")
        
        if response.status_code == 404:
            # Semantic instruction for a known error
            return f"Error: The SKU '{sku}' does not exist in the catalog. Please ask the user to double-check their spelling."
            
        if response.status_code == 429:
            # Semantic instruction for rate limiting
            return "Error: The inventory API is rate-limited. Wait 5 seconds, use the `wait` tool, and try again."
            
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.ConnectionError:
        # Hiding internal infrastructure failures from the LLM
        return "Critical Error: The warehouse system is temporarily down. Inform the user you cannot check inventory right now."
    except Exception as e:
        # Catch-all
        return f"Unexpected API Error. Do not retry this specific SKU."
```

### Why this works:
1. **No Crashes:** The Python process never actually hits a fatal exception. The LangGraph loop keeps spinning.
2. **Context Window Protection:** Instead of 2000 tokens of a stack trace, the LLM receives ~30 tokens of plain English.
3. **Behavior Modification:** By returning phrases like *"Please ask the user..."*, you explicitly override the LLM's instinct to hallucinate and direct it back to the human.

---

## 3. The Auto-Correction Loop (Pydantic Validation)

The most common error an LLM makes is a **Schema Error** (e.g., passing a string `"forty"` instead of an integer `40`).

If you use `pydantic` for your Tool Schemas (as discussed in the Schema Contracts deep dive), modern frameworks like LangChain/LangGraph will automatically intercept the `ValidationError` *before* the function even executes.

They will automatically generate a Semantic Error String:
> `Error: 1 validation error for ToolInput. age: Input should be a valid integer, unable to parse string as an integer.`

The agent receives this as its "Observation", realizes its mistake, and in the next step of the trajectory, it corrects the JSON payload to `40`. This is known as a **Recovery Loop**, and it is essential for high-reliability enterprise agents.
