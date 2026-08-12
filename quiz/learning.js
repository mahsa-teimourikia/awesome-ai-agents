export const learningPath = [
  {
    id: "b1",
    title: "AI Agents: foundations",
    description: "Explain the LLM → chatbot → assistant → agent → agentic-system ladder and choose the least autonomous reliable architecture.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: "../curriculum/beginner/01-ai-agent-foundations/01_agent_foundations.ipynb",
    category: "01 - AI Agents: foundations",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "b2",
    title: "The agent loop",
    description: "Design a bounded loop with typed actions, observations, budgets, and terminal states.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "02 - The agent loop",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "b4",
    title: "AgentOps Lab: build the loop yourself",
    description: "Implement the model → tool → observation loop and prove why production agents need explicit step, tool, and cost budgets.",
    material: "../curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
    notebook: "../curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
    category: "03 - AgentOps Lab: build the loop yourself",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "b3",
    title: "Tools and memory",
    description: "Specify a typed, authorized tool and a safe memory-write policy.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "04 - Tools and memory",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i1",
    title: "Workflows versus agents",
    description: "Compare deterministic workflows, agentic workflows, and open-ended agents using explicit trade-offs.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "01 - Workflows versus agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i4",
    title: "AgentOps Lab: agent or workflow?",
    description: "Choose between deterministic workflow, bounded workflow, single agent, and multi-agent team based on problem shape and trajectory cost.",
    material: "../curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
    notebook: "../curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
    category: "02 - AgentOps Lab: agent or workflow?",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i5",
    title: "Agent development frameworks",
    description: "Compare framework-owned mechanics with application-owned policy, then select a framework based on tools, output contracts, state, approvals, workflows, or collaboration.",
    material: "../curriculum/beginner/04-agent-development-frameworks/README.md",
    notebook: "../curriculum/beginner/04-agent-development-frameworks/04_openai_agents_sdk_incident_triage.ipynb",
    category: "04 - Agent development frameworks",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "b5",
    title: "Computer-Using Agents",
    description: "Choose API, DOM automation, visual browser use, desktop, or mobile interaction deliberately, then enforce grounding and authorization before every UI action.",
    material: "../curriculum/beginner/05-computer-using-agents/README.md",
    notebook: "../curriculum/beginner/05-computer-using-agents/computer_using_agents.ipynb",
    category: "05 - Computer-Using Agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i6",
    title: "AgentOps Lab: tool engineering",
    description: "Design agent-facing tools with narrow responsibility, structured validation, predictable failures, and explicit boundaries.",
    material: "../curriculum/intermediate/01-tool-engineering/README.md",
    notebook: "../curriculum/intermediate/01-tool-engineering/tool_engineering.ipynb",
    category: "01 - AgentOps Lab: tool engineering",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i13",
    title: "Context engineering for agents",
    description: "Route system policy, dynamic evidence, state, conversation, and external memory just in time while enforcing context isolation and poison quarantine.",
    material: "../curriculum/intermediate/02-context-engineering/README.md",
    notebook: "../curriculum/intermediate/02-context-engineering/context_engineering.ipynb",
    category: "02 - Context engineering for agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i7",
    title: "LangGraph state, persistence, and memory",
    description: "Distinguish thread-scoped state from long-term memory; recover safely after failure; and prevent unverified memory from biasing diagnosis.",
    material: "../curriculum/intermediate/10-langgraph-state-memory/README.md",
    notebook: "../curriculum/intermediate/10-langgraph-state-memory/langgraph_state_memory.ipynb",
    category: "10 - LangGraph state, persistence, and memory",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i8",
    title: "Human approval and permissions",
    description: "Apply READ, PROPOSE, and EXECUTE-WITH-APPROVAL capabilities; validate reviewer identity and tenant scope; and make approval resumes idempotent and auditable.",
    material: "../curriculum/intermediate/03-human-approval-permissions/README.md",
    notebook: "../curriculum/intermediate/03-human-approval-permissions/human_approval_permissions.ipynb",
    category: "03 - Human approval and permissions",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i9",
    title: "Guardrails and untrusted content",
    description: "Explain why external input, retrieved content, and tool responses cannot authorize operational actions—and prove containment even when detection is imperfect.",
    material: "../curriculum/intermediate/04-guardrails-untrusted-content/README.md",
    notebook: "../curriculum/intermediate/04-guardrails-untrusted-content/guardrails_untrusted_content.ipynb",
    category: "04 - Guardrails and untrusted content",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i10",
    title: "Agent evaluation: outcomes and trajectories",
    description: "Build a representative evaluation dataset, grade answers and traces, hard-fail unsafe behavior, compare baselines, and monitor cost per successful task.",
    material: "../curriculum/intermediate/05-agent-evaluation/README.md",
    notebook: "../curriculum/intermediate/05-agent-evaluation/agent_evaluation.ipynb",
    category: "05 - Agent evaluation: outcomes and trajectories",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i11",
    title: "Trajectory optimization",
    description: "Optimize for the shortest reliable trajectory to a correct result while preserving evidence, safety, recovery, and tenant scope.",
    material: "../curriculum/intermediate/06-trajectory-optimization/README.md",
    notebook: "../curriculum/intermediate/06-trajectory-optimization/trajectory_optimization.ipynb",
    category: "06 - Trajectory optimization",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i12",
    title: "Planning and task decomposition",
    description: "Build a constrained plan-and-execute system with goal decomposition, DAG scheduling, checkpoints, bounded replanning, and explicit escalation.",
    material: "../curriculum/intermediate/08-planning-task-decomposition/README.md",
    notebook: "../curriculum/intermediate/08-planning-task-decomposition/planning_task_decomposition.ipynb",
    category: "08 - Planning and task decomposition",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i14",
    title: "Agentic RAG / Knowledge-Grounded Agents",
    description: "Design bounded retrieval agents that choose search, SQL, graph, or web evidence deliberately and verify citations before grounded action.",
    material: "../curriculum/intermediate/09-agentic-rag/README.md",
    notebook: "../curriculum/intermediate/09-agentic-rag/agentic_rag.ipynb",
    category: "09 - Agentic RAG / Knowledge-Grounded Agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i2",
    title: "Architecture patterns",
    description: "Select a topology, define contracts, and identify its failure modes before implementation.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "10 - Architecture patterns",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "i3",
    title: "Evaluation and security",
    description: "Create a release gate that catches unsafe actions and unsuccessful task trajectories.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "11 - Evaluation and security",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a6",
    title: "Single agent versus multi-agent systems",
    description: "Compare a single investigator with supervisor, router, planner-executor, manager/subagent, hierarchy, peer, blackboard, debate, generator/critic, sequential, and parallel patterns using accuracy, safety, latency, cost, and coordination evidence.",
    material: "../curriculum/advanced/01-single-vs-multi-agent/README.md",
    notebook: "../curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb",
    category: "01 - Single agent versus multi-agent systems",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a7",
    title: "AgentOps Lab: AutoGen selector team",
    description: "Explain how selector-based team coordination works, why shared context can create loops, and how max team messages, per-agent turn budgets, and ownership contracts keep the system bounded.",
    material: "../curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb",
    notebook: "../curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb",
    category: "02 - AgentOps Lab: AutoGen selector team",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a8",
    title: "AgentOps Lab: CrewAI team",
    description: "Map specialist roles to agents, work products to tasks, and task context to a crew-level incident plan.",
    material: "../curriculum/advanced/03-crewai-teams/03_crewai_teams.ipynb",
    notebook: "../curriculum/advanced/03-crewai-teams/03_crewai_teams.ipynb",
    category: "03 - AgentOps Lab: CrewAI team",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a9",
    title: "AgentOps Lab: hybrid production architecture",
    description: "Design a production architecture that routes each task to the least autonomous reliable path instead of using one giant autonomous agent.",
    material: "../curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
    notebook: "../curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
    category: "04 - AgentOps Lab: hybrid production architecture",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a10",
    title: "AgentOps Lab: final capstone",
    description: "Combine architecture selection, tool definitions, instructions, state, memory policy, permissions, HITL, guardrails, termination, evaluation, trace analysis, cost/latency analysis, and single-vs-multi-agent comparison.",
    material: "../curriculum/advanced/05-incident-response-capstone/05_incident_response_capstone.ipynb",
    notebook: "../curriculum/advanced/05-incident-response-capstone/05_incident_response_capstone.ipynb",
    category: "05 - AgentOps Lab: final capstone",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a11",
    title: "Agent memory",
    description: "Design scoped, attributable memory with consolidation, forgetting, contradiction resolution, ranked retrieval, personalization, and privacy controls.",
    material: "../curriculum/advanced/06-agent-memory/README.md",
    notebook: "../curriculum/advanced/06-agent-memory/agent_memory.ipynb",
    category: "06 - Agent memory",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a12",
    title: "World models and environment modeling",
    description: "Design internal representations, simulations, counterfactual rollouts, digital twins, and model-based planning with uncertainty, safety, and real-world validation gates.",
    material: "../curriculum/advanced/07-world-models-environment-modeling/README.md",
    notebook: "../curriculum/advanced/07-world-models-environment-modeling/world_models_environment_modeling.ipynb",
    category: "07 - World models and environment modeling",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a13",
    title: "Proactive agents",
    description: "Design event-driven, scheduled, trigger-based, monitoring, background, and notification agents with goal persistence, opt-out, permissions, and operational budgets.",
    material: "../curriculum/advanced/08-proactive-agents/README.md",
    notebook: "../curriculum/advanced/08-proactive-agents/proactive_agents.ipynb",
    category: "08 - Proactive agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a14",
    title: "Model routing",
    description: "Route simple tasks to fast models, complex investigations to reasoning models, visual evidence to multimodal models, and repository work to coding models—then evaluate cascades, fallbacks, and ensembles.",
    material: "../curriculum/advanced/09-model-routing/README.md",
    notebook: "../curriculum/advanced/09-model-routing/model_routing.ipynb",
    category: "09 - Model routing",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a15",
    title: "Long-running and asynchronous agents",
    description: "Design background/scheduled/event-driven work with pause/resume, checkpointing, human approval, state recovery, cancellation, idempotency, and durable execution controls.",
    material: "../curriculum/advanced/10-long-running-asynchronous-agents/README.md",
    notebook: "../curriculum/advanced/10-long-running-asynchronous-agents/long_running_asynchronous_agents.ipynb",
    category: "10 - Long-running and asynchronous agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a16",
    title: "LLM-as-Judge and agent judges",
    description: "Design rubric, pairwise, trajectory/tool, critic, calibrated, human-aligned, and ensemble evaluation without treating one judge as ground truth.",
    material: "../curriculum/advanced/11-llm-as-judge-agent-judges/README.md",
    notebook: "../curriculum/advanced/11-llm-as-judge-agent-judges/llm_as_judge_agent_judges.ipynb",
    category: "11 - LLM-as-Judge and agent judges",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a17",
    title: "Agent benchmarks",
    description: "Select, reproduce, inspect, and extend SWE-bench, WebArena, BrowserGym, GAIA, τ-bench, OSWorld, AgentBench, domain, and custom enterprise benchmarks for a real release decision.",
    material: "../curriculum/advanced/12-agent-benchmarks/README.md",
    notebook: null,
    category: "12 - Agent benchmarks",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a18",
    title: "MCP: Model Context Protocol",
    description: "Explain MCP architecture, clients/servers, tools/resources/prompts, capability negotiation, remote MCP, authentication/authorization, gateways, enterprise controls, security, and safe agent integration within the broader protocol ecosystem.",
    material: "../curriculum/advanced/13-mcp-model-context-protocol/README.md",
    notebook: "../curriculum/advanced/13-mcp-model-context-protocol/mcp_model_context_protocol.ipynb",
    category: "13 - MCP: Model Context Protocol",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a19",
    title: "Agent Skills",
    description: "Distinguish tools from skills; design descriptions, discovery, libraries, dynamic loading, composition, routing, governance, MCP integration, and subagent delegation.",
    material: "../curriculum/advanced/14-agent-skills/README.md",
    notebook: "../curriculum/advanced/14-agent-skills/agent_skills.ipynb",
    category: "14 - Agent Skills",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e1",
    title: "Designing reliable agentic systems",
    description: "Select workflow, bounded agent, stateful graph, or specialist team using measurable trade-offs, then surround it with application-owned authorization, budgets, evaluation, and recovery controls.",
    material: "../curriculum/advanced/15-designing-reliable-agentic-systems/README.md",
    notebook: "../curriculum/advanced/15-designing-reliable-agentic-systems/designing_reliable_agentic_systems.ipynb",
    category: "01 - Designing reliable agentic systems",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e2",
    title: "Human + multi-agent organizations",
    description: "Create a manager-led human/agent organization with scoped work orders, least-privilege specialists, typed artifacts, reviewable delegation, policy boundaries, and explicit human authority over consequential action.",
    material: "../curriculum/advanced/16-human-multi-agent-organizations/README.md",
    notebook: "../curriculum/advanced/16-human-multi-agent-organizations/human_multi_agent_organizations.ipynb",
    category: "02 - Human + multi-agent organizations",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e3",
    title: "Agentic enterprise architecture",
    description: "Design a control plane for agent and tool catalogs, MCP registry/gateway, identity-bound discovery, shared knowledge, enterprise orchestration, governance, observability, evaluation, and FinOps.",
    material: "../curriculum/advanced/17-agentic-enterprise-architecture/README.md",
    notebook: "../curriculum/advanced/17-agentic-enterprise-architecture/agentic_enterprise_architecture.ipynb",
    category: "03 - Agentic enterprise architecture",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e4",
    title: "Agentic software engineering",
    description: "Design and evaluate a long-horizon coding-agent loop for repository understanding, code search, planning, editing, terminal tools, tests, debugging, review, PR preparation, CI, and benchmarks.",
    material: "../curriculum/advanced/18-agentic-software-engineering/README.md",
    notebook: "../curriculum/advanced/18-agentic-software-engineering/agentic_software_engineering.ipynb",
    category: "04 - Agentic software engineering",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e5",
    title: "Embodied agents and robotics",
    description: "Explain vision-language-action models, robot navigation/manipulation, embodied planning, physical feedback, simulation, and independent safety supervision.",
    material: "../curriculum/advanced/19-embodied-agents-robotics/README.md",
    notebook: "../curriculum/advanced/19-embodied-agents-robotics/embodied_agents_robotics.ipynb",
    category: "05 - Embodied agents and robotics",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e6",
    title: "Multimodal agents",
    description: "Build provenance-aware multimodal evidence, memory, and tool boundaries across images, audio, video, documents, screens, speech, and sensor data.",
    material: "../curriculum/advanced/20-multimodal-agents/README.md",
    notebook: "../curriculum/advanced/20-multimodal-agents/multimodal_agents.ipynb",
    category: "06 - Multimodal agents",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e7",
    title: "Cost, latency, and agent economics",
    description: "Set token, action, reasoning, spend, and latency budgets; choose cache, sequential, parallel, speculative, and routed paths; and evaluate cost, quality, and p95 latency together.",
    material: "../curriculum/advanced/21-cost-latency-agent-economics/README.md",
    notebook: "../curriculum/advanced/21-cost-latency-agent-economics/agent_economics.ipynb",
    category: "07 - Cost, latency, and agent economics",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e8",
    title: "Production agent architecture",
    description: "Separate stateless and stateful components; design sessions, persistence, queues, async execution, checkpoints, caching, retries, rate limits, autoscaling, and disaster recovery.",
    material: "../curriculum/advanced/22-production-agent-architecture/README.md",
    notebook: "../curriculum/advanced/22-production-agent-architecture/production_agent_architecture.ipynb",
    category: "08 - Production agent architecture",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e9",
    title: "Agent governance and responsible AI",
    description: "Build an agent inventory, assign ownership, classify risk/autonomy/data/tools, gate changes, preserve auditability, manage oversight, respond to incidents, and retire safely.",
    material: "../curriculum/advanced/23-agent-governance-responsible-ai/README.md",
    notebook: "../curriculum/advanced/23-agent-governance-responsible-ai/agent_governance_responsible_ai.ipynb",
    category: "09 - Agent governance and responsible AI",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e10",
    title: "Guardrails and policy enforcement",
    description: "Design policy engines, structured validation, allow/deny lists, permissions, sandboxing, rate/budget limits, approvals, kill switches, and auditable decisions.",
    material: "../curriculum/advanced/24-guardrails-policy-enforcement/README.md",
    notebook: "../curriculum/advanced/24-guardrails-policy-enforcement/guardrails_policy_enforcement.ipynb",
    category: "10 - Guardrails and policy enforcement",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e11",
    title: "Agent identity and authorization",
    description: "Separate user and agent identity; apply delegated OAuth/OIDC-style authority, capabilities, least privilege, temporary credentials, tool/peer authentication, audit, and policy enforcement.",
    material: "../curriculum/advanced/25-agent-identity-authorization/README.md",
    notebook: "../curriculum/advanced/25-agent-identity-authorization/agent_identity_authorization.ipynb",
    category: "11 - Agent identity and authorization",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e12",
    title: "Agent security",
    description: "Threat-model direct/indirect injection, hijacking, poisoned tools/MCP/memory/context, credential/exfiltration/privilege abuse, cross-agent/supply-chain attacks, and excessive agency with layered containment.",
    material: "../curriculum/advanced/26-agent-security/README.md",
    notebook: "../curriculum/advanced/26-agent-security/agent_security.ipynb",
    category: "12 - Agent security",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e13",
    title: "Agent observability",
    description: "Instrument distributed traces, agent trajectories, tool calls, token/cost/latency, state/context, failures, replay, monitoring, and dashboards with privacy-aware evidence.",
    material: "../curriculum/advanced/27-agent-observability/README.md",
    notebook: "../curriculum/advanced/27-agent-observability/agent_observability.ipynb",
    category: "13 - Agent observability",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e14",
    title: "Human-agent collaboration",
    description: "Design HITL/HOTL/autonomous boundaries, approval and confidence escalation, intervention, supervision, mixed initiative, handoffs, explainable actions, trust calibration, and revocable autonomy.",
    material: "../curriculum/advanced/28-human-agent-collaboration/README.md",
    notebook: "../curriculum/advanced/28-human-agent-collaboration/human_agent_collaboration.ipynb",
    category: "14 - Human-agent collaboration",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e15",
    title: "Agent orchestration",
    description: "Design orchestrators, routers, state machines, graph/DAG workflows, queues/events/schedules, checkpoints, durable execution, parallel joins, approval nodes, and recovery.",
    material: "../curriculum/advanced/29-agent-orchestration/README.md",
    notebook: "../curriculum/advanced/29-agent-orchestration/agent_orchestration.ipynb",
    category: "15 - Agent orchestration",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e16",
    title: "Agent communication and coordination",
    description: "Design messaging, shared state/blackboards, delegation, handoffs, negotiation, consensus/voting/debate, discovery, allocation, conflict resolution, and evidence-based team selection.",
    material: "../curriculum/advanced/30-agent-communication-coordination/README.md",
    notebook: "../curriculum/advanced/30-agent-communication-coordination/agent_communication_coordination.ipynb",
    category: "16 - Agent communication and coordination",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "e17",
    title: "The agent protocol stack",
    description: "Explain MCP, A2A, AG-UI, A2UI, UCP, and AP2 boundaries; design trusted discovery/delegation; and keep identity, policy, authorization, audit, and recovery independent of protocol messages.",
    material: "../curriculum/advanced/31-agent-protocol-stack/README.md",
    notebook: "../curriculum/advanced/31-agent-protocol-stack/agent_protocol_stack.ipynb",
    category: "17 - The agent protocol stack",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a1",
    title: "Multi-agent teams",
    description: "Explain when coordination overhead is justified and how to bound delegation.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "06 - Multi-agent teams",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a2",
    title: "Production operations",
    description: "Define operational SLOs and recovery paths for an agentic system.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "07 - Production operations",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a3",
    title: "Interoperability and autonomy",
    description: "Map protocol boundaries and choose where identity, policy, and approval are enforced.",
    material: "../README.md#tools-memory-and-protocols",
    notebook: null,
    category: "08 - Interoperability and autonomy",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a4",
    title: "Safety readiness",
    description: "Turn threat-model findings into a production readiness gate and rollback plan.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "09 - Safety readiness",
    minutes: 60,
    technologies: ["Python"]
  },
  {
    id: "a5",
    title: "Research team capstone",
    description: "Compare a bounded multi-agent team with a simpler single-agent baseline.",
    material: "../curriculum/beginner/01-ai-agent-foundations/README.md",
    notebook: null,
    category: "10 - Research team capstone",
    minutes: 60,
    technologies: ["Python"]
  },
];
