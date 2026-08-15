# 06 — Trajectory optimization: shortest reliable path

**Level:** Intermediate · **Time:** 60 min · **Prerequisites:** None

**Scenario:** Northstar, a SaaS support team, is integrating this concept into their agentic workflow.

**Notebook:** [`06_trajectory_optimization.ipynb`](06_trajectory_optimization.ipynb) 

Northstar’s EU checkout investigator succeeds in both versions below. One takes
nine steps, repeats search and log calls, costs more, and takes longer. The
other gathers the minimum independent evidence and produces the same supported
recommendation. Optimize the **full trajectory**, never token count in isolation.

![Diagram](https://kroki.io/mermaid/svg/eNo9jtFKxDAQRd_7FcM87-IfKBTKIrjIWtiX0IeQTjEaJjEzcbe4_rtJRV9nzrn3LiFe3KvNCk8vHZwMPrLzM7GCWnnHCfb7e-gN9rHwTDPQZ_s6ghQs49RBvxGDweFKrihB5LACEzVaYwzSqGGjzl84_PlSlsU7X5se8LuDcwNuyBFvcDD4zARvRdQvvsYwXRU-CuW1ZR1-G_-dlaRKo8GxpBSzVsGyXCjDHaQcUxQbmjdu3tHgkayUXCfYhXTd1SnOkcgOgtW6rV5cFMXpB4qJW0w=)

## What you learn

- Diagnose redundant model/tool calls, repeated retrieval, reflection loops,
  poor routing, and unnecessary context.
- Preserve grounding, policy compliance, recovery, and abstention while reducing
  latency and cost.
- Choose sequential versus parallel execution from dependencies and rate limits.
- Set budgets, cache safely, and prevent optimization regressions with evals.

## 1. Define the objective correctly

The shortest run is not automatically best. A one-step answer that invents a
diagnosis is worse than a three-step evidence path. Optimize subject to hard
constraints: safety/policy pass, correct supported outcome, tenant scope, and
recovery behavior. Then compare latency, cost, calls, retries, and trajectory
length. A useful operational metric is **cost per successful compliant task**.

## 2. Step-by-step method

1. Instrument every model call, tool call, retries, cached result, decision,
   latency, token/cost estimate, and policy block.
2. Build a baseline on representative tasks; inspect traces rather than averages.
3. Label each step as required evidence, justified recovery, duplicate,
   speculative reflection, or side effect.
4. Remove duplication, constrain tool choice, cache safe deterministic reads,
   parallelize only independent allowed reads, and replace open-ended reflection
   with an evaluator/threshold.
5. Re-run outcome, trajectory, safety, and operations evals; roll back any
   optimization that harms accuracy, grounding, or safety.

## Experiments

`lab.py` compares the nine-step wasteful trace with a three-step optimized
trace. Add an extra `query_logs` call and observe duplicate cost; remove
`query_logs` and observe that success fails because evidence is insufficient.
Use `choose_parallel` to show why independent reads may run in parallel, while
dependent calls and rate-limited systems must remain sequential.

## Production practices

- Cache only authorization-safe, freshness-bounded results; include tenant,
  policy, and data version in cache keys.
- Give each run step/tool/model budgets and a deadline; spend budget only on a
  defined information gain or recovery condition.
- Batch/parallelize independent reads cautiously; cap fan-out and respect rate
  limits and downstream load.
- Keep high-risk actions out of optimization loops; approval requirements never
  disappear because a trajectory is “efficient.”
- Compare candidate changes to a frozen baseline and canary release gate.

## Watch For

- **Assumption failure:** The model hallucinates an unsupported parameter.
- **State leak:** Context is incorrectly preserved across runs.
- **Timeout:** The tool takes too long and the agent loops.
- **Auth bypass:** The agent attempts an action it shouldn't.

## Checkpoint

**1. What is the primary purpose of this module?**
- A) To understand the core concept.
- B) To write complex boilerplate.
- C) To ignore system errors.
- D) To bypass security.

**2. How do we mitigate the primary failure mode?**
- A) Retries.
- B) Human approval.
- C) Logging.
- D) Idempotency keys.

## References

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)

## Deep Dives & State of the Art

- **[Few-Shot Prompting and DSPy](DEEP_DIVE_FEW_SHOT.md)**


## SOTA Deep Dives
Explore industry-standard architectural patterns and enterprise implementation details:

- [Few Shot](DEEP_DIVE_FEW_SHOT.md)
