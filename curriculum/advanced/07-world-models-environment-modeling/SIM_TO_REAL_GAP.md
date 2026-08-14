# Deep Dive: The Sim-to-Real Gap

If World Models are so powerful, why doesn't every agent use them?
Because simulations lie. This is known in robotics as the **Sim-to-Real Gap**.

## Hallucinated Physics
A Digital Twin is only as good as its underlying assumptions. 
If you build a simulation of your microservice architecture, and you hardcode the assumption that `Service_A` always responds to `Service_B` in 10 milliseconds, your Twin is flawed.

If the agent tests a plan in the Twin, the Twin will say: *"Success! The API calls completed in 20ms."*
The agent executes the plan in Production. In reality, the network is congested, `Service_A` takes 5000ms to respond, the connection times out, and the database locks up.

## Mitigating the Gap
1. **Calibrated Sensors:** The Twin must be continuously updated with live telemetry data. If latency spikes in prod, the Twin must update its internal latency variables.
2. **Confidence Scores:** The agent must be aware of its own uncertainty. If the agent knows the Twin hasn't synced with prod in 24 hours, it should lower its confidence score and request human approval before executing the winning simulation.
