# Evaluation and security for AI agents

Agent evaluation asks more than “was the final text good?” An agent creates a trajectory through tools and environments, may cause side effects, and can fail while still producing a confident explanation.

Security and evaluation therefore belong in the same engineering loop: define permitted behavior, test it under realistic and adversarial conditions, inspect traces, and enforce the controls in code.

## Build a task suite

Start with representative tasks, not generic prompts. Each task should define:

- initial state and user identity;
- available tools and permissions;
- expected outcome or acceptable outcome set;
- prohibited actions;
- required evidence or artifacts;
- approval points;
- time, turn, token, and cost budgets; and
- a deterministic reset or isolated environment.

Include:

- common tasks;
- difficult but legitimate tasks;
- ambiguous requests;
- missing-information cases;
- unavailable and partially failing tools;
- permission boundaries;
- requests that should be refused or escalated;
- injected instructions in documents, websites, and tool output; and
- duplicate, interrupted, and resumed operations.

Anthropic's [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) explains the relationship between tasks, trials, graders, transcripts, and evaluation harnesses.

## Grade three layers

### 1. Outcome

Did the environment reach an acceptable final state?

Prefer executable checks:

- expected database record exists;
- tests pass;
- the correct file was created;
- the ticket status changed once;
- the answer contains claims supported by named evidence; or
- no state changed when the request lacked permission.

For coding agents, [SWE-bench](https://www.swebench.com/) applies a proposed patch and runs tests. This is stronger than grading whether a response merely sounds like a fix.

### 2. Trajectory

Was the route to the outcome acceptable?

Measure:

- tool selection and argument correctness;
- grounding in tool observations;
- unnecessary or repeated calls;
- error recovery;
- adherence to required approvals;
- delegation quality;
- sensitive-data exposure; and
- whether the agent stopped for the correct reason.

Trajectory graders diagnose *why* outcome success changed. Avoid requiring one exact trajectory when multiple safe paths are valid.

### 3. Operations

Can the system run within its service envelope?

Track:

- end-to-end and per-step latency;
- model tokens and cost;
- tool count and tool latency;
- loop length;
- failure and retry rate;
- escalation and approval rate;
- side-effect reconciliation failures; and
- trace completeness.

Report distributions and tail behavior, not only averages.

## Grader types

Use the strongest affordable evidence:

1. **Environment or executable grader** — query state, run tests, compare artifacts.
2. **Rule-based grader** — schemas, invariants, exact fields, policy assertions.
3. **Reference-based model grader** — compare against a rubric and evidence.
4. **Reference-free model grader** — useful for qualities such as clarity, but calibrate against people.
5. **Human review** — best for high-stakes ambiguity and grader calibration, but expensive.

Model graders need versioning, blind examples, clear rubrics, adversarial calibration, and periodic comparison with expert judgments.

## Metrics

Do not compress every concern into one number.

| Category | Metrics |
| --- | --- |
| Outcome | pass rate, partial success, exact artifact validity |
| Tools | correct tool, argument accuracy, invalid-call rate, no-tool precision |
| Safety | policy violations, unauthorized attempts, harmful side effects |
| Reliability | retry recovery, resume success, duplicate-action rate |
| Efficiency | latency, turns, tool calls, model tokens, dollar cost |
| Human factors | escalation precision, approval burden, operator correction time |

[BFCL](https://gorilla.cs.berkeley.edu/leaderboard) is useful for tool-call correctness and relevance detection. [AgentBench](https://github.com/THUDM/AgentBench), [WebArena](https://webarena.dev/), [OSWorld](https://os-world.github.io/), and [GAIA](https://huggingface.co/gaia-benchmark) cover different interactive and real-world capabilities. Use them as external references, then build an in-domain task set.

## Trace design

A useful trace records:

- run, task, user, tenant, and version identifiers;
- redacted model input and output;
- available tool definitions and policy version;
- proposed and validated tool arguments;
- tool result, latency, error, and side-effect identifier;
- handoffs and agent ownership;
- approvals and reviewer decision;
- state checkpoints;
- budget consumption; and
- final termination reason and grader results.

The [OpenAI Agents SDK tracing documentation](https://openai.github.io/openai-agents-python/tracing/) describes traces and spans for generations, tool calls, handoffs, and guardrails. Do not log secrets or sensitive content merely to gain observability; apply redaction and retention policy.

## Threat model

OWASP's [Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) organizes risk around agent-specific surfaces. Threat-model at least:

### Instructions and observations

Untrusted pages, files, messages, and tool output may contain instructions designed to redirect the model. Keep trusted policy separate, label provenance, minimize retrieved content, and test indirect prompt injection.

### Tools and privileges

A correct-looking tool call may still be unauthorized. Authenticate the user and agent, authorize every operation at execution time, use least privilege and short-lived credentials, and distinguish read from write capabilities.

### Memory

Attackers may poison memory so future runs inherit false facts or instructions. Validate writes, store provenance, isolate tenants, apply retention, and allow review and deletion.

### Identity

An agent acting “for the user” needs a concrete delegated identity and scope. Do not put broad service credentials in a prompt or sandbox. Preserve the initiating principal through every downstream tool.

### Multi-agent messages

Another agent is not automatically trusted. Authenticate peers, validate messages and artifacts, restrict delegated authority, and prevent a worker from expanding its own permissions.

### Code and environment

Generated code and browser actions operate on adversarial input. Use isolated sandboxes, restricted network and filesystem access, secret brokers, resource limits, and disposable environments.

### Availability and cost

Loops, recursive delegation, oversized observations, and repeated failures can exhaust budgets. Bound depth, breadth, turns, time, tokens, tool calls, and spend.

## Permission model

Apply permissions in layers:

1. **User authorization:** may this person request the operation?
2. **Agent role:** is this agent allowed to use the tool?
3. **Run delegation:** was the capability delegated for this task and duration?
4. **Resource authorization:** may it affect this exact account, file, record, or environment?
5. **Argument policy:** are amount, destination, domain, command, or scope allowed?
6. **Approval:** does the risk class require a person to confirm?

Prompts may describe these rules, but the tool gateway must enforce them.

## Side-effect safety

For write operations:

- generate and validate a preview;
- use idempotency keys;
- attach the initiating identity and run ID;
- persist a receipt;
- verify the resulting state;
- compensate or escalate on partial failure; and
- avoid automatic retries when the prior outcome is uncertain.

High-impact actions should be deny-by-default when the runtime cannot determine authorization or resulting state.

## Release gates

Before release:

- [ ] Task suite covers common, boundary, failure, and adversarial cases.
- [ ] Outcome graders verify real environment state.
- [ ] Every tool enforces schema and authorization.
- [ ] Read and write tools have distinct risk policies.
- [ ] Consequential actions pause for informed approval.
- [ ] Loops and delegation have hard budgets.
- [ ] Sandboxes restrict code, browser, file, process, and network access.
- [ ] Memory is scoped, auditable, and deletable.
- [ ] Traces support incident reconstruction without leaking secrets.
- [ ] Retries and resumes cannot silently duplicate writes.
- [ ] Regression thresholds block unsafe releases.
- [ ] Operators have a kill switch and a documented escalation path.

## Continuous evaluation

1. Sample and redact production traces.
2. Cluster failures by outcome and trajectory.
3. Add representative failures to the regression set.
4. Fix the narrowest responsible layer: tool, policy, workflow, prompt, model, or data.
5. Run the full task and adversarial suites.
6. Compare quality, safety, latency, and cost to the current production baseline.
7. Release gradually and monitor for distribution shift.

Evaluate the complete system whenever a model, prompt, tool schema, permission policy, retrieval source, workflow, or runtime changes.

## Sources

- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [OWASP — Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
- [OWASP — Securing Agentic Applications Guide](https://genai.owasp.org/resource/securing-agentic-applications-guide-1-0/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [MITRE ATLAS](https://atlas.mitre.org/)
- [OpenAI Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/)
- [SWE-bench](https://www.swebench.com/)
- [BFCL](https://gorilla.cs.berkeley.edu/leaderboard)
