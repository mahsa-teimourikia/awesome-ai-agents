# Deep Dive: Hysteresis and Cooldowns

Deduplicating exact error logs is easy. But what happens when an agent is monitoring a continuous metric, like CPU usage?

Imagine an agent tasked with alerting if CPU usage exceeds 90%.
At 12:00:00, CPU hits 91%. The agent alerts.
At 12:00:05, CPU drops to 89%.
At 12:00:10, CPU hits 91% again. The agent alerts again.

This is called **Flapping**. The metric is oscillating around the threshold, causing the agent to spam the user.

## The Hysteresis Pattern
Hysteresis is a concept from control theory. It means that the threshold for turning a system *on* is different from the threshold for turning a system *off*.

To prevent flapping, you define two thresholds:
1. **Activation Threshold:** 90%
2. **Recovery Threshold:** 70%

When the CPU hits 91%, the agent enters an `ALERTING` state and fires the notification. 
Crucially, the agent stays in a `COOLDOWN` state until the metric drops *below 70%*. Even if the CPU drops to 89% and spikes back to 91%, the agent ignores it, because the system hasn't fully recovered.

## Fixed Time Cooldowns
Alternatively, if a recovery threshold is too complex to calculate, you can enforce a strict **Fixed Cooldown**. Once an alert fires for "High CPU", the agent is blocked from sending another "High CPU" alert for exactly 30 minutes, regardless of what the metric does.
