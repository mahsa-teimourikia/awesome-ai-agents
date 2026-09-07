# Agents, tasks, artifacts, and policy

CrewAI separates agent configuration from task configuration. A production application needs two more explicit concepts: validated artifacts and authority policy.

## Agent: bounded worker configuration

An agent's role, goal, and backstory steer behavior. Its visible tools reduce the model's action surface. None of those fields proves that the current identity may access a tenant, source, or action.

The Course 03 workers have narrow concerns:

- observability reads health and logs;
- deployment reads deploy metadata and the runbook;
- customer impact reads tenant-scoped aggregates;
- the incident analyst synthesizes accepted artifacts;
- the reviewer checks coverage and grounding.

The application-owned `CapabilityPolicy` separately grants capabilities for one tenant. Authorization is re-checked when a task executes. A model cannot add authority by editing its persona or naming a tool.

## Task: work contract

A task contract answers:

1. What stable work identity is this?
2. What objective and artifact type are expected?
3. Which typed inputs and predecessor tasks are required?
4. Which capabilities may this task exercise?
5. How many attempts, how much time, and how much estimated cost are admitted?

CrewAI `expected_output` is a human-readable description. It does not perform schema enforcement. `output_pydantic` or `output_json` requests structured conversion. The application must still validate the result.

Task position is scheduling information, not identity. Retries preserve the logical execution ID and use a unique attempt ID. That prevents a timeout retry from becoming an accidental new logical operation.

## Artifact: validated result

An envelope binds payload to task, producer, tenant, evidence records, source references, policy version, time, and content hash. Downstream tasks consume projections of accepted artifacts rather than an entire transcript.

Validation covers two different layers:

- structural validity: schema, enum values, required fields;
- trust validity: expected producer/task/tenant, known evidence, verified source/hash, active policy, allowed capability, supported claims.

Typed artifact does not equal trusted artifact. A perfectly valid object can cite an invented evidence ID or carry a diagnosis that none of its cited facts supports. Citation existence, envelope membership, and tenant are checked before support; support is computed only from the evidence records that each claim actually cites, never from unrelated facts elsewhere in the envelope.

Accepted artifacts are immutable. Correction creates a derived artifact with a new identity and hash, preserving the audit chain.

## Policy: authority

Policy owns the answers that model text cannot provide:

- Is this worker allowed for this task?
- Can it access this tenant and source?
- Is the proposed capability read-only and in scope?
- Is the artifact grounded and current?
- May a manager add this specific fallback task?
- Has the run exhausted cost, call, retry, depth, or deadline budgets?
- Does application state satisfy completion?

Tools still enforce real authentication and tenant isolation outside CrewAI. Application policy is necessary orchestration control; it is not a substitute for service-side authorization.

## Context projection

The fixture compares forwarding a broad context object with forwarding only the fields needed by a task. Projection reduces approximate tokens and removes operator email, session material, and injected conversation text while preserving deterministic fixture success.

This is not merely a cost optimization. Smaller context limits accidental disclosure and makes the evidence contract easier to review.

## Review is not execution approval

The reviewer can produce `REVIEW_PASS` when the brief is complete and grounded. That state permits course completion. It does not authorize a rollback. Production execution requires both `REVIEW_PASS` and independently validated approval; either missing boundary blocks the action. A consequential write must also cross the idempotent execution boundary described in earlier courses.

References: official CrewAI [Agents](https://docs.crewai.com/en/concepts/agents) and [Tasks](https://docs.crewai.com/en/concepts/tasks) documentation. Adapter behavior is tested with CrewAI `1.15.20`.
