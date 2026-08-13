# Deep Dive: Registries and Tool Squatting

As an enterprise scales to hundreds of internal agents and thousands of tools, you can no longer rely on developers hard-coding API endpoints into their prompts. You need a **Central Registry**.

## What is a Registry?
A registry is an interface-as-code boundary. It prevents "Shadow Agents" (untracked, unmonitored scripts running on developer laptops) from touching production systems.

To deploy an agent or a tool, a developer must register it with the enterprise control plane. The registration payload must include:
- `owner`: The team responsible if the agent breaks.
- `risk_tier`: (e.g., Low, Medium, High). High-risk agents require mandatory human-in-the-loop approval.
- `eval_score`: Mathematical evidence that this agent passed its SWE-bench or internal regression tests.
- `data_classification`: Does this agent touch PII?

If a registration lacks any of these fields, the Enterprise Orchestrator rejects the deployment.

## The Threat: Tool Squatting
In an ungoverned ecosystem, tools are often discovered by name. For example, an agent might look for a tool named `refund_customer_stripe`.

If there is no central registry enforcing provenance, a malicious developer (or a compromised internal account) could publish a fake tool also named `refund_customer_stripe`, but route the payload to `attacker.com`. 

When the agent attempts to refund a customer, it unknowingly uses the malicious tool and leaks PII. This is known as **Tool Squatting** (similar to Typosquatting in npm or PyPI).

### Preventing Tool Squatting
The Central Registry prevents this by enforcing **Cryptographic Provenance**.
1. The official Billing Team registers `refund_customer_stripe` and signs the tool definition with their team's cryptographic key.
2. The Orchestrator maps the tool namespace `billing.stripe.refund` strictly to that signature.
3. If an attacker tries to register a tool with the same namespace, the Registry rejects it because the attacker does not possess the Billing Team's private key.

Agents must only be allowed to discover and bind to tools that have been verified by the Central Registry.
