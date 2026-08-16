# Deep Dive: AI Risk Management & Autonomy

Deploying an autonomous agent without a formalized risk assessment is a recipe for a catastrophic failure. Two major frameworks dictate how enterprises must govern AI systems: the **NIST AI Risk Management Framework (RMF)** and the **EU AI Act**.

## The NIST AI RMF

The NIST AI RMF provides a structured process for governing AI systems. It is broken into four core functions:
1. **Map:** Identify the context, capabilities, and business purpose of the agent. (e.g., "This agent reads internal support tickets and drafts responses").
2. **Measure:** Quantify the risks. (e.g., "If the agent hallucinates, it could expose PII").
3. **Manage:** Implement technical controls. (e.g., "Implement NeMo Guardrails and a Human-in-the-Loop approval step").
4. **Govern:** Establish the culture of accountability. (e.g., "Assign a specific VP as the Human Owner of the agent").

## The EU AI Act Classification

If your agent interacts with users in the European Union, it must be classified under the EU AI Act's risk tiers:

1. **Unacceptable Risk (Prohibited):** Social scoring, subconscious manipulation, real-time biometric surveillance. Agents cannot do this.
2. **High Risk:** Agents used in critical infrastructure, employment (e.g., an agent screening resumes), or credit scoring. These require strict Human-in-the-Loop oversight, extensive logging, and explicit transparency.
3. **Limited/Minimal Risk:** Customer service chatbots. The primary requirement is transparency: the user *must* be informed they are talking to an AI, not a human.

## Defining Autonomy Tiers

You cannot govern an agent if you do not understand what it is allowed to do. Every agent must be classified into an Autonomy Tier during Registration:

### Tier 1: Passive/Assistive
- **Capability:** Reads data, summarizes information, drafts proposals.
- **Risk:** Low. If it hallucinates, the human just ignores the draft.
- **Control:** Output guardrails (PII redaction).

### Tier 2: Executes with Approval (HITL)
- **Capability:** Prepares state changes (e.g., a Terraform plan or a refund request), but halts execution until a human reviews it.
- **Risk:** Medium. The human is a backstop, but humans suffer from "automation bias" (Rubber Stamping).
- **Control:** Explainable handoff packets and cryptographically signed approvals.

### Tier 3: Fully Autonomous
- **Capability:** Reads, decides, and executes state changes (e.g., restarting servers, trading stocks) without human intervention.
- **Risk:** Extreme. A hijacked agent can cause catastrophic damage in milliseconds.
- **Control:** Strict Open Policy Agent (OPA) runtime policies, Action Budgets, Circuit Breakers, and a Global Kill Switch.
