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
| Intermediate | Tool engineering, context, state, approvals, guardrails, evaluation, trajectory economics, planning and task decomposition | Turn an agent into a controlled, measurable system that can pursue bounded multi-step work. |
| Advanced | Teams, framework comparisons, hybrid routing, agent memory, capstone | Build durable, governed systems whose knowledge survives safely across runs. |

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

Every runnable example now belongs to the lesson it supports. Look for
`lab.py` in each notebook-led topic, plus focused supporting scripts such as
`release_gate.py` or `durable_recovery.py` where a topic benefits from an
additional experiment.

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
