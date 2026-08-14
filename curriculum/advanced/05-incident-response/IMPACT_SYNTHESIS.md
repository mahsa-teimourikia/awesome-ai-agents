# Deep Dive: Impact Synthesis

Once the agent has gathered evidence and formulated a hypothesis (e.g., "The `Checkout UI v2.1` deployment broke the payment gateway"), it must synthesize the business impact.

A technical failure is only half the picture. The agent must quantify the blast radius.

## Quantifying the Blast Radius
The agent uses scoped read-only tools to query business databases.
1. **Identify Failing Requests:** The agent queries the logs to find the exact `tenant_id`s associated with the 500 errors.
2. **Determine Tier:** It cross-references those IDs with the billing database. "4 out of the 6 failing accounts are Enterprise tier."
3. **Calculate SLA Exposure:** It checks the Service Level Agreement (SLA) contracts for those Enterprise accounts. "If downtime exceeds 15 minutes, we owe $50,000 in SLA penalties. We are currently at 12 minutes."

## The Incident Brief
The output of Impact Synthesis is an **Incident Brief**. 
Instead of a panic-inducing Slack message ("The server is broken!"), the agent generates a professional, quantified brief:

> **Hypothesis:** Checkout UI v2.1 deployment caused 500 errors.
> **Impact:** 31% drop in conversion. 4 Enterprise accounts affected.
> **Risk:** Approaching 15-minute SLA breach ($50,000 penalty).
