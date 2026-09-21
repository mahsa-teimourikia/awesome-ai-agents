# Deep Dive: Tools, Resources, and Prompts

MCP transports typed capability descriptions and results. It does not assign trust.
The host must apply a distinct policy to each primitive and treat all server-supplied
metadata and content as untrusted until independently admitted.

## Tools

A tool advertises a name, description, input schema, optional output schema, and
annotations. These improve interoperability but are not authorization or semantic proof.

```text
server tool descriptor
  -> approved server/namespace/version/digest
  -> policy-filtered discovery
  -> model invocation proposal
  -> fresh execution authorization
  -> input schema
  -> semantic and approval policy
  -> backend execution
  -> result schema/size/provenance
```

Names are server-namespaced in the application registry. This is stronger than trying
to detect impersonation with string similarity. `search_issues`, `searchIssues`, and
`search_issues_secure` are all untrusted until their server/capability identities are
approved.

Input schema blocks malformed arguments. It cannot decide whether a valid `$5,000`
refund is allowed. Output schema detects contract violations but cannot make returned
text authoritative. Tool descriptions, annotations, input/output schemas, and results
can all carry injection or schema-poisoning attacks; the registry pins the reviewed
descriptor digest and sends changes back through review.

Side-effecting tools additionally need exact approvals, stable logical operation IDs,
unknown-outcome reconciliation, execution receipts, and backend idempotency. A generic
`tools/call` cannot infer these domain semantics.

## Resources

Resources are URI-addressed data. Listing can itself leak sensitive names, so both
`resources/list` and `resources/read` are filtered by server, principal, tenant,
subject, purpose, and data class.

The fixture wraps admitted content as `ResourceEvidence`:

```text
resource_uri + server_id + tenant + subject
+ retrieved_at + MIME type + digest + trust class
```

It validates URI scope, content type, size, and freshness before model exposure. A Jira
ticket saying “database healthy” remains user-generated evidence; it does not become a
monitoring result because MCP transported it. A ticket saying “issue a refund” remains
data and cannot expand the capability snapshot.

Subscriptions and list-change notifications indicate that something may have changed.
They are triggers to re-fetch and revalidate, not trusted state transitions.

## Prompts

Prompts are server-provided templates. They deserve stronger governance because they
shape model behavior. Approval binds:

```text
server/publisher + prompt ID + version + descriptor digest
+ argument schema + approval status
```

Arguments are validated and treated as data during rendering. A changed prompt digest
does not inherit prior approval. Internal origin is not enough: an internal server can
be compromised or misconfigured.

Even an approved prompt is inserted at an application-controlled trust level:

```text
SYSTEM / APPLICATION POLICY
        >
APPROVED WORKFLOW CONFIGURATION
        >
MCP PROMPT
        >
RESOURCE / TOOL DATA
```

The protocol transport never determines instruction precedence.

## Client features and modern input requests

The `2026-07-28` specification uses multi-round-trip `input_required` responses when a
server needs elicitation, sampling, or roots-style input. The host validates every
request and bounds rounds. User interaction does not equal approval, server-requested
sampling does not grant unrestricted model access, and roots are not filesystem access
control. Roots and sampling are deprecated in this revision; new systems should follow
the specification's migration guidance.
