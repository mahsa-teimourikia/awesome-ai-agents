# Deep Dive: Delegation and Accountability

When a human manager delegates a task to a human employee, they don't just say "Fix the company." They provide a specific goal, boundaries, and expect a specific artifact in return. 

When delegating to an agent, this process must be even more rigorous. You must explicitly separate **Human Accountability** from **Machine Agency**.

## The Vague Handoff (Anti-Pattern)
In a Vague Handoff, a human tells the agent: *"The EU checkout is broken. Please investigate and fix it."*

This is incredibly dangerous. The agent is now forced to interpret policy, determine what "fixed" means, and guess which tools it should use. It might decide that "fixing" the checkout means disabling the credit card fraud checks because they were throwing errors.

## The Work Order (Best Practice)
Agents should only operate via **Work Orders**. A Work Order is a typed, JSON-enforced contract that defines the exact boundaries of the delegation.

A Work Order must contain:
1. **`tenant_scope`**: Exactly which customer or region this applies to (e.g., `EU_Region_Only`).
2. **`objective`**: The strict goal.
3. **`allowed_tools`**: The agent does *not* get access to the whole tool registry. It only gets the exact tools needed for this order.
4. **`no_go_actions`**: Explicit instructions on what the agent cannot do (e.g., *Do not modify payment gateways*).
5. **`expected_artifact`**: The schema of the JSON response the agent must return.
6. **`escalation_rule`**: The exact condition under which the agent must stop and page a human (e.g., *If database responds with 500*).

### Inherited Authority
A critical rule of delegation: **Sub-agents do not inherit the permissions of their managers.**

If the Human Sponsor has "Global Admin" rights, and they delegate to a Manager Agent, the Manager Agent does *not* become a Global Admin. When the Manager Agent delegates to the Coding Agent, the Coding Agent only receives a token scoped exclusively to the files mentioned in its specific Work Order.
