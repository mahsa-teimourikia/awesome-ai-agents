"use client";

import { useEffect, useMemo, useState } from "react";


type Level = "Beginner" | "Intermediate" | "Advanced" | "Enterprise Agent";
type Subject = { id:string; level:Level; step:string; title:string; description:string; time:string; outcome:string; lesson:string; exercise:string; failures:string[]; notebook:string; refs:string[]; code:string; quiz:{q:string; options:string[]; answer:number | number[]}[] };

const guidePaths:Record<string,string> = {
  "b1": "curriculum/beginner/01-ai-agent-foundations/README.md",
  "b2": "curriculum/beginner/01-ai-agent-foundations/README.md#the-agent-loop",
  "b4": "curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
  "b3": "curriculum/beginner/01-ai-agent-foundations/README.md#tools",
  "i1": "curriculum/beginner/03-workflow-or-agent/README.md",
  "i4": "curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
  "i5": "curriculum/beginner/04-agent-development-frameworks/README.md",
  "b5": "curriculum/beginner/05-computer-using-agents/README.md",
  "i6": "curriculum/intermediate/01-tool-engineering/README.md",
  "i13": "curriculum/intermediate/02-context-engineering/README.md",
  "i7": "curriculum/intermediate/10-langgraph-state-memory/README.md",
  "i8": "curriculum/intermediate/03-human-approval-permissions/README.md",
  "i9": "curriculum/intermediate/04-guardrails-untrusted-content/README.md",
  "i10": "curriculum/intermediate/05-agent-evaluation/README.md",
  "i11": "curriculum/intermediate/06-trajectory-optimization/README.md",
  "i12": "curriculum/intermediate/08-planning-task-decomposition/README.md",
  "i14": "curriculum/intermediate/09-agentic-rag/README.md",
  "i2": "curriculum/intermediate/06-trajectory-optimization/README.md",
  "i3": "curriculum/intermediate/05-agent-evaluation/README.md",
  "a6": "curriculum/advanced/01-single-vs-multi-agent/README.md",
  "a7": "curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb",
  "a8": "curriculum/advanced/03-crewai-teams/03_crewai_teams.ipynb",
  "a9": "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
  "a10": "curriculum/advanced/05-incident-response/incident_response.ipynb",
  "a11": "curriculum/advanced/06-agent-memory/README.md",
  "a12": "curriculum/advanced/07-world-models-environment-modeling/README.md",
  "a13": "curriculum/advanced/08-proactive-agents/README.md",
  "a14": "curriculum/advanced/09-model-routing/README.md",
  "a15": "curriculum/advanced/10-long-running-asynchronous-agents/README.md",
  "a16": "curriculum/advanced/11-llm-as-judge-agent-judges/README.md",
  "a17": "curriculum/advanced/12-agent-benchmarks/README.md",
  "a18": "curriculum/advanced/13-mcp-model-context-protocol/README.md",
  "a19": "curriculum/advanced/14-agent-skills/README.md",
  "e1": "curriculum/advanced/15-designing-reliable-agentic-systems/README.md",
  "e2": "curriculum/advanced/16-human-multi-agent-organizations/README.md",
  "e3": "curriculum/advanced/17-agentic-enterprise-architecture/README.md",
  "e4": "curriculum/advanced/18-agentic-software-engineering/README.md",
  "e5": "curriculum/advanced/19-embodied-agents-robotics/README.md",
  "e6": "curriculum/advanced/20-multimodal-agents/README.md",
  "e7": "curriculum/advanced/21-cost-latency-agent-economics/README.md",
  "e8": "curriculum/advanced/22-production-agent-architecture/README.md",
  "e9": "curriculum/advanced/23-agent-governance-responsible-ai/README.md",
  "e10": "curriculum/advanced/24-guardrails-policy-enforcement/README.md",
  "e11": "curriculum/advanced/25-agent-identity-authorization/README.md",
  "e12": "curriculum/advanced/26-agent-security/README.md",
  "e13": "curriculum/advanced/27-agent-observability/README.md",
  "e14": "curriculum/advanced/28-human-agent-collaboration/README.md",
  "e15": "curriculum/advanced/29-agent-orchestration/README.md",
  "e16": "curriculum/advanced/30-agent-communication-coordination/README.md",
  "e17": "curriculum/advanced/31-agent-protocol-stack/README.md",
  "a1": "docs/multi-agent-systems.md",
  "a2": "curriculum/intermediate/05-agent-evaluation/README.md",
  "a3": "README.md#tools-memory-and-protocols",
  "a4": "curriculum/intermediate/05-agent-evaluation/README.md#threat-model",
  "a5": "docs/multi-agent-systems.md"
};

const subjects:Subject[] = [
  {
    "id": "b1",
    "level": "Beginner",
    "step": "01",
    "title": "AI Agents: foundations",
    "description": "Choose automation, workflow, RAG, or a bounded agent before writing an agent loop.",
    "time": "45-60 min",
    "outcome": "Explain the LLM → chatbot → assistant → agent → agentic-system ladder and choose the least autonomous reliable architecture.",
    "lesson": "Use a SaaS support scenario to classify real tasks, trace Goal → Observe → Reason → Plan → Act → Observe → Adapt → Complete, and locate the application policy boundary that keeps model autonomy bounded.",
    "exercise": "Run the deterministic architecture-selection rubric, alter task constraints, and defend why a workflow, RAG assistant, bounded agent, or human-approved route is appropriate.",
    "failures": [],
    "notebook": "curriculum/beginner/01-ai-agent-foundations/01_agent_foundations.ipynb",
    "refs": [
      "curriculum/beginner/01-ai-agent-foundations/README.md",
      "curriculum/beginner/01-ai-agent-foundations/01_agent_foundations.ipynb",
      "https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
      "https://www.anthropic.com/engineering/building-effective-agents",
      "https://arxiv.org/abs/2210.03629"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "b2",
    "level": "Beginner",
    "step": "02",
    "title": "The agent loop",
    "description": "Trace observe → decide → act → observe and make every transition inspectable.",
    "time": "45-60 min",
    "outcome": "Design a bounded loop with typed actions, observations, budgets, and terminal states.",
    "lesson": "Trace observe → decide → act → observe and make every transition inspectable.",
    "exercise": "Trace observe → decide → act → observe and make every transition inspectable.",
    "failures": [],
    "notebook": "curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
    "refs": [
      "curriculum/beginner/01-ai-agent-foundations/README.md#the-agent-loop",
      "https://arxiv.org/abs/2210.03629"
    ],
    "code": "",
    "quiz": [
      {
        "q": "What does a ReAct-style loop do?",
        "options": [
          "Interleaves reasoning with actions and observations",
          "Uses observations to update subsequent decisions",
          "Requires model-weight updates after every tool call",
          "Lets tools gather information from an environment",
          "Guarantees that every trajectory is correct"
        ],
        "answer": [
          0,
          1,
          3
        ]
      }
    ]
  },
  {
    "id": "b4",
    "level": "Beginner",
    "step": "03",
    "title": "AgentOps Lab: build the loop yourself",
    "description": "Investigate checkout failures with a manual tool-calling loop before using an agent framework.",
    "time": "45-60 min",
    "outcome": "Implement the model → tool → observation loop and prove why production agents need explicit step, tool, and cost budgets.",
    "lesson": "Use a fictional SaaS checkout incident to see the core anatomy from the article: model, instructions, tools, state, control loop, observations, and stopping conditions. The notebook deliberately breaks the loop with an overbroad instruction so you can see why budgets belong in application code.",
    "exercise": "Run the deterministic Python loop, inspect the trace, then open the notebook to modify the scenario and test the stopping conditions.",
    "failures": [],
    "notebook": "curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md",
      "curriculum/beginner/02-agent-loop/02_agent_loop.ipynb",
      "https://www.linkedin.com/pulse/building-ai-agents-from-loops-teams-oneplusi-y3atc/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "b3",
    "level": "Beginner",
    "step": "04",
    "title": "Tools and memory",
    "description": "Create narrow tool contracts and separate working state from long-term memory.",
    "time": "45-60 min",
    "outcome": "Specify a typed, authorized tool and a safe memory-write policy.",
    "lesson": "Create narrow tool contracts and separate working state from long-term memory.",
    "exercise": "Create narrow tool contracts and separate working state from long-term memory.",
    "failures": [],
    "notebook": "curriculum/intermediate/01-tool-engineering/tool_engineering.ipynb",
    "refs": [
      "curriculum/beginner/01-ai-agent-foundations/README.md#tools",
      "curriculum/beginner/01-ai-agent-foundations/README.md#state-and-memory"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which properties improve an agent-facing tool contract?",
        "options": [
          "A narrow, unambiguous purpose",
          "Typed input and output schemas",
          "Useful errors and explicit risk metadata",
          "A single tool that performs every available operation",
          "Idempotency or preview support for risky writes"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "i1",
    "level": "Intermediate",
    "step": "01",
    "title": "Workflows versus agents",
    "description": "Choose the least autonomous design that reliably solves the task.",
    "time": "45-60 min",
    "outcome": "Compare deterministic workflows, agentic workflows, and open-ended agents using explicit trade-offs.",
    "lesson": "Choose the least autonomous design that reliably solves the task.",
    "exercise": "Choose the least autonomous design that reliably solves the task.",
    "failures": [],
    "notebook": "curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
    "refs": [
      "curriculum/beginner/03-workflow-or-agent/README.md#workflow-versus-agent",
      "https://www.anthropic.com/engineering/building-effective-agents"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which statements correctly distinguish workflows from agents?",
        "options": [
          "A workflow follows code-defined paths",
          "An agent dynamically directs its process and tool use",
          "A workflow can still contain model decisions",
          "Every multi-step model application is automatically an agent",
          "A fixed workflow may be preferable for predictable tasks"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which practices make a long-running agent loop more reliable?",
        "options": [
          "Checkpoint meaningful state",
          "Represent failures as typed states",
          "Retry every write after any timeout",
          "Cap turns, time, tokens, tool calls, and spend",
          "Record a clear termination reason"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      },
      {
        "q": "What makes a human-approval checkpoint effective?",
        "options": [
          "It occurs before the consequential side effect",
          "It shows the exact action, target, evidence, and expected effect",
          "It supports approve, edit, reject, or redirect outcomes",
          "It asks only a context-free 'Approve?' question",
          "The workflow checkpoints state while waiting"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "When can a multi-agent design be justified?",
        "options": [
          "Independent subtasks benefit from parallel execution",
          "Specialists need distinct context, tools, or policies",
          "Evaluation shows a meaningful gain over a simpler baseline",
          "The architecture looks more impressive in a demo",
          "An orchestrator can define clear delegation contracts"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "i4",
    "level": "Intermediate",
    "step": "02",
    "title": "AgentOps Lab: agent or workflow?",
    "description": "Classify three checkout operations tasks and implement the simplest reliable architecture for each.",
    "time": "45-60 min",
    "outcome": "Choose between deterministic workflow, bounded workflow, single agent, and multi-agent team based on problem shape and trajectory cost.",
    "lesson": "Compare three tasks from the same SaaS checkout scenario. A status report uses known steps, an unhealthy-check flow uses a bounded branch, and a European checkout investigation needs dynamic evidence selection. The lesson operationalizes the article's architecture ladder.",
    "exercise": "Run the Python comparison, inspect the step trajectory for each task, then use the notebook to explain why Task C earns a bounded agent while Task A does not.",
    "failures": [],
    "notebook": "curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md#notebook-02-learning-objectives",
      "curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb",
      "curriculum/beginner/03-workflow-or-agent/README.md#workflow-versus-agent",
      "https://www.linkedin.com/pulse/building-ai-agents-from-loops-teams-oneplusi-y3atc/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i5",
    "level": "Beginner",
    "step": "04",
    "title": "Agent development frameworks",
    "description": "Choose a managed loop, typed output, state graph, workflow runtime, or bounded composition for the actual control-flow problem.",
    "time": "45-60 min",
    "outcome": "Compare framework-owned mechanics with application-owned policy, then select a framework based on tools, output contracts, state, approvals, workflows, or collaboration.",
    "lesson": "The Northstar Commerce scenario now uses six notebooks: OpenAI Agents SDK, Pydantic AI, LangGraph, Google ADK, Microsoft Agent Framework, and CrewAI. Each teaches a scenario chosen for its framework fit while keeping identity, tools, budgets, and approval outside the model.",
    "exercise": "Run the credential-free lab, then complete the framework notebooks and compare traces, evidence gates, workflow/state needs, task contracts, and coordination costs before enabling an optional SDK.",
    "failures": [],
    "notebook": "curriculum/advanced/20-multimodal-agents/multimodal_agents.ipynb",
    "refs": [
      "curriculum/beginner/04-agent-development-frameworks/README.md",
      "curriculum/advanced/20-multimodal-agents/multimodal_agents.ipynb",
      "curriculum/beginner/04-agent-development-frameworks/04_pydanticai_compliance_caseworker.ipynb",
      "curriculum/beginner/04-agent-development-frameworks/04_langgraph_remediation_approval.ipynb",
      "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
      "curriculum/advanced/27-agent-observability/agent_observability.ipynb",
      "curriculum/beginner/04-agent-development-frameworks/04_crewai_incident_response_crew.ipynb",
      "https://learn.microsoft.com/en-gb/agent-framework/",
      "https://docs.crewai.com/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "b5",
    "level": "Beginner",
    "step": "05",
    "title": "Computer-Using Agents",
    "description": "Operate a simulated UI with screenshot-grounded actions, sandbox policy, confirmation, and UI-change recovery.",
    "time": "45-60 min",
    "outcome": "Choose API, DOM automation, visual browser use, desktop, or mobile interaction deliberately, then enforce grounding and authorization before every UI action.",
    "lesson": "The Northstar support scenario starts with an Acme billing case, drafts an escalation after a UI label change, and pauses before the exact submit action. It demonstrates screenshot/accessibility grounding, typed mouse/keyboard-like actions, sandboxing, approval, verification, and bounded recovery.",
    "exercise": "Run the credential-free UI simulation, observe a stale DOM selector fail, recover through semantic visual grounding, test an out-of-bounds click rejection, and inspect the confirmation-gated submit trace.",
    "failures": [],
    "notebook": "curriculum/beginner/05-computer-using-agents/computer_using_agents.ipynb",
    "refs": [
      "curriculum/beginner/05-computer-using-agents/README.md",
      "curriculum/beginner/05-computer-using-agents/computer_using_agents.ipynb",
      "https://developers.openai.com/api/docs/guides/tools-computer-use",
      "https://openai.com/index/introducing-operator/",
      "https://arxiv.org/abs/2404.07972",
      "https://arxiv.org/abs/2307.13854"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which controls should intervene between a computer-use model's proposed click and a consequential UI action?",
        "options": [
          "A fresh observation and a unique grounded target",
          "Origin, authorization, risk, and action-budget validation",
          "A human confirmation bound to the exact commit action when policy requires it",
          "Trusting any instruction visible on the webpage",
          "A post-action state check or safe escalation path"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which statements correctly compare browser automation and visual computer use?",
        "options": [
          "A stable typed API is usually preferable when available",
          "DOM/accessibility automation can be easier to test on an owned app with stable semantic controls",
          "Screenshot-grounded interaction is useful for UI-only or visually meaningful interfaces",
          "Visual models remove the need for sandboxing and confirmation",
          "Both approaches require fresh observations and postcondition checks around consequential actions"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "What are safe responses when a browser or GUI changes unexpectedly?",
        "options": [
          "Stop the stale action and obtain a fresh observation",
          "Use an allowlisted, unique visible target for one bounded recovery attempt",
          "Repeat the old coordinate until the UI reacts",
          "Escalate when the new target is ambiguous, risky, or outside scope",
          "Record the UI change and terminal or recovery reason in the trace"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      }
    ]
  },
  {
    "id": "i6",
    "level": "Intermediate",
    "step": "01",
    "title": "AgentOps Lab: tool engineering",
    "description": "Replace a dangerous admin tool with narrow schemas, validation, approval, and retry rules.",
    "time": "45-60 min",
    "outcome": "Design agent-facing tools with narrow responsibility, structured validation, predictable failures, and explicit boundaries.",
    "lesson": "Start with a deliberately unsafe admin_api(command) that can query, restart, delete, deploy, notify, and reconfigure. Then refactor it into narrow tools with validation, human approval for restarts, and retry/escalation/stop rules for common failures.",
    "exercise": "Run the tool-engineering lab, observe the unsafe broad tool, validate a restart request, simulate timeouts and permission errors, and inspect the retry decisions.",
    "failures": [],
    "notebook": "curriculum/intermediate/01-tool-engineering/tool_engineering.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md#notebook-04-learning-objectives",
      "curriculum/intermediate/01-tool-engineering/tool_engineering.ipynb",
      "https://openai.github.io/openai-agents-python/tools/",
      "https://www.linkedin.com/pulse/building-ai-agents-from-loops-teams-oneplusi-y3atc/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i13",
    "level": "Intermediate",
    "step": "02",
    "title": "Context engineering for agents",
    "description": "Build the smallest trusted, tenant-scoped context packet for each agent decision.",
    "time": "45-60 min",
    "outcome": "Route system policy, dynamic evidence, state, conversation, and external memory just in time while enforcing context isolation and poison quarantine.",
    "lesson": "The Acme EU payment incident scenario compares triage and investigation packets, drops stale chat under a token budget, quarantines a poisoned runbook, and blocks high-relevance Globex data before the prompt is assembled.",
    "exercise": "Run the deterministic context router, compare phase-specific packets, inspect cache keys and structured compression, then add freshness or approval state without weakening tenant/trust filters.",
    "failures": [],
    "notebook": "curriculum/intermediate/02-context-engineering/context_engineering.ipynb",
    "refs": [
      "curriculum/intermediate/02-context-engineering/README.md",
      "curriculum/intermediate/02-context-engineering/context_engineering.ipynb",
      "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
      "https://docs.langchain.com/oss/python/concepts/memory",
      "https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization",
      "https://genai.owasp.org/llmrisk/llm01-prompt-injection/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i7",
    "level": "Intermediate",
    "step": "10",
    "title": "LangGraph state, persistence, and memory",
    "description": "Build a bounded incident graph with durable checkpoints, approval pauses, and governed memory.",
    "time": "45-60 min",
    "outcome": "Distinguish thread-scoped state from long-term memory; recover safely after failure; and prevent unverified memory from biasing diagnosis.",
    "lesson": "Northstar's incident investigator moves through typed state, evidence collection, conditional routing, and a human approval pause. It checkpoints after each node and allows only verified, namespaced cross-thread memory to enter the decision context.",
    "exercise": "Run the dependency-free state graph, simulate worker loss and resume without duplicate work, reject a rollback proposal, then translate the design to a real LangGraph StateGraph.",
    "failures": [],
    "notebook": "curriculum/intermediate/10-langgraph-state-memory/langgraph_state_memory.ipynb",
    "refs": [
      "curriculum/intermediate/10-langgraph-state-memory/README.md",
      "curriculum/intermediate/10-langgraph-state-memory/langgraph_state_memory.ipynb",
      "https://docs.langchain.com/oss/python/langgraph/persistence",
      "https://docs.langchain.com/oss/python/concepts/memory",
      "https://docs.langchain.com/oss/python/langgraph/interrupts"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i8",
    "level": "Intermediate",
    "step": "03",
    "title": "Human approval and permissions",
    "description": "Pause consequential actions behind least-privilege policy, informed review, and replay-safe execution.",
    "time": "45-60 min",
    "outcome": "Apply READ, PROPOSE, and EXECUTE-WITH-APPROVAL capabilities; validate reviewer identity and tenant scope; and make approval resumes idempotent and auditable.",
    "lesson": "Northstar's incident agent prepares a eu-west rollback after evidence collection. The application persists the exact action, risk, evidence, expiry, and fingerprint, then requires an incident commander to approve, modify, reject, or escalate it.",
    "exercise": "Run the deterministic lab, inspect the approval payload, compare approve and reject paths, test a scope-broadening edit, and trace the audit event plus idempotency key.",
    "failures": [],
    "notebook": "curriculum/intermediate/03-human-approval-permissions/human_approval_permissions.ipynb",
    "refs": [
      "curriculum/intermediate/03-human-approval-permissions/README.md",
      "curriculum/intermediate/03-human-approval-permissions/human_approval_permissions.ipynb",
      "https://docs.langchain.com/oss/python/langgraph/interrupts",
      "https://docs.langchain.com/oss/python/langgraph/persistence",
      "https://www.nist.gov/itl/ai-risk-management-framework",
      "https://genai.owasp.org/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i9",
    "level": "Intermediate",
    "step": "04",
    "title": "Guardrails and untrusted content",
    "description": "Contain poisoned retrieved content with trust boundaries, deterministic tool gates, and least privilege.",
    "time": "45-60 min",
    "outcome": "Explain why external input, retrieved content, and tool responses cannot authorize operational actions—and prove containment even when detection is imperfect.",
    "lesson": "A poisoned checkout runbook asks the agent to restart services and export records. The lab quarantines suspicious content, labels safe content as untrusted data, blocks cross-tenant and unknown tools, and requires application-owned approval for consequential actions.",
    "exercise": "Run the adversarial suite, compare poisoned and benign-untrusted contexts, test cross-tenant and unknown-tool calls, then extend it with obfuscated or multimodal attacks.",
    "failures": [],
    "notebook": "curriculum/intermediate/04-guardrails-untrusted-content/guardrails_untrusted_content.ipynb",
    "refs": [
      "curriculum/intermediate/04-guardrails-untrusted-content/README.md",
      "curriculum/intermediate/04-guardrails-untrusted-content/guardrails_untrusted_content.ipynb",
      "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
      "https://developers.openai.com/api/docs/guides/agent-builder-safety",
      "https://docs.langchain.com/oss/python/langchain/guardrails"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i10",
    "level": "Intermediate",
    "step": "05",
    "title": "Agent evaluation: outcomes and trajectories",
    "description": "Release agents only when outcome, trajectory, safety, and operations pass explicit checks.",
    "time": "45-60 min",
    "outcome": "Build a representative evaluation dataset, grade answers and traces, hard-fail unsafe behavior, compare baselines, and monitor cost per successful task.",
    "lesson": "Northstar evaluation cases show why a fluent answer, missing evidence, or forbidden rollback is not a successful run. The lab compares baseline and hardened traces before applying a release gate.",
    "exercise": "Run the evaluator, inspect each failed criterion, then add expensive tool calls, tool failures, and cross-tenant policy cases to the dataset.",
    "failures": [],
    "notebook": "curriculum/intermediate/05-agent-evaluation/agent_evaluation.ipynb",
    "refs": [
      "curriculum/intermediate/05-agent-evaluation/README.md",
      "curriculum/intermediate/05-agent-evaluation/agent_evaluation.ipynb",
      "https://developers.openai.com/api/docs/guides/evaluation-best-practices",
      "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents",
      "https://docs.langchain.com/langsmith/evaluation"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i11",
    "level": "Intermediate",
    "step": "06",
    "title": "Trajectory optimization",
    "description": "Replace wasteful successful paths with shorter reliable, policy-compliant evidence trajectories.",
    "time": "45-60 min",
    "outcome": "Optimize for the shortest reliable trajectory to a correct result while preserving evidence, safety, recovery, and tenant scope.",
    "lesson": "Compare a nine-step Northstar checkout trace with a three-step grounded route, then identify duplicates, choose sequential or parallel reads, and apply a release gate.",
    "exercise": "Run the deterministic comparison, test an insufficient short trace, add redundant calls, and decide when constrained parallelism is justified.",
    "failures": [],
    "notebook": "curriculum/intermediate/06-trajectory-optimization/trajectory_optimization.ipynb",
    "refs": [
      "curriculum/intermediate/06-trajectory-optimization/README.md",
      "curriculum/intermediate/06-trajectory-optimization/trajectory_optimization.ipynb",
      "https://www.anthropic.com/engineering/building-effective-agents",
      "https://developers.openai.com/api/docs/guides/evaluation-best-practices"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i12",
    "level": "Intermediate",
    "step": "08",
    "title": "Planning and task decomposition",
    "description": "Turn an Adaptive RAG research request into a validated task graph that can recover from a failed source.",
    "time": "45-60 min",
    "outcome": "Build a constrained plan-and-execute system with goal decomposition, DAG scheduling, checkpoints, bounded replanning, and explicit escalation.",
    "lesson": "The research-agent scenario uses a bounded dynamic execution graph.",
    "exercise": "Run the credential-free lab and inspect the replan trace.",
    "failures": [],
    "notebook": "curriculum/intermediate/08-planning-task-decomposition/planning_task_decomposition.ipynb",
    "refs": [
      "curriculum/intermediate/08-planning-task-decomposition/README.md",
      "curriculum/intermediate/08-planning-task-decomposition/planning_task_decomposition.ipynb",
      "https://arxiv.org/abs/2305.04091"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i14",
    "level": "Intermediate",
    "step": "09",
    "title": "Agentic RAG / Knowledge-Grounded Agents",
    "description": "Plan, route, evaluate, and verify retrieval before producing a grounded answer or action proposal.",
    "time": "45-60 min",
    "outcome": "Design bounded retrieval agents that choose search, SQL, graph, or web evidence deliberately and verify citations before grounded action.",
    "lesson": "The EU payments incident uses runbook, SQL, and service-graph evidence. Its controller plans retrieval, follows a dependency edge, evaluates support, and produces an approved-action proposal rather than executing remediation.",
    "exercise": "Run the deterministic evidence loop, inspect the query plan and multi-hop trace, then remove evidence or add a conflict to design corrective retrieval.",
    "failures": [],
    "notebook": "curriculum/intermediate/09-agentic-rag/agentic_rag.ipynb",
    "refs": [
      "curriculum/intermediate/09-agentic-rag/README.md",
      "curriculum/intermediate/09-agentic-rag/agentic_rag.ipynb",
      "https://arxiv.org/abs/2403.14403",
      "https://arxiv.org/abs/2401.15884",
      "https://microsoft.github.io/graphrag/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "i2",
    "level": "Intermediate",
    "step": "10",
    "title": "Architecture patterns",
    "description": "Apply routing, parallelization, orchestrator-worker, and evaluator-optimizer patterns.",
    "time": "45-60 min",
    "outcome": "Select a topology, define contracts, and identify its failure modes before implementation.",
    "lesson": "Apply routing, parallelization, orchestrator-worker, and evaluator-optimizer patterns.",
    "exercise": "Apply routing, parallelization, orchestrator-worker, and evaluator-optimizer patterns.",
    "failures": [],
    "notebook": "curriculum/intermediate/06-trajectory-optimization/trajectory_optimization.ipynb",
    "refs": [
      "curriculum/intermediate/06-trajectory-optimization/README.md",
      "docs/multi-agent-systems.md"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which are good practices for a routing workflow?",
        "options": [
          "Evaluate routing accuracy separately",
          "Include an unknown or human-escalation route",
          "Give every route identical tools and policies regardless of need",
          "Use specialist paths when categories need different controls",
          "Log the selected route for diagnosis"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      },
      {
        "q": "When is an evaluator-optimizer loop a strong fit?",
        "options": [
          "Success criteria are explicit",
          "Feedback can guide a concrete revision",
          "Iteration is bounded",
          "There is no way to assess whether the output improved",
          "Deterministic graders can supplement model judgment"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which statements correctly compare an agent-as-tool with a handoff?",
        "options": [
          "An agent-as-tool lets the orchestrator retain ownership",
          "A handoff transfers control to a specialist",
          "Both patterns remove the need for scoped permissions",
          "The choice should reflect who owns the next interaction",
          "Both introduce a context and evaluation boundary"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      },
      {
        "q": "Which controls improve parallel worker orchestration?",
        "options": [
          "Non-overlapping worker contracts",
          "A clear aggregation rule",
          "Provenance on worker outputs",
          "Unlimited delegation breadth and depth",
          "Per-worker budgets"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "i3",
    "level": "Intermediate",
    "step": "11",
    "title": "Evaluation and security",
    "description": "Evaluate trajectories, tool calls, outcomes, policy compliance, and cost.",
    "time": "45-60 min",
    "outcome": "Create a release gate that catches unsafe actions and unsuccessful task trajectories.",
    "lesson": "Evaluate trajectories, tool calls, outcomes, policy compliance, and cost.",
    "exercise": "Evaluate trajectories, tool calls, outcomes, policy compliance, and cost.",
    "failures": [],
    "notebook": "curriculum/intermediate/05-agent-evaluation/agent_evaluation.ipynb",
    "refs": [
      "curriculum/intermediate/05-agent-evaluation/README.md#evaluation-dimensions",
      "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which controls belong between a model-proposed action and tool execution?",
        "options": [
          "Schema validation",
          "Authorization for the exact resource and operation",
          "Approval when the action crosses a risk boundary",
          "Blindly trusting the model's stated intent",
          "Budget and policy checks"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which layers should a useful agent evaluation cover?",
        "options": [
          "Real task outcome",
          "Action and tool-use trajectory",
          "Latency, cost, and failure operations",
          "Only the fluency of the final response",
          "Policy compliance and side effects"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which inputs should an agent treat as untrusted?",
        "options": [
          "Retrieved documents and web pages",
          "Tool results",
          "Messages from another agent",
          "User-supplied content",
          "A tool result solely because it is formatted as JSON"
        ],
        "answer": [
          0,
          1,
          2,
          3,
          4
        ]
      },
      {
        "q": "Which practices reduce risk for agent-initiated write operations?",
        "options": [
          "Use idempotency keys",
          "Preview and validate the proposed change",
          "Persist a receipt and verify resulting state",
          "Automatically retry when the previous outcome is unknown",
          "Attach the initiating identity and run ID"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "a6",
    "level": "Advanced",
    "step": "01",
    "title": "Single agent versus multi-agent systems",
    "description": "Choose and evaluate specialized teams only when their coordination cost earns a measurable improvement.",
    "time": "45-60 min",
    "outcome": "Compare a single investigator with supervisor, router, planner-executor, manager/subagent, hierarchy, peer, blackboard, debate, generator/critic, sequential, and parallel patterns using accuracy, safety, latency, cost, and coordination evidence.",
    "lesson": "A 35% EU checkout conversion drop tests whether specialized evidence artifacts and critic review improve the result over a bounded single-agent baseline, while explicitly testing conflict, shared-state, and coordination failure paths.",
    "exercise": "Run simple, cross-domain, and ambiguous comparisons; publish source-backed artifacts, trigger critic conflict handling, inspect all pattern trade-offs, and justify which system to ship with explicit contracts and budgets.",
    "failures": [],
    "notebook": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb",
    "refs": [
      "curriculum/advanced/01-single-vs-multi-agent/README.md",
      "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb",
      "https://docs.langchain.com/oss/python/langchain/multi-agent/index",
      "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html",
      "https://arxiv.org/abs/2501.06322",
      "https://arxiv.org/abs/2601.01743"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a7",
    "level": "Advanced",
    "step": "02",
    "title": "AgentOps Lab: AutoGen selector team",
    "description": "Map the incident specialists to an AutoGen-style selector group chat with explicit ownership and turn limits.",
    "time": "45-60 min",
    "outcome": "Explain how selector-based team coordination works, why shared context can create loops, and how max team messages, per-agent turn budgets, and ownership contracts keep the system bounded.",
    "lesson": "AutoGen AgentChat exposes the team conversation as a first-class design object. This lesson uses a dependency-free simulation plus optional AutoGen code sketch to show participant descriptions, selector routing, termination, and failure-loop prevention.",
    "exercise": "Run the selector simulation, compare the successful ownership-aware transcript with the deliberately broken loop, then inspect the notebook's optional AutoGen implementation sketch.",
    "failures": [],
    "notebook": "curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md#notebook-11-learning-objectives",
      "curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb",
      "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html",
      "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html",
      "https://arxiv.org/abs/2308.08155"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a8",
    "level": "Advanced",
    "step": "03",
    "title": "AgentOps Lab: CrewAI team",
    "description": "Implement the same incident team with a CrewAI-style Agents + Tasks + Crew model.",
    "time": "45-60 min",
    "outcome": "Map specialist roles to agents, work products to tasks, and task context to a crew-level incident plan.",
    "lesson": "CrewAI makes the project-management shape of agent collaboration explicit. This lesson compares where CrewAI helps, where LangGraph gives more state control, where AutoGen makes conversation easier, and where OpenAI Agents SDK remains simpler.",
    "exercise": "Run the deterministic CrewAI-shaped lab, inspect each task owner and context dependency, then compare the framework trade-offs in the notebook.",
    "failures": [],
    "notebook": "curriculum/advanced/03-crewai-teams/03_crewai_teams.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md#notebook-12-learning-objectives",
      "curriculum/advanced/03-crewai-teams/03_crewai_teams.ipynb",
      "https://docs.crewai.com/",
      "https://docs.crewai.com/v1.15.10/en/concepts/agents",
      "https://docs.crewai.com/v1.15.6/en/concepts/crews"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a9",
    "level": "Advanced",
    "step": "04",
    "title": "AgentOps Lab: hybrid production architecture",
    "description": "Wrap agents in deterministic routing, policy checks, approval gates, budgets, and audit logs.",
    "time": "45-60 min",
    "outcome": "Design a production architecture that routes each task to the least autonomous reliable path instead of using one giant autonomous agent.",
    "lesson": "The final AgentOps lesson combines the full track: simple lookups use deterministic code, ambiguous investigations use a bounded single agent, high-risk cases use a specialist team, and every route converges on policy checks plus human approval before consequential action.",
    "exercise": "Run the router examples, inspect why each task is classified, and modify the risk, ambiguity, and known-path signals to see how architecture selection changes.",
    "failures": [],
    "notebook": "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md#notebook-13-learning-objectives",
      "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
      "https://www.anthropic.com/engineering/building-effective-agents",
      "https://www.linkedin.com/pulse/building-ai-agents-from-loops-teams-oneplusi-y3atc/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a10",
    "level": "Advanced",
    "step": "05",
    "title": "AgentOps Lab: final capstone",
    "description": "Design the full incident-response system and justify single-agent versus multi-agent experimentally.",
    "time": "45-60 min",
    "outcome": "Combine architecture selection, tool definitions, instructions, state, memory policy, permissions, HITL, guardrails, termination, evaluation, trace analysis, cost/latency analysis, and single-vs-multi-agent comparison.",
    "lesson": "The capstone incident begins at 09:04 with a 31% Europe checkout conversion drop, mostly-green dashboards, an 08:42 deployment, six support complaints, runbooks, and customer SLA data. Learners must recommend mitigation and prepare production actions without executing them.",
    "exercise": "Run the capstone harness, inspect the selected architecture, verify forbidden production actions were not executed, and modify the candidate metrics to test when a specialist team becomes justified.",
    "failures": [],
    "notebook": "curriculum/advanced/05-incident-response/incident_response.ipynb",
    "refs": [
      "curriculum/advanced/05-incident-response/README.md#notebook-14-capstone-objectives",
      "curriculum/advanced/05-incident-response/incident_response.ipynb",
      "curriculum/advanced/05-incident-response/incident_response.ipynb",
      "https://www.anthropic.com/engineering/building-effective-agents"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a11",
    "level": "Advanced",
    "step": "06",
    "title": "Agent memory",
    "description": "Build a governed write → manage → read subsystem instead of treating history as a vector dump.",
    "time": "45-60 min",
    "outcome": "Design scoped, attributable memory with consolidation, forgetting, contradiction resolution, ranked retrieval, personalization, and privacy controls.",
    "lesson": "The Acme incident scenario retains useful SLA and postmortem knowledge while expiring an unverified diagnosis. It compares working, episodic, semantic, and procedural memory and keeps cross-tenant data out of retrieval.",
    "exercise": "Run the deterministic store, observe the bad diagnosis before consolidation, then inspect its supersession, retrieval result, and audit trail.",
    "failures": [],
    "notebook": "curriculum/advanced/06-agent-memory/agent_memory.ipynb",
    "refs": [
      "curriculum/advanced/06-agent-memory/README.md",
      "curriculum/advanced/06-agent-memory/agent_memory.ipynb",
      "https://arxiv.org/abs/2310.08560",
      "https://arxiv.org/abs/2304.03442",
      "https://docs.langchain.com/oss/python/concepts/memory"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a12",
    "level": "Advanced",
    "step": "07",
    "title": "World models and environment modeling",
    "description": "Predict action consequences in a bounded environment model before proposing a real-world mitigation.",
    "time": "45-60 min",
    "outcome": "Design internal representations, simulations, counterfactual rollouts, digital twins, and model-based planning with uncertainty, safety, and real-world validation gates.",
    "lesson": "Northstar's checkout digital twin compares rollback, traffic routing, and waiting. It teaches that a predictive model is decision support—not production authorization—and must be calibrated against new observations.",
    "exercise": "Run the deterministic counterfactual planner, alter model confidence or policy constraints, and explain when it must stop, fall back, or request human approval.",
    "failures": [],
    "notebook": "curriculum/advanced/07-world-models-environment-modeling/world_models_environment_modeling.ipynb",
    "refs": [
      "curriculum/advanced/07-world-models-environment-modeling/README.md",
      "curriculum/advanced/07-world-models-environment-modeling/world_models_environment_modeling.ipynb",
      "https://deepmind.google/research/publications/60474/",
      "https://arxiv.org/abs/2510.16732",
      "https://arxiv.org/abs/2605.00080"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a13",
    "level": "Advanced",
    "step": "08",
    "title": "Proactive agents",
    "description": "Build persistent digital workers that wake on events or schedules and intervene only when policy and evidence justify it.",
    "time": "45-60 min",
    "outcome": "Design event-driven, scheduled, trigger-based, monitoring, background, and notification agents with goal persistence, opt-out, permissions, and operational budgets.",
    "lesson": "A Northstar checkout-health worker validates a low-conversion event, deduplicates it, respects quiet hours and notification consent, then notifies on-call or safely suppresses the event.",
    "exercise": "Run the deterministic worker, inspect its evidence and duplicate suppression, then add stale-event, hysteresis, cancellation, budget, and escalation policies.",
    "failures": [],
    "notebook": "curriculum/advanced/08-proactive-agents/proactive_agents.ipynb",
    "refs": [
      "curriculum/advanced/08-proactive-agents/README.md",
      "curriculum/advanced/08-proactive-agents/proactive_agents.ipynb",
      "https://doi.org/10.1145/3715097",
      "https://arxiv.org/abs/2607.17701",
      "https://arxiv.org/abs/2601.09382",
      "https://www.langchain.com/blog/introducing-ambient-agents"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a14",
    "level": "Advanced",
    "step": "09",
    "title": "Model routing",
    "description": "Select the least expensive eligible model route using capability, quality, latency, cost, and policy evidence.",
    "time": "45-60 min",
    "outcome": "Route simple tasks to fast models, complex investigations to reasoning models, visual evidence to multimodal models, and repository work to coding models—then evaluate cascades, fallbacks, and ensembles.",
    "lesson": "Northstar's support and incident assistant chooses a route for a known status report, an ambiguous EU checkout regression, a dashboard screenshot, and a test-backed patch while keeping tool authority and production actions outside the router.",
    "exercise": "Run the deterministic policy, inspect capability-first selection, trigger a bounded escalation from a weak fast answer, simulate a required capability outage, and compare a single route with an ensemble policy.",
    "failures": [],
    "notebook": "curriculum/advanced/09-model-routing/model_routing.ipynb",
    "refs": [
      "curriculum/advanced/09-model-routing/README.md",
      "curriculum/advanced/09-model-routing/model_routing.ipynb",
      "https://arxiv.org/abs/2406.18665",
      "https://arxiv.org/abs/2403.12031",
      "https://arxiv.org/abs/2305.05176",
      "https://arxiv.org/abs/2410.10347"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a15",
    "level": "Advanced",
    "step": "10",
    "title": "Long-running and asynchronous agents",
    "description": "Operate durable jobs that checkpoint, wait for trusted events or people, resume safely, and stop on explicit boundaries.",
    "time": "45-60 min",
    "outcome": "Design background/scheduled/event-driven work with pause/resume, checkpointing, human approval, state recovery, cancellation, idempotency, and durable execution controls.",
    "lesson": "Northstar's EU checkout investigation waits for evidence, persists an approval-ready proposal, survives worker loss, and resumes only for a fresh trusted approval or safely expires/cancels.",
    "exercise": "Run the deterministic state machine, inspect every checkpoint, simulate recovery after worker loss, test approval and rejection, then trigger deadline expiry and design duplicate-event protection.",
    "failures": [],
    "notebook": "curriculum/advanced/10-long-running-asynchronous-agents/long_running_asynchronous_agents.ipynb",
    "refs": [
      "curriculum/advanced/10-long-running-asynchronous-agents/README.md",
      "curriculum/advanced/10-long-running-asynchronous-agents/long_running_asynchronous_agents.ipynb",
      "https://docs.langchain.com/oss/python/langgraph/durable-execution",
      "https://docs.langchain.com/oss/python/langgraph/persistence",
      "https://docs.temporal.io/workflows"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a16",
    "level": "Advanced",
    "step": "11",
    "title": "LLM-as-Judge and agent judges",
    "description": "Evaluate answers and trajectories with rubrics, comparisons, tool/policy checks, calibration, and human agreement.",
    "time": "45-60 min",
    "outcome": "Design rubric, pairwise, trajectory/tool, critic, calibrated, human-aligned, and ensemble evaluation without treating one judge as ground truth.",
    "lesson": "Northstar's incident agent passes only when outcome, evidence, trajectory, and policy checks pass; unsafe actions hard-fail before any semantic judge is consulted.",
    "exercise": "Run the deterministic rubric judge, compare supported and forbidden traces, then design calibration, bias, pairwise, ensemble, and release-gate experiments.",
    "failures": [],
    "notebook": "curriculum/advanced/11-llm-as-judge-agent-judges/llm_as_judge_agent_judges.ipynb",
    "refs": [
      "curriculum/advanced/11-llm-as-judge-agent-judges/README.md",
      "curriculum/advanced/11-llm-as-judge-agent-judges/llm_as_judge_agent_judges.ipynb",
      "https://arxiv.org/abs/2303.16634",
      "https://arxiv.org/abs/2310.17631",
      "https://developers.openai.com/api/docs/guides/evaluation-best-practices"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a17",
    "level": "Advanced",
    "step": "12",
    "title": "Agent benchmarks",
    "description": "Use public and enterprise benchmarks as evidence—not production reliability certificates.",
    "time": "45-60 min",
    "outcome": "Select, reproduce, inspect, and extend SWE-bench, WebArena, BrowserGym, GAIA, τ-bench, OSWorld, AgentBench, domain, and custom enterprise benchmarks for a real release decision.",
    "lesson": "This reference guide explains benchmark scope, scoring limits, trajectory inspection, operational/adversarial extensions, and custom enterprise release gates. It intentionally has no notebook or lab.",
    "exercise": "Read the comparison guide, select the nearest proxy environment, pin a baseline, inspect trajectories, then build a privacy-safe enterprise evaluation slice and release gate.",
    "failures": [],
    "notebook": "",
    "refs": [
      "curriculum/advanced/12-agent-benchmarks/README.md",
      "https://www.swebench.com/",
      "https://webarena.dev/",
      "https://os-world.github.io/",
      "https://arxiv.org/abs/2406.12045"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a18",
    "level": "Advanced",
    "step": "13",
    "title": "MCP: Model Context Protocol",
    "description": "Connect agents to tools and context through MCP client/server capabilities while keeping identity, policy, authorization, and action control application-owned.",
    "time": "45-60 min",
    "outcome": "Explain MCP architecture, clients/servers, tools/resources/prompts, capability negotiation, remote MCP, authentication/authorization, gateways, enterprise controls, security, and safe agent integration within the broader protocol ecosystem.",
    "lesson": "Northstar negotiates a least-privilege deployment capability catalogue through a gateway, validates a read tool call, blocks an unapproved write, and treats every server result as data rather than authority.",
    "exercise": "Run the MCP boundary simulator, inspect authorization-aware capability negotiation and strict validation, test a denied write, then add tenant, expiry, outage, provenance, and idempotency controls.",
    "failures": [],
    "notebook": "curriculum/advanced/13-mcp-model-context-protocol/mcp_model_context_protocol.ipynb",
    "refs": [
      "curriculum/advanced/13-mcp-model-context-protocol/README.md",
      "curriculum/advanced/13-mcp-model-context-protocol/mcp_model_context_protocol.ipynb",
      "https://modelcontextprotocol.io/specification/",
      "https://a2a-protocol.org/latest/",
      "https://arxiv.org/abs/2505.02279"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which statements correctly describe MCP's boundary?",
        "options": [
          "It standardizes client/server capability contracts for tools, resources, and prompts",
          "It automatically grants an agent authority to use every discovered tool",
          "An enterprise can filter the offered capability list by current authorization scopes",
          "Tool results should be treated as observations or data, not as policy authority",
          "MCP replaces application-owned tenant policy and action approval"
        ],
        "answer": [
          0,
          2,
          3
        ]
      },
      {
        "q": "What should protect a consequential MCP tool call such as a rollback?",
        "options": [
          "Strict argument and result validation",
          "A short-lived scope for the exact operation and tenant",
          "An exact action fingerprint and approval when policy requires it",
          "Blind retry after an unknown timeout",
          "Idempotency, reconciliation, and an auditable trace"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "a19",
    "level": "Advanced",
    "step": "14",
    "title": "Agent Skills",
    "description": "Package reusable procedural knowledge as versioned, progressively loaded capabilities that guide approved tools and subagents without granting authority.",
    "time": "45-60 min",
    "outcome": "Distinguish tools from skills; design descriptions, discovery, libraries, dynamic loading, composition, routing, governance, MCP integration, and subagent delegation.",
    "lesson": "Northstar discovers metadata-only incident skills, activates a policy-eligible version, progressively loads its procedure, and demonstrates that composition never unions tool privileges by default.",
    "exercise": "Run the skills library simulator, test activation and denied-tool handling, inspect conservative composition, then add version, revocation, malicious-reference, and MCP/subagent controls.",
    "failures": [],
    "notebook": "curriculum/advanced/14-agent-skills/agent_skills.ipynb",
    "refs": [
      "curriculum/advanced/14-agent-skills/README.md",
      "curriculum/advanced/14-agent-skills/agent_skills.ipynb",
      "https://github.com/agentskills/agentskills",
      "https://openai.com/academy/skills/",
      "https://modelcontextprotocol.io/specification/"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which statements distinguish an agent skill from a tool?",
        "options": [
          "A tool normally performs one typed operation",
          "A skill can package a workflow, instructions, references, scripts, and assets",
          "Activating a skill automatically broadens all tool permissions",
          "Skills can use progressive disclosure so deeper material loads only when relevant",
          "A skill is a form of application authorization"
        ],
        "answer": [
          0,
          1,
          3
        ]
      },
      {
        "q": "Which controls make a skill library safe to operate?",
        "options": [
          "Record owner, provenance, version, compatibility, risk, tests, and revocation",
          "Filter discovery and activation by tenant, policy, and permitted tools",
          "Union every participating skill's tool privileges when composing skills",
          "Treat scripts, references, and assets as supply-chain inputs subject to review and scanning",
          "Trace the selected skill version and evaluate discovery/activation behavior"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      }
    ]
  },
  {
    "id": "e1",
    "level": "Enterprise Agent",
    "step": "01",
    "title": "Designing reliable agentic systems",
    "description": "Synthesize architecture, policy, privacy, evaluation, and operations into the least autonomous system that achieves a business outcome.",
    "time": "45-60 min",
    "outcome": "Select workflow, bounded agent, stateful graph, or specialist team using measurable trade-offs, then surround it with application-owned authorization, budgets, evaluation, and recovery controls.",
    "lesson": "Northstar Commerce's 31% EU checkout-conversion drop provides the synthesis scenario. You will compare capability against control, context against cost, memory against privacy, teams against complexity, and quality against latency before preparing—but not autonomously executing—a rollback proposal.",
    "exercise": "Run the deterministic architecture decision harness, compare baseline, single-agent, and team candidates, inspect the proposal-only path, then change task signals and defend the release decision with outcome, trajectory, cost, and safety evidence.",
    "failures": [],
    "notebook": "curriculum/advanced/15-designing-reliable-agentic-systems/designing_reliable_agentic_systems.ipynb",
    "refs": [
      "curriculum/advanced/15-designing-reliable-agentic-systems/README.md",
      "curriculum/advanced/15-designing-reliable-agentic-systems/designing_reliable_agentic_systems.ipynb",
      "https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
      "https://www.anthropic.com/engineering/building-effective-agents",
      "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents",
      "https://www.nist.gov/itl/ai-risk-management-framework",
      "https://arxiv.org/abs/2601.01743"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e2",
    "level": "Enterprise Agent",
    "step": "02",
    "title": "Human + multi-agent organizations",
    "description": "Design AI teammates and digital workers around bounded delegation, evidence artifacts, supervision, and human accountability.",
    "time": "45-60 min",
    "outcome": "Create a manager-led human/agent organization with scoped work orders, least-privilege specialists, typed artifacts, reviewable delegation, policy boundaries, and explicit human authority over consequential action.",
    "lesson": "Northstar Commerce's incident requires research, data, coding, analysis, and review work. You will compare a bounded single-agent baseline against a manager-led team, keeping customer commitments and production actions under human, server-side authority.",
    "exercise": "Run the credential-free organization simulator, inspect read-only specialist work orders and attributed artifacts, trigger the reviewer’s escalation path, then extend the design with a new digital worker and an evaluation plan.",
    "failures": [],
    "notebook": "curriculum/advanced/16-human-multi-agent-organizations/human_multi_agent_organizations.ipynb",
    "refs": [
      "curriculum/advanced/16-human-multi-agent-organizations/README.md",
      "curriculum/advanced/16-human-multi-agent-organizations/human_multi_agent_organizations.ipynb",
      "https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
      "https://alignment.anthropic.com/2026/ai-organizations/",
      "https://arxiv.org/abs/2510.02557",
      "https://arxiv.org/abs/2606.05391",
      "https://arxiv.org/abs/2605.12105",
      "https://www.nist.gov/itl/ai-risk-management-framework"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e3",
    "level": "Enterprise Agent",
    "step": "03",
    "title": "Agentic enterprise architecture",
    "description": "Operate a governed ecosystem of registered agents, tools, MCP services, knowledge, policies, evaluations, and budgets.",
    "time": "45-60 min",
    "outcome": "Design a control plane for agent and tool catalogs, MCP registry/gateway, identity-bound discovery, shared knowledge, enterprise orchestration, governance, observability, evaluation, and FinOps.",
    "lesson": "Northstar onboards a high-risk customer-impact agent and MCP metrics service. The lesson proves that registries and discovery improve reuse only when identity, policy, provenance, evaluation, audit, and spend controls remain server-side.",
    "exercise": "Run the credential-free control-plane simulator, register approved assets, test discovery, observe proposal-only enforcement for high-risk work, then add revocation, scope, and cost tests.",
    "failures": [],
    "notebook": "curriculum/advanced/17-agentic-enterprise-architecture/agentic_enterprise_architecture.ipynb",
    "refs": [
      "curriculum/advanced/17-agentic-enterprise-architecture/README.md",
      "curriculum/advanced/17-agentic-enterprise-architecture/agentic_enterprise_architecture.ipynb",
      "https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization",
      "https://a2a-protocol.org/latest/topics/agent-discovery/",
      "https://arxiv.org/abs/2508.03095",
      "https://arxiv.org/abs/2504.21034",
      "https://openai.com/business/frontier/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e4",
    "level": "Enterprise Agent",
    "step": "04",
    "title": "Agentic software engineering",
    "description": "Run repository-aware coding agents inside sandbox, test, review, PR, CI/CD, and human-merge controls.",
    "time": "45-60 min",
    "outcome": "Design and evaluate a long-horizon coding-agent loop for repository understanding, code search, planning, editing, terminal tools, tests, debugging, review, PR preparation, CI, and benchmarks.",
    "lesson": "The Northstar EU checkout bug shows how a coding agent may produce an evidence-backed PR draft while a sandbox, independent tests/review, CI, branch policy, and a human reviewer remain the production quality system.",
    "exercise": "Run the deterministic coding-agent harness, inspect its plan, patch/test evidence, review gate, and PR-ready status, then deliberately remove the regression test to trigger the blocked-review path.",
    "failures": [],
    "notebook": "curriculum/advanced/18-agentic-software-engineering/agentic_software_engineering.ipynb",
    "refs": [
      "curriculum/advanced/18-agentic-software-engineering/README.md",
      "curriculum/advanced/18-agentic-software-engineering/agentic_software_engineering.ipynb",
      "https://github.com/swe-bench/SWE-bench",
      "https://openai.com/index/separating-signal-from-noise-coding-evaluations/",
      "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents",
      "https://arxiv.org/abs/2606.07297"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e5",
    "level": "Enterprise Agent",
    "step": "05",
    "title": "Embodied agents and robotics",
    "description": "Apply agent architecture to physical-world perception, planning, action, verification, simulation, and safety constraints.",
    "time": "45-60 min",
    "outcome": "Explain vision-language-action models, robot navigation/manipulation, embodied planning, physical feedback, simulation, and independent safety supervision.",
    "lesson": "A concise warehouse package-placement scenario shows why a VLA agent must operate in small verified increments and why physics, sensors, safety supervisors, simulation, and human escalation remain outside its model loop.",
    "exercise": "Run the hardware-free simulation, inspect successful sensing and verification, then change clearance or force inputs to prove the safe-stop branch is selected.",
    "failures": [],
    "notebook": "curriculum/advanced/19-embodied-agents-robotics/embodied_agents_robotics.ipynb",
    "refs": [
      "curriculum/advanced/19-embodied-agents-robotics/README.md",
      "curriculum/advanced/19-embodied-agents-robotics/embodied_agents_robotics.ipynb",
      "https://deepmind.google/blog/rt-2-new-model-translates-vision-and-language-into-action/",
      "https://arxiv.org/abs/2406.09246",
      "https://arxiv.org/abs/2508.15201",
      "https://arxiv.org/abs/2604.23775"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e6",
    "level": "Enterprise Agent",
    "step": "06",
    "title": "Multimodal agents",
    "description": "Design agents that see, hear, reason, plan, and act across vision, documents, UI, audio, video, and sensors.",
    "time": "45-60 min",
    "outcome": "Build provenance-aware multimodal evidence, memory, and tool boundaries across images, audio, video, documents, screens, speech, and sensor data.",
    "lesson": "A warehouse control-room case correlates camera, alarm, manual, UI, and sensor evidence before a read-only escalation. It teaches that multimodality expands perception, not authority.",
    "exercise": "Run the metadata-only evidence router, inspect time/tenant/provenance alignment, then add untrusted content or timestamp skew to design quarantine and escalation rules.",
    "failures": [],
    "notebook": "curriculum/advanced/20-multimodal-agents/multimodal_agents.ipynb",
    "refs": [
      "curriculum/advanced/20-multimodal-agents/README.md",
      "curriculum/advanced/20-multimodal-agents/multimodal_agents.ipynb",
      "https://arxiv.org/abs/2312.11805",
      "https://arxiv.org/abs/2403.05530",
      "https://doi.org/10.1007/s11390-025-4802-8",
      "https://arxiv.org/abs/2605.27295"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e7",
    "level": "Enterprise Agent",
    "step": "07",
    "title": "Cost, latency, and agent economics",
    "description": "Budget full agent trajectories and optimize cost per successful safe task—not the price of a single model call.",
    "time": "45-60 min",
    "outcome": "Set token, action, reasoning, spend, and latency budgets; choose cache, sequential, parallel, speculative, and routed paths; and evaluate cost, quality, and p95 latency together.",
    "lesson": "Northstar transforms an 8-model-call, 12-tool-call investigation into an explicit budgeted trajectory using a valid cache, fast classification, bounded parallel reads, and a reasoning route only when uncertainty justifies it.",
    "exercise": "Run the deterministic budget controller, compare cache, parallel, sequential, and reasoning paths, trigger an exhausted-budget stop, then define a cost-per-success release gate.",
    "failures": [],
    "notebook": "curriculum/advanced/21-cost-latency-agent-economics/agent_economics.ipynb",
    "refs": [
      "curriculum/advanced/21-cost-latency-agent-economics/README.md",
      "curriculum/advanced/21-cost-latency-agent-economics/agent_economics.ipynb",
      "https://arxiv.org/abs/2305.05176",
      "https://arxiv.org/abs/2406.18665",
      "https://arxiv.org/abs/2403.12031",
      "https://arxiv.org/abs/2410.10347"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e8",
    "level": "Enterprise Agent",
    "step": "08",
    "title": "Production agent architecture",
    "description": "Operate agent runtime inside a control plane for identity, policy, durable state, queues, tools, knowledge, observability, and evaluation.",
    "time": "45-60 min",
    "outcome": "Separate stateless and stateful components; design sessions, persistence, queues, async execution, checkpoints, caching, retries, rate limits, autoscaling, and disaster recovery.",
    "lesson": "Northstar routes an authenticated investigation through a gateway and orchestrator to a bounded runtime that checkpoints while waiting for evidence, recovers after worker loss, and returns a proposal without executing remediation.",
    "exercise": "Run the deterministic architecture simulator, inspect the checkpoint/recovery trace, block an unauthenticated request, then define cache, queue, retry, SLO, and DR controls.",
    "failures": [],
    "notebook": "curriculum/advanced/22-production-agent-architecture/production_agent_architecture.ipynb",
    "refs": [
      "curriculum/advanced/22-production-agent-architecture/README.md",
      "curriculum/advanced/22-production-agent-architecture/production_agent_architecture.ipynb",
      "https://docs.langchain.com/oss/python/langgraph/durable-execution",
      "https://docs.temporal.io/workflows",
      "https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e9",
    "level": "Enterprise Agent",
    "step": "09",
    "title": "Agent governance and responsible AI",
    "description": "Operate accountable, auditable, risk-classified, human-supervised, and revocable agents through their lifecycle.",
    "time": "45-60 min",
    "outcome": "Build an agent inventory, assign ownership, classify risk/autonomy/data/tools, gate changes, preserve auditability, manage oversight, respond to incidents, and retire safely.",
    "lesson": "Northstar registers a high-risk incident adviser that can read evidence but must prepare an approval-gated proposal. Its release gate requires accountable owner, scope, classification, data treatment, and control evidence.",
    "exercise": "Run the credential-free release gate, observe approval for a governed agent and a block for missing approval control, then model a change and incident response lifecycle.",
    "failures": [],
    "notebook": "curriculum/advanced/23-agent-governance-responsible-ai/agent_governance_responsible_ai.ipynb",
    "refs": [
      "curriculum/advanced/23-agent-governance-responsible-ai/README.md",
      "curriculum/advanced/23-agent-governance-responsible-ai/agent_governance_responsible_ai.ipynb",
      "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications/",
      "https://www.nist.gov/itl/ai-risk-management-framework"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e10",
    "level": "Enterprise Agent",
    "step": "10",
    "title": "Guardrails and policy enforcement",
    "description": "Apply deterministic controls at input, context, tool, argument, action, output, and audit boundaries.",
    "time": "45-60 min",
    "outcome": "Design policy engines, structured validation, allow/deny lists, permissions, sandboxing, rate/budget limits, approvals, kill switches, and auditable decisions.",
    "lesson": "Northstar contains injected input, cross-tenant arguments, unlisted tools, high-risk actions, and budget exhaustion through application-owned policy controls.",
    "exercise": "Run the deterministic policy gate and test valid reads, prompt injection, tool denial, tenant mismatch, approval, and budget limits.",
    "failures": [],
    "notebook": "curriculum/advanced/24-guardrails-policy-enforcement/guardrails_policy_enforcement.ipynb",
    "refs": [
      "curriculum/advanced/24-guardrails-policy-enforcement/README.md",
      "curriculum/advanced/24-guardrails-policy-enforcement/guardrails_policy_enforcement.ipynb",
      "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications/",
      "https://www.nist.gov/itl/ai-risk-management-framework"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e11",
    "level": "Enterprise Agent",
    "step": "11",
    "title": "Agent identity and authorization",
    "description": "Grant agents distinct, short-lived, scoped, attributable authority instead of shared user or admin credentials.",
    "time": "45-60 min",
    "outcome": "Separate user and agent identity; apply delegated OAuth/OIDC-style authority, capabilities, least privilege, temporary credentials, tool/peer authentication, audit, and policy enforcement.",
    "lesson": "Northstar grants an Acme incident adviser a ten-minute read-status capability. Cross-tenant, expired, broadened, or high-impact requests are denied or require fresh approval.",
    "exercise": "Run the deterministic capability gate and test valid scope, tenant mismatch, expiry, approval, and an auditable delegation trace.",
    "failures": [],
    "notebook": "curriculum/advanced/25-agent-identity-authorization/agent_identity_authorization.ipynb",
    "refs": [
      "curriculum/advanced/25-agent-identity-authorization/README.md",
      "curriculum/advanced/25-agent-identity-authorization/agent_identity_authorization.ipynb",
      "https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics",
      "https://openid.net/specs/openid-connect-core-1_0.html",
      "https://spiffe.io/docs/latest/spiffe-about/overview/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e12",
    "level": "Enterprise Agent",
    "step": "12",
    "title": "Agent security",
    "description": "Contain agent-specific threats across untrusted context, memory, tools/MCP, identity, peers, and software supply chain.",
    "time": "45-60 min",
    "outcome": "Threat-model direct/indirect injection, hijacking, poisoned tools/MCP/memory/context, credential/exfiltration/privilege abuse, cross-agent/supply-chain attacks, and excessive agency with layered containment.",
    "lesson": "Northstar reads a poisoned external runbook. Deterministic trust, tenant, allow-list, authorization, sandbox, egress, approval, budget, audit, and revoke controls contain it even when detection is imperfect.",
    "exercise": "Run safe, injection, and cross-tenant cases; then extend the adversarial suite with poisoned descriptions, memory, credentials, peers, and dependencies.",
    "failures": [],
    "notebook": "curriculum/advanced/26-agent-security/agent_security.ipynb",
    "refs": [
      "curriculum/advanced/26-agent-security/README.md",
      "curriculum/advanced/26-agent-security/agent_security.ipynb",
      "https://csrc.nist.gov/pubs/ai/100/4/ipd",
      "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications/"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e13",
    "level": "Enterprise Agent",
    "step": "13",
    "title": "Agent observability",
    "description": "Trace trajectories, context, tools, state, policy, cost, and latency to answer why an agent acted.",
    "time": "45-60 min",
    "outcome": "Instrument distributed traces, agent trajectories, tool calls, token/cost/latency, state/context, failures, replay, monitoring, and dashboards with privacy-aware evidence.",
    "lesson": "Northstar's checkout incident trace links deterministic routing, model triage, metrics/log tools, and policy decision to an approval-required proposal and measurable operational outcomes.",
    "exercise": "Run the OpenTelemetry-shaped trace, inspect span attributes and cost/latency summary, then add failure, replay, alert, and redaction policies.",
    "failures": [],
    "notebook": "curriculum/advanced/27-agent-observability/agent_observability.ipynb",
    "refs": [
      "curriculum/advanced/27-agent-observability/README.md",
      "curriculum/advanced/27-agent-observability/agent_observability.ipynb",
      "https://opentelemetry.io/docs/",
      "https://openai.github.io/openai-agents-python/tracing/",
      "https://docs.smith.langchain.com/observability"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e14",
    "level": "Enterprise Agent",
    "step": "14",
    "title": "Human-agent collaboration",
    "description": "Match autonomy, monitoring, approval, and human decision authority to the risk and evidence of each agent action.",
    "time": "45-60 min",
    "outcome": "Design HITL/HOTL/autonomous boundaries, approval and confidence escalation, intervention, supervision, mixed initiative, handoffs, explainable actions, trust calibration, and revocable autonomy.",
    "lesson": "Northstar maps status, investigation, mitigation proposal, and critical rollback to low/medium/high/critical oversight while preserving evidence, explanation, modification/rejection, cancellation, and audit.",
    "exercise": "Run the risk controller, compare all four tiers, trigger low-confidence escalation, then design approval packets, handoffs, and intervention metrics.",
    "failures": [],
    "notebook": "curriculum/advanced/28-human-agent-collaboration/human_agent_collaboration.ipynb",
    "refs": [
      "curriculum/advanced/28-human-agent-collaboration/README.md",
      "curriculum/advanced/28-human-agent-collaboration/human_agent_collaboration.ipynb",
      "https://www.nist.gov/itl/ai-risk-management-framework",
      "https://arxiv.org/abs/1902.04623"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "e15",
    "level": "Enterprise Agent",
    "step": "15",
    "title": "Agent orchestration",
    "description": "Separate agent intelligence from deterministic systems that route, persist, schedule, recover, parallelize, and approve work.",
    "time": "45-60 min",
    "outcome": "Design orchestrators, routers, state machines, graph/DAG workflows, queues/events/schedules, checkpoints, durable execution, parallel joins, approval nodes, and recovery.",
    "lesson": "Northstar routes an incident into a durable graph, runs independent evidence in parallel, checkpoints an approval proposal, and resumes only through a trusted approval event.",
    "exercise": "Run the deterministic graph, inspect route/join/checkpoint/approval transitions, then add a timeout, retry, schedule, recovery, and duplicate-event policy.",
    "failures": [],
    "notebook": "curriculum/advanced/29-agent-orchestration/agent_orchestration.ipynb",
    "refs": [
      "curriculum/advanced/29-agent-orchestration/README.md",
      "curriculum/advanced/29-agent-orchestration/agent_orchestration.ipynb",
      "https://docs.langchain.com/oss/python/langgraph/overview",
      "https://docs.temporal.io/workflows",
      "https://docs.crewai.com/en/concepts/flows"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which responsibilities belong to deterministic agent orchestration rather than a model's free-form reasoning?",
        "options": [
          "Persisting state, checkpoints, and terminal reasons",
          "Routing, queue/event handling, scheduling, and bounded retries",
          "Approving its own high-impact action from a chat message",
          "Idempotency, cancellation, recovery, and revalidation on resume",
          "Joining dependency-ready parallel work before a proposal node"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      }
    ]
  },
  {
    "id": "e16",
    "level": "Enterprise Agent",
    "step": "16",
    "title": "Agent communication and coordination",
    "description": "Coordinate only the smallest eligible team through typed messaging, scoped evidence, bounded convergence, and comparison to a strong single-agent baseline.",
    "time": "45-60 min",
    "outcome": "Design messaging, shared state/blackboards, delegation, handoffs, negotiation, consensus/voting/debate, discovery, allocation, conflict resolution, and evidence-based team selection.",
    "lesson": "Northstar forms three specialists for a cross-domain incident, publishes provenance-tagged artifacts to a scoped blackboard, invokes a critic, and escalates disagreement rather than fabricating consensus.",
    "exercise": "Run the team router and blackboard, compare a supported proposal with a conflict path, then evaluate single-agent versus team success, cost, latency, and policy risk.",
    "failures": [],
    "notebook": "curriculum/advanced/30-agent-communication-coordination/agent_communication_coordination.ipynb",
    "refs": [
      "curriculum/advanced/30-agent-communication-coordination/README.md",
      "curriculum/advanced/30-agent-communication-coordination/agent_communication_coordination.ipynb",
      "https://docs.langchain.com/oss/python/langchain/multi-agent/index",
      "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html",
      "https://arxiv.org/abs/2501.06322"
    ],
    "code": "",
    "quiz": [
      {
        "q": "When is a multi-agent team justified over one well-designed agent?",
        "options": [
          "When distinct tools or contexts improve a named subtask",
          "When independent work reduces critical-path latency after join overhead",
          "Whenever a manager role makes a demo look more realistic",
          "When independent critique measurably catches material errors",
          "After comparison on the same task set for supported success, cost, latency, and policy risk"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      },
      {
        "q": "What makes a shared blackboard safer than an unrestricted multi-agent transcript?",
        "options": [
          "Typed, attributable artifacts with source or evidence identifiers",
          "Tenant-scoped read/write controls and versioning or correction history",
          "Treating the latest agent message as the authoritative fact",
          "A conflict policy that requests evidence or escalates rather than forcing consensus",
          "Budgets and termination rules for follow-up messages and debate"
        ],
        "answer": [
          0,
          1,
          3,
          4
        ]
      }
    ]
  },
  {
    "id": "e17",
    "level": "Enterprise Agent",
    "step": "17",
    "title": "The agent protocol stack",
    "description": "Use complementary protocols for tool/context access, remote agent delegation, user interaction, generated UI, commerce, and payments without confusing metadata with authority.",
    "time": "45-60 min",
    "outcome": "Explain MCP, A2A, AG-UI, A2UI, UCP, and AP2 boundaries; design trusted discovery/delegation; and keep identity, policy, authorization, audit, and recovery independent of protocol messages.",
    "lesson": "Northstar discovers an eligible release-analysis agent, delegates a tenant-scoped task, invokes a narrow deployment tool, and presents an approval card while blocking cross-tenant, denied-tool, and invalid-UI paths.",
    "exercise": "Run the protocol-boundary simulator, test trusted A2A discovery and delegation, MCP tool scopes, AG-UI/A2UI approval events, then add expiry, revocation, and payment-intent controls.",
    "failures": [],
    "notebook": "curriculum/advanced/31-agent-protocol-stack/agent_protocol_stack.ipynb",
    "refs": [
      "curriculum/advanced/31-agent-protocol-stack/README.md",
      "curriculum/advanced/31-agent-protocol-stack/agent_protocol_stack.ipynb",
      "https://modelcontextprotocol.io/specification/",
      "https://a2a-protocol.org/latest/",
      "https://docs.ag-ui.com/",
      "https://a2ui.org/specification/v0.9-a2ui/"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which protocol-layer pairings are correctly described?",
        "options": [
          "A2A: remote agent discovery, tasks, messages, delegation, and status",
          "AG-UI: agent-to-user-application interaction events and state",
          "A2UI: schema-rendered dynamic interface descriptions",
          "MCP: a replacement for payment-provider consent and fraud controls",
          "UCP/AP2-style boundaries: commerce/payment intent that still require separate authorization controls"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "a1",
    "level": "Advanced",
    "step": "06",
    "title": "Multi-agent teams",
    "description": "Design manager, handoff, peer, parallel, and graph topologies with explicit ownership.",
    "time": "45-60 min",
    "outcome": "Explain when coordination overhead is justified and how to bound delegation.",
    "lesson": "Design manager, handoff, peer, parallel, and graph topologies with explicit ownership.",
    "exercise": "Design manager, handoff, peer, parallel, and graph topologies with explicit ownership.",
    "failures": [],
    "notebook": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb",
    "refs": [
      "docs/multi-agent-systems.md",
      "assets/multi-agent-patterns.mmd"
    ],
    "code": "",
    "quiz": []
  },
  {
    "id": "a2",
    "level": "Advanced",
    "step": "07",
    "title": "Production operations",
    "description": "Add durable state, approvals, observability, replay, and rollback to long-running runs.",
    "time": "45-60 min",
    "outcome": "Define operational SLOs and recovery paths for an agentic system.",
    "lesson": "Add durable state, approvals, observability, replay, and rollback to long-running runs.",
    "exercise": "Add durable state, approvals, observability, replay, and rollback to long-running runs.",
    "failures": [],
    "notebook": "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
    "refs": [
      "curriculum/intermediate/05-agent-evaluation/README.md#release-gates",
      "https://langchain-ai.github.io/langgraph/concepts/durable_execution/"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which controls belong between a model-proposed action and tool execution?",
        "options": [
          "Schema validation",
          "Authorization for the exact resource and operation",
          "Approval when the action crosses a risk boundary",
          "Blindly trusting the model's stated intent",
          "Budget and policy checks"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which layers should a useful agent evaluation cover?",
        "options": [
          "Real task outcome",
          "Action and tool-use trajectory",
          "Latency, cost, and failure operations",
          "Only the fluency of the final response",
          "Policy compliance and side effects"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      },
      {
        "q": "Which inputs should an agent treat as untrusted?",
        "options": [
          "Retrieved documents and web pages",
          "Tool results",
          "Messages from another agent",
          "User-supplied content",
          "A tool result solely because it is formatted as JSON"
        ],
        "answer": [
          0,
          1,
          2,
          3,
          4
        ]
      },
      {
        "q": "Which practices reduce risk for agent-initiated write operations?",
        "options": [
          "Use idempotency keys",
          "Preview and validate the proposed change",
          "Persist a receipt and verify resulting state",
          "Automatically retry when the previous outcome is unknown",
          "Attach the initiating identity and run ID"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "a3",
    "level": "Advanced",
    "step": "08",
    "title": "Interoperability and autonomy",
    "description": "Combine MCP, A2A, human boundaries, and autonomy measurement without losing control.",
    "time": "45-60 min",
    "outcome": "Map protocol boundaries and choose where identity, policy, and approval are enforced.",
    "lesson": "Combine MCP, A2A, human boundaries, and autonomy measurement without losing control.",
    "exercise": "Combine MCP, A2A, human boundaries, and autonomy measurement without losing control.",
    "failures": [],
    "notebook": "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
    "refs": [
      "https://modelcontextprotocol.io/",
      "https://a2a-protocol.org/"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which statements about MCP and agent-to-agent protocols are accurate?",
        "options": [
          "MCP connects AI applications to contextual data and tools",
          "Agent-to-agent protocols can support capability discovery and task exchange",
          "MCP and A2A-style protocols can be complementary",
          "A protocol automatically grants every connected party full trust",
          "Protocol messages still require authentication and policy enforcement"
        ],
        "answer": [
          0,
          1,
          2,
          4
        ]
      }
    ]
  },
  {
    "id": "a4",
    "level": "Advanced",
    "step": "09",
    "title": "Safety readiness",
    "description": "Threat-model prompt injection, tool abuse, memory poisoning, and budget exhaustion.",
    "time": "45-60 min",
    "outcome": "Turn threat-model findings into a production readiness gate and rollback plan.",
    "lesson": "Threat-model prompt injection, tool abuse, memory poisoning, and budget exhaustion.",
    "exercise": "Threat-model prompt injection, tool abuse, memory poisoning, and budget exhaustion.",
    "failures": [],
    "notebook": "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb",
    "refs": [
      "curriculum/intermediate/05-agent-evaluation/README.md",
      "https://genai.owasp.org/"
    ],
    "code": "",
    "quiz": [
      {
        "q": "Which inputs should an agent treat as untrusted?",
        "options": [
          "Retrieved documents and web pages",
          "Tool results",
          "Messages from another agent",
          "User-supplied content",
          "A tool result solely because it is formatted as JSON"
        ],
        "answer": [
          0,
          1,
          2,
          3,
          4
        ]
      }
    ]
  },
  {
    "id": "a5",
    "level": "Advanced",
    "step": "10",
    "title": "Research team capstone",
    "description": "Coordinate search, critique, synthesis, citations, evaluation, and escalation.",
    "time": "45-60 min",
    "outcome": "Compare a bounded multi-agent team with a simpler single-agent baseline.",
    "lesson": "Coordinate search, critique, synthesis, citations, evaluation, and escalation.",
    "exercise": "Coordinate search, critique, synthesis, citations, evaluation, and escalation.",
    "failures": [],
    "notebook": "curriculum/advanced/05-incident-response/incident_response.ipynb",
    "refs": [
      "docs/multi-agent-systems.md",
      "curriculum/advanced/02-autogen-selector-teams/02_autogen_selector_teams.ipynb"
    ],
    "code": "",
    "quiz": []
  }
];



const base = "https://github.com/mahsa-teimourikia/awsome-ai-agents/blob/main/";

const levels:Record<Level,{sub:string;color:string}>={Beginner:{sub:"Build one trustworthy agent",color:"mint"},Intermediate:{sub:"Improve and measure tools",color:"gold"},Advanced:{sub:"Design for coordination",color:"coral"},"Enterprise Agent":{sub:"Scale to production",color:"blue"}};

export default function Home(){
 const [level,setLevel]=useState<"All"|Level>("All"); const [selected,setSelected]=useState(subjects[0]); const [tab,setTab]=useState<"learn"|"lab"|"quiz">("learn"); const [answers,setAnswers]=useState<Record<number,number>>({}); const [completed,setCompleted]=useState<string[]>([]);
 useEffect(()=>{try{const saved=window.localStorage.getItem("ai-agents-field-guide-progress-v1");if(saved)setCompleted(JSON.parse(saved));}catch{}} ,[]);
 useEffect(()=>{try{window.localStorage.setItem("ai-agents-field-guide-progress-v1",JSON.stringify(completed));}catch{}} ,[completed]);
 const filtered=useMemo(()=>level==="All"?subjects:subjects.filter(s=>s.level===level),[level]); 
 
 const isCorrect = (q:any, j:number) => Array.isArray(q.answer) ? q.answer.includes(j) : q.answer === j;
 const score=selected.quiz.reduce((n,q,i)=>n+(answers[i] !== undefined && isCorrect(q, answers[i]) ? 1 : 0),0);
 const select=(s:Subject)=>{setSelected(s);setTab("learn");setAnswers({});window.setTimeout(()=>document.getElementById("lesson-workspace")?.scrollIntoView({behavior:"smooth",block:"start"}),0);};
 
 return <main>
  <nav className="nav"><div className="brand"><span className="brand-mark">✦</span><span>AI AGENTS / <em>FIELD GUIDE</em></span></div><div className="nav-links"><a href="#curriculum">Curriculum</a><a href="/awsome-ai-agents/quiz/">Full quiz</a><a href="#how">How it works</a><a className="repo" href="https://github.com/mahsa-teimourikia/awsome-ai-agents" target="_blank">Open repo ↗</a></div></nav>
  <section className="hero"><div className="hero-copy"><div className="eyebrow">THE OPEN-SOURCE PATH · FROM THEORY TO OPERATIONS</div><h1>Build agents<br/><span>that know why.</span></h1><p className="hero-lede">A notebook-first learning hub built from the <em>awsome-ai-agents</em> repository: follow one scenario, learn the theory, run the Python, break the system, measure the fix, and keep the evidence.</p><div className="hero-actions"><a className="button primary" href="#curriculum">Start the curriculum <span>↓</span></a><a className="text-link" href="/awsome-ai-agents/quiz/">Take the full quiz ↗</a></div><div className="hero-meta"><span><b>36</b> scenario notebooks</span><span><b>36</b> repo lessons</span><span><b>1</b> learning hub</span></div></div><div className="hero-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="core"><span>AGENTS</span><small>autonomous systems</small></div><div className="node node-a">01<br/><b>PLAN</b></div><div className="node node-b">02<br/><b>ACT</b></div><div className="node node-c">03<br/><b>OBSERVE</b></div><div className="art-caption">Your agent is only<br/><strong>as good as its bounds.</strong></div></div></section>
  <section className="signal"><div><span className="signal-icon">↗</span><b>FOLLOW THE REPO</b><p>Objectives, notebooks, exercises, and next steps are mapped from the source material.</p></div><div><span className="signal-icon">⌁</span><b>LEARN IN LOOPS</b><p>Read a concept. Run the lab. Change one variable. Inspect the failure.</p></div><div><span className="signal-icon">◌</span><b>CHECK YOUR SIGNAL</b><p>Use the checkpoint quiz and the repo’s tests to see what actually stuck.</p></div></section>

  <section id="curriculum" className="curriculum"><div className="section-intro"><div><div className="eyebrow">THE CURRICULUM MAP</div><h2>One path.<br/>Four altitudes.</h2></div><p>The repo recommends starting with a beginner bounded loop, then improving tool engineering, and finally designing for teams, memory, and enterprise operations.</p></div><div className="progress-summary" aria-live="polite">{completed.length} of {subjects.length} lessons complete</div><div className="level-tabs"><button className={level==="All"?"active":""} onClick={()=>setLevel("All")}>All lessons <span>· {subjects.length} modules</span></button>{(["Beginner","Intermediate","Advanced","Enterprise Agent"] as Level[]).map(l=><button key={l} className={level===l?"active":""} onClick={()=>setLevel(l)}>{l}<span>· {levels[l].sub}</span></button>)}</div><div className="curriculum-grid">{filtered.map(s=><button className={"subject-card " + (selected.id===s.id?"selected ":"") + "level-" + s.level.replace(" ", "-")} key={s.id} onClick={()=>select(s)}><div className="card-top"><span className={"pill " + levels[s.level].color}>{s.level} · {s.step}</span><span className="duration">{s.time}</span>{completed.includes(s.id)&&<span className="completed-mark" aria-label="Completed">✓</span>}</div><h3>{s.title}</h3><p>{s.description}</p><span className="card-arrow">→</span></button>)}</div></section>
  <section id="lesson-workspace" className="workspace"><div className="workspace-heading"><div><div className="eyebrow">LESSON {selected.step} · {selected.level.toUpperCase()}</div><h2>{selected.title}</h2></div><div className="session-count"><span className="dot"/> {selected.time} <span>·</span> repo-grounded</div></div><div className="lesson-tabs"><button onClick={()=>setTab("learn")} className={tab==="learn"?"active":""}>01 / Learn</button><button onClick={()=>setTab("lab")} className={tab==="lab"?"active":""}>02 / Lab</button><button onClick={()=>setTab("quiz")} className={tab==="quiz"?"active":""}>03 / Checkpoint</button></div><div className="workspace-body">
   {tab==="learn"&&<><div className="lesson-copy"><div className="eyebrow">OUTCOME</div><p className="outcome">{selected.outcome}</p><button className="complete-lesson" onClick={()=>setCompleted(completed.includes(selected.id)?completed.filter(id=>id!==selected.id):[...completed,selected.id])}>{completed.includes(selected.id)?"Completed ✓":"Mark lesson complete"}</button><div className="material-actions"><a className="button primary" href={base+guidePaths[selected.id]} target="_blank">Read lesson material ↗</a><a className="notebook-link inline-link" href={base+selected.notebook} target="_blank">Open companion notebook ↗</a></div><div className="eyebrow">THE IDEA</div><p className="big-copy">{selected.lesson}</p><div className="failure-strip"><span className="eyebrow">WATCH FOR</span>{selected.failures.map(f=><span key={f}>× {f}</span>)}</div></div><div className="diagram"><div className="diagram-label">THE STUDY LOOP</div><div className="flow"><div className="flow-box">Read<small>concept</small></div><i>→</i><div className="flow-box active-box">Run<small>notebook</small></div><i>→</i><div className="flow-box">Change<small>one thing</small></div></div><div className="diagram-note">Make the failure visible.<br/><span>Then turn the fix into a test.</span></div><div className="reference-list"><span className="eyebrow">SOURCE MATERIAL</span>{selected.refs.map((r,i)=><a key={r} href={r.startsWith("http")?r:base+r} target="_blank"><span>0{i+1}</span>{r} ↗</a>)}</div><div className="next-step"><span className="eyebrow">AFTER THIS LESSON</span><p>{selected.level==="Beginner"?"Continue to the next beginner module, then move on to the intermediate track.":selected.level==="Intermediate"?"Continue to the next experiment, keeping a golden set open as you tune.":"Continue to the next advanced pattern, carrying forward authorization, evaluation, and traceability."}</p><button onClick={()=>{const n=subjects[subjects.findIndex(x=>x.id===selected.id)+1];if(n)select(n)}}>Next lesson →</button></div></div></>}
   {tab==="lab"&&<div className="lab-layout workspace-single-column"><div className="lesson-copy"><div className="eyebrow">PRACTICAL LAB</div><p className="big-copy">{selected.exercise}</p><a className="notebook-link" href={base+selected.notebook} target="_blank">Run the guided notebook ↗</a><div className="lab-note"><b>Study ritual from the repo</b><br/>Use the notebook as the primary lab: read the concept cells, run the implementation, change one variable, run the tests, and explain one failure mode.</div></div><pre><code>{selected.code}</code></pre></div>}
   {tab==="quiz"&&<div className="quiz workspace-single-column"><div className="quiz-head"><div><div className="eyebrow">CHECKPOINT QUIZ</div><p>Answer from the lesson. The repo’s original quiz uses the same habit: explain why, then follow the source.</p></div><div className="score">{Object.keys(answers).length?score + "/" + selected.quiz.length:"—"}<small>score</small></div></div>{selected.quiz.map((q,i)=><div className="question" key={q.q}><b>{String(i+1).padStart(2,"0")} / {q.q}</b><div className="options">{q.options.map((o,j)=><button key={o} onClick={()=>setAnswers({...answers,[i]:j})} className={answers[i]===j?(isCorrect(q, j)?"correct":"wrong"):""}>{o}<span>{answers[i]===j?(isCorrect(q, j)?"✓":"×"):""}</span></button>)}</div></div>)}</div>}
  </div></section>
  <section id="how" className="footer-cta"><div className="eyebrow">THE REPO’S RULE OF THUMB</div><h2>Read the idea.<br/><span>Run the evidence.</span></h2><p>Every lesson here links back to the original <a href="https://github.com/mahsa-teimourikia/awsome-ai-agents" target="_blank">awsome-ai-agents</a> curriculum, notebooks, and references. Use the full quiz when you want one cross-topic knowledge check.</p><a className="button dark" href="/awsome-ai-agents/quiz/">Open the full quiz ↗</a></section><footer><span>AI AGENTS / FIELD GUIDE</span><span>OPEN SOURCE · LEARN IN PUBLIC</span><a href="https://oneplusi.io" target="_blank">ONE+i · RESPONSIBLE AI ↗</a><a href="https://github.com/mahsa-teimourikia/awsome-ai-agents" target="_blank">github ↗</a></footer>
 </main>;
}
