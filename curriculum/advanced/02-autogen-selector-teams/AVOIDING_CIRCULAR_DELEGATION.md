# Deep Dive: Avoiding Circular Delegation

An “infinite polite loop” is memorable: one agent hands off, another acknowledges it, and the selector sends the conversation back. It is a common and expensive failure mode, not universally the greatest multi-agent risk.

## Name the failure you are stopping

| Signal | Definition | Response |
|---|---|---|
| Hard turn limit | absolute message/turn ceiling | stop and escalate; last-resort circuit breaker |
| Duplicate selection | same agent + target gap + evidence digest | reject before another identical turn |
| Semantic stagnation | evidence, diagnosis, and review state stay unchanged across N turns | `STALLED` |
| Speaker ping-pong | A–B–A–B on the same material-state digest | `LOOP_DETECTED` |
| Review churn | same proposal and same feedback repeat without evidence | bounded reconciliation or escalate |
| Repeated handoff | the same transfer recurs without new state | reject or escalate |
| No-progress loop | coordination repeats but no required gap closes | abstain/escalate |

A repeated speaker is not automatically a loop. `ObservabilityAgent` may inspect health, then return later for logs after deployment evidence changes the hypothesis. The evidence/state digest makes that revisit distinguishable from duplicate work.

## Layered termination

Normal success comes from typed state: evidence complete, candidate diagnosis present, and validated `REVIEW_PASS`. Separate controls stop unsafe or wasteful execution:

- cancellation and policy blocks;
- wall-clock deadline;
- message, selector-call, worker-call, per-agent-turn, repeated-speaker, and cost budgets;
- duplicate, stagnation, ping-pong, and review-churn detection;
- evidence insufficiency and explicit validated escalation; and
- AutoGen `MaxMessageTermination` as a final ceiling and circuit breaker, never as evidence of successful completion.

The course uses deterministic precedence: cancellation, policy block, deadline, hard budget, loop, stall, escalation, insufficient evidence, completion, continuation. Precedence matters because an externally cancelled run must not be labelled successful merely because a late review message also says pass.

## Why text matching is insufficient

`TextMentionTermination("ESCALATE_TO_HUMAN")` can be useful as a framework signal, but the phrase may appear in user input, retrieved evidence, or malicious worker content. Application state changes only when the signal comes from the expected role and its typed output has passed artifact validation.

Likewise, `REVIEW_PASS` means proposal review success only. A non-reviewer cannot set it, and a validated reviewer result still does not confer `production.execute`, validate a human approval, execute rollback, or mutate global state. Legacy prose tokens such as `APPROVED` and `FINAL_PROPOSAL` carry no authority.

## Failure and conflict handling

- Retry `TIMEOUT` only within a small retry budget.
- Try an allowlisted alternate source for `SOURCE_UNAVAILABLE`; otherwise mark required evidence insufficient.
- Never retry `AUTH_DENIED` or `POLICY_DENIED` as if repetition could create authority.
- Permit bounded repair for `INVALID_ARTIFACT`.
- Route contradictory specialist evidence to one bounded reconciliation turn or a human, rather than repeatedly asking the Analyst to pick a preferred claim.

## Cancellation invariant

Cancellation is checked before the next selector invocation and before the next worker invocation. Once set, neither `selector_calls` nor `worker_calls` may increase. Persist cancellation and budget state beside any AutoGen team state so pause/resume cannot reset the application-owned boundary.
