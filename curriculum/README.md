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
| Beginner | AI agent foundations, agent loop, workflow selection, and agent development frameworks | Build a bounded evidence-gathering agent and understand what the runtime owns. |
| Intermediate | Tool engineering, state, approvals, guardrails, evaluation, trajectory economics | Turn an agent into a controlled, measurable system. |
| Advanced | Teams, framework comparisons, hybrid routing, capstone | Justify when specialist coordination earns its added complexity. |

## Shared implementation and fixtures

`advanced/05-incident-response-capstone/agentops_lab/` contains the reusable, deterministic implementation
modules plus the incident data, runbooks, and evaluation fixtures. This is
intentional: every lesson has its own learning surface, while one shared source
of truth prevents copies of the simulated production environment from drifting.

Every runnable example now belongs to the lesson it supports. Look for
`lab.py` in each notebook-led topic, plus focused supporting scripts such as
`release_gate.py` or `durable_recovery.py` where a topic benefits from an
additional experiment.
