# Sequential versus hierarchical execution

Neither process is universally better. Use the smallest architecture that meets measured quality, recovery, safety, cost, and latency requirements.

## Sequential

Sequential execution fits known stages and stable dependencies. It offers predictable call counts, straightforward traces, and a smaller control surface. Its weaknesses are rigidity and missed concurrency when independent tasks are forced into a single order.

In the Northstar graph, five evidence tasks are independent. A literal sequential baseline takes the sum of their durations. A deterministic Flow can dispatch that ready set concurrently, then run synthesis and review after the evidence barrier.

Sequential should usually win the healthy simple case because a manager would add no information. This is a measurable expectation, not a universal reliability claim.

## Hierarchical

CrewAI hierarchical processing adds a manager that allocates or delegates work. It can be useful when evidence gaps are discovered during execution and the correct recovery is not known at design time.

That flexibility creates another failure surface:

- extra model calls, latency, and cost;
- unknown or unsuitable worker selection;
- invented or duplicate tasks;
- capability escalation;
- no-progress delegation loops;
- false completion based on persuasive text.

The manager therefore proposes a typed decision. Application policy validates parent lineage, requires every proposed capability to be granted to the selected worker, and limits workers, artifact types, capabilities, depth, delegations, manager calls, replans, cost, and deadline. `manager_calls` counts attempted calls; `delegations` counts accepted validated proposals. The same worker/task/input/evidence-gap signature cannot recur without material progress.

The manager cannot create `EmergencyRollbackTask`: the core lab is read-only and production-write capabilities are outside its grants.

## Recovery case

The deployment API becomes unavailable. The sequential baseline has no admitted fallback and stops short of completion. The bounded manager proposes the already-approved change-index source for the same deployment metadata. The application validates the proposal, and the hierarchy recovers.

This case justifies hierarchy only for that evaluated distribution. It does not prove the manager is broadly intelligent or safer.

## Quality gate

Accept hierarchy only when quality or recovery improves materially and:

- required-evidence recall and unsupported-claim rate do not regress;
- privileged-capability exposure does not increase;
- cost remains within budget;
- wall-clock latency remains within the SLA.

The bad fixture repeatedly proposes irrelevant work. Its delegation accuracy falls, duplicate rate rises, and it fails the gate.

## Flow comparison

If the application already knows the routing rule, deterministic Flow routing can be clearer and cheaper than asking a manager. The Northstar Flow always runs the investigation crew, validates its artifacts, and then runs the review crew. Autonomy is not itself a quality metric.

CrewAI `Process.sequential` runs tasks in their defined order. `Process.hierarchical` requires a manager model or explicit manager agent. See the official [Crews documentation](https://docs.crewai.com/en/concepts/crews). This course tests the adapter with `1.15.20`; architecture selection remains framework-neutral.
