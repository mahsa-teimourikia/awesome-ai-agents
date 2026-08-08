export const questions = [
  {
    id: "foundations-components",
    category: "Foundations",
    prompt: "Which are core components of a practical AI agent?",
    options: [
      "A model that chooses the next action",
      "Instructions that define goals and boundaries",
      "Tools that expose controlled operations",
      "A fashionable chat interface",
      "State and a bounded control loop",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "An agent combines a model, instructions, tools, state, and a control loop. A chat interface can be useful, but it is not what makes the system an agent.",
    source: {
      label: "What is an AI agent? — A practical definition",
      url: "docs/what-is-an-ai-agent.md#a-practical-definition",
    },
  },
  {
    id: "foundations-control",
    category: "Foundations",
    prompt: "Which statements correctly distinguish workflows from agents?",
    options: [
      "A workflow follows code-defined paths",
      "An agent dynamically directs its process and tool use",
      "A workflow can still contain model decisions",
      "Every multi-step model application is automatically an agent",
      "A fixed workflow may be preferable for predictable tasks",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "The distinction concerns control. Workflows define paths in code; agents give the model more discretion. Hybrid agentic workflows can contain bounded model decisions.",
    source: {
      label: "Agentic workflows — Workflow versus agent",
      url: "docs/agentic-workflows.md#workflow-versus-agent",
    },
  },
  {
    id: "foundations-stopping",
    category: "Foundations",
    prompt: "Which are appropriate terminal conditions for an agent run?",
    options: [
      "A deterministic validator accepts the result",
      "The turn or spend budget is exhausted",
      "A policy requires human escalation",
      "The agent has called at least one tool",
      "No useful safe action remains",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Completion, budgets, policy escalation, and lack of a useful safe next action are legitimate terminal states. Calling a tool alone says nothing about task completion.",
    source: {
      label: "What is an AI agent? — Stop conditions",
      url: "docs/what-is-an-ai-agent.md#stop-conditions",
    },
  },
  {
    id: "loop-react",
    category: "Agent Loop",
    prompt: "What does a ReAct-style loop do?",
    options: [
      "Interleaves reasoning with actions and observations",
      "Uses observations to update subsequent decisions",
      "Requires model-weight updates after every tool call",
      "Lets tools gather information from an environment",
      "Guarantees that every trajectory is correct",
    ],
    correct: [0, 1, 3],
    explanation:
      "ReAct interleaves reasoning, action, and observation so external feedback can update the plan. It neither requires weight updates nor guarantees correctness.",
    source: {
      label: "What is an AI agent? — The agent loop",
      url: "docs/what-is-an-ai-agent.md#the-agent-loop",
    },
  },
  {
    id: "loop-boundary",
    category: "Agent Loop",
    prompt: "Which controls belong between a model-proposed action and tool execution?",
    options: [
      "Schema validation",
      "Authorization for the exact resource and operation",
      "Approval when the action crosses a risk boundary",
      "Blindly trusting the model's stated intent",
      "Budget and policy checks",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "The model proposes an action; application code validates its shape, authorization, policy, budget, and any approval requirement before execution.",
    source: {
      label: "Evaluation and security — Permission model",
      url: "docs/evaluation-and-security.md#permission-model",
    },
  },
  {
    id: "loop-reliability",
    category: "Agent Loop",
    prompt: "Which practices make a long-running agent loop more reliable?",
    options: [
      "Checkpoint meaningful state",
      "Represent failures as typed states",
      "Retry every write after any timeout",
      "Cap turns, time, tokens, tool calls, and spend",
      "Record a clear termination reason",
    ],
    correct: [0, 1, 3, 4],
    explanation:
      "Checkpointing, typed failures, hard budgets, and explicit termination improve recovery and auditability. Retrying a write after an uncertain result can duplicate a side effect.",
    source: {
      label: "Agentic workflows — Reliability patterns",
      url: "docs/agentic-workflows.md#reliability-patterns",
    },
  },
  {
    id: "agentops-evidence",
    category: "Agent Loop",
    prompt: "In the AgentOps checkout scenario, what evidence should the assistant collect before claiming there is an active incident?",
    options: [
      "Current service health for checkout or a dependency",
      "An active incident record that matches checkout/payment failure symptoms",
      "The relevant checkout runbook or response policy",
      "A user instruction that says customers are upset",
      "Enough context to distinguish evidence from speculation",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "The assistant should ground its recommendation in service health, incident records, and runbook guidance. A customer report is a signal to investigate, not proof of an active incident.",
    source: {
      label: "AgentOps Lab",
      url: "docs/agentops-lab.md#notebook-01-learning-objectives",
    },
  },
  {
    id: "agentops-budgets",
    category: "Agent Loop",
    prompt: "Why does the manual AgentOps loop include step, tool-call, and cost budgets?",
    options: [
      "They prevent open-ended investigation loops",
      "They create auditable terminal reasons",
      "They let the application stop safely when confidence is not improving",
      "They guarantee the model will choose the correct tool",
      "They keep operational cost and latency bounded",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Budgets do not make a model correct, but they keep the application in control when the model repeats itself, seeks impossible certainty, or consumes too much time or spend.",
    source: {
      label: "AgentOps Lab",
      url: "docs/agentops-lab.md#notebook-01-learning-objectives",
    },
  },
  {
    id: "tools-contract",
    category: "Tools & Memory",
    prompt: "Which properties improve an agent-facing tool contract?",
    options: [
      "A narrow, unambiguous purpose",
      "Typed input and output schemas",
      "Useful errors and explicit risk metadata",
      "A single tool that performs every available operation",
      "Idempotency or preview support for risky writes",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Good agent tools are narrow, typed, clear about failures and risk, and safe to preview or repeat. Overly broad tools make selection, permissioning, and evaluation harder.",
    source: {
      label: "What is an AI agent? — Tools",
      url: "docs/what-is-an-ai-agent.md#tools",
    },
  },
  {
    id: "agentops-sdk-ownership",
    category: "Tools & Memory",
    prompt: "When rebuilding the AgentOps incident investigator with the OpenAI Agents SDK, which responsibilities can the framework package?",
    options: [
      "Function-tool schema generation",
      "Turn execution through a runner",
      "Tool dispatch and message state",
      "Product-specific authorization policy",
      "Tracing and session continuity",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "The SDK can package the loop mechanics, tool schemas, dispatch, traces, and sessions. Product-specific authorization, approval, and side-effect boundaries still belong in application design.",
    source: {
      label: "AgentOps Lab - Notebook 03",
      url: "docs/agentops-lab.md#notebook-03-learning-objectives",
    },
  },
  {
    id: "agentops-sdk-loop",
    category: "Tools & Memory",
    prompt: "What is the key lesson of replacing the manual loop with an agent framework?",
    options: [
      "The loop still exists even when the SDK manages it",
      "Framework traces help inspect model and tool behavior",
      "Tool boundaries no longer matter once a framework is used",
      "Sessions can help preserve working context",
      "Application code still defines which tools are safe to expose",
    ],
    correct: [0, 1, 3, 4],
    explanation:
      "Frameworks package the loop; they do not erase it. Traces and sessions improve inspectability and continuity, but tool exposure and safety boundaries remain design responsibilities.",
    source: {
      label: "AgentOps Lab - Notebook 03",
      url: "docs/agentops-lab.md#notebook-03-learning-objectives",
    },
  },
  {
    id: "memory-safety",
    category: "Tools & Memory",
    prompt: "Which controls are appropriate for long-term agent memory?",
    options: [
      "Store provenance for memory writes",
      "Scope memory by user and tenant",
      "Allow inspection and deletion",
      "Treat every model-generated memory as verified truth",
      "Apply validation and retention rules",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Long-term memory influences future runs, so writes need provenance, isolation, validation, retention, review, and deletion. Model-generated content is not automatically trustworthy.",
    source: {
      label: "What is an AI agent? — State and memory",
      url: "docs/what-is-an-ai-agent.md#state-and-memory",
    },
  },
  {
    id: "agentops-langgraph-state",
    category: "Tools & Memory",
    prompt: "In the AgentOps LangGraph lesson, what belongs in thread-scoped incident state?",
    options: [
      "The current request",
      "Evidence collected during this investigation",
      "Attempt count and confidence",
      "An unverified permanent claim that all checkout failures are caused by Redis",
      "The recommendation for this run",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Thread-scoped state tracks the current run: request, service, evidence, confidence, attempts, suspected cause, and recommendation. Unverified permanent facts belong behind memory validation, not directly in working state.",
    source: {
      label: "AgentOps Lab - Notebook 05",
      url: "docs/agentops-lab.md#notebook-05-learning-objectives",
    },
  },
  {
    id: "agentops-memory-bias",
    category: "Tools & Memory",
    prompt: "Why is the accidental Acme memory 'Checkout problems are usually caused by Redis' risky?",
    options: [
      "It can bias future diagnoses before fresh evidence is collected",
      "It is an unverified operational fact",
      "It should be scoped, auditable, and reversible",
      "It proves Redis is the root cause of the current incident",
      "It needs validation before influencing recommendations",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Unverified long-term memory can steer future incident diagnosis away from current evidence. It needs provenance, validation, scope, auditability, and a way to deactivate or delete it.",
    source: {
      label: "AgentOps Lab - Notebook 05",
      url: "docs/agentops-lab.md#notebook-05-learning-objectives",
    },
  },
  {
    id: "agentops-admin-api",
    category: "Tools & Memory",
    prompt: "Why is a broad `admin_api(command: str)` dangerous for an agent?",
    options: [
      "It hides intent inside a free-form string",
      "It mixes read-only and destructive capabilities",
      "It makes authorization and validation ambiguous",
      "It forces every operation to be safe and auditable",
      "It makes predictable error handling harder",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "A broad command tool collapses many risk levels into one string interface. Narrow tools make schema validation, permissions, approvals, tracing, and retries much clearer.",
    source: {
      label: "AgentOps Lab - Notebook 04",
      url: "docs/agentops-lab.md#notebook-04-learning-objectives",
    },
  },
  {
    id: "agentops-tool-errors",
    category: "Tools & Memory",
    prompt: "Which retry and escalation decisions are appropriate for the tool-engineering lab?",
    options: [
      "Retry `ToolTimeout` when the retry budget allows",
      "Retry or back off on `RateLimit`",
      "Escalate `PermissionDenied` to a human or higher-trust workflow",
      "Keep retrying `InvalidService` until it works",
      "Stop when validation proves the request is malformed",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Transient timeout and rate-limit errors may be retried within a budget. Permission failures should escalate, while invalid or malformed requests should stop rather than loop.",
    source: {
      label: "AgentOps Lab - Notebook 04",
      url: "docs/agentops-lab.md#notebook-04-learning-objectives",
    },
  },
  {
    id: "agentops-permission-levels",
    category: "Tools & Memory",
    prompt: "Which permission mapping fits the AgentOps human-in-the-loop lesson?",
    options: [
      "READ: query logs and retrieve runbooks",
      "READ: restart checkout-api immediately",
      "PROPOSE: prepare rollback or draft notification",
      "EXECUTE WITH APPROVAL: restart, rollback, or send notification",
      "EXECUTE WITH APPROVAL: any tool call, including status reads",
    ],
    correct: [0, 2, 3],
    explanation:
      "Read-only evidence tools should not require the same approval burden as consequential actions. Rollbacks, restarts, and customer notifications should pause for approval.",
    source: {
      label: "AgentOps Lab - Notebook 06",
      url: "docs/agentops-lab.md#notebook-06-learning-objectives",
    },
  },
  {
    id: "agentops-hitl-resume",
    category: "Tools & Memory",
    prompt: "What should a human approval checkpoint preserve before resuming an agent run?",
    options: [
      "The exact proposed action and arguments",
      "Evidence that motivated the action",
      "The reviewer decision: approve, modify, or reject",
      "A vague context-free approval prompt only",
      "An audit reason and actor identity",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Effective HITL checkpoints preserve the action, evidence, reviewer identity, decision, reason, and final action. Context-free approval creates review fatigue and weak auditability.",
    source: {
      label: "AgentOps Lab - Notebook 06",
      url: "docs/agentops-lab.md#notebook-06-learning-objectives",
    },
  },
  {
    id: "protocols",
    category: "Tools & Memory",
    prompt: "Which statements about MCP and agent-to-agent protocols are accurate?",
    options: [
      "MCP connects AI applications to contextual data and tools",
      "Agent-to-agent protocols can support capability discovery and task exchange",
      "MCP and A2A-style protocols can be complementary",
      "A protocol automatically grants every connected party full trust",
      "Protocol messages still require authentication and policy enforcement",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "MCP primarily connects applications to context and tools, while A2A-style protocols coordinate agents. Neither protocol removes the need for identity, authorization, and message validation.",
    source: {
      label: "README — Tools, memory, and protocols",
      url: "README.md#tools-memory-and-protocols",
    },
  },
  {
    id: "workflow-routing",
    category: "Workflows",
    prompt: "Which are good practices for a routing workflow?",
    options: [
      "Evaluate routing accuracy separately",
      "Include an unknown or human-escalation route",
      "Give every route identical tools and policies regardless of need",
      "Use specialist paths when categories need different controls",
      "Log the selected route for diagnosis",
    ],
    correct: [0, 1, 3, 4],
    explanation:
      "Routing is useful when categories need distinct prompts, tools, models, or policies. Unknown cases, routing evaluation, and traceability reduce silent misroutes.",
    source: {
      label: "Architecture patterns — Routing",
      url: "docs/architecture-patterns.md#3-routing",
    },
  },
  {
    id: "workflow-evaluator",
    category: "Workflows",
    prompt: "When is an evaluator-optimizer loop a strong fit?",
    options: [
      "Success criteria are explicit",
      "Feedback can guide a concrete revision",
      "Iteration is bounded",
      "There is no way to assess whether the output improved",
      "Deterministic graders can supplement model judgment",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Evaluator-optimizer works when quality can be judged and feedback can improve the artifact. Bound iterations and prefer executable or deterministic checks where available.",
    source: {
      label: "Architecture patterns — Evaluator-optimizer",
      url: "docs/architecture-patterns.md#6-evaluator-optimizer",
    },
  },
  {
    id: "agentops-task-a",
    category: "Workflows",
    prompt: "In AgentOps Task A, why is a deterministic workflow preferable to an agent?",
    options: [
      "The steps are known before runtime",
      "The task only needs a status read and report formatting",
      "A model-controlled loop would add unnecessary cost and failure paths",
      "Agents are never useful for operations work",
      "The expected output can be produced from structured tool data",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Task A has a fixed path: retrieve checkout status and format it. Operations work can absolutely use agents, but this task does not need dynamic tool selection.",
    source: {
      label: "AgentOps Lab - Notebook 02",
      url: "docs/agentops-lab.md#notebook-02-learning-objectives",
    },
  },
  {
    id: "agentops-task-c",
    category: "Workflows",
    prompt: "What makes AgentOps Task C a better fit for a bounded agent than a fixed workflow?",
    options: [
      "The evidence path is discovered at runtime",
      "The system may need to choose among service health, incidents, deployments, logs, and runbooks",
      "The task should still have max-step and tool boundaries",
      "The model should be allowed to call any production API it can name",
      "The final recommendation should preserve uncertainty instead of inventing root cause",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Task C justifies bounded agency because each observation affects the next evidence source. That does not remove application-owned tool allowlists, budgets, or grounding rules.",
    source: {
      label: "AgentOps Lab - Notebook 02",
      url: "docs/agentops-lab.md#notebook-02-learning-objectives",
    },
  },
  {
    id: "workflow-human",
    category: "Workflows",
    prompt: "What makes a human-approval checkpoint effective?",
    options: [
      "It occurs before the consequential side effect",
      "It shows the exact action, target, evidence, and expected effect",
      "It supports approve, edit, reject, or redirect outcomes",
      "It asks only a context-free 'Approve?' question",
      "The workflow checkpoints state while waiting",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Informed approval happens before consequence, presents decision context and alternatives, and pauses on durable state. A vague confirmation encourages approval fatigue.",
    source: {
      label: "Agentic workflows — Human-in-the-loop",
      url: "docs/agentic-workflows.md#human-in-the-loop-is-a-workflow-boundary",
    },
  },
  {
    id: "orchestration-ownership",
    category: "Orchestration",
    prompt: "Which statements correctly compare an agent-as-tool with a handoff?",
    options: [
      "An agent-as-tool lets the orchestrator retain ownership",
      "A handoff transfers control to a specialist",
      "Both patterns remove the need for scoped permissions",
      "The choice should reflect who owns the next interaction",
      "Both introduce a context and evaluation boundary",
    ],
    correct: [0, 1, 3, 4],
    explanation:
      "Agents-as-tools return a specialist result to the orchestrator; handoffs transfer ownership. Both still need permissions, context design, tracing, and evaluation.",
    source: {
      label: "Architecture patterns — Orchestrator-worker",
      url: "docs/architecture-patterns.md#5-orchestrator-worker",
    },
  },
  {
    id: "orchestration-when",
    category: "Orchestration",
    prompt: "When can a multi-agent design be justified?",
    options: [
      "Independent subtasks benefit from parallel execution",
      "Specialists need distinct context, tools, or policies",
      "Evaluation shows a meaningful gain over a simpler baseline",
      "The architecture looks more impressive in a demo",
      "An orchestrator can define clear delegation contracts",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Multi-agent systems can help through parallelism and specialization, but coordination has real cost. Use them when contracts are clear and measured gains exceed that cost.",
    source: {
      label: "Agentic workflows — When to introduce multiple agents",
      url: "docs/agentic-workflows.md#when-to-introduce-multiple-agents",
    },
  },
  {
    id: "orchestration-parallel",
    category: "Orchestration",
    prompt: "Which controls improve parallel worker orchestration?",
    options: [
      "Non-overlapping worker contracts",
      "A clear aggregation rule",
      "Provenance on worker outputs",
      "Unlimited delegation breadth and depth",
      "Per-worker budgets",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Clear contracts, provenance, aggregation, and budgets reduce duplicated work, merge errors, and runaway fan-out. Delegation depth and breadth should be bounded.",
    source: {
      label: "Architecture patterns — Parallelization and orchestrator-worker",
      url: "docs/architecture-patterns.md#4-parallelization",
    },
  },
  {
    id: "evaluation-layers",
    category: "Evaluation & Safety",
    prompt: "Which layers should a useful agent evaluation cover?",
    options: [
      "Real task outcome",
      "Action and tool-use trajectory",
      "Latency, cost, and failure operations",
      "Only the fluency of the final response",
      "Policy compliance and side effects",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Agent evaluation needs outcome, trajectory, operations, and safety evidence. Fluent final text can conceal a failed or unauthorized task.",
    source: {
      label: "Evaluation and security — Grade three layers",
      url: "docs/evaluation-and-security.md#grade-three-layers",
    },
  },
  {
    id: "security-trust",
    category: "Evaluation & Safety",
    prompt: "Which inputs should an agent treat as untrusted?",
    options: [
      "Retrieved documents and web pages",
      "Tool results",
      "Messages from another agent",
      "User-supplied content",
      "A tool result solely because it is formatted as JSON",
    ],
    correct: [0, 1, 2, 3, 4],
    explanation:
      "Origin and authorization determine trust, not presentation. User content, retrieval, tool output, and peer messages can all carry malicious or incorrect instructions—even in valid JSON.",
    source: {
      label: "Evaluation and security — Threat model",
      url: "docs/evaluation-and-security.md#threat-model",
    },
  },
  {
    id: "security-side-effects",
    category: "Evaluation & Safety",
    prompt: "Which practices reduce risk for agent-initiated write operations?",
    options: [
      "Use idempotency keys",
      "Preview and validate the proposed change",
      "Persist a receipt and verify resulting state",
      "Automatically retry when the previous outcome is unknown",
      "Attach the initiating identity and run ID",
    ],
    correct: [0, 1, 2, 4],
    explanation:
      "Safe writes use previews, idempotency, attribution, receipts, and state verification. An uncertain timeout may mean a write succeeded, so blind retries can duplicate it.",
    source: {
      label: "Evaluation and security — Side-effect safety",
      url: "docs/evaluation-and-security.md#side-effect-safety",
    },
  },
];
