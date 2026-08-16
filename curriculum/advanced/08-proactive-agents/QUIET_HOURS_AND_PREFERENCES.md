# Deep Dive: Quiet Hours and Preferences

A proactive agent's most important capability is knowing when to shut up. 

If an agent detects a minor UI bug on the website at 3:00 AM, it should not trigger a PagerDuty alert that wakes up an engineer. It should respect the engineer's timezone and quiet hours.

## Notification Routing
When an agent decides an event warrants a notification, it should not call a hardcoded `send_slack_message()` tool. It should yield a **Notification Proposal** to a central routing system.

The Notification Router evaluates:
1. **Urgency:** Is this a P1 (Database down) or a P4 (Typo in documentation)?
2. **User Timezone:** Is it currently within the user's defined "Working Hours"?
3. **User Preferences:** Did the user opt-out of Slack messages and prefer email?

## The Downgrade Pattern
If the router receives a P4 proposal at 3:00 AM, it executes a **Downgrade**:
1. It blocks the real-time push notification.
2. It pushes the event into a `daily_digest` database table.
3. At 9:00 AM, a scheduled agent reads the `daily_digest` table, summarizes the 5 minor issues that occurred overnight, and sends a single, polite email.
