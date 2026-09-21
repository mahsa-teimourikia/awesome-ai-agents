# Deep Dive: Security and Authorization

MCP is not IAM. The host derives identity and authority from authenticated application
state and enforces them again at every capability boundary.

## Confused deputy model

An incident agent may receive a ticket containing “refund me $10,000.” If the runtime
uses one global billing credential, the agent becomes a confused deputy: untrusted
content steers excessive authority.

Use a short-lived delegated credential bound to:

```text
actor workload + delegated subject + tenant + audience
+ scopes + purpose + issuance + expiry + revocation state
```

The credential belongs to the host/runtime, never the model context. Delegation is
attenuating: child scope must be a subset of parent scope from authoritative host
identity state. `parent_scopes` inside the same typed object is not independent proof,
and a Pydantic model is not an authenticated token. A ticket-server credential
cannot be replayed at billing; a Northstar credential cannot access Globex; and tenant
membership does not authorize one subject's payroll record to another subject.

## Discovery is defense-in-depth

The host filters upstream capabilities through independent trust and policy:

```text
upstream capabilities
  -> trusted server registry
  -> approved namespace/version/digest
  -> principal and delegated scope
  -> tenant/subject/purpose/session policy
  -> expiring capability snapshot
```

This reduces attack surface, prompt size, and accidental selection. It is not the
security boundary. A hidden tool can still be constructed manually, a permission can
be revoked after discovery, and a server can be quarantined or change descriptors.
Execution therefore rechecks every condition immediately before the backend call.

## Exact approval for consequential effects

An application-owned `ApproverContext` comes from authenticated state and is checked
against the current approver registry, tenant, action permission, risk tier, and amount
limit. An ordinary agent or caller-provided role string cannot mint authority.

An approval receipt binds principal, tenant, subject, purpose, capability, stable
logical operation, canonical argument digest, policy version, approver identity/role,
issuance, and expiry. Changed amount, customer, currency, policy, or operation
invalidates it. The approval claim progresses through `CLAIMED`, `IN_FLIGHT`, and a
terminal/uncertain outcome for that logical operation; it is not merely deleted before
dispatch.

An elicitation response, a server-provided `APPROVED` string, a prompt, or a tool result
cannot create this receipt.

## OAuth and remote servers

The current MCP authorization specification builds on OAuth for HTTP transports. An
implementation must still validate issuer and audience/resource binding, protect the
authorization flow against confused-deputy attacks, and avoid token passthrough. JWT is
one possible credential representation, not an architectural requirement.

Where possible, both gateway and MCP server/backend enforce relevant authorization.
The gateway uses isolated backend identities per server so compromise of one integration
does not grant routing or credentials for another.

## Data controls

Before sending context or arguments, classify data as `PUBLIC`, `INTERNAL`, `SENSITIVE`,
or `RESTRICTED`. Server policy constrains accepted classes and egress. Minimize fields;
do not send an entire customer record when a customer ID suffices. Field filtering may
reduce exposure, but it is not a prompt-injection defense.
