export const learningPath = [
  {
    "id": "b1",
    "title": "AI Agent Foundations",
    "description": "Master the core vocabulary: distinguish between LLMs, chatbots, assistants, agents, and agentic workflows. Understand why reliability is a system property, not a prompt property.",
    "material": "../curriculum/beginner/01-ai-agent-foundations/README.md",
    "notebook": "../curriculum/beginner/01-ai-agent-foundations/01_agent_foundations.ipynb",
    "category": "Beginner - AI Agent Foundations",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "b2",
    "title": "The Agent Loop",
    "description": "Move beyond basic ReAct loops. Learn how SOTA loops use strict JSON Tool Calling and State Machines (like LangGraph) to prevent regex hallucination and enable time travel/persisted state.",
    "material": "../curriculum/beginner/02-agent-loop/README.md",
    "notebook": "../curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
    "category": "Beginner - The Agent Loop",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "b3",
    "title": "Workflow vs Agent",
    "description": "Discover why Enterprise production systems favor Agentic Workflows (deterministic DAGs) over pure non-deterministic Agents to maximize reliability while minimizing costs.",
    "material": "../curriculum/beginner/03-workflow-or-agent/README.md",
    "notebook": "../curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
    "category": "Beginner - Workflow vs Agent",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "b4",
    "title": "Agent Development Frameworks",
    "description": "Explore the vast framework landscape. Compare orchestration libraries (LangGraph, CrewAI) and determine which SOTA architecture matches your specific use case.",
    "material": "../curriculum/beginner/05-agent-development-frameworks/README.md",
    "notebook": "../curriculum/beginner/05-agent-development-frameworks/05_agent_development_frameworks.ipynb",
    "category": "Beginner - Agent Development Frameworks",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "b5",
    "title": "Computer-Using Agents",
    "description": "Bridge the gap between LLMs and UI. Learn how OmniParser prevents spatial hallucination using bounding boxes, and why Accessibility Trees (AXTrees) are vastly superior to raw DOM inputs.",
    "material": "../curriculum/beginner/07-computer-using-agents/README.md",
    "notebook": "../curriculum/beginner/07-computer-using-agents/07_computer_using_agents.ipynb",
    "category": "Beginner - Computer-Using Agents",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i1",
    "title": "Tool Engineering",
    "description": "Design narrow, single-purpose tools with explicit JSON schema contracts. Master Typed Error handling to let agents self-correct without parsing chaotic stack traces.",
    "material": "../curriculum/intermediate/01-tool-engineering/README.md",
    "notebook": "../curriculum/intermediate/01-tool-engineering/01_tool_engineering.ipynb",
    "category": "Intermediate - Tool Engineering",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i2",
    "title": "Context Engineering",
    "description": "Control the exact knowledge boundaries of an agent. Prevent token bloat, manage prompt injection risks, and dynamically load only the context necessary for the current state.",
    "material": "../curriculum/intermediate/02-context-engineering/README.md",
    "notebook": "../curriculum/intermediate/02-context-engineering/02_context_engineering.ipynb",
    "category": "Intermediate - Context Engineering",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i3",
    "title": "Human Approval & Permissions",
    "description": "Build enterprise-grade HITL (Human-in-the-Loop) flows. Learn why strict Idempotency Keys are mandatory to prevent catastrophic retries when models mutate state.",
    "material": "../curriculum/intermediate/03-human-approval-permissions/README.md",
    "notebook": "../curriculum/intermediate/03-human-approval-permissions/03_human_approval_permissions.ipynb",
    "category": "Intermediate - Human Approval & Permissions",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i4",
    "title": "Guardrails & Untrusted Content",
    "description": "Defend against prompt injection and malicious output. Implement strict output validation, regex sanitization, and isolated sandboxes before action execution.",
    "material": "../curriculum/intermediate/04-guardrails-untrusted-content/README.md",
    "notebook": "../curriculum/intermediate/04-guardrails-untrusted-content/04_guardrails_untrusted_content.ipynb",
    "category": "Intermediate - Guardrails & Untrusted Content",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i5",
    "title": "Agent Evaluation",
    "description": "Stop guessing about agent performance. Learn SOTA scoring techniques, LLM-as-a-judge patterns, and how to build regression suites for autonomous reasoning.",
    "material": "../curriculum/intermediate/05-agent-evaluation/README.md",
    "notebook": "../curriculum/intermediate/05-agent-evaluation/05_agent_evaluation.ipynb",
    "category": "Intermediate - Agent Evaluation",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i6",
    "title": "Trajectory Optimization",
    "description": "Optimize the path an agent takes. Use Few-Shot examples in prompts, tune system instructions, and enforce bounded retries to prevent runaway inference loops.",
    "material": "../curriculum/intermediate/06-trajectory-optimization/README.md",
    "notebook": "../curriculum/intermediate/06-trajectory-optimization/06_trajectory_optimization.ipynb",
    "category": "Intermediate - Trajectory Optimization",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "LangGraph"
    ]
  },
  {
    "id": "i8",
    "title": "Planning & Task Decomposition",
    "description": "Build a bounded research DAG with typed contracts, application-owned capability checks, atomic replanning, provenance, and checkpoint-gated completion.",
    "material": "../curriculum/intermediate/08-planning-task-decomposition/README.md",
    "notebook": "../curriculum/intermediate/08-planning-task-decomposition/08_planning_task_decomposition.ipynb",
    "category": "Intermediate - Planning & Task Decomposition",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "Validated DAG scheduling"
    ]
  },
  {
    "id": "i9",
    "title": "Agentic RAG",
    "description": "Build a bounded multi-source retrieval controller that validates routes, measures evidence sufficiency, verifies citations, and safely abstains.",
    "material": "../curriculum/intermediate/09-agentic-rag/README.md",
    "notebook": "../curriculum/intermediate/09-agentic-rag/09_agentic_rag.ipynb",
    "category": "Intermediate - Agentic RAG",
    "minutes": 60,
    "technologies": [
      "Python",
      "Pydantic",
      "Framework-neutral retrieval policy"
    ]
  },
  {
    "id": "i10",
    "title": "Governed State, Persistence & Memory",
    "description": "Build tenant-scoped durable checkpoints, replay-safe resume, structured approval interrupts, governed long-term memory, and redacted event streams.",
    "material": "../curriculum/intermediate/10-langgraph-state-memory/README.md",
    "notebook": "../curriculum/intermediate/10-langgraph-state-memory/10_langgraph_state.ipynb",
    "category": "Intermediate - State & Memory (LangGraph)",
    "minutes": 150,
    "technologies": [
      "Python",
      "Pydantic",
      "SQLite",
      "LangGraph (optional)"
    ]
  },
  {
    "id": "a1",
    "title": "Single vs Multi-Agent Architecture Decisions",
    "description": "Compare single agents, dynamic tools, pipelines, managers, handoffs, and parallel specialists on one measured incident.",
    "material": "../curriculum/advanced/01-single-vs-multi-agent/README.md",
    "notebook": "../curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb",
    "category": "Advanced - Architecture Decisions",
    "minutes": 120,
    "technologies": [
      "Python",
      "Pydantic",
      "Deterministic evaluation"
    ]
  },
  {
    "id": "a2",
    "title": "Bounded AutoGen Selector Teams",
    "description": "Route a governed incident through validated eligible speakers, typed evidence, and bounded termination.",
    "material": "../curriculum/advanced/02-autogen-selector-teams/README.md",
    "notebook": "../curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb",
    "category": "Advanced - AutoGen Selector Teams",
    "minutes": 120,
    "technologies": [
      "Python",
      "Pydantic",
      "AutoGen AgentChat 0.7.5"
    ]
  },
  {
    "id": "a3",
    "title": "Crewai teams",
    "description": "Advanced exploration of Crewai teams.",
    "material": "../curriculum/advanced/03-crewai-teams/README.md",
    "notebook": null,
    "category": "Advanced - Crewai teams",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a4",
    "title": "Hybrid production architecture",
    "description": "Advanced exploration of Hybrid production architecture.",
    "material": "../curriculum/advanced/04-hybrid-production-architecture/README.md",
    "notebook": null,
    "category": "Advanced - Hybrid production architecture",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a5",
    "title": "Incident response",
    "description": "Advanced exploration of Incident response.",
    "material": "../curriculum/advanced/05-incident-response/README.md",
    "notebook": null,
    "category": "Advanced - Incident response",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a6",
    "title": "Agent memory",
    "description": "Advanced exploration of Agent memory.",
    "material": "../curriculum/advanced/06-agent-memory/README.md",
    "notebook": null,
    "category": "Advanced - Agent memory",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a7",
    "title": "World models environment modeling",
    "description": "Advanced exploration of World models environment modeling.",
    "material": "../curriculum/advanced/07-world-models-environment-modeling/README.md",
    "notebook": null,
    "category": "Advanced - World models environment modeling",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a8",
    "title": "Proactive agents",
    "description": "Advanced exploration of Proactive agents.",
    "material": "../curriculum/advanced/08-proactive-agents/README.md",
    "notebook": null,
    "category": "Advanced - Proactive agents",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a9",
    "title": "Model routing",
    "description": "Advanced exploration of Model routing.",
    "material": "../curriculum/advanced/09-model-routing/README.md",
    "notebook": null,
    "category": "Advanced - Model routing",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a10",
    "title": "Long running asynchronous agents",
    "description": "Advanced exploration of Long running asynchronous agents.",
    "material": "../curriculum/advanced/10-long-running-asynchronous-agents/README.md",
    "notebook": null,
    "category": "Advanced - Long running asynchronous agents",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a11",
    "title": "Llm as judge agent judges",
    "description": "Advanced exploration of Llm as judge agent judges.",
    "material": "../curriculum/advanced/11-llm-as-judge-agent-judges/README.md",
    "notebook": null,
    "category": "Advanced - Llm as judge agent judges",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a12",
    "title": "Agent benchmarks",
    "description": "Advanced exploration of Agent benchmarks.",
    "material": "../curriculum/advanced/12-agent-benchmarks/README.md",
    "notebook": null,
    "category": "Advanced - Agent benchmarks",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a13",
    "title": "Mcp model context protocol",
    "description": "Advanced exploration of Mcp model context protocol.",
    "material": "../curriculum/advanced/13-mcp-model-context-protocol/README.md",
    "notebook": null,
    "category": "Advanced - Mcp model context protocol",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a14",
    "title": "Agent skills",
    "description": "Advanced exploration of Agent skills.",
    "material": "../curriculum/advanced/14-agent-skills/README.md",
    "notebook": null,
    "category": "Advanced - Agent skills",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a15",
    "title": "Designing reliable agentic systems",
    "description": "Advanced exploration of Designing reliable agentic systems.",
    "material": "../curriculum/advanced/15-designing-reliable-agentic-systems/README.md",
    "notebook": null,
    "category": "Advanced - Designing reliable agentic systems",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a16",
    "title": "Human multi agent organizations",
    "description": "Advanced exploration of Human multi agent organizations.",
    "material": "../curriculum/advanced/16-human-multi-agent-organizations/README.md",
    "notebook": null,
    "category": "Advanced - Human multi agent organizations",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a17",
    "title": "Agentic enterprise architecture",
    "description": "Advanced exploration of Agentic enterprise architecture.",
    "material": "../curriculum/advanced/17-agentic-enterprise-architecture/README.md",
    "notebook": null,
    "category": "Advanced - Agentic enterprise architecture",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a18",
    "title": "Agentic software engineering",
    "description": "Advanced exploration of Agentic software engineering.",
    "material": "../curriculum/advanced/18-agentic-software-engineering/README.md",
    "notebook": null,
    "category": "Advanced - Agentic software engineering",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a19",
    "title": "Embodied agents robotics",
    "description": "Advanced exploration of Embodied agents robotics.",
    "material": "../curriculum/advanced/19-embodied-agents-robotics/README.md",
    "notebook": null,
    "category": "Advanced - Embodied agents robotics",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a20",
    "title": "Multimodal agents",
    "description": "Advanced exploration of Multimodal agents.",
    "material": "../curriculum/advanced/20-multimodal-agents/README.md",
    "notebook": null,
    "category": "Advanced - Multimodal agents",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a21",
    "title": "Cost latency agent economics",
    "description": "Advanced exploration of Cost latency agent economics.",
    "material": "../curriculum/advanced/21-cost-latency-agent-economics/README.md",
    "notebook": null,
    "category": "Advanced - Cost latency agent economics",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a22",
    "title": "Production agent architecture",
    "description": "Advanced exploration of Production agent architecture.",
    "material": "../curriculum/advanced/22-production-agent-architecture/README.md",
    "notebook": null,
    "category": "Advanced - Production agent architecture",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a23",
    "title": "Agent governance responsible ai",
    "description": "Advanced exploration of Agent governance responsible ai.",
    "material": "../curriculum/advanced/23-agent-governance-responsible-ai/README.md",
    "notebook": null,
    "category": "Advanced - Agent governance responsible ai",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a24",
    "title": "Guardrails policy enforcement",
    "description": "Advanced exploration of Guardrails policy enforcement.",
    "material": "../curriculum/advanced/24-guardrails-policy-enforcement/README.md",
    "notebook": null,
    "category": "Advanced - Guardrails policy enforcement",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a25",
    "title": "Agent identity authorization",
    "description": "Advanced exploration of Agent identity authorization.",
    "material": "../curriculum/advanced/25-agent-identity-authorization/README.md",
    "notebook": null,
    "category": "Advanced - Agent identity authorization",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a26",
    "title": "Agent security",
    "description": "Advanced exploration of Agent security.",
    "material": "../curriculum/advanced/26-agent-security/README.md",
    "notebook": null,
    "category": "Advanced - Agent security",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a27",
    "title": "Agent observability",
    "description": "Advanced exploration of Agent observability.",
    "material": "../curriculum/advanced/27-agent-observability/README.md",
    "notebook": null,
    "category": "Advanced - Agent observability",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a28",
    "title": "Human agent collaboration",
    "description": "Advanced exploration of Human agent collaboration.",
    "material": "../curriculum/advanced/28-human-agent-collaboration/README.md",
    "notebook": null,
    "category": "Advanced - Human agent collaboration",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a29",
    "title": "Agent orchestration",
    "description": "Advanced exploration of Agent orchestration.",
    "material": "../curriculum/advanced/29-agent-orchestration/README.md",
    "notebook": null,
    "category": "Advanced - Agent orchestration",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a30",
    "title": "Agent communication coordination",
    "description": "Advanced exploration of Agent communication coordination.",
    "material": "../curriculum/advanced/30-agent-communication-coordination/README.md",
    "notebook": null,
    "category": "Advanced - Agent communication coordination",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  },
  {
    "id": "a31",
    "title": "Agent protocol stack",
    "description": "Advanced exploration of Agent protocol stack.",
    "material": "../curriculum/advanced/31-agent-protocol-stack/README.md",
    "notebook": null,
    "category": "Advanced - Agent protocol stack",
    "minutes": 60,
    "technologies": [
      "Python"
    ]
  }
];
