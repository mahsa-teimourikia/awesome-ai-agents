# AgentOps notebook-first lab track

The AgentOps notebooks are the primary training material for the scenario-based
AI agents course. Each notebook combines theory, architecture guidance,
implementation, failure analysis, evaluation, and reflection. The Python files
under [`../agentops_lab/`](../agentops_lab/) are reusable implementation modules
that the notebooks explain and run.

Use this track when you want to learn by building. Read the notebook first, then
open the linked Python module when you want to inspect or extend the underlying
implementation.

## How to use each notebook

1. Read the concept model and architecture boundary.
2. Inspect the tool, state, policy, or team contract.
3. Run the deterministic implementation cells.
4. Trigger or reason through the deliberate failure case.
5. Record the evaluation, cost, latency, safety, and trace observations.
6. Answer the final architecture question: why is this the least autonomous
   reliable design?

## Track map

| Step | Notebook | Primary implementation | Main design question |
| --- | --- | --- | --- |
| 01 | [`06_agentops_manual_loop.ipynb`](06_agentops_manual_loop.ipynb) | [`loop_yourself.py`](../agentops_lab/loop_yourself.py) | What is the agent loop before a framework hides it? |
| 02 | [`07_agentops_workflow_or_agent.ipynb`](07_agentops_workflow_or_agent.ipynb) | [`workflow_or_agent.py`](../agentops_lab/workflow_or_agent.py) | Does this task need a workflow, agentic workflow, agent, or team? |
| 03 | [`08_agentops_openai_agents_sdk.ipynb`](08_agentops_openai_agents_sdk.ipynb) | [`agents_sdk_rebuild.py`](../agentops_lab/agents_sdk_rebuild.py) | What does a managed agent runtime own, and what remains application policy? |
| 04 | [`09_agentops_tool_engineering.ipynb`](09_agentops_tool_engineering.ipynb) | [`tool_engineering.py`](../agentops_lab/tool_engineering.py) | How do narrow schemas make agent tools safer and easier to evaluate? |
| 05 | [`10_agentops_langgraph_state_memory.ipynb`](10_agentops_langgraph_state_memory.ipynb) | [`state_memory_langgraph.py`](../agentops_lab/state_memory_langgraph.py) | What belongs in thread state versus long-term memory? |
| 06 | [`11_agentops_human_permissions.ipynb`](11_agentops_human_permissions.ipynb) | [`human_permissions.py`](../agentops_lab/human_permissions.py) | Where should humans approve, modify, reject, or redirect action? |
| 07 | [`12_agentops_guardrails_untrusted_content.ipynb`](12_agentops_guardrails_untrusted_content.ipynb) | [`guardrails_untrusted_content.py`](../agentops_lab/guardrails_untrusted_content.py) | How do you keep retrieved content outside the trusted control boundary? |
| 08 | [`13_agentops_evaluate_trajectory.ipynb`](13_agentops_evaluate_trajectory.ipynb) | [`evaluation_trajectory.py`](../agentops_lab/evaluation_trajectory.py) | Did the agent use the right evidence path without forbidden actions? |
| 09 | [`14_agentops_optimize_trajectory.ipynb`](14_agentops_optimize_trajectory.ipynb) | [`trajectory_optimization.py`](../agentops_lab/trajectory_optimization.py) | What is the shortest reliable trajectory to a correct result? |
| 10 | [`15_agentops_when_one_agent_becomes_team.ipynb`](15_agentops_when_one_agent_becomes_team.ipynb) | [`multi_agent_team.py`](../agentops_lab/multi_agent_team.py) | What does an additional agent make meaningfully better? |
| 11 | [`16_agentops_autogen_selector_team.ipynb`](16_agentops_autogen_selector_team.ipynb) | [`autogen_selector_team.py`](../agentops_lab/autogen_selector_team.py) | How do selector teams coordinate without bouncing forever? |
| 12 | [`17_agentops_crewai_team.ipynb`](17_agentops_crewai_team.ipynb) | [`crewai_team.py`](../agentops_lab/crewai_team.py) | When does a role/task/crew mental model clarify collaboration? |
| 13 | [`18_agentops_hybrid_production_architecture.ipynb`](18_agentops_hybrid_production_architecture.ipynb) | [`hybrid_production_architecture.py`](../agentops_lab/hybrid_production_architecture.py) | How do deterministic systems route work around agents? |
| 14 | [`19_agentops_final_capstone.ipynb`](19_agentops_final_capstone.ipynb) | [`capstone_incident_response.py`](../agentops_lab/capstone_incident_response.py) | Which architecture wins experimentally for the final incident? |

## Framework mapping

The track does not reimplement every notebook in every framework. That would
turn the course into a shallow framework tour. Instead, each library appears
where it teaches a distinct engineering idea.

| Stage | Main implementation focus |
| --- | --- |
| Raw reasoning loop | Python + model API-shaped loop |
| Managed single agent | OpenAI Agents SDK concepts |
| State, workflows, memory | LangGraph concepts |
| HITL and persistence | LangGraph/LangChain concepts |
| Guardrails and tracing | OpenAI Agents SDK + application policy |
| Conversational agent teams | AutoGen concepts |
| Role/task-oriented teams | CrewAI concepts |
| Evaluation | Framework-independent harness |
| Final architecture | Compare all options against the simplest reliable baseline |
