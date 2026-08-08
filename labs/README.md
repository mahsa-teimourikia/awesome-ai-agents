# AI Agents labs

The labs turn the Hub's explanations into small, inspectable Python programs.
They are intentionally runnable without an API key: model decisions are represented
by deterministic stubs so you can study control flow, policies, state, and tests
before connecting a provider.

## Beginner

- [`01_agent_loop.py`](beginner/01_agent_loop.py) — observe → decide → act with budgets and stop conditions.
- [`02_tool_contracts.py`](beginner/02_tool_contracts.py) — typed tool validation, authorization, dry runs, and idempotency.
- [`03_checkpointed_state.py`](beginner/03_checkpointed_state.py) — resumable state and typed failure handling.
- [`04_research_assistant_capstone.py`](beginner/04_research_assistant_capstone.py) — citations, evidence budgets, and abstention.

## AgentOps scenario track

- [`agentops_lab/loop_yourself.py`](agentops_lab/loop_yourself.py) — manual incident-investigation loop over deterministic service status, incident search, and runbook tools.
- [`agentops_lab/workflow_or_agent.py`](agentops_lab/workflow_or_agent.py) — compare deterministic workflows, bounded workflows, and dynamic agent investigations.
- [`agentops_lab/agents_sdk_rebuild.py`](agentops_lab/agents_sdk_rebuild.py) — compare manual loop ownership with an OpenAI Agents SDK-shaped runtime.
- [`agentops_lab/tool_engineering.py`](agentops_lab/tool_engineering.py) — refactor a broad admin tool into narrow, validated, failure-aware tools.
- [`notebooks/06_agentops_manual_loop.ipynb`](notebooks/06_agentops_manual_loop.ipynb) — scenario notebook for building, tracing, and safely stopping the loop yourself.
- [`notebooks/07_agentops_workflow_or_agent.ipynb`](notebooks/07_agentops_workflow_or_agent.ipynb) — scenario notebook for deciding whether a task needs a workflow, agentic workflow, single agent, or multi-agent team.
- [`notebooks/08_agentops_openai_agents_sdk.ipynb`](notebooks/08_agentops_openai_agents_sdk.ipynb) — scenario notebook for rebuilding the incident investigator with OpenAI Agents SDK concepts.
- [`notebooks/09_agentops_tool_engineering.ipynb`](notebooks/09_agentops_tool_engineering.ipynb) — scenario notebook for narrow tool schemas, validation, errors, retries, and approval boundaries.

The AgentOps track uses one evolving SaaS incident-response scenario to show
why teams move from deterministic workflows to bounded agents, stateful agents,
human-approved actions, evaluations, and eventually multi-agent teams.

## Intermediate

- [`01_architecture_patterns.py`](intermediate/01_architecture_patterns.py) — compare routing, parallelization, and evaluator-optimizer designs.
- [`02_langgraph_workflow.py`](intermediate/02_langgraph_workflow.py) — model an explicit state graph with conditional routing.
- [`03_evaluation_release_gate.py`](intermediate/03_evaluation_release_gate.py) — gate releases on outcomes, policy compliance, and cost.
- [`04_support_workflow_capstone.py`](intermediate/04_support_workflow_capstone.py) — routing, account lookup, approval, and escalation.

## Advanced

- [`01_multi_agent_team.py`](advanced/01_multi_agent_team.py) — manager/worker contracts, findings, and provenance.
- [`02_durable_recovery.py`](advanced/02_durable_recovery.py) — idempotency, replay safety, and a kill switch.
- [`03_protocol_boundaries.py`](advanced/03_protocol_boundaries.py) — identity and capability checks for interoperability.
- [`04_safety_readiness.py`](advanced/04_safety_readiness.py) — threat-model checks and production readiness gates.
- [`05_multi_agent_research_capstone.py`](advanced/05_multi_agent_research_capstone.py) — bounded research team with claims, citations, and escalation.

## Optional LangGraph environment

The LangGraph sample keeps the same state-machine concepts while showing a graph
runtime. Install the optional dependency with `pip install -r requirements.txt`
and run [`02_langgraph_workflow.py`](intermediate/02_langgraph_workflow.py).

The examples are teaching artifacts, not production authorization systems. Keep
identity, policy, secrets, and side effects in application code around the model.

The [`notebooks/`](notebooks/) directory contains Markdown-first companions for
running the same ideas interactively. Larger implementations remain in Python so
they can be tested and reused outside a notebook.

See [`provider-guide.md`](provider-guide.md) before connecting a real model or API key.

Provider seams are demonstrated in [`providers/`](providers/); install a provider
SDK only when you are ready to add credentials and retain the surrounding policy
and evaluation boundaries.
