# AI Agents curriculum

The curriculum is the primary hands-on route through this repository. Every
AgentOps lesson keeps the **training notebook**, a short topic guide, and a
direct link to its runnable implementation together. The lessons share one
fictional SaaS incident-response scenario, so complexity is introduced only
when the preceding design can no longer solve the problem reliably.

## How to use a lesson

1. Read the topic `README.md` for outcomes and prerequisites.
2. Open the notebook and work through the concept, diagram, implementation,
   deliberate failure case, exercises, and checkpoint.
3. Run the reusable implementation from `curriculum/advanced/05-incident-response-capstone/agentops_lab/`.
4. Use the [Learning Hub](../hub/index.html) for guided navigation and the
   [knowledge check](../quiz/index.html) to test the concepts.

## Learning path

| Level | Lessons | Outcome |
| --- | --- | --- |
| Beginner | AI agent foundations, agent loop, workflow selection, agent development frameworks, and computer-using agents | Build a bounded evidence-gathering or UI-operating agent and understand what the runtime owns. |
| Intermediate | Tool engineering, context, approvals, guardrails, evaluation, trajectory economics, planning, agentic RAG, and stateful LangGraph execution | Turn an agent into a controlled, measurable system that can pursue bounded multi-step work and recover safely. |
| Advanced | Teams, framework comparisons, hybrid routing, agent memory, capstone | Build durable, governed systems whose knowledge survives safely across runs. |
| Enterprise Agent | Designing Reliable Agentic Systems; Human + Multi-Agent Organizations | Synthesize architecture selection, governance, economics, security, privacy, evaluation, and human/agent operating models into release-ready systems. |

[Advanced 07 — World Models and Environment Modeling](advanced/07-world-models-environment-modeling/README.md)
teaches predictive internal representations, simulation, digital twins, model-based and
counterfactual planning, agent environment simulation, uncertainty, and reality checks.

[Advanced 08 — Proactive Agents](advanced/08-proactive-agents/README.md) moves from
request/response toward permission-bound persistent digital workers using events,
schedules, monitoring, notifications, goal persistence, and safe suppression/escalation.

## Enterprise synthesis module

[Enterprise Agent 01 — Designing Reliable Agentic Systems](enterprise-agent/01-designing-reliable-agentic-systems/README.md)
is the end-to-end architecture module. The Northstar Commerce incident asks learners
to decide whether deterministic code, a bounded agent, a durable graph, or a
specialist team is warranted, then protect that choice with tenant scope,
authorization, approvals, budgets, evaluations, traceability, and recovery.

[Enterprise Agent 02 — Human + Multi-Agent Organizations](enterprise-agent/02-human-multi-agent-organizations/README.md)
extends that synthesis from system architecture to organizational design: people set
purpose and authority, a manager agent coordinates scoped digital workers, specialists
return attributable artifacts, and a human reviews consequential proposals.

[Enterprise Agent 03 — Agentic Enterprise Architecture](enterprise-agent/03-agentic-enterprise-architecture/README.md)
turns individual agents into a governed ecosystem with agent/tool/MCP registries,
identity-bound discovery, shared knowledge boundaries, enterprise orchestration,
observability, evaluation, and FinOps.

[Enterprise Agent 04 — Agentic Software Engineering](enterprise-agent/04-agentic-software-engineering/README.md)
uses a long-horizon repository change to teach code search, planning, sandboxed
terminal work, test generation/execution, debugging, review, PRs, CI/CD, and
benchmark-aware evaluation.

[Enterprise Agent 05 — Embodied Agents and Robotics](enterprise-agent/05-embodied-agents-robotics/README.md)
is a concise physical-world module on VLA models, navigation, manipulation,
simulation, feedback, and independent safety constraints.

[Enterprise Agent 06 — Multimodal Agents](enterprise-agent/06-multimodal-agents/README.md)
covers vision, audio, video, documents, UI/screens, speech, sensors, multimodal
memory, and tool use through a provenance-aware See → Hear → Reason → Plan → Act loop.

## Advanced memory module

[06 — Agent Memory](advanced/06-agent-memory/README.md) treats memory as a
governed write → manage → read system, covering working/episodic/semantic/
procedural memory, ranking, consolidation, forgetting, contradictions, privacy,
and personalization.

## Shared implementation and fixtures

`advanced/05-incident-response-capstone/agentops_lab/` contains the reusable, deterministic implementation
modules plus the incident data, runbooks, and evaluation fixtures. This is
intentional: every lesson has its own learning surface, while one shared source
of truth prevents copies of the simulated production environment from drifting.

Every runnable example now belongs to the lesson it supports. Look for the
co-located `lab.py` in each notebook-led topic; each notebook imports and
explains that single implementation rather than maintaining parallel scripts.

## Intermediate planning module

[08 — Planning and task decomposition](intermediate/08-planning-task-decomposition/README.md)
uses a dynamic Adaptive RAG research-agent scenario. Its notebook demonstrates
goal contracts, DAG scheduling, planner/executor separation, checkpoints,
bounded replanning, and safe terminal states; its co-located `lab.py` is a
credential-free reference implementation.

## Intermediate agentic RAG module

[09 — Agentic RAG / Knowledge-Grounded Agents](intermediate/09-agentic-rag/README.md)
teaches retrieval as a bounded agent tool: query planning and decomposition,
multi-hop/iterative/adaptive retrieval, routing across search/SQL/graph/web
sources, corrective retrieval, citation verification, and grounded proposals.

## Final intermediate module: LangGraph state and memory

[10 — LangGraph State, Persistence, and Memory](intermediate/10-langgraph-state-memory/README.md)
closes the intermediate sequence. The Northstar incident-investigation notebook
uses typed state, conditional routing, checkpoints, recovery, interrupts,
streaming, and a governed store to demonstrate why working state and long-term
memory need distinct scopes and policies.

## Intermediate context module

[02 — Context Engineering for Agents](intermediate/02-context-engineering/README.md)
teaches how to construct the smallest trustworthy context packet for each agent
decision: stable policy, task state, just-in-time evidence, scoped memory,
structured compression, cache isolation, and poison quarantine.

## Beginner computer-use module

[05 — Computer-Using Agents](beginner/05-computer-using-agents/README.md) teaches
browser, GUI, OS, and mobile interaction boundaries using a simulated support
portal. Its notebook and lab cover visual grounding, screenshot understanding,
typed UI actions, sandboxing, confirmations, and safe recovery from UI drift.
