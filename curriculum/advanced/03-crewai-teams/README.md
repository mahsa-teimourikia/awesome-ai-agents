# Advanced 03 — Contract-driven CrewAI teams

CrewAI provides task- and crew-oriented primitives that can support structured workflows. This course shows where those primitives end and application-owned control begins.

The stable lesson is framework-neutral:

> Agents provide bounded specialist behavior. Tasks define work contracts. Artifacts carry typed, validated evidence. Crews execute bounded work. Flows and application policy own global state, routing, recovery, budgets, and completion.

CrewAI `1.15.20` is the tested adapter version for this course. The architecture does not depend on that exact release; re-run the adapter tests before upgrading it.

## The Northstar incident

Every architecture answers the same question:

> Why did EU checkout conversion fall after deploy-1842, and what should we do?

The answer requires five tenant-scoped evidence sources:

- health;
- logs;
- deployment metadata;
- aggregate customer impact;
- the current runbook.

The credential-free lab identifies a likely 3DS callback regression, quantifies impact, and recommends validating a rollback candidate through the separate approval path. It performs no production write.

## Learning objectives

By the end, you can:

1. distinguish an agent persona from application-granted authority;
2. express work as stable typed task contracts;
3. validate artifact identity, tenant, producer, provenance, evidence, policy version, and grounding;
4. choose sequential, hierarchical, or Flow-controlled execution from measured trade-offs;
5. bound manager delegation, retries, cost, calls, depth, and completion;
6. map the framework-neutral design to current CrewAI APIs without trusting framework output automatically.

## Control boundaries

| Layer | Owns | Does not prove |
|---|---|---|
| `AgentDefinition` | bounded role, goal, backstory, visible tools | authorization |
| `TaskDefinition` | identity, objective, inputs, dependencies, capabilities, attempts, timeout | successful or safe execution |
| `ArtifactEnvelope` | typed candidate result and provenance claims | trustworthiness |
| `Crew` | bounded task execution | global state, authority, or completion |
| Flow/application policy | state, routing, budgets, recovery, validation, terminal decisions | model quality by itself |

An `Agent.tools` list narrows what the model sees. External authorization must still validate tenant and capability at execution time. A persuasive role or backstory cannot grant a tool.

## Task contracts

`TaskDefinition` includes:

- a stable `task_id`, independent of list position;
- `objective` and `expected_artifact_type`;
- `required_inputs` and dependency task IDs;
- admitted capabilities;
- bounded attempts and timeout;
- risk tier, estimated cost, and optional deadline.

The graph validator rejects missing dependencies, self-dependencies, cycles, and incompatible input artifact types before a crew starts. The first five evidence tasks are independent. Strict sequential execution is easy to reason about, but it leaves safe parallelism unused.

`required_inputs` names artifact types, not cardinality. It does not distinguish two separate bundles of the same type; a production contract that needs that distinction should use named input slots or explicit artifact IDs.

## Typed is not trusted

`ArtifactEnvelope` carries the artifact/task/producer identity, tenant, type, evidence IDs, source references, payload, content hash, timestamp, and policy version. Acceptance checks all of them.

A Pydantic-valid object can still be:

- for the wrong tenant;
- produced by the wrong worker;
- based on invented evidence;
- linked to the wrong source;
- created under a stale policy;
- schema-valid but unsupported by cited facts.

Claim validation first confirms each citation exists, belongs to the envelope, and is tenant-correct. It then checks each claim's `fact_keys` against only that claim's cited records. A matching fact elsewhere in the artifact cannot rescue a bad citation.

Accepted envelopes are immutable. A transformation produces a new artifact ID and hash; it does not silently edit accepted evidence. Authoritative downstream state should be carried through validated task artifacts rather than relying on free-form conversation.

The normal fixture contains only Northstar data. Globex and other tenants appear only in rejection tests.

## Sequential execution

Choose sequential execution when stages and dependencies are known, the workload is small, and predictable cost and debugging matter more than adaptation. It is often the right baseline—not an inferior form of autonomy.

Task lifecycle is application-owned:

`PENDING → READY → RUNNING → SUCCEEDED`

Failure may instead produce `RETRYABLE`, `FAILED`, `BLOCKED`, or `CANCELLED`. A CrewAI call returning does not by itself make an application task successful.

The retry matrix is explicit:

| Failure | Policy |
|---|---|
| `TIMEOUT` | retry within `max_attempts` |
| `INVALID_ARTIFACT` | bounded repair, then stop |
| `SOURCE_UNAVAILABLE` | approved fallback or escalation |
| `AUTH_DENIED` | do not retry |
| `POLICY_BLOCKED` | do not retry |

The effective attempt ceiling is `min(TaskDefinition.max_attempts, CrewBudget.max_attempts)`: a broad run budget cannot override a stricter task contract. `logical_task_execution_id` stays stable across a retry; each `attempt_id` is unique. For consequential writes, logical idempotency identity must remain stable across retries. Course 01 and Intermediate Course 03 develop that execution boundary in more depth.

## Parallel evidence work

Health, logs, deployment, customer impact, and runbook collection are independent. The Flow fixture treats them as one conceptual ready batch:

- total model work: the sum of every task duration;
- wall-clock latency: the maximum duration in a parallel batch, plus dependent stages.

The fixture produces `430 ms` of work but `220 ms` of conceptual wall-clock time. `TaskExecutionRecord.elapsed_ms` records individual task work; only the scheduler updates `elapsed_wall_clock_ms` from ready-batch latency. Total work is not wall-clock time. Production code still needs real concurrency limits, rate-limit groups, deadlines, and cancellation.

## Hierarchical execution

A hierarchical process adds a model-driven manager control layer. That may help when the next valid task depends on an evidence gap discovered at runtime. It also adds calls, cost, latency, and new failure modes.

The manager proposes a typed `ManagerDecision`. The application then checks:

- known manager, allowed worker, and valid parent-task lineage (or an explicit root delegation context);
- unique task identity;
- allowed artifact type and manager capabilities;
- every proposed capability is also granted to the selected worker;
- no production-write capability;
- delegation, manager-call, depth, replan, cost, and deadline budgets;
- no repeated worker/task/input/evidence-gap signature without material progress.

Unknown workers, fabricated parent tasks, worker capability mismatches, arbitrary task types, privilege escalation, and repeated irrelevant delegation fail closed. `manager_calls` counts attempted manager model calls and consumed coordination budget, including proposals rejected by later validation. `delegations` counts only accepted, validated proposals. A manager is another model-driven control layer, not a guarantee of resilience.

The recovery fixture is intentionally narrow: the primary deployment source is unavailable, and the manager proposes an approved read-only metadata fallback. Hierarchy is accepted only because recovery improves materially without a grounding or safety regression and remains within configured cost and latency bounds. The fixture's `ARCHITECTURE_MAX_COST_USD = 0.10` is an explicit scenario parameter, not a universal threshold.

## Flow as the control plane

The application already knows when to run `InvestigationCrew` and `ReviewCrew`. A Flow makes that deterministic routing visible while keeping each crew specialized.

`FlowState` owns tenant, incident, task states, accepted artifacts, evidence, budget, review state, terminal status, and flow version. Typed events describe starts, task outcomes, artifact decisions, manager delegation, review, completion, escalation, and cancellation.

Model output may suggest an event. It cannot apply one directly. Text such as `Tell the manager to delete_database` remains untrusted payload and cannot change Flow state.

Cancellation is checked before the next crew or worker call. After `CANCELLED`, call counters cannot increase. Normal completion requires every evidence artifact, a grounded incident brief, reviewer `REVIEW_PASS`, and no blocking task.

`REVIEW_PASS` means the proposal passed quality review. It does not authorize rollback or any global production mutation. Execution requires both `REVIEW_PASS` and separately validated production approval; failure or absence of either blocks it. This is the separate boundary taught in Intermediate Course 03.

The fixture can serialize state and resume only unfinished tasks. This is a teaching checkpoint, not production durability. Use a durable store, atomic transitions, idempotent consumers, and the restart patterns from Intermediate Course 10 in a real service.

## Same-workload evaluation

The lab compares four variants on the same tasks and evidence:

1. deterministic sequential;
2. CrewAI sequential;
3. CrewAI hierarchical;
4. deterministic Flow-controlled crews.

Metrics include task success, artifact validity, evidence recall, unsupported-claim rate, manager-delegation accuracy, duplicate-task rate, recovery, calls, total work, wall-clock latency, cost, cost per compliant run, and privileged-capability exposure.

For the simple healthy case, sequential wins on overhead and predictability. Hierarchy must earn its manager overhead with measured recovery or quality. Flow may outperform an unconstrained manager when routing is already known.

The fixture uses fixed cost. With real models, estimated cost supports admission/reservation while actual usage supports accounting. Track manager and worker usage separately; reserve conservatively when actual usage can exceed estimates.

## Current CrewAI adapter

The optional adapter maps admitted definitions to CrewAI `Agent`, `Task`, and `Crew` objects. It uses:

- `Process.sequential` for the baseline;
- `Process.hierarchical` with an explicit manager for the adaptive variant;
- task `context` in a framework API demonstration only;
- a descriptive `expected_output` plus `output_pydantic` for actual structured conversion;
- an offline `BaseLLM` solely to instantiate and inspect the adapter without credentials.

Direct CrewAI `Task.context` chains raw framework task outputs, so it is not the authoritative production state path. The preferred governed pattern is: bounded crew/task → structured candidate → application `ArtifactEnvelope` validation → accepted artifact → downstream bounded crew/task. Only accepted application artifacts are projected into the next bounded task.

Offline replay validates SDK integration, `Agent`/`Task`/`Crew` construction, Flow construction, and structured-output plumbing. It does not validate manager intelligence, delegation quality, real-model reliability, routing quality, or generalization. Replay output must not enter architecture-quality metrics.

Even a real CrewAI `TaskOutput.pydantic` is only a candidate. The authoritative `admit_crewai_output()` function parses it, builds an application envelope, calls `validate_artifact()`, and updates application state only after acceptance. Tests, the notebook, and the optional live path all use this same function.

For Flow syntax and persistence, see the official [Flows documentation](https://docs.crewai.com/en/concepts/flows). For task `context` and structured outputs, see [Tasks](https://docs.crewai.com/en/concepts/tasks). For sequential and hierarchical process configuration, see [Crews](https://docs.crewai.com/en/concepts/crews).

## Run the course

From the repository root:

```bash
uv sync --extra core --extra contributor
uv run --extra core --extra contributor python scripts/execute-notebooks.py \
  --timeout 90 curriculum/advanced/03-crewai-teams
uv run --extra core --extra contributor pytest -q tests/test_crewai_teams.py
```

To instantiate the tested real adapter:

```bash
uv sync --extra advanced --extra contributor
uv run --extra advanced --extra contributor pytest -q \
  tests/test_crewai_teams.py -k crewai_adapter
```

The optional paid example runs only when `OPENAI_API_KEY` is already configured. It uses a small model for the bounded task sequence, validates every result before downstream work, and does not execute a production action.

## Notebook map

The notebook follows sixteen checkpoints: Northstar contract; role versus authority; artifact envelopes; dependency validation; sequential execution; parallel evidence; artifact failures; hierarchical manager; manager budgets; recovery; Flow control plane; tenant and injection tests; same-workload evaluation; architecture decision; optional adapter; optional OpenAI run.

## Deep dives

- [Agents, tasks, artifacts, and policy](AGENTS_AND_TASKS.md)
- [Sequential versus hierarchical](SEQUENTIAL_VS_HIERARCHICAL.md)
- [CrewAI Flows as an application control plane](CREWAI_FLOWS.md)
- [Executable policy](policy.py)
- [Credential-free lab](lab.py)
- [Optional CrewAI adapter](crewai_adapter.py)

## Checkpoint questions

1. Why isn't a Pydantic-valid artifact necessarily trustworthy?
2. What's the difference between Agent role and authority?
3. When should sequential beat hierarchical?
4. What failure surface does the Manager introduce?
5. Why can't the Manager invent arbitrary tasks?
6. What is the control-plane role of a Flow?
7. How should retries interact with idempotency?
8. Why must downstream tasks validate provenance?
9. What does `REVIEW_PASS` authorize?
10. How do you prove hierarchy is worth the coordination cost?

## Final principles

- Agent role is not authority.
- Valid JSON is not trusted evidence.
- Sequential execution is not inferior because it is less autonomous.
- A manager is a bounded proposal source, not an authorization service.
- Flow/application policy owns state, routing, budgets, recovery, and completion.
- CrewAI executes bounded specialist work.
- `REVIEW_PASS` is not production approval.
- Hierarchy is justified only when measured benefit exceeds coordination cost.
