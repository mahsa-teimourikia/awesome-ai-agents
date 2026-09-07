export const questions = [
  {
    "id": "computer-use-control-boundary",
    "category": "Computer-Using Agents",
    "prompt": "Which controls should intervene between a computer-use model's proposed click and a consequential UI action?",
    "options": [
      "A fresh observation and a unique grounded target",
      "Origin, authorization, risk, and action-budget validation",
      "A human confirmation bound to the exact commit action when policy requires it",
      "Trusting any instruction visible on the webpage",
      "A post-action state check or safe escalation path"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "A model proposes an action; deterministic control code verifies the current target and permissions, pauses consequential commits, and checks the resulting state. Page content is untrusted data and cannot grant authority.",
    "source": {
      "label": "Computer-Using Agents",
      "url": "curriculum/beginner/07-computer-using-agents/README.md"
    }
  },
  {
    "id": "computer-use-interaction-choice",
    "category": "Computer-Using Agents",
    "prompt": "Which statements correctly compare browser automation and visual computer use?",
    "options": [
      "A stable typed API is usually preferable when available",
      "DOM/accessibility automation can be easier to test on an owned app with stable semantic controls",
      "Screenshot-grounded interaction is useful for UI-only or visually meaningful interfaces",
      "Visual models remove the need for sandboxing and confirmation",
      "Both approaches require fresh observations and postcondition checks around consequential actions"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Interaction choice is a reliability and authorization decision. Visual capability broadens reach but does not make UI actions safe or deterministic.",
    "source": {
      "label": "Computer-Using Agents",
      "url": "curriculum/beginner/07-computer-using-agents/README.md#3-browser-automation-versus-visual-computer-use"
    }
  },
  {
    "id": "computer-use-ui-recovery",
    "category": "Computer-Using Agents",
    "prompt": "What are safe responses when a browser or GUI changes unexpectedly?",
    "options": [
      "Stop the stale action and obtain a fresh observation",
      "Use an allowlisted, unique visible target for one bounded recovery attempt",
      "Repeat the old coordinate until the UI reacts",
      "Escalate when the new target is ambiguous, risky, or outside scope",
      "Record the UI change and terminal or recovery reason in the trace"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "UI drift is an observation problem, not permission to click broadly. A safe controller re-grounds the action in current state, bounds recovery, and pauses whenever it cannot establish a unique authorized target.",
    "source": {
      "label": "Computer-Using Agents",
      "url": "curriculum/beginner/07-computer-using-agents/README.md#6-ui-changes-and-failure-recovery"
    }
  },
  {
    "id": "foundations-components",
    "category": "Foundations",
    "prompt": "Which are core components of a practical AI agent?",
    "options": [
      "A model that chooses the next action",
      "Instructions that define goals and boundaries",
      "Tools that expose controlled operations",
      "A fashionable chat interface",
      "State and a bounded control loop"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "An agent combines a model, instructions, tools, state, and a control loop. A chat interface can be useful, but it is not what makes the system an agent.",
    "source": {
      "label": "What is an AI agent? — A practical definition",
      "url": "curriculum/beginner/01-ai-agent-foundations/README.md#a-practical-definition"
    }
  },
  {
    "id": "foundations-control",
    "category": "Foundations",
    "prompt": "Which statements correctly distinguish workflows from agents?",
    "options": [
      "A workflow follows code-defined paths",
      "An agent dynamically directs its process and tool use",
      "A workflow can still contain model decisions",
      "Every multi-step model application is automatically an agent",
      "A fixed workflow may be preferable for predictable tasks"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The distinction concerns control. Workflows define paths in code; agents give the model more discretion. Hybrid agentic workflows can contain bounded model decisions.",
    "source": {
      "label": "Agentic workflows — Workflow versus agent",
      "url": "curriculum/beginner/03-workflow-or-agent/README.md#workflow-versus-agent"
    }
  },
  {
    "id": "foundations-stopping",
    "category": "Foundations",
    "prompt": "Which are appropriate terminal conditions for an agent run?",
    "options": [
      "A deterministic validator accepts the result",
      "The turn or spend budget is exhausted",
      "A policy requires human escalation",
      "The agent has called at least one tool",
      "No useful safe action remains"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Completion, budgets, policy escalation, and lack of a useful safe next action are legitimate terminal states. Calling a tool alone says nothing about task completion.",
    "source": {
      "label": "What is an AI agent? — Stop conditions",
      "url": "curriculum/beginner/01-ai-agent-foundations/README.md#stop-conditions"
    }
  },
  {
    "id": "loop-react",
    "category": "Agent Loop",
    "prompt": "What does a ReAct-style loop do?",
    "options": [
      "Interleaves reasoning with actions and observations",
      "Uses observations to update subsequent decisions",
      "Requires model-weight updates after every tool call",
      "Lets tools gather information from an environment",
      "Guarantees that every trajectory is correct"
    ],
    "correct": [
      0,
      1,
      3
    ],
    "explanation": "ReAct interleaves reasoning, action, and observation so external feedback can update the plan. It neither requires weight updates nor guarantees correctness.",
    "source": {
      "label": "What is an AI agent? — The agent loop",
      "url": "curriculum/beginner/01-ai-agent-foundations/README.md#the-agent-loop"
    }
  },
  {
    "id": "loop-boundary",
    "category": "Agent Loop",
    "prompt": "Which controls belong between a model-proposed action and tool execution?",
    "options": [
      "Schema validation",
      "Authorization for the exact resource and operation",
      "Approval when the action crosses a risk boundary",
      "Blindly trusting the model's stated intent",
      "Budget and policy checks"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The model proposes an action; application code validates its shape, authorization, policy, budget, and any approval requirement before execution.",
    "source": {
      "label": "Evaluation and security — Permission model",
      "url": "curriculum/intermediate/05-agent-evaluation/README.md#permission-model"
    }
  },
  {
    "id": "loop-reliability",
    "category": "Agent Loop",
    "prompt": "Which practices make a long-running agent loop more reliable?",
    "options": [
      "Checkpoint meaningful state",
      "Represent failures as typed states",
      "Retry every write after any timeout",
      "Cap turns, time, tokens, tool calls, and spend",
      "Record a clear termination reason"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Checkpointing, typed failures, hard budgets, and explicit termination improve recovery and auditability. Retrying a write after an uncertain result can duplicate a side effect.",
    "source": {
      "label": "Agentic workflows — Reliability patterns",
      "url": "curriculum/beginner/03-workflow-or-agent/README.md#reliability-patterns"
    }
  },
  {
    "id": "agentops-evidence",
    "category": "Agent Loop",
    "prompt": "In the AgentOps checkout scenario, what evidence should the assistant collect before claiming there is an active incident?",
    "options": [
      "Current service health for checkout or a dependency",
      "An active incident record that matches checkout/payment failure symptoms",
      "The relevant checkout runbook or response policy",
      "A user instruction that says customers are upset",
      "Enough context to distinguish evidence from speculation"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The assistant should ground its recommendation in service health, incident records, and runbook guidance. A customer report is a signal to investigate, not proof of an active incident.",
    "source": {
      "label": "AgentOps Lab",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-01-learning-objectives"
    }
  },
  {
    "id": "agentops-budgets",
    "category": "Agent Loop",
    "prompt": "Why does the manual AgentOps loop include step, tool-call, and cost budgets?",
    "options": [
      "They prevent open-ended investigation loops",
      "They create auditable terminal reasons",
      "They let the application stop safely when confidence is not improving",
      "They guarantee the model will choose the correct tool",
      "They keep operational cost and latency bounded"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Budgets do not make a model correct, but they keep the application in control when the model repeats itself, seeks impossible certainty, or consumes too much time or spend.",
    "source": {
      "label": "AgentOps Lab",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-01-learning-objectives"
    }
  },
  {
    "id": "tools-contract",
    "category": "Tool Engineering",
    "prompt": "Which properties improve an agent-facing tool contract?",
    "options": [
      "A narrow, unambiguous purpose",
      "Typed input and output schemas",
      "Useful errors and explicit risk metadata",
      "A single tool that performs every available operation",
      "Idempotency or preview support for risky writes"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Good agent tools are narrow, typed, clear about failures and risk, and safe to preview or repeat. Overly broad tools make selection, permissioning, and evaluation harder.",
    "source": {
      "label": "What is an AI agent? — Tools",
      "url": "curriculum/beginner/01-ai-agent-foundations/README.md#tools"
    }
  },
  {
    "id": "agentops-sdk-ownership",
    "category": "Tool Engineering",
    "prompt": "When rebuilding the AgentOps incident investigator with the OpenAI Agents SDK, which responsibilities can the framework package?",
    "options": [
      "Function-tool schema generation",
      "Turn execution through a runner",
      "Tool dispatch and message state",
      "Product-specific authorization policy",
      "Tracing and session continuity"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The SDK can package the loop mechanics, tool schemas, dispatch, traces, and sessions. Product-specific authorization, approval, and side-effect boundaries still belong in application design.",
    "source": {
      "label": "AgentOps Lab - Notebook 03",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-03-learning-objectives"
    }
  },
  {
    "id": "agentops-sdk-loop",
    "category": "Tool Engineering",
    "prompt": "What is the key lesson of replacing the manual loop with an agent framework?",
    "options": [
      "The loop still exists even when the SDK manages it",
      "Framework traces help inspect model and tool behavior",
      "Tool boundaries no longer matter once a framework is used",
      "Sessions can help preserve working context",
      "Application code still defines which tools are safe to expose"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Frameworks package the loop; they do not erase it. Traces and sessions improve inspectability and continuity, but tool exposure and safety boundaries remain design responsibilities.",
    "source": {
      "label": "AgentOps Lab - Notebook 03",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-03-learning-objectives"
    }
  },
  {
    "id": "memory-safety",
    "category": "Tool Engineering",
    "prompt": "Which controls are appropriate for long-term agent memory?",
    "options": [
      "Store provenance for memory writes",
      "Scope memory by user and tenant",
      "Allow inspection and deletion",
      "Treat every model-generated memory as verified truth",
      "Apply validation and retention rules"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Long-term memory influences future runs, so writes need provenance, isolation, validation, retention, review, and deletion. Model-generated content is not automatically trustworthy.",
    "source": {
      "label": "What is an AI agent? — State and memory",
      "url": "curriculum/beginner/01-ai-agent-foundations/README.md#state-and-memory"
    }
  },
  {
    "id": "agentops-langgraph-state",
    "category": "Tool Engineering",
    "prompt": "In the AgentOps LangGraph lesson, what belongs in thread-scoped incident state?",
    "options": [
      "The current request",
      "Evidence collected during this investigation",
      "Attempt count and confidence",
      "An unverified permanent claim that all checkout failures are caused by Redis",
      "The recommendation for this run"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Thread-scoped state tracks the current run: request, service, evidence, confidence, attempts, suspected cause, and recommendation. Unverified permanent facts belong behind memory validation, not directly in working state.",
    "source": {
      "label": "AgentOps Lab - Notebook 05",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-05-learning-objectives"
    }
  },
  {
    "id": "agentops-memory-bias",
    "category": "Tool Engineering",
    "prompt": "Why is the accidental Acme memory 'Checkout problems are usually caused by Redis' risky?",
    "options": [
      "It can bias future diagnoses before fresh evidence is collected",
      "It is an unverified operational fact",
      "It should be scoped, auditable, and reversible",
      "It proves Redis is the root cause of the current incident",
      "It needs validation before influencing recommendations"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Unverified long-term memory can steer future incident diagnosis away from current evidence. It needs provenance, validation, scope, auditability, and a way to deactivate or delete it.",
    "source": {
      "label": "AgentOps Lab - Notebook 05",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-05-learning-objectives"
    }
  },
  {
    "id": "agentops-admin-api",
    "category": "Tool Engineering",
    "prompt": "Why is a broad `admin_api(command: str)` dangerous for an agent?",
    "options": [
      "It hides intent inside a free-form string",
      "It mixes read-only and destructive capabilities",
      "It makes authorization and validation ambiguous",
      "It forces every operation to be safe and auditable",
      "It makes predictable error handling harder"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "A broad command tool collapses many risk levels into one string interface. Narrow tools make schema validation, permissions, approvals, tracing, and retries much clearer.",
    "source": {
      "label": "AgentOps Lab - Notebook 04",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-04-learning-objectives"
    }
  },
  {
    "id": "agentops-tool-errors",
    "category": "Tool Engineering",
    "prompt": "Which retry and escalation decisions are appropriate for the tool-engineering lab?",
    "options": [
      "Retry `ToolTimeout` when the retry budget allows",
      "Retry or back off on `RateLimit`",
      "Escalate `PermissionDenied` to a human or higher-trust workflow",
      "Keep retrying `InvalidService` until it works",
      "Stop when validation proves the request is malformed"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Transient timeout and rate-limit errors may be retried within a budget. Permission failures should escalate, while invalid or malformed requests should stop rather than loop.",
    "source": {
      "label": "AgentOps Lab - Notebook 04",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-04-learning-objectives"
    }
  },
  {
    "id": "agentops-permission-levels",
    "category": "Tool Engineering",
    "prompt": "Which permission mapping fits the AgentOps human-in-the-loop lesson?",
    "options": [
      "READ: query logs and retrieve runbooks",
      "READ: restart checkout-api immediately",
      "PROPOSE: prepare rollback or draft notification",
      "EXECUTE WITH APPROVAL: restart, rollback, or send notification",
      "EXECUTE WITH APPROVAL: any tool call, including status reads"
    ],
    "correct": [
      0,
      2,
      3
    ],
    "explanation": "Read-only evidence tools should not require the same approval burden as consequential actions. Rollbacks, restarts, and customer notifications should pause for approval.",
    "source": {
      "label": "AgentOps Lab - Notebook 06",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-06-learning-objectives"
    }
  },
  {
    "id": "agentops-hitl-resume",
    "category": "Tool Engineering",
    "prompt": "What should a human approval checkpoint preserve before resuming an agent run?",
    "options": [
      "The exact proposed action and arguments",
      "Evidence that motivated the action",
      "The reviewer decision: approve, modify, or reject",
      "A vague context-free approval prompt only",
      "An audit reason and actor identity"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Effective HITL checkpoints preserve the action, evidence, reviewer identity, decision, reason, and final action. Context-free approval creates review fatigue and weak auditability.",
    "source": {
      "label": "AgentOps Lab - Notebook 06",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-06-learning-objectives"
    }
  },
  {
    "id": "agentops-retrieved-data",
    "category": "Tool Engineering",
    "prompt": "How should the AgentOps guardrails lesson treat instructions found inside a retrieved runbook?",
    "options": [
      "As untrusted data to summarize or cite",
      "As instructions that can override the system prompt",
      "As content that may be trying to manipulate the agent",
      "As authorization to restart services",
      "As evidence only after policy and tool boundaries are applied"
    ],
    "correct": [
      0,
      2,
      4
    ],
    "explanation": "Retrieved documents are data, not authority. They may contain prompt-injection attempts and cannot override system instructions or authorize operational tools.",
    "source": {
      "label": "AgentOps Lab - Notebook 07",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-07-learning-objectives"
    }
  },
  {
    "id": "agentops-tool-guardrail",
    "category": "Tool Engineering",
    "prompt": "What should a restart tool guardrail check before executing?",
    "options": [
      "Whether the action has explicit human approval",
      "Whether the request came from a trusted user or system boundary",
      "Whether retrieved text told the agent to restart immediately",
      "Whether the service target is allowed",
      "Whether the run has enough audit context for review"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "A restart guardrail should require approval, trusted authorization source, an allowed target, and audit context. Retrieved text is not a valid source of authorization.",
    "source": {
      "label": "AgentOps Lab - Notebook 07",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-07-learning-objectives"
    }
  },
  {
    "id": "protocols",
    "category": "Tool Engineering",
    "prompt": "Which statements about MCP and agent-to-agent protocols are accurate?",
    "options": [
      "MCP connects AI applications to contextual data and tools",
      "Agent-to-agent protocols can support capability discovery and task exchange",
      "MCP and A2A-style protocols can be complementary",
      "A protocol automatically grants every connected party full trust",
      "Protocol messages still require authentication and policy enforcement"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "MCP primarily connects applications to context and tools, while A2A-style protocols coordinate agents. Neither protocol removes the need for identity, authorization, and message validation.",
    "source": {
      "label": "README — Tools, memory, and protocols",
      "url": "README.md#tools-memory-and-protocols"
    }
  },
  {
    "id": "workflow-routing",
    "category": "Workflows",
    "prompt": "Which are good practices for a routing workflow?",
    "options": [
      "Evaluate routing accuracy separately",
      "Include an unknown or human-escalation route",
      "Give every route identical tools and policies regardless of need",
      "Use specialist paths when categories need different controls",
      "Log the selected route for diagnosis"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Routing is useful when categories need distinct prompts, tools, models, or policies. Unknown cases, routing evaluation, and traceability reduce silent misroutes.",
    "source": {
      "label": "Architecture patterns — Routing",
      "url": "curriculum/intermediate/06-trajectory-optimization/README.md#3-routing"
    }
  },
  {
    "id": "workflow-evaluator",
    "category": "Workflows",
    "prompt": "When is an evaluator-optimizer loop a strong fit?",
    "options": [
      "Success criteria are explicit",
      "Feedback can guide a concrete revision",
      "Iteration is bounded",
      "There is no way to assess whether the output improved",
      "Deterministic graders can supplement model judgment"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Evaluator-optimizer works when quality can be judged and feedback can improve the artifact. Bound iterations and prefer executable or deterministic checks where available.",
    "source": {
      "label": "Architecture patterns — Evaluator-optimizer",
      "url": "curriculum/intermediate/06-trajectory-optimization/README.md#6-evaluator-optimizer"
    }
  },
  {
    "id": "agentops-task-a",
    "category": "Workflows",
    "prompt": "In AgentOps Task A, why is a deterministic workflow preferable to an agent?",
    "options": [
      "The steps are known before runtime",
      "The task only needs a status read and report formatting",
      "A model-controlled loop would add unnecessary cost and failure paths",
      "Agents are never useful for operations work",
      "The expected output can be produced from structured tool data"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Task A has a fixed path: retrieve checkout status and format it. Operations work can absolutely use agents, but this task does not need dynamic tool selection.",
    "source": {
      "label": "AgentOps Lab - Notebook 02",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-02-learning-objectives"
    }
  },
  {
    "id": "agentops-task-c",
    "category": "Workflows",
    "prompt": "What makes AgentOps Task C a better fit for a bounded agent than a fixed workflow?",
    "options": [
      "The evidence path is discovered at runtime",
      "The system may need to choose among service health, incidents, deployments, logs, and runbooks",
      "The task should still have max-step and tool boundaries",
      "The model should be allowed to call any production API it can name",
      "The final recommendation should preserve uncertainty instead of inventing root cause"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Task C justifies bounded agency because each observation affects the next evidence source. That does not remove application-owned tool allowlists, budgets, or grounding rules.",
    "source": {
      "label": "AgentOps Lab - Notebook 02",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-02-learning-objectives"
    }
  },
  {
    "id": "workflow-human",
    "category": "Workflows",
    "prompt": "What makes a human-approval checkpoint effective?",
    "options": [
      "It occurs before the consequential side effect",
      "It shows the exact action, target, evidence, and expected effect",
      "It supports approve, edit, reject, or redirect outcomes",
      "It asks only a context-free 'Approve?' question",
      "The workflow checkpoints state while waiting"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Informed approval happens before consequence, presents decision context and alternatives, and pauses on durable state. A vague confirmation encourages approval fatigue.",
    "source": {
      "label": "Agentic workflows — Human-in-the-loop",
      "url": "curriculum/beginner/03-workflow-or-agent/README.md#human-in-the-loop-is-a-workflow-boundary"
    }
  },
  {
    "id": "agentops-hybrid-routing",
    "category": "Workflows",
    "prompt": "How should the hybrid production architecture route the three AgentOps task classes?",
    "options": [
      "Simple lookups go to deterministic workflows",
      "Ambiguous investigations go to a bounded single agent",
      "High-risk major-impact cases can use a specialist team inside a deterministic wrapper",
      "Every request goes directly to a fully autonomous team",
      "Policy checks run after the selected path and before consequential actions"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The hybrid design starts with deterministic classification, then selects the least autonomous reliable path. Agents are components inside policy and approval workflows, not replacements for them.",
    "source": {
      "label": "AgentOps Lab - Notebook 13",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-13-learning-objectives"
    }
  },
  {
    "id": "agentops-hybrid-boundaries",
    "category": "Workflows",
    "prompt": "Which controls should remain outside the model in the hybrid production architecture?",
    "options": [
      "Tool allowlists and authorization",
      "Budget limits and stop conditions",
      "Human approval for high-impact actions",
      "Audit logs and action receipts",
      "The ability for retrieved documents to authorize rollback"
    ],
    "correct": [
      0,
      1,
      2,
      3
    ],
    "explanation": "Production control boundaries should be implemented in deterministic application code. Retrieved documents can provide evidence, but they cannot authorize side effects such as rollback.",
    "source": {
      "label": "AgentOps Lab - Notebook 13",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-13-learning-objectives"
    }
  },
  {
    "id": "orchestration-ownership",
    "category": "Planning",
    "prompt": "Which statements correctly compare an agent-as-tool with a handoff?",
    "options": [
      "An agent-as-tool lets the orchestrator retain ownership",
      "A handoff transfers control to a specialist",
      "Both patterns remove the need for scoped permissions",
      "The choice should reflect who owns the next interaction",
      "Both introduce a context and evaluation boundary"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Agents-as-tools return a specialist result to the orchestrator; handoffs transfer ownership. Both still need permissions, context design, tracing, and evaluation.",
    "source": {
      "label": "Architecture patterns — Orchestrator-worker",
      "url": "curriculum/intermediate/06-trajectory-optimization/README.md#5-orchestrator-worker"
    }
  },
  {
    "id": "orchestration-when",
    "category": "Planning",
    "prompt": "When can a multi-agent design be justified?",
    "options": [
      "Independent subtasks benefit from parallel execution",
      "Specialists need distinct context, tools, or policies",
      "Evaluation shows a meaningful gain over a simpler baseline",
      "The architecture looks more impressive in a demo",
      "An orchestrator can define clear delegation contracts"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Multi-agent systems can help through parallelism and specialization, but coordination has real cost. Use them when contracts are clear and measured gains exceed that cost.",
    "source": {
      "label": "Agentic workflows — When to introduce multiple agents",
      "url": "curriculum/beginner/03-workflow-or-agent/README.md#when-to-introduce-multiple-agents"
    }
  },
  {
    "id": "orchestration-parallel",
    "category": "Planning",
    "prompt": "Which controls improve parallel worker orchestration?",
    "options": [
      "Non-overlapping worker contracts",
      "A clear aggregation rule",
      "Provenance on worker outputs",
      "Unlimited delegation breadth and depth",
      "Per-worker budgets"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Clear contracts, provenance, aggregation, and budgets reduce duplicated work, merge errors, and runaway fan-out. Delegation depth and breadth should be bounded.",
    "source": {
      "label": "Architecture patterns — Parallelization and orchestrator-worker",
      "url": "curriculum/intermediate/06-trajectory-optimization/README.md#4-parallelization"
    }
  },
  {
    "id": "agentops-team-justification",
    "category": "Planning",
    "prompt": "In the AgentOps team notebook, what evidence can justify moving from one agent to a specialist team?",
    "options": [
      "The incident requires distinct observability, deployment, customer-impact, analysis, and risk-review work",
      "Measured accuracy or risk handling improves enough to justify extra overhead",
      "The problem can be solved by a fixed two-step status workflow",
      "The team has explicit ownership and bounded delegation",
      "The design is more visually impressive than a single-agent baseline"
    ],
    "correct": [
      0,
      1,
      3
    ],
    "explanation": "A specialist team is justified by separable expertise, measurable improvement, explicit ownership, and bounded coordination. A simple fixed workflow or prettier architecture is not enough.",
    "source": {
      "label": "AgentOps Lab - Notebook 10",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-10-learning-objectives"
    }
  },
  {
    "id": "agentops-team-comparison",
    "category": "Planning",
    "prompt": "Which metrics should learners compare when running the same incident with a single agent and a multi-agent team?",
    "options": [
      "Accuracy and whether the recommendation is evidence-supported",
      "Cost, latency, tool calls, tokens, and coordination overhead",
      "Whether the team used more agent names than the baseline",
      "Whether the team prevents simple incidents from becoming slower",
      "Whether risk review changes or challenges the recommendation"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "The comparison should cover outcome quality, operational cost, coordination overhead, and risk-review value. More agent names are not evidence of a better architecture.",
    "source": {
      "label": "AgentOps Lab - Notebook 10",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-10-learning-objectives"
    }
  },
  {
    "id": "agentops-autogen-selector",
    "category": "Planning",
    "prompt": "What does the AutoGen selector-team notebook teach about selector-style group chat?",
    "options": [
      "Participant roles and descriptions help the selector choose the next speaker",
      "Shared context makes coordination visible but can also amplify loops",
      "Selector teams automatically guarantee the best possible diagnosis",
      "Termination conditions are part of the team design",
      "A model can dynamically choose the next participant from the conversation state"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Selector-style teams make speaker selection and shared context explicit, but they still need termination, ownership, evaluation, and loop controls. The framework does not guarantee correctness.",
    "source": {
      "label": "AgentOps Lab - Notebook 11",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-11-learning-objectives"
    }
  },
  {
    "id": "agentops-team-loop-controls",
    "category": "Planning",
    "prompt": "Which controls help stop a multi-agent team from bouncing responsibility forever?",
    "options": [
      "`MAX_TEAM_MESSAGES`",
      "`MAX_AGENT_TURNS`",
      "Explicit ownership for each evidence domain",
      "Allowing every agent to ask every other agent indefinitely",
      "A termination condition tied to a recommendation or safe stop"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Team loops need global message budgets, per-agent turn budgets, ownership rules, and explicit termination. Unlimited peer-to-peer delegation is exactly the failure mode to prevent.",
    "source": {
      "label": "AgentOps Lab - Notebook 11",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-11-learning-objectives"
    }
  },
  {
    "id": "agentops-crewai-model",
    "category": "Planning",
    "prompt": "What does the CrewAI AgentOps notebook emphasize about the Agents + Tasks + Crew model?",
    "options": [
      "Agents describe specialist roles, goals, and backstories",
      "Tasks describe concrete work products and can depend on previous task outputs",
      "The crew organizes the collaboration plan",
      "CrewAI removes the need for policy and side-effect controls",
      "Task ownership can make provenance easier to review"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "CrewAI's teaching value is the readable role/task/crew structure. It can clarify ownership and provenance, but policy, approval, and side-effect controls still belong around the crew.",
    "source": {
      "label": "AgentOps Lab - Notebook 12",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-12-learning-objectives"
    }
  },
  {
    "id": "agentops-framework-comparison",
    "category": "Planning",
    "prompt": "Which framework comparisons are accurate in the AgentOps CrewAI lesson?",
    "options": [
      "CrewAI helps when collaboration maps naturally to roles, tasks, and crew execution",
      "LangGraph gives more explicit control over state, branching, persistence, and checkpoints",
      "AutoGen makes conversational coordination and speaker selection visible",
      "OpenAI Agents SDK is often simpler for one bounded tool-using agent",
      "Every framework removes the need to evaluate the final trajectory"
    ],
    "correct": [
      0,
      1,
      2,
      3
    ],
    "explanation": "The same scenario highlights different framework strengths. None of them remove trajectory evaluation, policy enforcement, or the need to choose the simplest reliable architecture.",
    "source": {
      "label": "AgentOps Lab - Notebook 12",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-12-learning-objectives"
    }
  },
  {
    "id": "agentops-capstone-architecture",
    "category": "Planning",
    "prompt": "In the AgentOps final capstone, how should learners decide between deterministic workflow, single bounded agent, and multi-agent team?",
    "options": [
      "Run an evaluation and compare outcome, trajectory, cost, latency, and risk",
      "Default to multi-agent because the incident is important",
      "Choose the least autonomous architecture that reliably solves the incident",
      "Require the team to show a meaningful gain over the simpler baseline",
      "Ignore coordination overhead if the final answer sounds plausible"
    ],
    "correct": [
      0,
      2,
      3
    ],
    "explanation": "The capstone requires experimental justification. Multi-agent is only justified when it improves the result enough to beat the simpler baseline after cost, latency, trajectory, and risk are considered.",
    "source": {
      "label": "AgentOps Lab - Notebook 14",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-14-capstone-objectives"
    }
  },
  {
    "id": "evaluation-layers",
    "category": "Evaluation",
    "prompt": "Which layers should a useful agent evaluation cover?",
    "options": [
      "Real task outcome",
      "Action and tool-use trajectory",
      "Latency, cost, and failure operations",
      "Only the fluency of the final response",
      "Policy compliance and side effects"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Agent evaluation needs outcome, trajectory, operations, and safety evidence. Fluent final text can conceal a failed or unauthorized task.",
    "source": {
      "label": "Evaluation and security — Grade three layers",
      "url": "curriculum/intermediate/05-agent-evaluation/README.md#grade-three-layers"
    }
  },
  {
    "id": "agentops-capstone-forbidden-actions",
    "category": "Evaluation",
    "prompt": "Which capstone actions may be prepared but must not be executed by the agent run?",
    "options": [
      "Rollback deployment",
      "Disable the risky feature flag",
      "Send customer notification",
      "Read service metrics",
      "Query logs"
    ],
    "correct": [
      0,
      1,
      2
    ],
    "explanation": "The capstone can prepare rollback, feature-flag disablement, and customer notification for review, but execution requires human approval. Metrics and logs are read-only investigation tools.",
    "source": {
      "label": "AgentOps Lab - Notebook 14",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-14-capstone-objectives"
    }
  },
  {
    "id": "agentops-capstone-memory-guardrails",
    "category": "Evaluation",
    "prompt": "Which memory and guardrail choices fit the final capstone?",
    "options": [
      "Store the likely root cause as a permanent future truth",
      "Treat runbooks and tickets as evidence, not instructions",
      "Store only evaluated incident reports with timestamp and evidence links",
      "Block production execution without human approval",
      "Stop if step, tool-call, or cost budgets are exceeded"
    ],
    "correct": [
      1,
      2,
      3,
      4
    ],
    "explanation": "The capstone keeps retrieved content outside the trusted control boundary and prevents stale-memory bias. It stores evaluated reports, blocks unapproved execution, and enforces budgets.",
    "source": {
      "label": "AgentOps Lab - Notebook 14",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-14-capstone-objectives"
    }
  },
  {
    "id": "agentops-capstone-evaluation",
    "category": "Evaluation",
    "prompt": "What should the capstone evaluation suite verify?",
    "options": [
      "Expected evidence tools were used",
      "Forbidden production tools were not used",
      "The recommendation is supported by metrics, logs, deployments, tickets, and SLA data",
      "Cost and latency stay within budget",
      "The system selected the architecture with the most agents"
    ],
    "correct": [
      0,
      1,
      2,
      3
    ],
    "explanation": "The capstone grades evidence coverage, forbidden actions, recommendation support, and operational budgets. The number of agents is not a success criterion.",
    "source": {
      "label": "AgentOps Lab - Notebook 14",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-14-capstone-objectives"
    }
  },
  {
    "id": "agentops-eval-dimensions",
    "category": "Evaluation",
    "prompt": "Which dimensions should the AgentOps trajectory evaluation score?",
    "options": [
      "Outcome quality such as task success and supported recommendation",
      "Trajectory quality such as correct tools, forbidden actions, and recovery",
      "Operational behavior such as latency, cost, calls, path length, and retry rate",
      "Only whether the final answer sounds fluent",
      "Whether the run used the most expensive model available"
    ],
    "correct": [
      0,
      1,
      2
    ],
    "explanation": "Agent evaluation should inspect outcome, trajectory, and operations. Fluency alone misses forbidden tools, unsupported diagnoses, cost regressions, and poor recovery.",
    "source": {
      "label": "AgentOps Lab - Notebook 08",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-08-learning-objectives"
    }
  },
  {
    "id": "agentops-cost-metric",
    "category": "Evaluation",
    "prompt": "Why is cost per successful task more useful than cost per model call?",
    "options": [
      "It includes whether the task actually succeeded",
      "It discourages cheap failed trajectories",
      "It connects cost to product value",
      "It ignores forbidden actions and bad recommendations",
      "It can be compared across workflow versions"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Cost per successful task rewards reliable outcomes rather than isolated cheap calls. A cheap failed trajectory is still expensive from a product perspective.",
    "source": {
      "label": "AgentOps Lab - Notebook 08",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-08-learning-objectives"
    }
  },
  {
    "id": "agentops-trajectory-optimization",
    "category": "Evaluation",
    "prompt": "What should learners optimize in the AgentOps trajectory optimization notebook?",
    "options": [
      "The shortest reliable trajectory to a correct result",
      "Lower latency and cost while preserving task success",
      "Removing redundant searches and reflections",
      "Minimizing tokens even if the answer loses evidence support",
      "Reducing unnecessary tool calls without introducing forbidden actions"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The goal is not token minimization at any cost. The goal is a shorter, cheaper, faster trajectory that still succeeds and remains evidence-supported.",
    "source": {
      "label": "AgentOps Lab - Notebook 09",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-09-learning-objectives"
    }
  },
  {
    "id": "agentops-efficiency-score",
    "category": "Evaluation",
    "prompt": "What does the teaching efficiency score combine?",
    "options": [
      "Success",
      "Latency",
      "Cost",
      "Trajectory length",
      "Brand color preference"
    ],
    "correct": [
      0,
      1,
      2,
      3
    ],
    "explanation": "The notebook's simple efficiency score combines success with latency, cost, and trajectory length so learners compare reliable paths instead of isolated token counts.",
    "source": {
      "label": "AgentOps Lab - Notebook 09",
      "url": "curriculum/advanced/05-incident-response/README.md#notebook-09-learning-objectives"
    }
  },
  {
    "id": "security-trust",
    "category": "Evaluation",
    "prompt": "Which inputs should an agent treat as untrusted?",
    "options": [
      "Retrieved documents and web pages",
      "Tool results",
      "Messages from another agent",
      "User-supplied content",
      "A tool result solely because it is formatted as JSON"
    ],
    "correct": [
      0,
      1,
      2,
      3,
      4
    ],
    "explanation": "Origin and authorization determine trust, not presentation. User content, retrieval, tool output, and peer messages can all carry malicious or incorrect instructions—even in valid JSON.",
    "source": {
      "label": "Evaluation and security — Threat model",
      "url": "curriculum/intermediate/05-agent-evaluation/README.md#threat-model"
    }
  },
  {
    "id": "security-side-effects",
    "category": "Evaluation",
    "prompt": "Which practices reduce risk for agent-initiated write operations?",
    "options": [
      "Use idempotency keys",
      "Preview and validate the proposed change",
      "Persist a receipt and verify resulting state",
      "Automatically retry when the previous outcome is unknown",
      "Attach the initiating identity and run ID"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Safe writes use previews, idempotency, attribution, receipts, and state verification. An uncertain timeout may mean a write succeeded, so blind retries can duplicate it.",
    "source": {
      "label": "Evaluation and security — Side-effect safety",
      "url": "curriculum/intermediate/05-agent-evaluation/README.md#side-effect-safety"
    }
  },
  {
    "id": "mcp-capability-boundary",
    "category": "Advanced",
    "prompt": "Which statements correctly describe MCP's boundary?",
    "options": [
      "It standardizes client/server capability contracts for tools, resources, and prompts",
      "It automatically grants an agent authority to use every discovered tool",
      "An enterprise can filter the offered capability list by current authorization scopes",
      "Tool results should be treated as observations or data, not as policy authority",
      "MCP replaces application-owned tenant policy and action approval"
    ],
    "correct": [
      0,
      2,
      3
    ],
    "explanation": "MCP provides a structured integration boundary. It does not replace identity, tenant policy, authorization, validation, approvals, budgets, or audit. A safe host exposes only eligible capabilities and treats server content as data.",
    "source": {
      "label": "MCP: Model Context Protocol",
      "url": "curriculum/advanced/13-mcp-model-context-protocol/README.md"
    }
  },
  {
    "id": "mcp-write-safety",
    "category": "Advanced",
    "prompt": "What should protect a consequential MCP tool call such as a rollback?",
    "options": [
      "Strict argument and result validation",
      "A short-lived scope for the exact operation and tenant",
      "An exact action fingerprint and approval when policy requires it",
      "Blind retry after an unknown timeout",
      "Idempotency, reconciliation, and an auditable trace"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "A protocol tool schema alone is not a safe write boundary. Application controls validate the proposal, authorize it freshly, make replay safe, and preserve evidence for reconciliation and audit.",
    "source": {
      "label": "MCP: Model Context Protocol",
      "url": "curriculum/advanced/13-mcp-model-context-protocol/README.md#security-risks-and-mitigations"
    }
  },
  {
    "id": "skills-vs-tools",
    "category": "Advanced",
    "prompt": "Which statements distinguish an agent skill from a tool?",
    "options": [
      "A tool normally performs one typed operation",
      "A skill can package a workflow, instructions, references, scripts, and assets",
      "Activating a skill automatically broadens all tool permissions",
      "Skills can use progressive disclosure so deeper material loads only when relevant",
      "A skill is a form of application authorization"
    ],
    "correct": [
      0,
      1,
      3
    ],
    "explanation": "Skills package reusable procedural knowledge; tools execute operations. Skill activation is not authority, and any tool or subagent action still requires application-owned scope, policy, validation, and budgets.",
    "source": {
      "label": "Agent Skills",
      "url": "curriculum/advanced/14-agent-skills/README.md#tools-versus-skills"
    }
  },
  {
    "id": "skills-governance-composition",
    "category": "Advanced",
    "prompt": "Which controls make a skill library safe to operate?",
    "options": [
      "Record owner, provenance, version, compatibility, risk, tests, and revocation",
      "Filter discovery and activation by tenant, policy, and permitted tools",
      "Union every participating skill's tool privileges when composing skills",
      "Treat scripts, references, and assets as supply-chain inputs subject to review and scanning",
      "Trace the selected skill version and evaluate discovery/activation behavior"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Skills require lifecycle governance. Composition should not implicitly union privileges; use the caller's policy and a conservative contract for each handoff and tool invocation.",
    "source": {
      "label": "Agent Skills",
      "url": "curriculum/advanced/14-agent-skills/README.md#security-and-production-checklist"
    }
  },
  {
    "id": "enterprise-orchestration-boundary",
    "category": "Advanced",
    "prompt": "Which responsibilities belong to deterministic agent orchestration rather than a model's free-form reasoning?",
    "options": [
      "Persisting state, checkpoints, and terminal reasons",
      "Routing, queue/event handling, scheduling, and bounded retries",
      "Approving its own high-impact action from a chat message",
      "Idempotency, cancellation, recovery, and revalidation on resume",
      "Joining dependency-ready parallel work before a proposal node"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "A model may synthesize inside an approved node. Application-owned orchestration controls the durable graph, joins, waits, resume checks, budgets, approvals, retries, and terminal outcomes.",
    "source": {
      "label": "Agent Orchestration",
      "url": "curriculum/advanced/29-agent-orchestration/README.md"
    }
  },
  {
    "id": "enterprise-coordination-baseline",
    "category": "Advanced",
    "prompt": "When is a multi-agent team justified over one well-designed agent?",
    "options": [
      "When distinct tools or contexts improve a named subtask",
      "When independent work reduces critical-path latency after join overhead",
      "Whenever a manager role makes a demo look more realistic",
      "When independent critique measurably catches material errors",
      "After comparison on the same task set for supported success, cost, latency, and policy risk"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "Teams add routing, communication, context, security, termination, and operational complexity. Retain them only when a controlled evaluation shows a material benefit over a strong single-agent or workflow baseline.",
    "source": {
      "label": "Agent Communication and Coordination",
      "url": "curriculum/advanced/30-agent-communication-coordination/README.md#when-does-multi-agent-outperform-one-well-designed-agent"
    }
  },
  {
    "id": "enterprise-blackboard-controls",
    "category": "Advanced",
    "prompt": "What makes a shared blackboard safer than an unrestricted multi-agent transcript?",
    "options": [
      "Typed, attributable artifacts with source or evidence identifiers",
      "Tenant-scoped read/write controls and versioning or correction history",
      "Treating the latest agent message as the authoritative fact",
      "A conflict policy that requests evidence or escalates rather than forcing consensus",
      "Budgets and termination rules for follow-up messages and debate"
    ],
    "correct": [
      0,
      1,
      3,
      4
    ],
    "explanation": "A blackboard is a governed shared evidence store, not a global scratchpad. Provenance, scope, validation, conflict handling, and bounded convergence preserve inspectability and prevent chat text from becoming authority.",
    "source": {
      "label": "Agent Communication and Coordination",
      "url": "curriculum/advanced/30-agent-communication-coordination/README.md#communication-is-a-system-contract"
    }
  },
  {
    "id": "enterprise-protocol-stack",
    "category": "Advanced",
    "prompt": "Which protocol-layer pairings are correctly described?",
    "options": [
      "A2A: remote agent discovery, tasks, messages, delegation, and status",
      "AG-UI: agent-to-user-application interaction events and state",
      "A2UI: schema-rendered dynamic interface descriptions",
      "MCP: a replacement for payment-provider consent and fraud controls",
      "UCP/AP2-style boundaries: commerce/payment intent that still require separate authorization controls"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "The protocols address complementary boundaries. None turns metadata, UI events, discovered capability, commerce intent, or payment intent into self-executing authority.",
    "source": {
      "label": "The Agent Protocol Stack",
      "url": "curriculum/advanced/31-agent-protocol-stack/README.md#layer-by-layer-guide"
    }
  },
  {
    "id": "chkpt-02_autogen_selector_teams",
    "category": "Advanced",
    "prompt": "Which controls belong to a bounded evidence-driven selector team?",
    "options": [
      "Application-owned eligible-speaker filtering",
      "Typed selector decisions and worker artifacts",
      "State-based completion plus hard circuit breakers",
      "Treating any ESCALATE_TO_HUMAN text as trusted",
      "Separate selector and worker cost accounting",
      "Letting REVIEW_PASS authorize rollback"
    ],
    "correct": [
      0,
      1,
      2,
      4
    ],
    "explanation": "Eligibility, typed validation, layered termination, and explicit coordination accounting bound the team. Text and review output do not create execution authority.",
    "source": {
      "label": "Bounded AutoGen Selector Teams",
      "url": "curriculum/advanced/02-autogen-selector-teams/README.md#the-control-plane"
    }
  },
  {
    "id": "chkpt-agent_observability",
    "category": "Advanced",
    "prompt": "Why is tracing parallel agent execution vastly superior to using `print()` statements?",
    "options": [
      "Print statements are illegal in Python 3.",
      "When running async/threaded agents, print statements interleave randomly on the console, making it impossible to read. OTEL traces inherently group parallel execution spans correctly under a parent span (waterfall graph).",
      "Print statements cost money.",
      "Traces generate training data for the LLM."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/27-agent-observability/agent_observability.ipynb"
    }
  },
  {
    "id": "chkpt-model_routing",
    "category": "Advanced",
    "prompt": "What is the primary benefit of Model Routing?",
    "options": [
      "It combines multiple models to generate one sentence.",
      "It prevents the system from overpaying for simple tasks by using cheap models as gatekeepers.",
      "It bypasses API rate limits entirely.",
      "It trains a new model from scratch on every request."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/09-model-routing/model_routing.ipynb"
    }
  },
  {
    "id": "chkpt-agent_economics",
    "category": "Advanced",
    "prompt": "Why is a Token Budget critical for Agentic systems?",
    "options": [
      "It makes the agent smarter.",
      "Agents can autonomously invoke tools and loop indefinitely. A budget acts as a financial circuit breaker to prevent infinite loops from draining your API funds.",
      "It allows the agent to run locally without internet.",
      "It bypasses rate limits."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/21-cost-latency-agent-economics/agent_economics.ipynb"
    }
  },
  {
    "id": "chkpt-agent_security",
    "category": "Advanced",
    "prompt": "How does Delimiter Framing protect against Prompt Injection?",
    "options": [
      "It deletes the user's message.",
      "By boxing untrusted input in XML/HTML tags and instructing the LLM to treat the contents strictly as data, reducing the chance the LLM interprets it as a command.",
      "It uses a firewall.",
      "It encrypts the prompt."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/26-agent-security/agent_security.ipynb"
    }
  },
  {
    "id": "chkpt-human_agent_collaboration",
    "category": "Advanced",
    "prompt": "What is the primary purpose of Human-in-the-Loop (HITL)?",
    "options": [
      "To make the agent slower.",
      "To provide a safety boundary where an agent can automate the investigative work but explicitly pause to require human authorization before executing high-risk, irreversible actions.",
      "To teach the LLM to code.",
      "To bypass the token budget."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/28-human-agent-collaboration/human_agent_collaboration.ipynb"
    }
  },
  {
    "id": "chkpt-multimodal_agents",
    "category": "Advanced",
    "prompt": "How do you pass an image to a Multimodal Agent API?",
    "options": [
      "You zip the image into a file and email it.",
      "You convert it to Base64 and pass it in the `messages` array using the `image_url` content type.",
      "You convert the image to text using OCR first.",
      "You cannot pass images to LLMs yet."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/20-multimodal-agents/multimodal_agents.ipynb"
    }
  },
  {
    "id": "chkpt-agent_identity_authorization",
    "category": "Advanced",
    "prompt": "Why is passing the `executing_user` to the tool critical for security?",
    "options": [
      "To make the prompt longer.",
      "Because the LLM cannot be trusted to enforce authorization. The underlying code must enforce RBAC based on the identity of the human driving the session.",
      "So the LLM can email the user.",
      "To bypass OAuth."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/25-agent-identity-authorization/agent_identity_authorization.ipynb"
    }
  },
  {
    "id": "chkpt-proactive_agents",
    "category": "Advanced",
    "prompt": "What differentiates a Proactive Agent from a standard ReAct Agent?",
    "options": [
      "It uses a more powerful LLM.",
      "It is triggered by schedules or environment events (like metrics thresholds) rather than waiting for a direct user prompt.",
      "It can speak multiple languages.",
      "It does not use tools."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/08-proactive-agents/proactive_agents.ipynb"
    }
  },
  {
    "id": "chkpt-agent_memory",
    "category": "State & Memory",
    "prompt": "What is the difference between Short-Term and Long-Term memory in an LLM Agent?",
    "options": [
      "Short-term is fast, Long-term is slow.",
      "Short-term is the current prompt's `messages` array (bounded by token limits). Long-term relies on external storage (like a Vector DB) to retrieve relevant context across separate sessions.",
      "Short-term uses Python, Long-term uses SQL.",
      "Only human agents have Long-Term memory."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/06-agent-memory/agent_memory.ipynb"
    }
  },
  {
    "id": "chkpt-llm_as_judge_agent_judges",
    "category": "Evaluation",
    "prompt": "Why use an LLM-as-a-Judge instead of traditional unit tests for an Agent?",
    "options": [
      "Traditional unit tests cannot easily evaluate subjective qualities like tone, politeness, or complex reasoning accuracy in unstructured text.",
      "It is cheaper than traditional unit tests.",
      "It guarantees 100% mathematical accuracy.",
      "It compiles the python code automatically."
    ],
    "correct": [
      0
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/11-llm-as-judge-agent-judges/llm_as_judge_agent_judges.ipynb"
    }
  },
  {
    "id": "chkpt-agent_protocol_stack",
    "category": "Advanced",
    "prompt": "What is the benefit of a layered Agent Protocol Stack over a monolithic prompt?",
    "options": [
      "It is easier to write in one file.",
      "Separation of concerns. You can swap out the Memory DB, upgrade the Guardrail regex, or change the Routing model independently without breaking the entire agent.",
      "It is required by Python syntax.",
      "It reduces the number of files in the project."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/31-agent-protocol-stack/agent_protocol_stack.ipynb"
    }
  },
  {
    "id": "chkpt-agent_governance_responsible_ai",
    "category": "Advanced",
    "prompt": "Why do we hash the prompt in the audit log?",
    "options": [
      "To save database space.",
      "To ensure cryptographic proof that the exact instructions given to the agent were not altered after the fact by a malicious actor.",
      "To make the prompt execute faster.",
      "To hide the prompt from the user."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/23-agent-governance-responsible-ai/agent_governance_responsible_ai.ipynb"
    }
  },
  {
    "id": "chkpt-single_vs_multi_agent",
    "category": "Advanced",
    "prompt": "When do multiple LLM roles or calls not constitute multiple agents?",
    "options": [
      "Whenever the calls use different prompts.",
      "When application code owns one deterministic pipeline, state, capabilities, and completion rule.",
      "Whenever a reviewer call follows a producer call.",
      "Only when every call uses the same model."
    ],
    "correct": [
      1
    ],
    "explanation": "Multiple calls can be stages in one application-owned pipeline. An agent boundary involves distinct control, capability, context, state, or lifecycle semantics—not merely another prompt.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-manager-vs-handoff",
    "category": "Advanced",
    "prompt": "What is the defining control difference between manager delegation and a handoff?",
    "options": [
      "A manager always uses more models.",
      "A handoff is always faster.",
      "The manager retains final-answer control when calling specialists as tools, while a handoff changes the active owner.",
      "Only handoffs can return typed artifacts."
    ],
    "correct": [2],
    "explanation": "Manager-style orchestration keeps the manager in control of synthesis. A handoff transfers the active conversation or workflow phase to the receiving specialist.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-parallel-work-clock",
    "category": "Advanced",
    "prompt": "Why does parallel specialist work not imply linear wall-clock latency?",
    "options": [
      "Parallel calls consume no compute.",
      "Total work sums every task, while an independent parallel batch contributes roughly its slowest task to the critical path.",
      "Token use disappears during fan-out.",
      "Parallel systems cannot encounter rate limits."
    ],
    "correct": [1],
    "explanation": "Aggregate model and tool work remains additive, but independent operations overlap in elapsed time. Queueing, contention, and serialization must still be measured.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-agent-security-boundary",
    "category": "Advanced",
    "prompt": "Why is an agent boundary not automatically a security boundary?",
    "options": [
      "Agents cannot use tools.",
      "Agent names and prompts do not enforce credentials, authorization, network isolation, sandboxes, or approvals.",
      "Security applies only to production writes.",
      "Typed outputs automatically isolate every agent."
    ],
    "correct": [1],
    "explanation": "Security boundaries are application and infrastructure controls. A different prompt or agent name does not isolate credentials, data, tools, networks, or execution authority.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-capability-attenuation",
    "category": "Advanced",
    "prompt": "What does capability attenuation prevent during delegation?",
    "options": [
      "Specialists returning low-confidence findings.",
      "A child receiving broader capability than the authorized request and parent, unless explicit application policy grants it.",
      "Managers using typed artifacts.",
      "Parallel tasks finishing out of order."
    ],
    "correct": [1],
    "explanation": "Attenuation prevents privilege laundering: delegation cannot manufacture authority that the parent or current request did not possess without an explicit trusted grant.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-handoff-state-loss",
    "category": "Advanced",
    "prompt": "How should state loss during a handoff be measured?",
    "options": [
      "Ask the receiving model whether it remembers everything.",
      "Compare required structured facts with the fields actually preserved and compute handoff-information recall.",
      "Count the number of messages in the transcript.",
      "Assume typed artifacts cannot lose information."
    ],
    "correct": [1],
    "explanation": "A required-facts contract makes state preservation observable. Recall is computed from transmitted structured fields rather than self-reported memory or staged prose.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-routing-multi-unknown",
    "category": "Advanced",
    "prompt": "Why must a production router support both MULTI_ROUTE and UNKNOWN?",
    "options": [
      "They make every request use more agents.",
      "They represent cross-domain work and unsupported requests without forcing an incorrect single destination.",
      "They eliminate the need for authorization.",
      "They guarantee perfect routing accuracy."
    ],
    "correct": [1],
    "explanation": "Set-valued and unknown outcomes prevent systematic under-routing and unsafe forced classification. Policy validation is still required after routing.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-pipeline-not-team",
    "category": "Advanced",
    "prompt": "When is a deterministic pipeline preferable to a multi-agent team?",
    "options": [
      "When stages, order, artifact contracts, and the completion gate are known in advance.",
      "Whenever the task has more than one model call.",
      "Only when no evaluation data exists.",
      "When specialists should debate without a turn limit."
    ],
    "correct": [0],
    "explanation": "Known stages such as generate, review, revise, and gate are clearer and more bounded as a pipeline. Open-ended coordination must earn its added cost through evaluation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-split-quality-gate",
    "category": "Advanced",
    "prompt": "Which evidence can justify splitting an agent under the course quality gate?",
    "options": [
      "Any reduction in one latency sample.",
      "A more sophisticated-looking architecture diagram.",
      "Improved success or materially lower privileged exposure, with no grounding or safety regression and cost/latency within limits.",
      "A larger number of model calls."
    ],
    "correct": [2],
    "explanation": "The gate requires measured structural benefit plus non-regression constraints. One improved metric cannot excuse worse grounding, safety, budget, or SLO performance.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-architecture-pareto",
    "category": "Advanced",
    "prompt": "What does Pareto-optimal mean when comparing agent architectures?",
    "options": [
      "One architecture has the highest score after hiding trade-offs.",
      "An architecture is not dominated by another that is at least as good on every tracked dimension and better on one.",
      "Every architecture has identical cost and quality.",
      "The architecture uses parallel specialists."
    ],
    "correct": [1],
    "explanation": "A Pareto front preserves meaningful trade-offs among quality, grounding, latency, cost, and exposure instead of claiming a universal winner.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/01-single-vs-multi-agent/single_vs_multi_agent.ipynb"
    }
  },
  {
    "id": "chkpt-incident_response",
    "category": "Advanced",
    "prompt": "Why is generating a structured Post-Mortem using Pydantic (Structured Outputs) critical for an automated incident pipeline?",
    "options": [
      "It allows the LLM to write poetry.",
      "The resulting JSON can be reliably inserted directly into a ticketing system (like Jira or ServiceNow) via their APIs, without human parsing.",
      "It makes the LLM run faster.",
      "It encrypts the post-mortem."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/05-incident-response/incident_response.ipynb"
    }
  },
  {
    "id": "chkpt-world_models_environment_modeling",
    "category": "Advanced",
    "prompt": "What is a 'World Model' in Agentic AI?",
    "options": [
      "A 3D simulation of the earth.",
      "A structured representation (like a graph or rule engine) of the environment, allowing the agent to understand dependencies and consequences *before* acting.",
      "A global translation model.",
      "A database of all internet websites."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/07-world-models-environment-modeling/world_models_environment_modeling.ipynb"
    }
  },
  {
    "id": "chkpt-long_running_asynchronous_agents",
    "category": "Advanced",
    "prompt": "Why use Async Job Queues for Agents?",
    "options": [
      "It makes the LLM hallucinate less.",
      "LLM agents often take a long time to loop through tools and reason. Async queues prevent HTTP timeouts and allow the user to check back later.",
      "It is required by OpenAI's Terms of Service.",
      "It reduces the token cost."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/10-long-running-asynchronous-agents/long_running_asynchronous_agents.ipynb"
    }
  },
  {
    "id": "chkpt-03_crewai_teams",
    "category": "Advanced",
    "prompt": "Over-delegation",
    "options": [
      "CrewAI is only for Python 2.",
      "CrewAI is conversation-driven, while AutoGen is task-driven.",
      "CrewAI is task-driven (agents execute specific assigned tasks), while AutoGen is conversation-driven (agents chat with each other).",
      "They are exactly the same.",
      "All tasks run in parallel.",
      "The output of Task 1 is automatically passed as context to Task 2.",
      "The agents vote on which task to do first.",
      "The crew is deleted after running."
    ],
    "correct": [
      2
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/03-crewai-teams/03_crewai_teams.ipynb"
    }
  },
  {
    "id": "chkpt-guardrails_policy_enforcement",
    "category": "Guardrails",
    "prompt": "Why use deterministic regex/Presidio for PII scrubbing instead of just asking the LLM not to output PII?",
    "options": [
      "Deterministic code is faster.",
      "LLMs are probabilistic and prone to jailbreaks or hallucinations. A deterministic guardrail guarantees that known PII patterns will *never* reach the user, regardless of what the LLM decides.",
      "Regex understands context better than LLMs.",
      "It looks cooler."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/24-guardrails-policy-enforcement/guardrails_policy_enforcement.ipynb"
    }
  },
  {
    "id": "chkpt-04_hybrid_production_architecture",
    "category": "Advanced",
    "prompt": "What is the primary benefit of a Hybrid Architecture?",
    "options": [
      "It uses multiple LLMs at the same time.",
      "It maximizes speed, reliability, and cost-efficiency by reserving the LLM only for tasks that traditional code cannot handle.",
      "It allows the LLM to write its own Python code.",
      "It prevents prompt injections entirely."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/advanced/04-hybrid-production-architecture/04_hybrid_production_architecture.ipynb"
    }
  },
  {
    "id": "chkpt-02_agent_loop",
    "category": "Agent Loops",
    "prompt": "Crashing on Tool Errors",
    "options": [
      "Crash the program immediately so the developer knows.",
      "Catch the exception, format it as a string, and append it as a `tool` observation so the LLM can see the error.",
      "Silently ignore it and continue the loop.",
      "Restart the OpenAI client.",
      "OpenAI charges more for later steps.",
      "The LLM gets slower over time.",
      "The `messages` array contains the entire history of the conversation, so the LLM has to read a longer prompt on every iteration.",
      "Tools use up tokens when they execute locally."
    ],
    "correct": [
      6
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/02-agent-loop/02_agent_loop.ipynb"
    }
  },
  {
    "id": "chkpt-04_crewai_incident_response_crew",
    "category": "Frameworks",
    "prompt": "Sequential vs Hierarchical",
    "options": [
      "You have to manually write Python code to pass the variables.",
      "CrewAI automatically passes the `expected_output` of the first task as context to the second task.",
      "The agents communicate via a Slack integration.",
      "They don't; they are completely isolated."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/05-agent-development-frameworks/05_agent_development_frameworks.ipynb"
    }
  },
  {
    "id": "chkpt-04_langgraph_remediation_approval",
    "category": "Frameworks",
    "prompt": "Memory Savers in Production",
    "options": [
      "It prevents the agent from ever using tools.",
      "It deletes the tools from the agent's memory.",
      "It pauses the graph execution right before the `tools` node runs, allowing a human or external system to inspect the state and approve continuation.",
      "It causes an exception if tools take too long to run.",
      "To save OpenAI API keys securely.",
      "Because pausing a graph means the application might exit. The checkpointer persists the current state (like variables and message history) so the graph can be resumed later.",
      "To make the graph run faster.",
      "To prevent hallucinations."
    ],
    "correct": [
      5
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/05-agent-development-frameworks/05_agent_development_frameworks.ipynb"
    }
  },
  {
    "id": "chkpt-04_pydanticai_compliance_caseworker",
    "category": "Frameworks",
    "prompt": "Strictness vs Flexibility",
    "options": [
      "The program crashes immediately with a KeyError.",
      "Pydantic automatically catches the validation error, sends it back to the LLM, and asks it to correct the schema.",
      "It converts it to `0`.",
      "It ignores the schema completely."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/05-agent-development-frameworks/05_agent_development_frameworks.ipynb"
    }
  },
  {
    "id": "chkpt-computer_using_agents",
    "category": "Computer-Using Agents",
    "prompt": "Fragility",
    "options": [
      "It has to wait for GUI elements to render and animations to finish before taking the next screenshot.",
      "The LLM models are smaller.",
      "It writes code to a database.",
      "It uses a slower internet connection.",
      "Fetching the current weather (which has a free REST API).",
      "Scraping data from a legacy internal tool that has no API and requires clicking through 5 drop-down menus.",
      "Calculating the sum of two numbers.",
      "Translating a document from English to Spanish."
    ],
    "correct": [
      5
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/07-computer-using-agents/07_computer_using_agents.ipynb"
    }
  },
  {
    "id": "chkpt-01_agent_foundations",
    "category": "Foundations",
    "prompt": "Skipping the Ladder",
    "options": [
      "RAG uses Vector DBs; Agents do not.",
      "RAG only reads data and generates text; Agents can dynamically choose and execute tools to alter their environment.",
      "Agents are always faster than RAG.",
      "RAG cannot use OpenAI.",
      "Summarizing a long support ticket.",
      "Querying a customer's order history.",
      "Processing a $500 refund to a user's credit card.",
      "Translating an email from French to English."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/01-ai-agent-foundations/01_agent_foundations.ipynb"
    }
  },
  {
    "id": "chkpt-03_workflow_or_agent",
    "category": "Workflows",
    "prompt": "Agentic Hammer",
    "options": [
      "When the task requires creative problem solving and dynamic tool usage.",
      "When the execution path is strict, compliance is required, and steps cannot be skipped.",
      "When you want to save money on API keys.",
      "When the task requires web browsing.",
      "The LLM.",
      "The user.",
      "The hardcoded edges (e.g. `builder.add_edge(\"auth\", \"balance\")`).",
      "The system prompt."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/beginner/03-workflow-or-agent/03_workflow_or_agent.ipynb"
    }
  },
  {
    "id": "chkpt-guardrails_untrusted_content",
    "category": "Guardrails",
    "prompt": "What is a Prompt Injection attack?",
    "options": [
      "When a hacker steals your OpenAI API key.",
      "When untrusted data (like an email) contains hidden instructions designed to override the agent's System Prompt.",
      "When the LLM generates a SQL injection string.",
      "When the context window runs out of tokens.",
      "They encrypt the data.",
      "They block the OpenAI API from reading the text.",
      "They provide strict visual and semantic boundaries, allowing the System Prompt to explicitly instruct the LLM to ignore commands found within those boundaries.",
      "They validate the input against a database."
    ],
    "correct": [
      6
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/04-guardrails-untrusted-content/04_guardrails_untrusted_content.ipynb"
    }
  },
  {
    "id": "chkpt-trajectory_optimization",
    "category": "Trajectory Optimization",
    "prompt": "What is a 'Trajectory' in the context of AI Agents?",
    "options": [
      "The physical location of the server.",
      "The sequence of Observations, Thoughts, and Actions (tool calls) taken by the agent to solve a problem.",
      "The memory usage of the python script.",
      "The learning rate of the model."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/06-trajectory-optimization/06_trajectory_optimization.ipynb"
    }
  },
  {
    "id": "chkpt-langgraph_state_memory",
    "category": "State & Memory",
    "prompt": "Why must a durable agent revalidate identity, policy, and approval when resuming a checkpoint?",
    "options": [
      "A thread ID is a bearer token that permanently authorizes every future action.",
      "Persisted state can outlive the process, policy, credentials, proposal target, and original user session.",
      "Checkpoint serialization automatically refreshes every expired credential.",
      "Resume always starts a completely new run with empty budgets."
    ],
    "correct": [
      1
    ],
    "explanation": "A checkpoint preserves execution state, not authority. Resume must re-check tenant/thread ownership, current policy, versions, retention, credentials, and any exact approval binding.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/10-langgraph-state-memory/10_langgraph_state.ipynb"
    }
  },
  {
    "id": "chkpt-agent_evaluation",
    "category": "Evaluation",
    "prompt": "Why is relying on \"vibes\" (manual spot checking) bad for agent development?",
    "options": [
      "It is illegal.",
      "Agents are non-deterministic. A system prompt change might fix one edge case but silently break 5 others. Without an automated eval harness, regression is inevitable.",
      "It is too fast.",
      "It uses too many API tokens."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/05-agent-evaluation/05_agent_evaluation.ipynb"
    }
  },
  {
    "id": "chkpt-agentic_rag",
    "category": "Agentic RAG",
    "prompt": "What makes Agentic RAG safe and useful for the Northstar incident?",
    "options": [
      "Letting retrieved text expand the source allowlist when evidence is missing.",
      "Letting a bounded controller choose retrieval steps, validate each source, measure evidence gaps, verify claim support, and abstain when needed.",
      "Always querying every internal and public source before answering.",
      "Treating a citation URL as proof that every nearby claim is supported."
    ],
    "correct": [
      1
    ],
    "explanation": "Agency is bounded by application-owned tenant, source, query, hop, cost, deadline, and action policy. Retrieved content remains evidence, and unsupported answers must abstain.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/09-agentic-rag/09_agentic_rag.ipynb"
    }
  },
  {
    "id": "chkpt-tool_engineering",
    "category": "Tool Engineering",
    "prompt": "Broad Inputs",
    "options": [
      "It runs faster than a standard action.",
      "It prevents the LLM from executing irreversible side-effects by requiring human authorization.",
      "It uses less tokens.",
      "It bypasses Pydantic validation.",
      "It causes the LLM to crash safely.",
      "It allows the LLM to read the exact constraint it violated and self-correct.",
      "It saves database space.",
      "We shouldn't; we should hide errors from the LLM for security."
    ],
    "correct": [
      1
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/01-tool-engineering/01_tool_engineering.ipynb"
    }
  },
  {
    "id": "chkpt-context_engineering",
    "category": "Context Engineering",
    "prompt": "Why is it dangerous for an Agent to read full server logs?",
    "options": [
      "The logs might contain viruses.",
      "LLMs cannot read log formats.",
      "Large logs will quickly exhaust the LLM's token context window and cause crashes or massive API bills.",
      "It's illegal.",
      "The first user message.",
      "The System Prompt.",
      "The most recent tool observation.",
      "The LLM's apologies."
    ],
    "correct": [
      2
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/02-context-engineering/02_context_engineering.ipynb"
    }
  },
  {
    "id": "chkpt-planning_task_decomposition",
    "category": "Planning",
    "prompt": "Why can an explicit Plan-and-Execute DAG help on some long, complex tasks?",
    "options": [
      "It uses a more expensive model.",
      "It separates bounded planning from policy-controlled execution, exposes dependencies and artifacts, and makes progress and checkpoints inspectable.",
      "It allows the LLM to skip tools entirely.",
      "It runs on a quantum computer."
    ],
    "correct": [
      1
    ],
    "explanation": "An explicit DAG can improve inspectability and coordination when dependencies matter, but it is not universally better than ReAct; the correct pattern depends on task shape and evaluation results.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/08-planning-task-decomposition/08_planning_task_decomposition.ipynb"
    }
  },
  {
    "id": "chkpt-human_approval_permissions",
    "category": "Permissions & Approval",
    "prompt": "Where is the correct place to enforce permissions for an Agent?",
    "options": [
      "In the System Prompt (e.g., \"Do not delete databases\").",
      "In the Application/API layer using standard RBAC, checking the Agent's identity before executing the tool.",
      "By asking the user for a password before running the tool.",
      "In the vector database.",
      "It makes the LLM run faster.",
      "It allows the LLM to execute dangerous tools securely.",
      "It restricts the LLM to merely generating structured data (Proposals) which a human can safely review and execute later.",
      "It encrypts the LLM's memory."
    ],
    "correct": [
      6
    ],
    "explanation": "Refer to the notebook for the detailed explanation.",
    "source": {
      "label": "Notebook Checkpoint",
      "url": "curriculum/intermediate/03-human-approval-permissions/03_human_approval_permissions.ipynb"
    }
  },
  {
    "id": "sota-react-fragility",
    "category": "Agent Loops",
    "prompt": "Why is the traditional ReAct pattern (parsing Action/Observation text blocks) considered fragile for production workloads?",
    "options": [
      "It requires expensive GPU clusters to evaluate the text",
      "LLMs often hallucinate spacing, indentation, and colon placement, breaking standard regex parsers",
      "It cannot be run synchronously in standard Python code",
      "It consumes significantly more tokens than Native JSON Tool Calling",
      "It prevents the model from generating multiple tool calls in parallel"
    ],
    "correct": [
      1,
      3,
      4
    ],
    "explanation": "ReAct loops that rely on regex parsing of unstructured text frequently fail due to minor formatting hallucinations. They also waste tokens outputting boilerplate text ('Thought:', 'Action:', 'Observation:') and lack the structured strictness of JSON arrays for parallel execution.",
    "source": {
      "label": "Deep Dive: ReAct Pattern",
      "url": "curriculum/beginner/02-agent-loop/DEEP_DIVE_REACT_PATTERN.md"
    }
  },
  {
    "id": "sota-graph-state-machines",
    "category": "Agent Loops",
    "prompt": "What is the primary architectural advantage of using State Machines (like LangGraph) over traditional while loops?",
    "options": [
      "They automatically train a fine-tuned model for you",
      "They allow discrete nodes to be interrupted, persisted to a database, and safely resumed across asynchronous human workflows",
      "They eliminate the possibility of context-window exhaustion",
      "They formally separate the LLM reasoning payload from the deterministic tool execution payload"
    ],
    "correct": [
      1,
      3
    ],
    "explanation": "State graphs explicitly decouple logic into isolated nodes, allowing the graph state to be snapshotted (Time Travel) and safely paused/resumed, unlike standard memory-bound while loops.",
    "source": {
      "label": "Deep Dive: SOTA Loops",
      "url": "curriculum/beginner/02-agent-loop/DEEP_DIVE_SOTA_LOOPS.md"
    }
  },
  {
    "id": "sota-dags-vs-agents",
    "category": "Workflows",
    "prompt": "In an Enterprise context, what is the 'Agentic Workflow' paradigm compared to a pure Autonomous Agent?",
    "options": [
      "An Agentic Workflow is an autonomous LLM that writes its own code dynamically",
      "An Agentic Workflow utilizes a strict, hard-coded DAG architecture, but selectively injects autonomous LLMs as specific 'Router' or 'Evaluator' nodes to handle non-deterministic inputs",
      "An Agentic Workflow refers to a DAG running inside a Jupyter Notebook",
      "A pure Autonomous Agent is generally preferred for safety-critical environments due to its adaptability"
    ],
    "correct": [
      1
    ],
    "explanation": "SOTA Enterprise designs avoid pure non-deterministic agents. They utilize 'Agentic Workflows': macro-architectures that are highly deterministic (DAGs), but micro-architectures that leverage agents to route messy natural language inputs.",
    "source": {
      "label": "Deep Dive: DAGs vs Agents",
      "url": "curriculum/beginner/03-workflow-or-agent/DEEP_DIVE_DAGS_VS_AGENTS.md"
    }
  },
  {
    "id": "sota-multimodal-omniparser",
    "category": "Computer-Using Agents",
    "prompt": "How do SOTA Multimodal systems (like OmniParser) prevent 'Spatial Hallucination' when an agent interacts with a graphical user interface?",
    "options": [
      "They feed raw coordinate arrays directly into the text stream",
      "They utilize a specialized vision model to draw bounding boxes and assign unique integer IDs to actionable elements before sending the semantic image to the LLM",
      "They force the LLM to output precise X, Y pixel coordinates natively",
      "They require human developers to hard-code X,Y coordinates for every website"
    ],
    "correct": [
      1
    ],
    "explanation": "Vision-Language Models struggle to accurately calculate exact pixel coordinates (Spatial Hallucination). OmniParser mitigates this by drawing bounding boxes and assigning integer IDs, reducing the LLM's task from 'calculate pixels' to 'select ID'.",
    "source": {
      "label": "Deep Dive: SOTA Multimodal",
      "url": "curriculum/beginner/07-computer-using-agents/DEEP_DIVE_SOTA_MULTIMODAL.md"
    }
  },
  {
    "id": "sota-axtree-bloat",
    "category": "Computer-Using Agents",
    "prompt": "Why is extracting an Accessibility Tree (AXTree) preferred over providing the raw HTML DOM to an LLM?",
    "options": [
      "Raw HTML DOMs contain massive amounts of CSS, metadata, and non-actionable script tags that bloat the context window",
      "AXTrees natively understand how to bypass CAPTCHAs",
      "AXTrees distill the interface into a semantic tree of purely actionable and relevant elements",
      "HTML DOMs cannot be retrieved by Playwright"
    ],
    "correct": [
      0,
      2
    ],
    "explanation": "Feeding raw DOMs into a prompt results in extreme token bloat. AXTrees strip away styling and metadata, leaving a lean, semantic representation of the interface.",
    "source": {
      "label": "Deep Dive: Accessibility Trees",
      "url": "curriculum/beginner/07-computer-using-agents/DEEP_DIVE_ACCESSIBILITY_TREES.md"
    }
  },
  {
    "id": "sota-hitl-idempotency",
    "category": "Permissions & Approval",
    "prompt": "Why is injecting an Idempotency Key critical when building Human-in-the-Loop (HITL) approval workflows for consequential actions?",
    "options": [
      "It speeds up the LLM inference time",
      "It ensures that if an approval confirmation request is accidentally retried or duplicated (e.g., due to network jitter), the system does not execute the dangerous side effect multiple times",
      "It allows the LLM to bypass the human approval if the human takes too long",
      "It proves the identity of the human approver"
    ],
    "correct": [
      1
    ],
    "explanation": "Idempotency ensures that mutating actions (like restarting a server or transferring funds) happen exactly once, regardless of how many times the API request is retried.",
    "source": {
      "label": "Deep Dive: Idempotency",
      "url": "curriculum/intermediate/03-human-approval-permissions/DEEP_DIVE_IDEMPOTENCY.md"
    }
  },
  {
    "id": "sota-typed-errors",
    "category": "Tool Engineering",
    "prompt": "How does strict Typed Error handling improve autonomous agent loops?",
    "options": [
      "By failing silently so the agent assumes success",
      "By wrapping exceptions in Pydantic models with explicit remediation suggestions (e.g., 'Validation Error: Region must be eu-west'), allowing the agent to self-correct",
      "By crashing the loop and immediately pinging Slack",
      "By preventing the LLM from entering a hallucination cycle caused by unstructured stack traces"
    ],
    "correct": [
      1,
      3
    ],
    "explanation": "Raw stack traces consume excessive tokens and confuse LLMs. Returning typed, conversational error messages with specific hints enables the LLM to understand its mistake and intelligently retry.",
    "source": {
      "label": "Deep Dive: Typed Errors",
      "url": "curriculum/intermediate/01-tool-engineering/DEEP_DIVE_TYPED_ERRORS.md"
    }
  },
  {
    "id": "sota-plan-and-execute",
    "category": "Planning",
    "prompt": "In a policy-controlled Plan-and-Execute system, what is the planner's strict role?",
    "options": [
      "To execute all tools asynchronously in a single massive prompt",
      "To propose bounded, typed tasks and dependencies for application validation; it does not authorize or execute tools",
      "To constantly rewrite the codebase to accommodate new requirements",
      "To bypass authorization restrictions to accelerate task completion"
    ],
    "correct": [
      1
    ],
    "explanation": "The planner proposes structure. Application code validates capabilities, dependencies, budgets, and coverage before restricted executors run any task; checkpoints then control replanning and completion.",
    "source": {
      "label": "Deep Dive: Plan and Execute",
      "url": "curriculum/intermediate/08-planning-task-decomposition/DEEP_DIVE_PLAN_AND_EXECUTE.md"
    }
  },
  {
    "id": "sota-semantic-routing",
    "category": "Agentic RAG",
    "prompt": "What is the correct role of semantic routing in a production retrieval controller?",
    "options": [
      "It proposes one or more registered sources for an evidence question; application policy still validates permissions, tenant scope, and budgets.",
      "It authorizes any source whose embedding score exceeds a threshold.",
      "It must force every query into exactly one route.",
      "It guarantees lower latency and higher accuracy than deterministic routing."
    ],
    "correct": [
      0
    ],
    "explanation": "Routing is a proposal layer, not an authorization boundary. Its accuracy, abstention quality, latency, and cost must be measured on the actual route set and query distribution.",
    "source": {
      "label": "Deep Dive: Semantic Routing",
      "url": "curriculum/intermediate/09-agentic-rag/DEEP_DIVE_SEMANTIC_ROUTING.md"
    }
  },
  {
    "id": "agent-loop-state-machine",
    "category": "The Agent Loop",
    "prompt": "What is the primary advantage of a state machine loop (like LangGraph) over a basic ReAct while-loop?",
    "options": [
      "It uses fewer tokens",
      "It forces the model to generate correct JSON",
      "It makes state transitions explicit, inspectable, and controllable",
      "It eliminates the need for tool schemas",
      "It runs significantly faster"
    ],
    "correct": [2],
    "explanation": "State machines separate the control flow from the model generation, making every step inspectable, testable, and capable of supporting human-in-the-loop checkpoints.",
    "source": {
      "label": "The Agent Loop",
      "url": "curriculum/beginner/02-agent-loop/README.md"
    }
  },
  {
    "id": "agent-loop-runaway",
    "category": "The Agent Loop",
    "prompt": "Which of the following is an effective way to prevent a runaway agent loop?",
    "options": [
      "Asking the model politely to stop after 5 steps",
      "Implementing hard budgets on turns, time, and spend",
      "Using a more advanced model",
      "Relying on system prompts to define terminal states"
    ],
    "correct": [1],
    "explanation": "Agent loops must be bounded by deterministic application code (max steps, timeouts, budgets), not by prompt engineering or model capability.",
    "source": {
      "label": "The Agent Loop",
      "url": "curriculum/beginner/02-agent-loop/README.md"
    }
  },
  {
    "id": "tools-structured-outputs",
    "category": "Tools & Structured Outputs Fundamentals",
    "prompt": "Why is it important to use Structured Outputs (e.g., JSON Schema/Pydantic) for agent tools?",
    "options": [
      "It makes the API response look cleaner",
      "It guarantees the model will never hallucinate",
      "It provides strict type enforcement and reduces parsing errors",
      "It allows the model to run faster"
    ],
    "correct": [2],
    "explanation": "Structured Outputs enforce type constraints at the API level, drastically reducing the chances of a model providing improperly formatted arguments.",
    "source": {
      "label": "Tools & Structured Outputs Fundamentals",
      "url": "curriculum/beginner/04-tools-and-structured-outputs/README.md"
    }
  },
  {
    "id": "tools-authorization",
    "category": "Tools & Structured Outputs Fundamentals",
    "prompt": "What is the relationship between exposing a tool to a model and authorization?",
    "options": [
      "Exposing a tool automatically authorizes the model to use it safely",
      "Exposing a tool is merely a capability; authorization must be enforced by the application layer",
      "Models inherently understand access control from the tool description",
      "Only read-only tools need authorization checks"
    ],
    "correct": [1],
    "explanation": "A model proposes a tool call; the application layer must always validate if the current session or user actually has the permissions to execute it.",
    "source": {
      "label": "Tools & Structured Outputs Fundamentals",
      "url": "curriculum/beginner/04-tools-and-structured-outputs/README.md"
    }
  },
  {
    "id": "agent-frameworks-architecture",
    "category": "Agent Development Frameworks",
    "prompt": "What is the key difference between an agent framework and an agent architecture?",
    "options": [
      "They are the exact same thing",
      "A framework provides the runtime mechanics, while the architecture defines the control flow and boundaries",
      "An architecture is written in Python, while a framework is the API",
      "Frameworks dictate that you must use multi-agent systems"
    ],
    "correct": [1],
    "explanation": "Frameworks (like LangGraph or CrewAI) package runtime mechanics like state management and tool execution. Architecture is the design choice of how control, boundaries, and evaluation are structured.",
    "source": {
      "label": "Agent Development Frameworks",
      "url": "curriculum/beginner/05-agent-development-frameworks/README.md"
    }
  },
  {
    "id": "frameworks-durable-execution",
    "category": "Agent Development Frameworks",
    "prompt": "How do durable execution checkpointers (like LangGraph MemorySaver) enhance long-running agent reliability?",
    "options": [
      "They automatically fix any model hallucination",
      "They allow workflows to safely pause at human-in-the-loop breakpoints and resume without losing state",
      "They remove the need for writing unit tests",
      "They eliminate the need for API keys"
    ],
    "correct": [1],
    "explanation": "Durable checkpointers persist the execution state at each graph transition, enabling safe interrupts, human confirmation gates, and resumption across process restarts.",
    "source": {
      "label": "Agent Development Frameworks",
      "url": "curriculum/beginner/05-agent-development-frameworks/README.md"
    }
  },
  {
    "id": "frameworks-dependency-injection",
    "category": "Agent Development Frameworks",
    "prompt": "Why is dependency injection (such as PydanticAI RunContext) preferable to global variables in agent tool functions?",
    "options": [
      "It makes the tools faster to execute",
      "It securely injects trusted execution context (user ID, tenant ID, permissions) into tools without letting the model fabricate credentials",
      "It allows the model to alter user roles dynamically",
      "It avoids defining Pydantic schemas"
    ],
    "correct": [1],
    "explanation": "Dependency injection guarantees that tools execute with application-verified user context, database handles, and tenant boundaries rather than untrusted model arguments.",
    "source": {
      "label": "Agent Development Frameworks",
      "url": "curriculum/beginner/05-agent-development-frameworks/README.md"
    }
  },
  {
    "id": "capstone-agent-testing",
    "category": "Building Your First Complete Agent",
    "prompt": "When building a complete, testable agent, what is the most robust way to handle external dependencies?",
    "options": [
      "Call production APIs directly to ensure realism",
      "Use mocks or local fixtures for deterministic, repeatable testing",
      "Disable all tests until the agent is in production",
      "Write prompts that tell the model to imagine the API response"
    ],
    "correct": [1],
    "explanation": "Local fixtures and mocks ensure that agent trajectories can be tested deterministically without risking side effects or dealing with network flakiness.",
    "source": {
      "label": "Building Your First Complete Agent",
      "url": "curriculum/beginner/06-building-your-first-agent/README.md"
    }
  },
  {
    "id": "capstone-dispatcher-boundary",
    "category": "Building Your First Complete Agent",
    "prompt": "Why must all tool executions route through a centralized dispatcher rather than direct function calls?",
    "options": [
      "To enforce schema validation, authorization, business rules, and idempotency checks before invoking side effects",
      "To convert all tool returns into unvalidated strings",
      "Because Python does not allow calling functions directly",
      "To allow the model to bypass permission checks"
    ],
    "correct": [0],
    "explanation": "A centralized dispatcher acts as the application's security boundary, ensuring that every proposed action is strictly validated against schemas, permissions, business invariants, and idempotency guarantees before execution.",
    "source": {
      "label": "Building Your First Complete Agent",
      "url": "curriculum/beginner/06-building-your-first-agent/README.md"
    }
  },
  {
    "id": "capstone-approval-binding",
    "category": "Building Your First Complete Agent",
    "prompt": "What parameters should a human approval token bind to for high-risk write actions?",
    "options": [
      "Only the current date",
      "Proposal digest, target resource, action payload, approver identity, and expiration timestamp",
      "Any future action the model decides to take",
      "Only the model's confidence score"
    ],
    "correct": [1],
    "explanation": "Cryptographically bound approvals guarantee that an approval token is valid only for the exact proposed action, target, payload digest, and time window, preventing replay attacks or action drift.",
    "source": {
      "label": "Building Your First Complete Agent",
      "url": "curriculum/beginner/06-building-your-first-agent/README.md"
    }
  }
];
