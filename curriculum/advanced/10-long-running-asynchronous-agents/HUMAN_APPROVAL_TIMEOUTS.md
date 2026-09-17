# Deep dive — Approval, timers, cancellation, and races

Human review is a control boundary only when the reviewed object and the authority to act are both explicit.

## Proposal is not permission

An agent may produce a typed `Proposal`. Planning permission allows that proposal to appear in the workflow; it does not authorize execution. A separate trusted path creates an `ApprovalReceipt`, and execution revalidates it against current state.

The receipt binds run, tenant, subject, proposal ID/digest, precondition digest, action, target, approver, role, policy version, and time window. It is consumed once in the same transaction that advances the run.

Text such as `APPROVED`, an email subject, model output, or a callback body is not authority. UI/API authentication must establish the approver identity and role outside the model. The receipt records the resulting trusted decision.

## Current authority at execution

An approval can become stale even before it expires. Immediately before the operation claim, the runtime checks:

- tenant and subject still match;
- policy version is current;
- action and target remain permitted;
- approver still holds the required role; and
- the current precondition digest exactly matches what was reviewed.

The fixture preconditions bind target ID, resource version, evidence digest, deployment, account state, and policy version. Changing `order-v7` to `order-v8` blocks execution. A production system may choose to generate a new proposal and request new approval.

## Durable timer pattern

The workflow stores a timer ID, due time, and explicit timeout policy before releasing the worker. A timer service or orchestrator later delivers a timer event. The event does not carry authority to choose a different timeout result; persisted policy determines `EXPIRE`, `ESCALATE`, or `CANCEL`.

Managed orchestrators provide native durable waiting. For example, [AWS Step Functions callback tasks](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html) wait for a task token and support timeouts, while [Azure Durable Functions](https://learn.microsoft.com/en-us/azure/azure-functions/durable-functions/durable-functions-orchestrations) recommends durable timers inside orchestrations rather than language-native sleeps. The course's SQLite timer is a transparent local analogue, not a full scheduler.

## Approval versus timeout

Both deliveries may be valid when emitted. Only one may advance the current state.

```text
WAITING_APPROVAL, version 2
    approval transaction ── CAS version 2 → READY_TO_RESUME, version 3
    timeout transaction  ── reloads version 3 → STALE_TIMER_EVENT
```

If the timeout commits first, the approval becomes stale because the run is terminal. This is a deterministic state-machine decision, not an assumption about message arrival order.

## Cancellation and manual takeover

Cancellation must be persisted and checked before the next worker/provider call. Rejecting a result after an expensive or consequential call is too late. In the fixture, `CANCELLED` and `MANUAL_CONTROL` are terminal, so later approvals and callbacks are admitted only as stale audit records.

A production system should define:

- who may cancel or assume manual control;
- whether in-flight activities receive cooperative cancellation;
- what happens when a remote effect cannot be cancelled;
- how reconciliation and compensation continue after cancellation; and
- whether and how an operator may start a new run.

Manual takeover should stop automated mutation. It should not erase the durable history or reuse an old approval receipt.

## Security and UX checklist

- Authenticate the reviewer and protect the review channel against CSRF/replay.
- Show the exact action, target, parameters, evidence, preconditions, and expiry.
- Prevent the agent or retrieved text from choosing the reviewer or approval scope.
- Use one-time receipt consumption and audit both success and rejection reasons.
- Revalidate current permissions and preconditions before the side effect.
- Make timeout behavior visible before review.
- Provide cancellation and manual-control paths with clear ownership.
- Keep late and duplicate events observable rather than dropping them silently.
