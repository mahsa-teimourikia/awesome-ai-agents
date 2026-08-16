# AI Agent Governance & Responsibility Checklist

This document provides a state-of-the-art template for evaluating the governance, ethics, and responsibility of an autonomous AI Agent before deployment. It synthesizes requirements from the **NIST AI Risk Management Framework (RMF)**, the **EU AI Act**, and industry best practices.

**How to use this template:** 
A designated team (e.g., AI Governance Board, Security, and the accountable Business Owner) must complete this questionnaire prior to moving an agent from a development environment to production. Any "No" or "Unclear" answers in critical sections must block deployment until remediated.

---

## 1. Accountability & Ownership
*Autonomous systems cannot hold legal or operational liability; humans do.*

- [ ] **1.1 Human Owner:** Is there a specifically named, accountable Human Owner (not a generic distribution list) registered in the AI BOM?
- [ ] **1.2 Escallation Path:** Is there a defined on-call rotation or escalation path for this agent if it misbehaves in production?
- [ ] **1.3 Business Justification:** Is the specific business purpose of the agent documented, along with explicit "non-goals" (actions it should never take)?

## 2. System Provenance & AI BOM
*You cannot govern a system if you do not know exactly what is running.*

- [ ] **2.1 AI Bill of Materials (BOM):** Does the deployment package include a cryptographic or version-controlled AI BOM detailing:
  - Foundation model version (e.g., `gpt-4o-2024-08-06`)?
  - System prompt hash?
  - Explicit versions of all exposed tools/APIs?
- [ ] **2.2 Data Lineage:** If the agent uses RAG (Retrieval-Augmented Generation), are the data sources vetted for copyright, consent, and accuracy?

## 3. Risk & Autonomy Classification
*Applying appropriate controls based on the EU AI Act and NIST AI RMF.*

- [ ] **3.1 Risk Tiering:** Has the system been classified according to harm potential? (e.g., Unacceptable, High, Limited, Minimal).
- [ ] **3.2 Autonomy Tiering:** Is the agent's autonomy explicitly classified?
  - *Tier 1 (Assistive):* Read-only, proposes actions.
  - *Tier 2 (Human-in-the-Loop):* Prepares state changes but requires human cryptographic approval to execute.
  - *Tier 3 (Fully Autonomous):* Executes state changes without human intervention.
- [ ] **3.3 HITL Enforcement:** If classified as High Risk or Tier 2, are Human-in-the-Loop (HITL) constraints physically enforced at the tool boundary (not just in the prompt)?

## 4. Guardrails & Least Privilege
*Technical controls to enforce the policy.*

- [ ] **4.1 Workload Identity:** Does the agent authenticate to tools using a strictly scoped, short-lived token (e.g., SPIFFE/OAuth Token Exchange) rather than a global API key? (Defense against the Confused Deputy).
- [ ] **4.2 Input Guardrails:** Are user prompts and retrieved RAG data scanned for Prompt Injection/Jailbreak signatures *before* inference?
- [ ] **4.3 Runtime Policy:** Are tool arguments validated dynamically by a policy engine (e.g., OPA/Rego) to ensure the agent is authorized to access the requested tenant/resource?
- [ ] **4.4 Output Guardrails:** Is the LLM's final response scrubbed for Personally Identifiable Information (PII) before being returned to the user?

## 5. Ethics, Fairness, and Transparency
*Ensuring the agent acts safely and transparently.*

- [ ] **5.1 User Transparency:** Are end-users explicitly informed that they are interacting with an AI agent? (Required by the EU AI Act).
- [ ] **5.2 Bias & Fairness:** Has the agent's underlying model and prompt instructions been evaluated for demographic bias or discriminatory outcomes, particularly for employment, credit, or healthcare use cases?
- [ ] **5.3 Explainability:** When the agent takes an action, is the reasoning chain (the "Why") logged in a human-readable format for auditability?

## 6. Incident Response & Resiliency
*Containing the blast radius when things go wrong.*

- [ ] **6.1 The Kill Switch:** Does a Global Kill Switch exist that can instantly revoke the agent's IAM/SPIFFE identity at the infrastructure level?
- [ ] **6.2 Circuit Breakers:** Are there action budgets (e.g., max 5 tool calls per session) or rate limits enforced to prevent infinite execution loops?
- [ ] **6.3 Audit Logging:** Are all agent decisions, tool executions, and user interactions logged securely to a centralized SIEM (Security Information and Event Management) system, with PII redacted?
