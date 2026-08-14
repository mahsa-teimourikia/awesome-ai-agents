# Deep Dive: Mitigation Proposals

The final phase is the **Mitigation Proposal**. 
This is where the agent transitions from Read-Only to Mutating State. However, in enterprise architecture, an agent *never* executes a high-risk mutation autonomously.

## The Proposal Boundary
Instead of calling `execute_rollback()`, the agent calls `propose_mitigation()`. 

This tool does not touch production. It creates a payload containing:
1. **The Target Action:** e.g., `git revert <commit_hash>` or `toggle_feature_flag('new_checkout', False)`.
2. **The Justification:** A link to the Incident Brief and Evidence Timeline.
3. **The Idempotency Key:** A unique hash to ensure the rollback doesn't accidentally trigger twice if the human clicks "Approve" multiple times.
4. **The Rollback Verification:** How the system will know if the mitigation worked (e.g., "Watch Datadog 500 errors drop to 0 within 2 minutes").

## Human-in-the-Loop (HITL) Execution
The proposal is routed to a PagerDuty alert or a Slack interactive button.
The on-call human engineer reviews the evidence, agrees with the logic, and clicks **Approve**.

Only then does the orchestrator (not the agent) execute the exact, dry-run validated payload against production. This ensures accountability, prevents hallucinated destruction, and treats the agent as a highly competent analyst rather than a rogue operator.
