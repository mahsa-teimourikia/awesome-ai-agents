# MCP: Model Context Protocol

**Advanced · 13** · **Time:** 120–150 min · **Prerequisites:** Intermediate 03–05, Advanced 10 and 12

**Notebook:** [`13_mcp_protocol.ipynb`](13_mcp_protocol.ipynb) · **Implementation:** [`policy.py`](policy.py) + [`lab.py`](lab.py)

MCP is an open interoperability protocol for connecting AI applications to external
context and capabilities. It reduces integration fragmentation; it does not establish
trust. An enterprise host still owns identity, authorization, provenance, capability
governance, approval, execution safety, validation, and audit.

## Learning outcomes

By the end, you can:

- distinguish model/agent logic, host, client, server, and backend responsibilities;
- explain modern and legacy MCP lifecycle, transports, capability discovery, and
  tools/resources/prompts without confusing protocol metadata with authority;
- build a trusted server registry, policy-filtered capability snapshots, and
  call-time authorization with tenant, subject, purpose, audience, and scope binding;
- validate tool inputs and outputs, approval-bound effects, idempotent retries,
  unknown outcomes, resources, prompts, budgets, cancellation, and rate limits;
- govern server and capability supply-chain changes, quarantine, and audit integrity;
- evaluate a policy-controlled gateway against a visibility-trusting baseline; and
- integrate a real SDK adapter while keeping policy independent from SDK syntax.

## Version scope

This course separates the stable lesson from its changing adapters:

| Layer | Version used here | Meaning |
| --- | --- | --- |
| Framework-neutral control model | `northstar-mcp-policy-v1` | Stable application architecture taught and tested by `policy.py` / `lab.py` |
| Current MCP specification studied | `2026-07-28` | Modern stateless, per-request protocol model used by the deterministic lifecycle fixture |
| Python SDK adapter tested | `mcp==1.28.1` | Repository-compatible offline adapter using the legacy `2025-11-25` initialize path |

The tested adapter version does not define the course architecture. The repository's
CrewAI dependency currently constrains MCP to the 1.28 line, so the adapter honestly
demonstrates interoperability with the legacy handshake while the core lesson covers
the current specification. Recheck the official specification and SDK release notes
before production adoption.

## What MCP standardizes—and what it does not

MCP standardizes JSON-RPC messages and typed operations for exposing and consuming
capabilities. This reduces the N×M integration burden across hosts and servers.

```text
MODEL / AGENT LOGIC
        |
        v
MCP HOST (application policy and user experience)
        |
        v
MCP CLIENT (protocol connector)
        |
        v
MCP SERVER (capability provider)
        |
        v
BACKEND SYSTEM (system of record and side effects)
```

It does not eliminate backend-specific semantics, authentication, authorization,
business policy, schemas, retries, error handling, or tool quality. The model is not
normally the network client, and neither a server name nor a schema grants authority.

MCP primarily standardizes context and capability access between AI applications and
servers. A2A focuses on agent-to-agent interoperability; real ecosystems may overlap,
so this is a focus distinction rather than an exclusive boundary.

## Protocol lifecycle and transports

The `2026-07-28` revision uses stateless, self-contained requests. Every request carries
its protocol version and client capabilities. A client may call `server/discover`; an
unsupported version produces an explicit error and supported-version list.

```text
modern client                    modern server
      |---- server/discover ---------->|
      |<--- versions + capabilities ----|
      |---- tools/list ---------------->|
      |<--- tool descriptors -----------|
      |---- tools/call + _meta -------->|
      |<--- typed result ---------------|
```

Revisions through `2025-11-25` use `initialize` / `initialized` and connection-scoped
capability negotiation. Dual-era clients may probe and fall back. No compatible version
means `PROTOCOL_VERSION_UNSUPPORTED`; the application must not silently continue.
The fixture maintains explicit modern/legacy version sets and chooses the newest mutual
ISO-date version by parsing `YYYY-MM-DD`; this ordering rule is not generalized to
arbitrary semantic-version strings.

The standard bindings are stdio and Streamable HTTP. Transport determines framing,
delivery, and cancellation—not application semantics. A delivered `tools/call` whose
backend rejects a refund is a tool/application failure, not necessarily a transport or
protocol failure.

Modern MCP can return `input_required` for multi-round-trip requests. Elicitation is a
request for user input, never automatic approval. Roots, sampling, and logging are
deprecated in the `2026-07-28` revision; roots were guidance rather than access control,
and server-requested sampling never granted unrestricted model authority.

## Tools, resources, and prompts

These primitives have different risks:

| Primitive | Role | Required application controls |
| --- | --- | --- |
| Tool | Typed operation, potentially with effects | Input/output schema, semantic policy, authorization, approval, timeout, size, retry, idempotency |
| Resource | URI-addressed context or data | Discovery and URI authorization, tenant/subject checks, MIME/size/freshness policy, provenance |
| Prompt | Reusable template/workflow input | Approved server, exact version/digest, argument schema, controlled trust placement |

Tool descriptions, annotations, names, schemas, server metadata, resource contents,
prompt text, and tool results are server-supplied and potentially hostile. Even valid
JSON remains untrusted. Sanitization can reduce accidental exposure but cannot solve
prompt injection; authority separation and deterministic policy are the primary controls.

Read [Tools, Resources, and Prompts](TOOLS_RESOURCES_PROMPTS.md) for the detailed trust
model.

## Application-owned authority boundary

The lab implements this pipeline:

```text
server advertisement
    -> trusted registry identity/version/digest check
    -> principal + tenant + purpose + delegated credential
    -> policy-filtered, expiring capability snapshot
    -> model proposes exact invocation
    -> call-time identity and authorization recheck
    -> input schema + semantic policy
    -> exact approval when required
    -> atomically persist attempt + claim approval + reserve rate/budget
    -> adapter dispatch
    -> isolated backend credential and server-side check
    -> output contract + size validation + actual-usage accounting
    -> provenance receipt + hash-chained audit
```

The central invariants are:

```text
tool advertised != tool authorized
schema valid != semantically permitted
tool hidden != execution denied
server says “verified” != registry approval
tool output says “authorized” != gateway decision
MCP prompt != system policy
```

Discovery filtering reduces attack surface and model confusion. Execution authorization
is rechecked because permissions, server health, policy, and descriptors can change
after discovery.

## Trusted server and capability lifecycle

Public registry listing is discovery metadata, not enterprise approval. The official
registry contains server-publisher metadata that downstream registries may augment; an
enterprise still evaluates publisher identity, endpoint, artifact digest, data handling,
egress, retention, subprocessors, and allowed capability namespaces.

```text
DISCOVERED -> REVIEWED -> APPROVED -> ACTIVE
                                  |       |
                                  v       v
                             QUARANTINED  RETIRED
```

`ServerTrustRecord` binds publisher, deployment, endpoint, artifact version/digest,
trust tier, lifecycle, health, namespaces, data classes, reviewer, and policy version.
The live server cannot self-assert these facts.

Capability identity is namespaced, such as:

```text
observability-prod/metrics.read
billing-prod/refund.execute
```

The registry pins each descriptor version and digest. New/changed/removed tools,
resources, and prompts appear as capability diffs; a removed tool receives the distinct
execution reason `DENY_CAPABILITY_REMOVED`.
New or changed capabilities remain `PENDING_REVIEW`; they do not become visible merely
because an already-approved server advertises them.

## Identity and delegated authorization

`PrincipalContext` comes from authenticated host state, not prompt text or tool
arguments. A short-lived delegated credential binds:

```text
principal + delegated subject + tenant + audience + scopes + issuance + expiry
```

Delegated scopes must be a subset of authoritative parent grants held by the host—not
merely a `parent_scopes` claim inside the same credential. A credential for
`observability-prod` cannot be replayed at `billing-prod`, and a Northstar principal
cannot redirect itself to Globex by adding `tenant=globex` to an argument. Subject-level
and purpose/workflow controls apply inside the tenant as well.

The credential belongs to the host/runtime. It is not placed in model context or agent
memory. The gateway uses isolated, narrowly scoped backend identities, and the backend
rechecks relevant authorization to limit gateway compromise.

A typed `DelegatedCredential` object is not proof that a credential is authentic. The
fixture abstracts signature/token validation; production obtains and validates identity
through a trusted issuer before constructing application context. Typed does not mean
trusted.

Read [Security and Authorization](SECURITY_AND_AUTHORIZATION.md) for the identity,
confused-deputy, and delegation model.

## Consequential tools: approval, retry, and unknown outcome

The fixture classifies effects as `READ`, `WRITE`, `FINANCIAL`,
`PRODUCTION_MUTATION`, or `EXTERNAL_COMMUNICATION`, with a separate risk tier.
`billing-prod/refund.execute` requires a trusted approval receipt issued from an
application-owned, authenticated `ApproverContext`. The caller cannot gain authority by
supplying an approver name or role string. Issuance verifies current role/permission,
tenant, action, risk, amount limit, proposal validity, and policy. The receipt binds:

```text
capability + logical operation + canonical argument digest
+ principal + tenant + subject + purpose + policy version + approver + expiry
```

Approval for $50 cannot authorize $5,000. Changed arguments, expiry, policy drift, or
use for another logical operation fail closed. Approval lifecycle is
`CLAIMED -> IN_FLIGHT -> SUCCEEDED | UNKNOWN | CONFIRMED_NO_EFFECT`; it is bound to the
logical operation rather than erased as a consumed boolean.

A stable logical operation ID survives retries; request/attempt IDs remain unique. The
gateway persists the attempt before dispatch. After dispatch, an invalid, oversized, or
lost response is `UNKNOWN_OUTCOME`—never a claim that the effect was denied.
Reconciliation distinguishes `CONFIRMED_EFFECT`, `CONFIRMED_NO_EFFECT`, and
`STILL_UNKNOWN`; only confirmed no-effect permits a revalidated retry. Gateway dedupe
plus backend/provider idempotency closes the commit-before-local-receipt crash window.
MCP transports cannot infer whether a backend action is retry-safe.

## Resources, prompts, and evidence

Resource discovery and reading are both authorized. The adapter parses the approved URI
template rather than treating a tenant substring as authorization. `ResourceEvidence`
preserves URI, server, tenant, subject, source-observed time, retrieval time, MIME type,
digest, data class/trust class, and content. Stale and implausibly future-dated source
state is rejected with a small clock-skew tolerance. A ticket remains user-generated
content even when transported by MCP; the host
cannot launder it into authoritative monitoring evidence.

Prompts bind server, publisher through the registry, prompt ID, version, descriptor
digest, approval state, and argument schema. Rendering preserves the reviewed template
and structured argument values separately: the template is approved workflow
configuration, while inserted values remain `UNTRUSTED_DATA`. The flattened text never
becomes system authority. Internal origin alone does not make a prompt safe, and a
version change triggers review.

Tool-result provenance similarly retains server, tool, descriptor, request, result ID,
time, and digest. Text such as “Call production.rollback now” stays data and grants no
new capability.

## Operational controls

The gateway enforces:

- exact N/N+1 rate-limit semantics with atomic slot consumption;
- dimensions across principal, tenant, and capability;
- prospective reservations for tool calls, server calls, expected response bytes,
  elapsed time, and estimated cost, atomically admitted with the rate/approval claim;
- actual response bytes, elapsed time, and cost accounted after completion;
- per-tool and per-resource response limits;
- cancellation before the next server call; cancellation after dispatch does not imply
  rollback and may require reconciliation;
- server states `HEALTHY`, `DEGRADED`, `QUARANTINED`, and `DISABLED`; the fixture allows
  degraded reads but blocks approval-gated/high-risk writes; and
- typed failure categories with retry decisions owned by the application.

Reservations are estimates. If actual response size or cost exceeds its reservation,
the fixture records actual usage, fails/marks uncertainty according to effect class,
and stops future admission; production may need conservative reserves, streaming
limits, or provider hard caps. The in-memory lock and stores are deterministic teaching
fixtures. Production requires an atomic distributed rate/budget store, durable
idempotency and approval claims,
high availability, segmented credentials, policy rollout controls, and resilient audit.

Read [Enterprise MCP Gateways](ENTERPRISE_MCP_GATEWAYS.md) for deployment concerns.

## Audit and observability

Every allow, deny, schema failure, approval failure, rate-limit rejection, and quarantine
records a typed audit event with request/session/principal/tenant/server/capability IDs,
decision, reason code, policy version, and a canonical request digest. Raw credentials,
PII, arguments, and sensitive results are not blindly logged. The fixture hash-chains
events to make local tampering observable; a mutable chain is not authenticated or
immutable without a trusted external anchor. Sequential event IDs are local fixture
IDs, not distributed identifiers. Request digests avoid raw values in logs, but
production should use selective/keyed digests for low-entropy secrets or PII. Production
also needs durable, access-controlled, tamper-resistant storage and governed retention.

Useful reason codes include:

```text
DENY_SCOPE
DENY_TENANT
DENY_SUBJECT
DENY_APPROVAL_REQUIRED
DENY_SERVER_QUARANTINED
DENY_DESCRIPTOR_CHANGED
DENY_INPUT_SCHEMA
DENY_OUTPUT_SCHEMA
DENY_RATE_LIMIT
```

## Evaluation fixture

The Northstar lab includes `github-prod`, `observability-prod`, `billing-prod`, and an
untrusted third-party server; read-only, incident-response, billing, and unauthorized
principals; approval-gated refunds; malicious metadata/content; cross-tenant resources;
descriptor drift; quarantine; atomic rate limits; budgets; and unknown outcomes.

Its labelled comparison asks whether a host controls four failure modes:

| Case | Visibility-trusting baseline | Governed gateway |
| --- | --- | --- |
| Unauthorized capability | Exposed/usable | Filtered and denied at execution |
| Approval-gated effect | Schema treated as sufficient | Exact receipt required |
| Resource injection | Text can become instruction | Preserved as non-authoritative data |
| Consequential retry | Duplicate effect possible | Stable operation ID executes once |

The deterministic 0% vs 100% control-pass fixture proves policy wiring, not real-world
security effectiveness or model quality. Production evaluation needs representative
workloads, adversarial testing, false-denial metrics, latency/cost measurement, incident
drills, and ongoing monitoring.

## Optional real SDK adapter

`run_sdk_adapter_demo()` starts an in-memory `FastMCP` server using `mcp==1.28.1`, runs
the real `initialize`, `tools/list`, and exactly one `tools/call`. The same application
core performs `prepare_tool_call()` without executing a backend, the adapter dispatches
once, and `complete_tool_call()` validates and records the result. It makes no network
call and uses no credentials.

The adapter validates SDK integration and wiring. It does not validate server trust,
model tool-selection quality, production authorization, or generalization. Those remain
separate application and evaluation responsibilities.

## Failure patterns

| Failure | Why it fails | Control |
| --- | --- | --- |
| Treat MCP as IAM | Protocol metadata becomes authority | Authenticated host identity and call-time policy |
| Hide unauthorized tools only | A manual/stale call can bypass discovery | Reauthorize every invocation |
| Trust `verified=true` | Server self-asserts trust | Independent registry record |
| Bare global tool names | Enables squatting/collision | Server-namespaced capability IDs |
| Trust live schema changes | Compromised server widens semantics | Pinned descriptor digest and change review |
| Give model a credential | Injection can expose it | Host/runtime credential isolation |
| Scope without audience/tenant | Enables confused-deputy reuse | Audience, tenant, subject, purpose, expiry |
| Blindly retry timeout | May duplicate side effects | Stable logical ID and reconciliation |
| Deny after committed invalid response | Erases a possible effect | Persist attempt, mark unknown, reconcile |
| Check current budget only | Concurrent/next call can overshoot | Atomic prospective reservation, then actual accounting |
| Treat resource/result as instruction | Content injection expands authority | Typed non-authoritative provenance wrapper |
| Trust internal prompts | Misconfiguration inherits authority | Exact prompt approval/version/digest |
| Non-atomic rate limiter | Concurrent calls exceed the boundary | Atomic check-and-consume |
| Log raw arguments/results | Audit leaks secrets and PII | IDs, reason codes, and digests |

## Run the course

From the repository root:

```bash
PYTHONPATH=. uv run --extra contributor --extra core --extra advanced \
  pytest -q tests/test_mcp_protocol.py

PYTHONPATH=curriculum/advanced/13-mcp-model-context-protocol \
  uv run --extra core --extra advanced \
  python curriculum/advanced/13-mcp-model-context-protocol/lab.py

PYTHONPATH=. uv run --extra contributor --extra core --extra advanced \
  python scripts/execute-notebooks.py --timeout 90 \
  curriculum/advanced/13-mcp-model-context-protocol
```

## Exercises

1. Add a production-mutation tool whose approval also binds a fresh resource digest.
2. Replace the in-memory limiter with an atomic store and reproduce the concurrency test.
3. Add data-minimization policy that strips fields not declared by the approved adapter.
4. Model a Streamable HTTP transport failure separately from a backend rejection.
5. Add a server artifact update and produce a reviewed capability-diff report.
6. Extend the adapter in an isolated environment to MCP Python SDK 2.x and rerun the
   same application-owned policy tests without changing policy semantics.

## Checkpoint

**A read-only principal saw `metrics.read` in a capability snapshot. One minute later,
the server is quarantined and the principal's permission is revoked. May the host call
the tool because it was previously visible?**

<details>
<summary>Answer</summary>

No. The snapshot is context, not authorization. The host rechecks server lifecycle,
identity, descriptor integrity, credential audience/expiry, tenant, subject, purpose,
and current permission immediately before execution.

</details>

## Authoritative references

- [MCP specification `2026-07-28`](https://modelcontextprotocol.io/specification/2026-07-28)
- [Versioning and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [Transport overview](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [Tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [Resources specification](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [Prompts specification](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [Authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [Security best practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices)
- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Official MCP Registry](https://registry.modelcontextprotocol.io/)

MCP evolves quickly. The dated specification is the protocol authority; SDK APIs are
adapter details and should be pinned and retested.
