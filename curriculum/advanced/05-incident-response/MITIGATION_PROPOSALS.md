# Deep Dive: Mitigation Proposals

A mitigation proposal is a reviewable plan, not permission to mutate production. This course keeps proposal, technical review, human authorization, orchestrator execution, provider reconciliation, and incident resolution as separate control boundaries.

## Typed action contract

The fixture proposes `RollbackDeploymentArgs(service_id, deployment_id)`. It never treats an LLM-generated `git revert ...` string as executable authority. The proposal binds the exact incident, tenant, action, target, typed parameters, evidence IDs, evidence-snapshot digest, expected effect, blast radius, rollback plan, verification plan, risk tier, and its own digest.

If the accepted evidence or target changes materially, the proposal must be reviewed and approved again.

## Review is not approval

An independent technical reviewer returns `REVIEW_PASS`, `REVIEW_FAIL`, or `NEEDS_REVISION`. `REVIEW_PASS` means the proposal is technically coherent under the fixture policy. It does not authorize a production write.

An `ApprovalReceipt` separately binds an authenticated approver to the incident, tenant, proposal ID and digest, action, exact target, policy version, issue time, and expiry. A PagerDuty or Slack button is only a user interface; authority comes from identity, role, current policy, and the authoritative approval record.

In this course's enterprise policy, consequential production mutations require external authorization and orchestrator-controlled execution. This is a course policy, not a claim that every organization must choose identical automation.

## Stable idempotency

The logical operation ID is stable for the same approved mitigation. It is not a fresh random value on every retry. Each provider attempt retains a unique attempt ID:

```text
logical operation -> stable across retries
attempt ID         -> unique per provider attempt
```

This allows duplicate alerts or repeated approval delivery to return the same logical receipt rather than repeat a rollback. See Intermediate Courses 01 and 03 for the broader idempotency and approval patterns.

## Unknown outcome reconciliation

If the provider times out after accepting a request, the true outcome is unknown. Blind retry is unsafe. The orchestrator first checks provider operation state or the currently deployed release:

```text
UNKNOWN_OUTCOME
  -> deploy-1841 is current: mark RECONCILED, then verify
  -> deploy-1842 is current: mark failed/escalate or admit a bounded new attempt
```

The durable incident state retains the attempt budget and receipts across a process restart.

## Verification before resolution

Execution success only confirms the action completed. Independent verification checks error rate, conversion, p99 latency, and provider health. Only a `PASS` may transition to `RESOLVED`.

If errors remain high, the mitigation is ineffective and the workflow returns to bounded investigation or escalation. If errors improve while p99 latency regresses, verification returns `REGRESSION`; one healthy signal cannot hide a new customer-impacting failure.

Manual takeover or cancellation is checked before the next automated step. Once active, the agent and orchestrator do not start another proposal, write, or verification action.
