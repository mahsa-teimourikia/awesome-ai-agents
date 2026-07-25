# What is an AI agent?

An AI agent is a system that can pursue a goal over multiple steps, decide which actions to take, use tools to affect or inspect an environment, and adapt its next action based on the results.

The word *agent* is used loosely. A useful engineering definition should distinguish an agent from a chatbot, a single model call, and a deterministic automation.

## A practical definition

OpenAI's [Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) describes an agent through three core components: a model, tools, and instructions. Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) adds an important control distinction: an agent dynamically directs its own process and tool use, while a workflow follows predefined code paths.

Combining those views, a production agent has:

1. **A goal and success criteria.** The system needs a task to pursue and a way to decide when it is complete.
2. **A model.** The model interprets the goal, context, state, and observations, then proposes the next action.
3. **Instructions and policy.** These describe the role, process, constraints, permissions, and escalation rules.
4. **Tools.** Typed interfaces let the agent retrieve information, run code, query systems, or make controlled changes.
5. **State.** The run retains progress, observations, artifacts, pending work, budgets, and decisions.
6. **A control loop.** The runtime invokes the model, executes or rejects an action, records the result, and repeats.
7. **Boundaries.** Guardrails, permissions, approvals, budgets, and stop conditions keep the loop within its operating envelope.
8. **Evidence.** Traces and evaluations reveal what happened and whether the task succeeded.

## The agent loop

The [ReAct paper](https://arxiv.org/abs/2210.03629) established a widely used pattern: interleave reasoning with actions and observations. In implementation terms:

```text
state = initialize(goal, policy, budget)

while not terminal(state):
    proposed_action = model(goal, instructions, state, available_tools)
    checked_action = policy_engine.validate(proposed_action)

    if checked_action.requires_approval:
        checked_action = request_human_approval(checked_action)

    observation = execute_or_reject(checked_action)
    state = record(state, checked_action, observation)

return final_result(state)
```

The model does not directly receive arbitrary system access. It proposes a structured action; application code validates permissions and arguments, executes the action in a controlled environment, and returns an observation.

## What is not necessarily an agent?

| System | Agent? | Why |
| --- | --- | --- |
| One prompt → one response | Usually no | No persistent loop or environment interaction |
| Fixed three-step summarization pipeline | Workflow | The code determines every step |
| Router choosing one known branch | Agentic workflow | The model makes a bounded decision inside predefined control flow |
| Assistant that searches, compares, retries, and stops when evidence is sufficient | Agent | The model dynamically selects steps based on observations |
| Scheduler running a static script | Automation | Autonomous timing does not imply model-directed reasoning |

Autonomy is not binary. Systems lie on a spectrum based on how much discretion the model has over decomposition, tool choice, sequencing, repetition, stopping, and side effects. Anthropic's [work on measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) is useful for describing that spectrum rather than applying a single label.

## Model

The model is a decision component, not the whole agent. Its responsibilities may include:

- understanding the task and current state;
- choosing a tool or producing a final response;
- decomposing a goal;
- evaluating whether an observation is sufficient;
- recovering from tool errors; and
- deciding when to stop or escalate.

Model selection should be evaluation-driven. A stronger model may improve planning but cost more; a smaller model may be sufficient for routing or extraction. Different nodes in a workflow can use different models.

## Instructions

Good agent instructions specify:

- the goal and definition of done;
- the allowed and prohibited actions;
- when to use each tool;
- how to handle uncertainty and conflicting evidence;
- when to ask for approval or hand off to a person;
- output and artifact requirements; and
- explicit stop conditions.

Instructions are not a security boundary. A prompt can influence model behavior, but application code must enforce identity, permissions, schemas, spend limits, and irreversible-action approvals.

## Tools

Tools turn text generation into action. Examples include search, retrieval, databases, browsers, code execution, ticket systems, payments, and messaging.

The quality of an agent depends heavily on the quality of its tools. Anthropic's [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) emphasizes evaluating how agents actually use tool descriptions and responses. Prefer:

- a narrow, unambiguous operation;
- typed input and output schemas;
- clear preconditions and error messages;
- an explicit read/write or risk classification;
- idempotency keys for repeatable writes;
- a preview or dry-run mode for high-impact operations; and
- compact results containing the information needed for the next decision.

## State and memory

These terms are often conflated:

- **Context** is the information supplied to the model for one inference.
- **Working state** is the durable record needed to resume or inspect the current task.
- **Episodic memory** records past events or attempts.
- **Semantic memory** stores facts or learned knowledge.
- **Procedural memory** stores reusable instructions or skills.

The [Reflexion paper](https://arxiv.org/abs/2303.11366) is an influential example of using linguistic feedback stored in episodic memory to improve later attempts without updating model weights. The [MemGPT paper](https://arxiv.org/abs/2310.08560) explores managing limited model context with memory tiers.

Memory creates risk as well as utility. A bad or malicious memory can affect future tasks. Long-term writes therefore need provenance, user or tenant scoping, validation, retention rules, inspection, and deletion.

## Stop conditions

Every agent needs terminal states. Common examples:

- success criteria are met;
- the model returns a final response;
- a deterministic validator accepts an artifact;
- no useful action remains;
- a maximum turn, time, token, or spend budget is reached;
- a policy blocks further progress;
- repeated failures trigger escalation; or
- a person cancels the run.

“Keep trying” without bounded stopping behavior is a reliability and denial-of-wallet risk.

## Why agents are difficult

Errors compound over a trajectory. A slightly wrong plan can select the wrong tool; a weak tool result can corrupt the next decision; retries can duplicate side effects; and a polished final answer can hide an unsuccessful task.

This is why an agent must be evaluated as a system:

- Did it achieve the real-world outcome?
- Were the chosen tools and arguments correct?
- Did it comply with policy?
- Were side effects authorized and consistent?
- Could an operator understand and reproduce the trajectory?
- Did it stay within latency and cost limits?

Continue with [Agentic workflows](agentic-workflows.md), [Architecture patterns](architecture-patterns.md), and [Evaluation and security](evaluation-and-security.md).

## Sources

- [OpenAI — A Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OpenAI Agents SDK documentation](https://openai.github.io/openai-agents-python/)
- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic — Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [ReAct](https://arxiv.org/abs/2210.03629)
- [Reflexion](https://arxiv.org/abs/2303.11366)
- [MemGPT](https://arxiv.org/abs/2310.08560)
