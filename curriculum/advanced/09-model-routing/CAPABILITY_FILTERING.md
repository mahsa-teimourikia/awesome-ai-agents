# Deep Dive: Capability Filtering

When building an enterprise AI platform, you cannot hardcode the model name (e.g., `model="gpt-4o"`). 
Instead, you must build a **Model Registry** and a **Router**.

## The Model Registry
Every model in your platform should be registered with metadata describing its capabilities.

```json
{
  "claude-3-haiku": {
    "cost_per_1k": 0.00025,
    "supports_vision": true,
    "supports_function_calling": true
  },
  "llama-3-8b": {
    "cost_per_1k": 0.00010,
    "supports_vision": false,
    "supports_function_calling": false
  }
}
```

## Capability Filtering
When an agent receives a task, the Router evaluates the prompt constraints before selecting a model.

If the user uploads a screenshot of a broken UI, the Router looks at the prompt constraints: `requires_vision = True`.
It iterates through the Model Registry and dynamically drops `llama-3-8b` from the pool of eligible models because it cannot fulfill the task constraints. 

Filtering models based on strict capabilities *before* evaluating cost or latency prevents catastrophic failures where a text-only model receives an image and crashes the application.
