# Deep Dive: Skills, Tools, MCP, IAM, and Workflows

These concepts compose, but none substitutes for the others.

| Layer | Responsibility | Does not automatically provide |
| --- | --- | --- |
| Skill | Reusable procedure and contract | Identity, permission, credentials, transport, durable execution |
| Tool | Typed operation and result | Multi-step procedure, user intent, authorization policy |
| MCP | Protocol for exchanging context and invoking exposed capabilities | Application IAM, package trust, safe business semantics |
| IAM/policy | Authenticated identity, grants, tenant/subject/purpose constraints | Good routing or procedural knowledge |
| Workflow runtime | State, scheduling, checkpoints, retries, cancellation, reconciliation | Package trust or operation authorization |

An MCP server may enforce authorization as part of an application's deployment, but
MCP itself is not “the authorization layer.” The current [MCP authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
defines protocol mechanisms; the application still owns identity mapping, delegated
scope, tenant/subject/purpose policy, tool governance, and point-of-use decisions.

## Example boundary

An incident-analysis skill may recommend these steps:

1. read current metrics;
2. search logs if the optional capability is available;
3. validate citations;
4. propose a feature-flag rollback.

The metrics and log operations might be local functions, REST calls, MCP tools, or
queue jobs. The skill's procedure does not depend on that transport. At activation the
application grants only the intersection of requested, principal, tenant, and currently
available capabilities. Before every call, the relevant runtime revalidates current
authority and budgets.

The rollback remains a proposal. A tool description, skill instruction, retrieved
document, or token such as `APPROVED` cannot authorize it. The application validates an
exact approval and target state, then invokes the write through its governed execution
boundary.

## Failure patterns

- **“The skill lists the tool, so it is allowed.”** Requested capability is metadata.
- **“The MCP server will handle all security.”** The host still owns trust and policy.
- **“MCP tools are stateless; skills are stateful.”** State is orthogonal to both.
- **“Every skill uses MCP.”** A skill may call local code or no tools at all.
- **“A skill is a workflow engine.”** Durable orchestration needs explicit state and
  recovery machinery outside prompt instructions.
- **“The child skill needs more permission, so union the sets.”** Composition preserves
  least authority; missing required scope denies activation.
- **“The result says success.”** Completion depends on application-verified
  postconditions and evidence.

## Cross-course handoff

- Advanced 10 supplies durable checkpoints, retries, cancellation, idempotency, and
  reconciliation.
- Advanced 13 supplies governed MCP discovery and point-of-use tool execution.
- Advanced 14 supplies package trust, skill eligibility/routing, activation receipts,
  progressive disclosure, composition, and skill-specific evaluation.

This separation lets teams change a package format, ranker, SDK, transport, or workflow
engine without moving the authority boundary into model-generated text.
