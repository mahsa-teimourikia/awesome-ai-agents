# Deep Dive: Architecture Routing and Policy

An LLM may help interpret a request. It must not turn its own interpretation into authority.

The Course 04 control plane separates five decisions that are often collapsed into one prompt:

1. **Classification proposal** — what intent, ambiguity, risk, side effect, data, evidence, and latency features appear present?
2. **Policy validation** — which features are consistent with trusted identity and hard high-risk rules?
3. **Architecture admission** — which execution shape and budget are permitted?
4. **Action authorization** — are capability, tenant scope, and any approval valid at use time?
5. **Result validation** — does the candidate result match its contract and evidence?

The proposer may use rules, conventional ML, a small model, or an LLM. The authoritative layer is deterministic policy code. Unknown requests remain `UNKNOWN`; destructive unknowns become `HIGH_RISK_UNKNOWN` and receive no privileged capability.

## Monotonic authority

Architecture selection can only attenuate existing grants:

```text
worker capabilities ⊆ execution contract ⊆ trusted request context
```

Tenant context never widens. Selecting a team does not create more authority than selecting a direct handler. Text copied from tools or models is evidence, never identity, approval, or permission.

Tenant identity is necessary but insufficient. The authenticated user and roles survive from trusted context into the execution contract and password-reset state. A subject mismatch fails before identity verification or a write. If attenuation removes a minimum required capability, admission returns `AUTH_DENIED` without invoking a worker.

## Layered result and action gateways

A production gateway is layered rather than a single regular expression:

- Pydantic/JSON schema and request correlation;
- tenant, role, and capability checks;
- data-class and provider/egress policy;
- evidence provenance and grounding through request/tenant/source/version/digest receipts;
- actual tool/model/cost/deadline accounting;
- structured PII/DLP policy (`ALLOW`, `MASK`, `REDACT`, `BLOCK`);
- validated approval immediately before a consequential action;
- output limits and audit events.

An evidence-name string is only a claim. Application-owned tool/adaptor code registers receipts during the run, and the common gateway resolves every successful evidence claim through that registry. The model cannot self-declare accepted provenance.

The lab's regex detector is intentionally illustrative. Its recursive transformation preserves structured output, but production DLP needs stronger detectors. A short output can still leak a secret, and a long output can be legitimate. Size limits manage resources; they do not prove confidentiality.

## Control-plane failure

If classification or routing is unavailable, do not silently use the most capable worker. Fail closed to human review or a narrowly safe deterministic fallback. Record classifier, router, and policy versions so incidents and offline evaluations can reproduce the decision.

## Approval boundary

A route or plan may validly contain an approval-gated action. That means the action is allowed to be proposed under a future condition. It does not mean the condition has been satisfied. Course 04 carries `approval_required` into the execution contract and validates a typed receipt—request, tenant, action, target, proposal digest, approver, policy version, and expiry—immediately before the write, consistent with Intermediate Course 03.

## Audit minimization

Auditability does not require copying raw sensitive requests forever. The fixture records a request reference and digest, normalized classification and decision fields, policy versions, and outcomes. Production systems should minimize content and apply explicit retention by data classification.
