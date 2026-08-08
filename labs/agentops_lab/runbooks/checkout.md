# Checkout incident runbook

Use this runbook when checkout conversion drops, payment authorization failures
increase, or customer support reports widespread payment failures.

## Evidence to collect

- Current health for `checkout` and `payments`.
- Active incidents mentioning checkout, payment authorization, payment gateway,
  or customer checkout failures.
- Last checkout deployment and whether failures started after rollout.

## Initial response

1. Confirm whether there is an active incident before telling support an incident exists.
2. If checkout is degraded and an active checkout incident exists, recommend a
   proactive support advisory for affected tiers.
3. If payment errors are above threshold, recommend routing eligible enterprise
   customers through the fallback provider.
4. If evidence is incomplete, escalate to the payments-platform on-call instead
   of inventing a root cause.

## Safe actions in this lab

This notebook is read-only. It can recommend pausing a rollout or notifying a
team, but it cannot execute production changes.
