# Agent architecture patterns

Agent architecture is the allocation of control: which decisions belong to application code, a model, a specialist, a validator, or a person.

The patterns below draw primarily from Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), OpenAI's [Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/), and the [ReAct paper](https://arxiv.org/abs/2210.03629).

## 1. Augmented model call

Give one model call carefully selected capabilities such as retrieval, tools, or memory.

```text
request → model + context/tools → structured result → validation
```

**Use when:** one decision or generation step is sufficient.

**Strengths:** low latency, simple traces, easy evaluation.

**Failure modes:** overloading the prompt, exposing too many tools, or mistaking one tool call for a robust end-to-end process.

## 2. Prompt chaining

Break a task into a fixed sequence. Each step consumes the previous step's output.

```text
extract → validate → transform → validate → publish
```

**Use when:** the decomposition is stable and an intermediate representation improves reliability.

**Example:** extract requirements, generate a draft, check required sections, then format.

**Failure modes:** early errors propagate; latency grows with every call.

**Controls:** validate between steps and stop immediately when a contract fails.

## 3. Routing

Classify an input and send it to a specialized path.

```text
input → router ─┬→ billing workflow
                ├→ technical workflow
                └→ human review
```

**Use when:** categories need different prompts, tools, models, or policies.

**Failure modes:** ambiguous requests, silent misroutes, and category drift.

**Controls:** include an unknown/escalate route, log confidence and rationale, and evaluate the router separately.

## 4. Parallelization

Run independent tasks simultaneously, then combine the results.

Two common forms:

- **Sectioning:** split work into independent pieces.
- **Voting or perspectives:** ask multiple workers to evaluate the same input differently.

**Use when:** subtasks do not depend on each other's outputs or diverse judgments improve robustness.

**Failure modes:** redundant cost, inconsistent assumptions, merge conflicts, and a weak aggregator.

**Controls:** give workers non-overlapping contracts and make the aggregation rule explicit.

## 5. Orchestrator-worker

An orchestrator dynamically decomposes a goal, delegates subtasks, and synthesizes worker results.

```text
goal → orchestrator → worker A ─┐
                    → worker B ─┼→ synthesis → validation
                    → worker C ─┘
```

**Use when:** the number or nature of subtasks cannot be known in advance.

**Example:** research a market by delegating company, regulation, technical, and competitive-analysis threads.

**Failure modes:** vague delegation, duplicated work, missing context, unverifiable synthesis, and runaway fan-out.

**Controls:** delegation schemas, worker budgets, provenance on every result, maximum breadth/depth, and a deterministic completeness check.

OpenAI's Agents SDK supports both [agents as tools](https://openai.github.io/openai-agents-python/tools/#agents-as-tools) and [handoffs](https://openai.github.io/openai-agents-python/handoffs/). Use an agent as a tool when the orchestrator should retain ownership; use a handoff when the specialist should take over the interaction.

## 6. Evaluator-optimizer

One model creates an output while another evaluates it against explicit criteria. Feedback drives a bounded revision loop.

```text
generate → evaluate ─ accepted → finish
              │
              └ feedback → revise → evaluate
```

**Use when:** success criteria are clear, feedback is actionable, and refinement produces measurable improvement.

**Examples:** code with tests, writing against a rubric, or SQL checked against constraints.

**Failure modes:** evaluator bias, mutually reinforcing errors, and endless polishing.

**Controls:** deterministic graders where possible, a maximum iteration count, and a rule for escalation when revisions stop improving.

## 7. ReAct tool loop

The model alternates reasoning, an action, and an observation until it answers or reaches a stop condition.

```text
goal → decide → tool call → observation ┐
          ↑                             │
          └──────── update state ───────┘
```

The [ReAct paper](https://arxiv.org/abs/2210.03629) showed how actions can ground reasoning in an external environment and observations can update the plan.

**Use when:** the next step genuinely depends on tool feedback.

**Failure modes:** loops, wrong tools, malformed arguments, premature answers, and accidental side effects.

**Controls:** small tool set, typed schemas, policy checks, turn and spend limits, tool-result validation, and stop/escalation rules.

## 8. Planner-executor

A planner produces a task graph or ordered plan; an executor performs steps and reports state back for replanning.

**Use when:** a long-horizon task benefits from an explicit plan that operators can inspect.

**Failure modes:** plans become stale after new observations, or planning consumes tokens without improving execution.

**Controls:** plan validation, dependencies, status for each step, and replan triggers instead of unconditional replanning.

## 9. Human approval

Insert a checkpoint before a consequential action.

**Use when:** a mistake could create legal, financial, privacy, security, reputational, or irreversible impact.

The approval payload should show:

- the exact proposed action;
- target and scope;
- relevant evidence;
- expected effect;
- risk or uncertainty;
- whether it can be undone; and
- alternatives.

**Failure modes:** approval fatigue, vague summaries, or asking after the side effect has already occurred.

## 10. Multi-agent conversation

Specialists exchange messages or take turns under a collaboration protocol.

**Use when:** role separation and iterative cross-review are themselves useful.

**Failure modes:** circular discussion, shared misconceptions, context growth, unclear ownership, and no objective stopping rule.

**Controls:** a coordinator, message schemas, role-specific tools, a shared artifact rather than full transcript duplication, and a deterministic termination policy.

## Choosing a pattern

Ask these questions in order:

1. Can one structured model call solve the task?
2. Is the sequence known? Use a workflow.
3. Is only one bounded decision uncertain? Insert routing or a tool-selection node.
4. Are subtasks independent? Parallelize.
5. Is decomposition unknown? Add an orchestrator.
6. Can quality be graded? Add evaluator-optimizer.
7. Must the next step depend on environment feedback? Use an agent loop.
8. Can actions create material consequences? Add approval and compensation.
9. Does specialization measurably improve success enough to pay for coordination? Consider multiple agents.

## Pattern evaluation

Compare patterns on the same task set:

| Dimension | Example metric |
| --- | --- |
| Task result | Exact success rate or executable validator |
| Policy | Violation and unauthorized-action rate |
| Efficiency | Median and tail latency, tokens, tool calls, cost |
| Robustness | Success under tool errors, ambiguity, and adversarial input |
| Recovery | Rate of safe recovery from injected failures |
| Operability | Trace completeness and human-debug time |

Architecture decisions should follow evidence from these measurements.

## Sources

- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI — A Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [ReAct](https://arxiv.org/abs/2210.03629)
- [LangGraph workflows and agents](https://langchain-ai.github.io/langgraph/tutorials/workflows/)
