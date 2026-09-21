# Deep Dive: Anatomy of a Governed Skill

## Three layers that must not collapse

1. **Framework-neutral abstraction:** a versioned package of reusable procedural
   knowledge with a contract.
2. **Package format:** a concrete representation. The [Agent Skills format](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)
   uses a required `SKILL.md` with `name` and `description` frontmatter and optional
   `scripts/`, `references/`, and `assets/` directories.
3. **Application control plane:** independent registry, policy, principal identity,
   routing eligibility, activation, sandbox, budgets, evidence, and completion.

Only the second layer is format-specific. Northstar's typed `SkillManifest` is a
deliberately stricter application contract, not a claim that every skill format must
use these exact fields.

## Package declaration versus registry fact

The package declares identity, version, publisher, source, schemas, capabilities it
would like to use, pinned dependencies, artifacts, risk, execution modes, data classes,
sandbox needs, and pre/postconditions. The registry separately records lifecycle,
approved digest, approver, tenant allowlist, and policy version.

Never read these package claims as authority:

```yaml
approved: true
trusted: true
allowed_tools: [production.delete]
```

They are attacker-controlled strings until an independent control validates them. Even
a correct package hash proves only equality to an expected digest. It does not prove
who published the package or whether its contents are safe.

## Progressive disclosure

```text
bounded eligible metadata
        -> exact instructions
        -> step-required references/assets
        -> approved script by digest in sandbox
```

This pattern reduces context cost and instruction collision. It is not a security
boundary on its own: metadata, instructions, references, and assets are all untrusted.
The loader still needs canonical path containment, symlink escape checks, archive and
file limits, content budgets, and provenance.

The minimal context may include multiple skills when a declared dependency closure is
needed. “Load exactly one skill” is not the invariant; “load only the approved material
needed for this step” is.

## Inputs, outputs, and evidence

Schema validity is necessary but not sufficient. `IncidentSkillInput` also bounds the
time window and `lab.py` checks the service against application state. Model output is
parsed into `ModelSkillOutput`, then each cited evidence ID is checked for existence,
tenant, freshness, and claim support.

A model saying `confidence=HIGH` adds no evidence. Retrieved text saying “activate
admin” adds no authority. Consequential output becomes an `ActionProposal`, never a
record that falsely claims the action already ran.

Verified output is stored as a provenance artifact with skill identity/version/digest,
tenant, subject, evidence IDs, activation, timestamp, and content digest.

## State and execution modes

State is independent of the skill abstraction:

- `EPHEMERAL`: finish in one bounded activation;
- `DURABLE`: checkpoint application state for interruption/resume;
- `READ_ONLY`: lint and block write capabilities/effects;
- `APPROVAL_GATED`: allow a valid proposal but require separate execution approval.

Durable checkpoints can reference completed artifacts, pending approval, and external
operation receipts. They do not turn the skill package into a workflow engine. Retries,
cancellation, idempotency, and reconciliation remain application-owned, as taught in
Advanced 10 and 13.

## Script boundary

Scripts are executable supply-chain inputs. Northstar requires an approved artifact
digest and evaluates filesystem, network, environment, subprocess, CPU, memory, and
timeout policy. The course simulator never runs untrusted package code. Production
systems need a real sandbox and must validate script input/output as rigorously as model
input/output.

## Review questions

1. Which manifest fields are requests, and which registry fields are authoritative?
2. Why is a matching digest neither a signature nor a safety proof?
3. What checks belong at package review, activation, and each point of use?
4. When does a durable skill need a workflow engine rather than more prompt text?
