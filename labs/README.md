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
- [`agentops_lab/state_memory_langgraph.py`](agentops_lab/state_memory_langgraph.py) — model a stateful investigation graph and memory-bias experiment.
- [`agentops_lab/human_permissions.py`](agentops_lab/human_permissions.py) — model approval-gated tools, persisted pause state, and resume decisions.
- [`agentops_lab/guardrails_untrusted_content.py`](agentops_lab/guardrails_untrusted_content.py) — demonstrate poisoned retrieved content and tool-level guardrails.
- [`agentops_lab/evaluation_trajectory.py`](agentops_lab/evaluation_trajectory.py) — evaluate outcome, trajectory, operations, and cost per successful task.
- [`agentops_lab/trajectory_optimization.py`](agentops_lab/trajectory_optimization.py) — compare inefficient and optimized successful trajectories.
- [`agentops_lab/multi_agent_team.py`](agentops_lab/multi_agent_team.py) — compare one incident investigator with a specialist incident-response team.
- [`agentops_lab/autogen_selector_team.py`](agentops_lab/autogen_selector_team.py) — simulate AutoGen selector-style team coordination, ownership, and loop budgets.
- [`agentops_lab/crewai_team.py`](agentops_lab/crewai_team.py) — map the same specialist team to a CrewAI-style Agents + Tasks + Crew structure.
- [`agentops_lab/hybrid_production_architecture.py`](agentops_lab/hybrid_production_architecture.py) — route simple lookups, investigations, and high-risk cases through a hybrid production architecture.
- [`agentops_lab/capstone_incident_response.py`](agentops_lab/capstone_incident_response.py) — combine architecture selection, tools, state, permissions, guardrails, evaluation, trace, and cost analysis.
- [`notebooks/06_agentops_manual_loop.ipynb`](notebooks/06_agentops_manual_loop.ipynb) — scenario notebook for building, tracing, and safely stopping the loop yourself.
- [`notebooks/07_agentops_workflow_or_agent.ipynb`](notebooks/07_agentops_workflow_or_agent.ipynb) — scenario notebook for deciding whether a task needs a workflow, agentic workflow, single agent, or multi-agent team.
- [`notebooks/08_agentops_openai_agents_sdk.ipynb`](notebooks/08_agentops_openai_agents_sdk.ipynb) — scenario notebook for rebuilding the incident investigator with OpenAI Agents SDK concepts.
- [`notebooks/09_agentops_tool_engineering.ipynb`](notebooks/09_agentops_tool_engineering.ipynb) — scenario notebook for narrow tool schemas, validation, errors, retries, and approval boundaries.
- [`notebooks/10_agentops_langgraph_state_memory.ipynb`](notebooks/10_agentops_langgraph_state_memory.ipynb) — scenario notebook for LangGraph-style state, confidence loops, and memory safety.
- [`notebooks/11_agentops_human_permissions.ipynb`](notebooks/11_agentops_human_permissions.ipynb) — scenario notebook for human approval gates, least privilege, and persisted resume.
- [`notebooks/12_agentops_guardrails_untrusted_content.ipynb`](notebooks/12_agentops_guardrails_untrusted_content.ipynb) — scenario notebook for untrusted retrieved content, prompt injection, and tool guardrails.
- [`notebooks/13_agentops_evaluate_trajectory.ipynb`](notebooks/13_agentops_evaluate_trajectory.ipynb) — scenario notebook for outcome, trajectory, and operational evaluation.
- [`notebooks/14_agentops_optimize_trajectory.ipynb`](notebooks/14_agentops_optimize_trajectory.ipynb) — scenario notebook for reducing latency, cost, calls, and path length while preserving success.
- [`notebooks/15_agentops_when_one_agent_becomes_team.ipynb`](notebooks/15_agentops_when_one_agent_becomes_team.ipynb) — scenario notebook for deciding when specialists justify coordination overhead.
- [`notebooks/16_agentops_autogen_selector_team.ipynb`](notebooks/16_agentops_autogen_selector_team.ipynb) — scenario notebook for AutoGen-style selector teams, shared context, and bounded failure loops.
- [`notebooks/17_agentops_crewai_team.ipynb`](notebooks/17_agentops_crewai_team.ipynb) — scenario notebook for implementing the same team with CrewAI concepts.
- [`notebooks/18_agentops_hybrid_production_architecture.ipynb`](notebooks/18_agentops_hybrid_production_architecture.ipynb) — scenario notebook for combining deterministic workflows, bounded agents, teams, policy, and approvals.
- [`notebooks/19_agentops_final_capstone.ipynb`](notebooks/19_agentops_final_capstone.ipynb) — final capstone notebook where learners justify the full production design experimentally.

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
