# ✨ Awesome AI Agents & Agentic Workflows ✨

> A notebook-first course and curated reference for building, evaluating, securing, and operating AI agents.

[![Awesome](https://awesome.re/badge.svg)](https://awesome.re) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

## Start here: AI Agents Learning Hub

**[Open the AI Agents Learning Hub →](https://mahsa-teimourikia.github.io/awsome-ai-agents/)**

The Hub is the main learning experience. Choose a level, select a topic, read
the explanation, run the linked notebook and `lab.py`, then complete its
checkpoint. It keeps progress in the browser and links every lesson to its
source material.

**[Take the full Knowledge Check →](https://mahsa-teimourikia.github.io/awsome-ai-agents/quiz/)**

## What is an AI agent?

An AI agent combines a model with instructions, tools, state or memory, and a
control loop so it can pursue a goal over multiple steps. An agentic workflow
uses similar parts but keeps more of the path explicit in code. Production
systems add identity, policy, budgets, evaluation, tracing, recovery, and human
oversight around the model.

![AI agent loop showing the user goal, model, tools, environment feedback, memory, guardrails, and evaluation](assets/agent-loop.svg)

Start with the least autonomous design that reliably solves the task:

| Choose | When it fits |
| --- | --- |
| Single model call | A well-defined response needs no external action |
| Deterministic workflow | Steps and branches are known and need auditability |
| Agentic workflow | Code owns the path but selected decisions need model judgment |
| Single agent | Tool feedback determines an open-ended path |
| Multi-agent system | Distinct context, tools, parallelism, or independent review measurably help |

## Explore the curriculum

Every topic has a co-located `README.md`, self-contained notebook, and
credential-free `lab.py`. The notebooks are the primary theory-and-practice
surface; scripts hold reusable deterministic implementation.

### Beginner — build the mental model

| Step | Topic | Learn and run |
| --- | --- | --- |
| 01 | [AI Agents: Foundations](curriculum/beginner/01-ai-agent-foundations/README.md) | From LLM to agentic system, reliability, autonomy, architecture anatomy |
| 02 | [The Agent Loop](curriculum/beginner/02-agent-loop/README.md) | Observe → reason → act → recover; ReAct, planning, termination, harnesses |
| 03 | [Workflow or Agent?](curriculum/beginner/03-workflow-or-agent/README.md) | Choose deterministic workflows, bounded agents, or teams |
| 04 | [Agent Development Frameworks](curriculum/beginner/04-agent-development-frameworks/README.md) | Compare OpenAI Agents SDK, LangGraph, Google ADK, PydanticAI, CrewAI, and Microsoft Agent Framework |
| 05 | [Computer-Using Agents](curriculum/beginner/05-computer-using-agents/README.md) | Browser, GUI, OS, visual grounding, sandboxing, and recovery |

### Intermediate — make agents dependable

| Step | Topic | Learn and run |
| --- | --- | --- |
| 01 | [Tool Engineering](curriculum/intermediate/01-tool-engineering/README.md) | Schemas, routing, composition, failures, permissions, and least privilege |
| 02 | [Context Engineering](curriculum/intermediate/02-context-engineering/README.md) | Dynamic context, compression, isolation, caching, and poisoning defenses |
| 03 | [Human Approval and Permissions](curriculum/intermediate/03-human-approval-permissions/README.md) | Risk tiers, approvals, intervention, and scoped authority |
| 04 | [Guardrails and Untrusted Content](curriculum/intermediate/04-guardrails-untrusted-content/README.md) | Prompt injection, tool validation, and trusted boundaries |
| 05 | [Agent Evaluation](curriculum/intermediate/05-agent-evaluation/README.md) | Outcome, trajectory, tool, safety, robustness, and operational evaluation |
| 06 | [Trajectory Optimization](curriculum/intermediate/06-trajectory-optimization/README.md) | Cost, latency, reliable shortest paths, and budgets |
| 08 | [Planning and Task Decomposition](curriculum/intermediate/08-planning-task-decomposition/README.md) | Goal decomposition, DAGs, replanning, constraints, and recovery |
| 09 | [Agentic RAG](curriculum/intermediate/09-agentic-rag/README.md) | Retrieval as an agent tool, adaptive search, grounding, and citations |
| 10 | [LangGraph State, Persistence, and Memory](curriculum/intermediate/10-langgraph-state-memory/README.md) | Graph state, checkpoints, interrupts, recovery, and governed memory |

### Advanced — scale intelligence and autonomy responsibly

| Step | Topic | Learn and run |
| --- | --- | --- |
| 01 | [Single vs Multi-Agent Systems](curriculum/advanced/01-single-vs-multi-agent/README.md) | Topologies, coordination, and evidence-based team promotion |
| 02 | [AutoGen Selector Teams](curriculum/advanced/02-autogen-selector-teams/README.md) | Selector-based collaboration and termination controls |
| 03 | [CrewAI Teams](curriculum/advanced/03-crewai-teams/README.md) | Agents, tasks, crews, flows, and constrained collaboration |
| 04 | [Hybrid Production Architecture](curriculum/advanced/04-hybrid-production-architecture/README.md) | Route tasks to workflows, agents, or teams with policy/approval controls |
| 05 | [Incident Response Capstone](curriculum/advanced/05-incident-response-capstone/README.md) | End-to-end architecture, evaluation, observability, and trade-offs |
| 06 | [Agent Memory](curriculum/advanced/06-agent-memory/README.md) | Working, episodic, semantic, procedural, and governed memory |
| 07 | [World Models and Environment Modeling](curriculum/advanced/07-world-models-environment-modeling/README.md) | Simulation, counterfactuals, digital twins, and model-based planning |
| 08 | [Proactive Agents](curriculum/advanced/08-proactive-agents/README.md) | Events, schedules, persistent goals, and permission boundaries |
| 09 | [Model Routing](curriculum/advanced/09-model-routing/README.md) | Capability, cost, latency, fallback, and ensemble routing |
| 10 | [Long-Running and Asynchronous Agents](curriculum/advanced/10-long-running-asynchronous-agents/README.md) | Jobs, pause/resume, checkpoints, queues, and durable execution |
| 11 | [LLM-as-Judge and Agent Judges](curriculum/advanced/11-llm-as-judge-agent-judges/README.md) | Rubrics, pairwise judging, calibration, bias, and ensembles |
| 12 | [Agent Benchmarks](curriculum/advanced/12-agent-benchmarks/README.md) | SWE-bench, WebArena, BrowserGym, GAIA, τ-bench, OSWorld, and enterprise benchmarks |
| 13 | [MCP: Model Context Protocol](curriculum/advanced/13-mcp-model-context-protocol/README.md) | Tools, resources, prompts, gateways, security, and interoperability |
| 14 | [Agent Skills](curriculum/advanced/14-agent-skills/README.md) | Procedural knowledge, dynamic loading, composition, MCP, and subagents |
| 15 | [Designing Reliable Agentic Systems](curriculum/advanced/15-designing-reliable-agentic-systems/README.md) | Core engineering trade-offs and reliable system design |
| 16 | [Human + Multi-Agent Organizations](curriculum/advanced/16-human-multi-agent-organizations/README.md) | Delegation, management, supervision, and mixed teams |
| 17 | [Agentic Enterprise Architecture](curriculum/advanced/17-agentic-enterprise-architecture/README.md) | Registries, gateways, discovery, governance, and FinOps |
| 18 | [Agentic Software Engineering](curriculum/advanced/18-agentic-software-engineering/README.md) | Repository understanding, coding agents, tests, review, and CI/CD |
| 19 | [Embodied Agents and Robotics](curriculum/advanced/19-embodied-agents-robotics/README.md) | VLA, simulation, feedback, and physical-world safety |
| 20 | [Multimodal Agents](curriculum/advanced/20-multimodal-agents/README.md) | Vision, audio, documents, UI, sensors, memory, and tools |
| 21 | [Cost, Latency, and Agent Economics](curriculum/advanced/21-cost-latency-agent-economics/README.md) | Budgets, caching, routing, and cost per safe success |
| 22 | [Production Agent Architecture](curriculum/advanced/22-production-agent-architecture/README.md) | Gateways, sessions, queues, scaling, and disaster recovery |
| 23 | [Agent Governance and Responsible AI](curriculum/advanced/23-agent-governance-responsible-ai/README.md) | Inventory, ownership, risk, lifecycle, and incident response |
| 24 | [Guardrails and Policy Enforcement](curriculum/advanced/24-guardrails-policy-enforcement/README.md) | Layered validation, limits, sandboxing, and kill switches |
| 25 | [Agent Identity and Authorization](curriculum/advanced/25-agent-identity-authorization/README.md) | Delegated authority, non-human identity, scopes, and audit |
| 26 | [Agent Security](curriculum/advanced/26-agent-security/README.md) | Injection, poisoning, exfiltration, supply chain, and excessive agency |
| 27 | [Agent Observability](curriculum/advanced/27-agent-observability/README.md) | Traces, trajectories, costs, replay, debugging, and dashboards |
| 28 | [Human-Agent Collaboration](curriculum/advanced/28-human-agent-collaboration/README.md) | HITL/HOTL, intervention, escalation, trust, and autonomy boundaries |
| 29 | [Agent Orchestration](curriculum/advanced/29-agent-orchestration/README.md) | Graphs, queues, checkpoints, approvals, recovery, and durable execution |
| 30 | [Agent Communication and Coordination](curriculum/advanced/30-agent-communication-coordination/README.md) | Messaging, blackboards, delegation, consensus, conflict, and team design |
| 31 | [The Agent Protocol Stack](curriculum/advanced/31-agent-protocol-stack/README.md) | MCP, A2A, AG-UI, A2UI, UCP, AP2, and interoperable boundaries |

For a directory-level view, use the [full curriculum map](COURSE_MAP.md).

## How to use a lesson locally

Each topic folder contains:

```text
curriculum/<level>/<topic>/
├── README.md     # guided theory, diagrams, references, and exercises
├── *.ipynb       # self-contained notebook: theory and implementation together
└── lab.py        # deterministic reusable implementation
```

Clone the repository, create a Python environment, and install the project
dependencies listed in the relevant topic or repository setup guide. Run the
lab first, then open the notebook:

```bash
python curriculum/beginner/02-agent-loop/lab.py
jupyter notebook curriculum/beginner/02-agent-loop/
```

Default labs are designed to run without credentials or external side effects.
Provider-specific extensions are explicitly marked and should use your own
environment variables and scoped credentials.

## Curated resources

### Primary learning resources

- [OpenAI: A Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Hugging Face Agents Course](https://huggingface.co/learn/agents-course/)
- [ReAct paper](https://arxiv.org/abs/2210.03629)
- [Lilian Weng: LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)

### Frameworks and protocols

- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- [AutoGen](https://microsoft.github.io/autogen/stable/)
- [CrewAI](https://docs.crewai.com/)
- [Google ADK](https://google.github.io/adk-docs/)
- [PydanticAI](https://ai.pydantic.dev/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Agent2Agent Protocol](https://a2a-protocol.org/latest/)
- [Agent Skills specification](https://github.com/agentskills/agentskills)

### Production and security

- [OpenTelemetry](https://opentelemetry.io/docs/)
- [OWASP Agentic Applications Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [SWE-bench](https://www.swebench.com/), [WebArena](https://webarena.dev/), [OSWorld](https://os-world.github.io/), [GAIA](https://huggingface.co/gaia-benchmark), and [τ-bench](https://github.com/sierra-research/tau-bench)

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before
opening a pull request. Prefer primary research, official documentation, and
maintained open-source projects. Add material through the relevant curriculum
topic so theory, notebook, lab, Hub entry, and checkpoint stay aligned.

## License

This repository is licensed under the [MIT License](LICENSE).
