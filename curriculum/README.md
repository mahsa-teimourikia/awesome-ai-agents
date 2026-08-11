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
| Advanced | Teams, framework comparisons, hybrid architecture/model routing, agent memory, world models, proactive agents, capstone | Build durable, governed systems that choose capable paths economically and whose knowledge survives safely across runs. |
| Enterprise Agent | Reliable systems, organizations, enterprise architecture, software engineering, embodied/multimodal agents, and agent economics | Synthesize architecture selection, governance, economics, security, privacy, evaluation, and human/agent operating models into release-ready systems. |

[Advanced 07 — World Models and Environment Modeling](advanced/07-world-models-environment-modeling/README.md)
teaches predictive internal representations, simulation, digital twins, model-based and
counterfactual planning, agent environment simulation, uncertainty, and reality checks.

[Advanced 08 — Proactive Agents](advanced/08-proactive-agents/README.md) moves from
request/response toward permission-bound persistent digital workers using events,
schedules, monitoring, notifications, goal persistence, and safe suppression/escalation.

[Advanced 09 — Model Routing](advanced/09-model-routing/README.md) selects the
least expensive eligible model path for simple text, complex reasoning, visual
evidence, and coding work. It covers capability, cost, and latency routing,
bounded cascades, fallbacks, ensembles, and routing evaluation.

[Advanced 10 — Long-Running and Asynchronous Agents](advanced/10-long-running-asynchronous-agents/README.md)
teaches durable jobs, checkpointing, scheduled/event-triggered waits, human approval,
pause/resume, state recovery, cancellation, and bounded execution over minutes to days.

[Advanced 11 — LLM-as-Judge and Agent Judges](advanced/11-llm-as-judge-agent-judges/README.md)
teaches rubric, pairwise, trajectory/tool, critic, calibrated human-aligned, and ensemble judging.

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

[Enterprise Agent 07 — Cost, Latency, and Agent Economics](enterprise-agent/07-cost-latency-agent-economics/README.md)
governs the full request trajectory: token, action, reasoning, spend, and latency
budgets; caching; bounded parallel and speculative work; dynamic model selection;
fallbacks; and cost-per-success evaluation.

[Enterprise Agent 08 — Production Agent Architecture](enterprise-agent/08-production-agent-architecture/README.md)
connects gateway, orchestrator, runtime, durable state, queues, tools/MCP, RAG,
policy/identity, observability, evaluation, caching, scaling, recovery, and DR.

[Enterprise Agent 09 — Agent Governance and Responsible AI](enterprise-agent/09-agent-governance-responsible-ai/README.md)
operationalizes inventory, ownership, risk/autonomy/access/data classification, auditability,
oversight, change management, incident response, revocation, and retirement.

[Enterprise Agent 08 — Production Agent Architecture](enterprise-agent/08-production-agent-architecture/README.md)
brings gateway, orchestrator, runtime, memory, tools/MCP, RAG, policy/identity,
observability/evaluation, queues, checkpoints, caching, recovery, scaling, and DR together.

[Enterprise Agent 10 — Guardrails and Policy Enforcement](enterprise-agent/10-guardrails-policy-enforcement/README.md)
implements layered input, context, tool, argument, action, output, and audit controls.

[Enterprise Agent 11 — Agent Identity and Authorization](enterprise-agent/11-agent-identity-authorization/README.md)
teaches non-human identity, OAuth/OIDC delegation, short-lived scoped capabilities,
least privilege, tool/peer authorization, audit trails, and policy enforcement.

[Enterprise Agent 12 — Agent Security](enterprise-agent/12-agent-security/README.md)
covers injection/hijacking, poisoned context/memory/tools/MCP, credential/identity abuse,
cross-agent and supply-chain threats, exfiltration, excessive agency, and containment.

[Enterprise Agent 13 — Agent Observability](enterprise-agent/13-agent-observability/README.md)
teaches traces, trajectories, tool/state/context inspection, replay/debugging, OpenTelemetry,
monitoring, dashboards, and cost/latency/outcome measurement.

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
