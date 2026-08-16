# Deep Dive: Counterfactual Planning

Once you have a Digital Twin (a safe simulation environment), you can upgrade your agent to use **Counterfactual Planning**.

Instead of testing a single idea, the agent asks: *"What if?"*

## The Tree of Thoughts (ToT)
When a critical incident occurs (e.g., checkout conversion drops to 0%), the agent spins up 3 parallel simulations.
1. **Simulation A:** Tests the command `rollback_deployment()`.
2. **Simulation B:** Tests the command `wait_10_minutes()`.
3. **Simulation C:** Tests the command `push_hotfix()`.

The agent evaluates the terminal state of each simulation.
- Simulation A predicts 5 minutes of downtime, then recovery. (Score: 85)
- Simulation B predicts 15 minutes of downtime. (Score: 40)
- Simulation C crashes the twin because the hotfix didn't compile. (Score: 0)

The agent compares the predicted utilities, selects Option A, and executes the rollback in the real world. This mirrors how humans play chess: visualizing branches of future moves before touching a piece.
