# Capstone Engineering Guide

Work in missions. Commit each deliverable with its test/evaluation result; do not jump to a multi-agent design before a workflow and single-agent baseline.

## Suggested milestones

1. **Evidence-first investigator:** add a hypothesis ledger with claim, source IDs, counter-evidence, confidence, and next evidence gap.
2. **Governed proposal:** add a structured `PreparedAction` contract with tenant, approver, expiry, action fingerprint, idempotency key, and verification plan.
3. **Adversarial and recovery suite:** add cases for poisoned `checkout_poisoned.md`, missing deployment, duplicate approval, denied tenant, tool timeout, and expired budget.
4. **Architecture experiment:** run workflow/single/team baselines across `capstone_tasks.json`; report outcome, evidence support, policy pass, cost per success, p95 latency, and coordination overhead.
5. **Release review:** document SLOs, monitoring, rollback/kill, ownership/on-call, retention, and staged deployment.

## Definition of done

The final submission may recommend mitigation but cannot execute it. It must contain attributable evidence, calibrated uncertainty, a valid architecture justification, policy/tenant/permission results, trace/evaluation output, an approval-ready action, and an explicit recovery/rollback plan.
