# Deep Dive: Data Protection Before Model Invocation

Data minimization is a core principle of enterprise architectures. While models and API providers often have zero-retention policies, reducing the amount of Personally Identifiable Information (PII) or sensitive data sent over the network is still a best practice. 

However, **data protection is not a security boundary against prompt injection.**

---

## 1. Compliance Realities

It is a common misconception that sending PII to a third-party model provider automatically violates HIPAA, GDPR, or SOC2. In reality, data processing compliance depends on:
- **Legal Basis:** Why is the data being processed?
- **Provider Agreements:** Do you have a Business Associate Agreement (BAA) or Data Processing Agreement (DPA) in place?
- **Retention Policies:** Does the provider train on the data or retain it?
- **Residency:** Where is the data processed geographically?
- **Organizational Policy:** What are your internal compliance mandates?

You should always minimize sensitive data, but understand that compliance is a holistic organizational process, not just a regex filter.

---

## 2. The Redaction Workflow

The goal of data minimization is to intercept the raw string, detect sensitive patterns, and replace them with placeholder tokens (e.g., `[REDACTED_SSN]`).

1. **User Input:** "My SSN is 123-45-6789 and my email is john@doe.com."
2. **Local Scrubber:** Runs Regex or NLP locally.
3. **PII-Reduced String:** "My SSN is `[REDACTED_SSN]` and my email is `[REDACTED_EMAIL]`."
4. **LLM Inference:** The LLM processes the reduced string.

*Note:* We call the output "PII-reduced" or "redacted" input, not "safe" input. Redacting an email address does nothing to stop a prompt injection attack embedded in the same sentence.

---

## 3. Regex vs. NLP (Microsoft Presidio)

### The Limits of Regex
Using Python's `re` module is fast and works well for structured data (like Credit Cards or Social Security Numbers). However, Regex fails at unstructured PII, such as detecting a person's name or address.

### Microsoft Presidio
**Microsoft Presidio** is a practical open-source option for this problem. It combines Regex with lightweight, local NLP models to perform Named Entity Recognition (NER) on the CPU. It can accurately detect and classify Names, Locations, Organizations, and standard ID numbers.

---

## 4. The Re-Hydration Pattern

Redacting data creates a problem: What if the agent actually *needs* that data to use a tool?

*Scenario:* A user asks to check their order status, providing their email. If you redact the email to `[REDACTED_EMAIL]`, the agent will call the `check_order(email="[REDACTED_EMAIL]")` tool, which will fail the database lookup.

### Architecture: The Secure Vault
To solve this, frameworks implement a **Vault Re-hydration** loop.

1. **Scrub & Store:** The local scrubber detects `john@doe.com`. It replaces it with a unique token `[TOKEN_991]`. 
2. **LLM Processing:** The LLM sees: "Check order for `[TOKEN_991]`".
3. **Tool Execution:** The LLM outputs a tool call: `check_order(email="[TOKEN_991]")`.
4. **Re-hydration:** *Before* the tool executes, the orchestration framework intercepts the payload and securely swaps `[TOKEN_991]` back to `john@doe.com`.

### Critical Security Constraints for Tokens
Tokenization is data protection, not authorization. A robust token system must bind the token to specific contexts:
- **Tenant Binding:** `[TOKEN_991]` can only be resolved for actions occurring within the `acme` tenant.
- **User/Session Binding:** Only the session that created the token can resolve it.
- **Tool/Field Binding:** `[TOKEN_991]` may only be permitted to resolve into the `email` field of the `check_order` tool. It cannot be used to inject strings into arbitrary tools.
- **TTL (Time to Live):** Tokens should expire quickly.
- **Purpose Restriction:** Tokens must explicitly state what they are allowed to be used for.

Without these bindings, an attacker could force the model to regurgitate `[TOKEN_991]` into an unauthorized export tool, bypassing the redaction entirely.
