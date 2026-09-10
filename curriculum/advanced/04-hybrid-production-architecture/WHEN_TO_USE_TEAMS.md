# Deep Dive: When to Use Teams (and When Not To)

A team is an execution architecture, not a maturity badge. It adds model calls, context boundaries, orchestration states, failure modes, and observability work. Those costs are justified only by a measured benefit.

## Reasons a team may earn its overhead

- **Parallel specialization:** observability, deployment, and customer-impact evidence can be gathered concurrently.
- **Capability isolation:** workers receive different least-privilege tool sets.
- **Modality or model specialization:** one worker may handle vision while another uses code or retrieval.
- **Fault isolation:** a specialist can fail without corrupting every artifact.
- **Workspace, organization, or data isolation:** policy requires separate execution boundaries.
- **Context isolation:** narrow workers avoid placing unrelated sensitive context in one prompt.

Adversarial review is one useful pattern, but it is not the only reason. Conversely, naming five roles does not prove five agents are needed.

## Pipeline or team?

A known producer → independent reviewer → deterministic gate dependency is a pipeline. Use a team when more than one evidence gap can be pursued dynamically or in parallel and the coordination policy cannot be represented more simply.

Prefer typed artifacts feeding synthesis or review. Open-ended debate is rarely the default: it is harder to bound, evaluate, and terminate.

## Measure the same workload

Compare direct, workflow, single-agent, and team candidates on identical inputs and evidence. Report successful, grounded, policy-compliant completion; actual cost and cost per successful compliant request; wall-clock latency and accumulated work; model/tool calls and privileged exposure; recovery; and operational complexity.

There is no universal “team tax” number. Measure your providers, tools, prompts, workloads, and concurrency limits. A team that lowers wall time may still consume much more total work.

## Application ownership remains

Manager, selector, crew, or group-chat frameworks coordinate execution. The application still owns eligibility, authorization, budgets, artifact validation, architecture transitions, termination policy, and completion. A framework-selected speaker or tool is a candidate decision that must pass the same contract checks as the credential-free core.
