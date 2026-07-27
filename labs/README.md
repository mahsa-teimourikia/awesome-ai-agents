# AI Agents labs

The labs turn the Hub's explanations into small, inspectable Python programs.
They are intentionally runnable without an API key: model decisions are represented
by deterministic stubs so you can study control flow, policies, state, and tests
before connecting a provider.

## Beginner

- [`01_agent_loop.py`](beginner/01_agent_loop.py) — observe → decide → act with budgets and stop conditions.
- [`02_tool_contracts.py`](beginner/02_tool_contracts.py) — typed tool validation, authorization, dry runs, and idempotency.
- [`03_checkpointed_state.py`](beginner/03_checkpointed_state.py) — resumable state and typed failure handling.

## Optional LangGraph environment

The LangGraph sample keeps the same state-machine concepts while showing a graph
runtime. Install the optional dependency with `pip install -r requirements.txt`
and run [`02_langgraph_workflow.py`](intermediate/02_langgraph_workflow.py).

The examples are teaching artifacts, not production authorization systems. Keep
identity, policy, secrets, and side effects in application code around the model.
