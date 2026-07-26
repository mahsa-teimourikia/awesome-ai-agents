# Multi-agent systems and teams of agents

A multi-agent system is an application in which two or more specialized agents collaborate on a task. Each agent may have its own instructions, tools, context, memory, permissions, model, and success criteria. A team needs more than a list of agents: it needs an ownership model, communication protocol, state strategy, termination rule, and evaluation plan.

## When a team is justified

Start with a strong single agent and add a team only when a measured limitation calls for it. A multi-agent design is a good candidate when:

- subtasks are independent enough to run in parallel;
- specialists need distinct tools, policies, or context;
- one context window would become noisy or exceed a useful budget;
- roles have different evaluation criteria, such as researcher, coder, and reviewer;
- a human or deterministic system needs an explicit approval boundary; or
- the task naturally forms a graph with branches, joins, retries, and loops.

AutoGen's team tutorial recommends optimizing a single agent first and moving to a team for complex tasks that require collaboration and diverse expertise. Multi-agent scaffolding adds coordination cost, latency, and failure modes; “more agents” is not a quality metric.

## The design dimensions

Before choosing a framework, decide these dimensions:

| Dimension | Questions to answer |
| --- | --- |
| Ownership | Who owns the user-facing conversation and final answer? |
| Delegation | Who chooses the next agent: code, manager, selector, or graph? |
| Communication | Do agents exchange messages, typed artifacts, events, or shared state? |
| Context | Does each specialist receive the full history, a summary, or only a task packet? |
| State | What is ephemeral working state versus durable memory? |
| Permissions | Which tools and side effects can each role access? |
| Termination | What exact condition stops the team? |
| Failure | How are timeouts, invalid outputs, disagreements, and partial success handled? |
| Evaluation | Is the team better than the single-agent and deterministic baselines? |

## Team topologies

### 1. Manager with agents as tools

One manager remains responsible for the user-facing answer and calls specialists as bounded tools. OpenAI's Agents SDK describes this as a central manager invoking `Agent.as_tool()`; the specialist receives generated task input and returns a result to the manager.

```text
user → manager ──┬─→ research specialist ──┐
                 ├─→ data specialist ──────┼─→ manager → user
                 └─→ review specialist ────┘
```

**Use when:** one agent must synthesize several outputs, enforce shared guardrails, or maintain one consistent voice.

**Contract:** each specialist should return a typed result with evidence, confidence, unresolved questions, and a suggested next action. Do not return an unbounded transcript by default.

**Risks:** the manager may delegate poorly, hide specialist failures, or over-call tools. Add per-specialist budgets, provenance, and a completeness check.

### 2. Triage and handoffs

A triage agent routes the interaction to a specialist; the specialist becomes the active owner. OpenAI's handoff model represents delegation as a tool choice, but the downstream agent takes over the conversation.

```text
user → triage ── billing specialist → user
             └─ technical specialist → user
```

**Use when:** the specialist should respond directly, own the next turn, and use a focused prompt.

**Risks:** misrouting, lost context, and ambiguous ownership. Define a handoff input filter, preserve a compact task summary, and provide an escalation route.

### 3. Orchestrator-worker

An orchestrator decomposes an open-ended goal, launches workers, then synthesizes results. Anthropic's multi-agent research system is a practical example: a lead agent delegates specialized research in parallel and composes the answer.

```text
goal → orchestrator → worker A ─┐
                    → worker B ─┼→ synthesis → validator
                    → worker C ─┘
```

**Use when:** the number and shape of subtasks cannot be fully enumerated ahead of time.

**Risks:** duplicated work, weak delegation, missing context, fan-out explosions, and synthesis that cannot prove its claims. Limit depth and breadth, require worker contracts, and attach provenance to every result.

### 4. Parallel specialists with a join

Code launches independent specialists concurrently and joins their typed outputs.

```text
input ──┬─→ security review ──┐
        ├─→ performance review ┼─→ join and reconcile
        └─→ correctness review ┘
```

**Use when:** subtasks do not depend on each other and latency matters.

**Risks:** inconsistent assumptions, duplicated context, and an aggregator that silently chooses a weak result. Give each worker a narrow scope and make conflicts explicit.

### 5. Sequential pipeline

Each specialist transforms the output of the previous one:

```text
researcher → planner → writer → critic → reviser
```

**Use when:** each stage depends on a stable artifact from the previous stage.

**Risks:** early errors propagate and total latency grows. Validate each artifact before handing it forward; stop when a contract fails.

### 6. Group chat or selector team

Agents share a conversation or topic, and a manager or selector chooses the next speaker. AutoGen's group-chat pattern uses a manager to request the next speaker; it can be round-robin, selector-driven, or custom.

```text
        ┌──────── writer ────────┐
user → group topic ← reviewer ← manager
        └──── researcher ────────┘
```

**Use when:** the team benefits from iterative discussion, critique, or dynamic role selection.

**Risks:** circular conversations, context growth, repeated arguments, and no objective stopping condition. Limit turns, use message schemas, and make the manager enforce termination.

### 7. Graph team

Represent agents as nodes and transitions as edges. A graph can express sequential steps, parallel fan-out, conditional branches, joins, retries, and loops with explicit exits.

```text
start → planner → [research A | research B] → join → reviewer
                                         ↘ failed → replanner
```

**Use when:** operators need deterministic control, resumability, checkpoints, and visible state transitions.

**Risks:** graph complexity and stale state. Keep node contracts small, checkpoint after side effects, and make every loop have a bounded exit.

## Communication contracts

Avoid passing “please figure it out” between agents. Use task packets and result packets:

```json
{
  "task_id": "research-42",
  "objective": "Find primary sources about feature X",
  "scope": ["official docs", "research papers"],
  "constraints": {"max_sources": 8, "deadline_seconds": 60},
  "required_output": ["claims", "citations", "open_questions"]
}
```

```json
{
  "task_id": "research-42",
  "status": "partial_success",
  "claims": [{"text": "...", "source": "..."}],
  "open_questions": ["..."],
  "tool_calls": 4,
  "cost": 0.03
}
```

Every message should identify its task, producer, schema version, provenance, and status. Separate user-visible prose from machine-consumed fields.

## Context and state strategy

There are three useful choices:

1. **Full history:** simplest, but expensive and noisy. Use only for small, trusted conversations.
2. **Task packet plus selected evidence:** usually the best default for specialists.
3. **Shared state or event log:** useful for graph teams and long-running workflows; requires concurrency and ownership rules.

Do not let every agent write arbitrary shared memory. Use an owner or state reducer, version updates, validate artifacts, and record conflicts.

## Permissions and trust

Agents in the same team are not automatically trusted. Give each role only the tools it needs:

| Role | Typical access | Usually avoid |
| --- | --- | --- |
| Researcher | Read-only search and retrieval | Production writes |
| Analyst | Read-only data query and computation | Credential administration |
| Writer | Draft artifact store | External publishing |
| Reviewer | Read-only artifacts and validators | Silent mutation of source data |
| Deployer | Approved artifact and deployment API | Arbitrary code execution |
| Orchestrator | Delegation and synthesis | Broad side effects by default |

Treat worker outputs, retrieved content, and peer messages as untrusted input. Validate tool arguments at the execution boundary, not only in prompts.

## Termination and failure design

A team needs both local and global termination:

- worker success or typed failure;
- maximum turns per worker;
- maximum fan-out and recursion depth;
- global time, token, and spend budgets;
- quorum or minimum evidence threshold;
- explicit reviewer approval; and
- final artifact validator.

Represent failures such as `Timeout`, `InvalidResult`, `PermissionDenied`, `Conflict`, `BudgetExceeded`, and `NeedsHuman` instead of hiding them in prose. The coordinator should decide whether to retry, replace a worker, continue partially, or escalate.

## Choosing manager, handoff, or graph

| Need | Recommended starting point |
| --- | --- |
| One consistent final answer from specialists | Manager with agents as tools |
| Route a conversation to one expert | Handoff or triage |
| Unknown decomposition and parallel exploration | Orchestrator-worker |
| Independent reviews with a deterministic join | Parallel fan-out and join |
| Clear steps, approvals, retries, and resumption | Graph workflow |
| Debate or iterative critique | Bounded group chat |

Combine patterns when ownership stays clear. For example, a triage agent can hand off to a domain specialist that calls two research agents as tools.

## Evaluation plan

Compare the team with a single-agent and deterministic baseline on the same task set:

- outcome success and artifact correctness;
- delegation and routing accuracy;
- tool-call correctness and unauthorized attempts;
- evidence coverage and provenance;
- recovery from worker failure;
- total turns, latency, token usage, and cost;
- escalation precision and human review burden; and
- safety under prompt injection and malicious worker output.

Do not reward a team for producing more messages. Reward verified task outcomes within a bounded operating envelope.

## Implementation checklist

- [ ] Prove the single-agent baseline is insufficient.
- [ ] Assign a narrow role and tool set to every agent.
- [ ] Choose who owns the user-facing answer.
- [ ] Define typed task and result contracts.
- [ ] Decide full history, task packet, or shared-state context.
- [ ] Add provenance and status to every worker result.
- [ ] Set per-agent and global budgets.
- [ ] Define retries, partial success, conflict, and escalation behavior.
- [ ] Validate final artifacts deterministically where possible.
- [ ] Trace handoffs, delegation, messages, tool calls, and approvals.
- [ ] Evaluate against a single-agent baseline before shipping.

## Sources

- [OpenAI Agents SDK — agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- [OpenAI Agents SDK — agents as tools](https://openai.github.io/openai-agents-python/tools/)
- [OpenAI Agents SDK — handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [Anthropic — Building a multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [AutoGen — Group chat design pattern](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html)
- [AutoGen — Teams tutorial](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/teams.html)
- [LangGraph — multi-agent systems](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
