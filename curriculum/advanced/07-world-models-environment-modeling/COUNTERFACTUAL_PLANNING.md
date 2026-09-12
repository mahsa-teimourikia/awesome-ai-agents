# Deep Dive: Counterfactual Planning Under Model Error

Scenario planning asks what a model predicts under assumed future conditions. Counterfactual or interventional reasoning asks what would happen under an alternative action and requires meaningful intervention semantics in the transition model. Model predictive control, search, scenario analysis, dynamic programming, Monte Carlo Tree Search, and deterministic fixtures can support planning, but predictive simulation alone is not causal proof.

It is **not synonymous with Tree of Thoughts**. Tree of Thoughts is an LLM inference/search technique over intermediate reasoning candidates. This course uses seeded Monte Carlo scenario analysis over typed environment actions; it does not expose or require private model reasoning.

## Distributions, not arbitrary point scores

For each Northstar action, the lab reports recovery and data-loss probabilities, mean and p10/p50/p90 recovery time, customer and SLA impact, worst-case outcomes, and robustness. Explicit weights turn those components into expected utility.

Utility ranks only feasible actions. Hard constraints independently reject cross-tenant effects, unapproved services, possible data loss, excessive worst-case downtime, low robustness, and invariant violations. A database rollback can therefore have attractive average recovery and still be invalid.

The planning cycle's joint stress test changes traffic and provider latency together. If that plausible stress flips the winner or removes every feasible action, the decision becomes `DECISION_UNSTABLE`; the system should gather better evidence or escalate rather than manufacture certainty. One-at-a-time sensitivity instead varies traffic, provider latency, or database capacity independently so the driver is interpretable.

Most importantly, a winning simulation creates only a proposal for review:

```text
SIMULATION_PASS != APPROVED
```

Allowed proposal actions, execution capability, approval, execution-time model validity, hard constraints, and execution remain separate application-owned controls. A planner can propose rollback without possessing `production.rollback`; the external executor still needs that production capability.

For the distinct Tree of Thoughts method, see Yao et al., [Tree of Thoughts](https://arxiv.org/abs/2305.10601).
