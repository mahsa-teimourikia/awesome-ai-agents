# Provider and LangGraph setup

The core labs run without credentials. When you are ready to connect a model,
keep provider calls behind the same `decide`, `tool`, and `policy` boundaries.

## LangGraph

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r labs/requirements.txt
python labs/intermediate/02_langgraph_workflow.py
```

Replace the deterministic `write_draft` node only after the graph state,
conditional edges, retry budget, and review policy are tested.

## Provider integration checklist

1. Store API keys in environment variables or a secret manager.
2. Keep model calls in a small adapter with timeouts and retry policy.
3. Validate model-produced tool arguments before execution.
4. Add a fake adapter for deterministic unit tests.
5. Record model, latency, token usage, and a redacted trace.

The model is a decision component; it is not the authorization boundary.
