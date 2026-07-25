# Agentic workflows

An agentic workflow mixes deterministic software control with selected model-directed decisions. It is often the most practical production design: the system gains flexibility where judgment is valuable while keeping critical sequencing, validation, and side effects explicit.

## Workflow versus agent

Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) uses this distinction:

- **Workflow:** models and tools are orchestrated through predefined code paths.
- **Agent:** the model dynamically directs its own process and tool use.

This is a control distinction, not a quality ranking. A fixed workflow may be more reliable, fast, and auditable. An agent may handle paths the developer could not enumerate. Many useful systems sit between them.

## A control-spectrum view

| Design | Who chooses the next step? | Example |
| --- | --- | --- |
| Single call | Application | Classify one ticket |
| Prompt chain | Application | Extract → validate → draft |
| Routed workflow | Model chooses among code-defined routes | Send billing, technical, or sales request to a specialist |
| Graph workflow | Application and model share control | Fixed approval nodes around flexible investigation |
| Single agent | Model, within runtime limits | Research until sufficient evidence is collected |
| Multi-agent system | Orchestrator and specialists | Lead agent delegates parallel research and synthesizes |

The best starting point is the least flexible design that can meet the task's success rate on representative cases.

## Where model judgment helps

Use a model-directed decision when the correct path depends on semantic or incomplete information:

- classify intent from free-form language;
- choose a relevant tool from a bounded set;
- decompose an unfamiliar goal;
- decide whether evidence is sufficient;
- repair an approach after an unexpected observation;
- synthesize heterogeneous specialist outputs; or
- decide which issue needs human review.

Keep control in code when the condition is crisp:

- permissions and identity;
- schema and argument validation;
- budgets and rate limits;
- transactional writes;
- required approval;
- retry limits;
- invariant business rules; and
- stop conditions.

## Build the workflow around contracts

Each node should have an explicit contract:

```text
Node:
  purpose: Verify that a proposed refund follows policy
  input: RefundRequest + CustomerContext
  output: Approved | Rejected(reason) | NeedsHuman(reason)
  tools: read_order, read_refund_policy
  side_effects: none
  timeout: 20 seconds
  retries: 1
```

Structured contracts make nodes independently testable and prevent “agent” from becoming a label for an opaque prompt.

## State machines and graphs

A graph runtime represents work as nodes connected by transitions. State persists between nodes, making branching, interruption, replay, and recovery explicit. [LangGraph](https://langchain-ai.github.io/langgraph/) is a prominent open-source example; its documentation emphasizes durable execution, persistence, streaming, and human-in-the-loop control.

State should contain facts and artifacts, not an unbounded transcript:

- task identifier and owner;
- current phase and completed steps;
- normalized inputs;
- tool observations with provenance;
- generated artifacts and validation results;
- pending approvals;
- remaining budgets; and
- error and retry history.

## Human-in-the-loop is a workflow boundary

Human review is strongest when it is a defined transition:

1. The agent prepares a proposed action and concise evidence.
2. The runtime pauses and checkpoints state.
3. The reviewer sees the exact operation, arguments, expected effect, and alternatives.
4. The reviewer approves, edits, rejects, or redirects.
5. The runtime records the decision and resumes from the checkpoint.

A generic “Approve?” button without the action's consequences encourages approval fatigue. Ask for approval at the boundary of consequence—before sending, purchasing, deleting, publishing, changing access, or executing untrusted code.

## Reliability patterns

### Validate between probabilistic steps

Use deterministic checks wherever possible:

- parse structured output against a schema;
- verify cited records exist;
- run tests or a compiler;
- check a proposed query is read-only;
- compare totals before and after a transaction; and
- verify an artifact satisfies required fields.

### Make retries safe

Retries must distinguish failed inference from uncertain side effects. A network timeout after `create_payment` does not prove the payment failed.

Use:

- idempotency keys;
- operation identifiers;
- read-after-write verification;
- capped exponential backoff;
- compensating operations; and
- reconciliation jobs.

### Design resumability

Long-running workflows should checkpoint after meaningful actions. On restart, restore state and continue from the next safe transition rather than replaying every side effect.

### Use typed failure states

Do not hide every failure in natural language. Represent conditions such as:

- `ToolUnavailable`
- `PermissionDenied`
- `InvalidArguments`
- `BudgetExceeded`
- `ApprovalRejected`
- `NeedsHuman`
- `ValidationFailed`
- `PartialSuccess`

The workflow can then route each failure deliberately.

## Event-driven workflows

Business processes often wait for external events: a person approves, a payment settles, a document arrives, or a service returns later. Do not keep an inference loop alive while waiting. Persist state, subscribe to the event, and resume when it arrives.

This separates orchestration time from model inference time and makes days-long processes practical.

## When to introduce multiple agents

Multiple agents help when:

- subtasks can run independently in parallel;
- specialists need distinct tools, policies, or context;
- one context window would become noisy;
- an orchestrator can state clear delegation contracts; and
- evaluation shows the quality gain exceeds coordination cost.

They do not automatically improve a hard task. Every handoff introduces another prompt, context boundary, failure mode, latency component, and cost. Anthropic's [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) describes both the benefits of parallel exploration and the engineering difficulty of delegation and synthesis.

## Adoption ladder

1. **One model call** with structured output.
2. **Deterministic workflow** with validators.
3. **Tool-using workflow** with bounded model choices.
4. **Single agent** for an open-ended subproblem.
5. **Human approval** for consequential actions.
6. **Multiple agents** only for measured specialization or parallelism.

At every rung, keep the previous design as a baseline. If the more agentic system does not materially improve task success, the added complexity is not paying for itself.

## Sources

- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic — Building a multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [OpenAI — A Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OpenAI Agents SDK — Running agents](https://openai.github.io/openai-agents-python/running_agents/)
- [LangGraph documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph durable execution](https://langchain-ai.github.io/langgraph/concepts/durable_execution/)
