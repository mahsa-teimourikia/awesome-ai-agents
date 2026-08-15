# Deep Dive: Pre-LLM Regex & PII Scrubbing

The fundamental rule of Enterprise Generative AI is: **Do not send sensitive data to an LLM provider.**

Even if OpenAI or Anthropic have zero-retention policies, passing Personally Identifiable Information (PII) or Protected Health Information (PHI) over the network to a third-party inference endpoint violates HIPAA, GDPR, and SOC2 compliance standards.

To solve this, SOTA architectures implement **Pre-LLM Guardrails**, operating entirely locally on the CPU *before* the API call is made.

---

## 1. The Redaction Workflow

The goal is to intercept the raw user string, detect sensitive patterns, and replace them with placeholder tokens (e.g., `[REDACTED_SSN]`).

1. **User Input:** "My SSN is 123-45-6789 and my email is john@doe.com."
2. **Local Scrubber:** Runs Regex and NLP locally.
3. **Safe String:** "My SSN is `[REDACTED_SSN]` and my email is `[REDACTED_EMAIL]`."
4. **LLM Inference:** The LLM processes the safe string and generates a response.

---

## 2. Regex vs. NLP (Microsoft Presidio)

### The Limits of Regex
Using Python's `re` module is fast and works well for structured data (like Credit Cards or Social Security Numbers).
```python
import re
safe_text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', user_input)
```
However, Regex fails at unstructured PII, such as detecting a person's name ("John Doe") or an address ("123 Main St, Springfield").

### The SOTA Solution: Presidio
Enterprise architectures rely on open-source libraries like **Microsoft Presidio**. Presidio combines Regex with lightweight, local NLP models (like spaCy) to perform Named Entity Recognition (NER) on the CPU.

It can accurately detect and classify Names, Locations, Organizations, and standard ID numbers with high confidence, without ever sending data out of your VPC.

---

## 3. The Re-Hydration Pattern

Redacting data creates a problem: What if the agent actually *needs* that data to use a tool?

*Scenario:* A user asks to check their order status, providing their email: "Check order for john@doe.com."
If you redact the email to `[REDACTED_EMAIL]`, the agent will call the `check_order(email="[REDACTED_EMAIL]")` tool, which will fail the database lookup.

### SOTA Architecture: The Secure Vault
To solve this, frameworks implement a **Vault Re-hydration** loop.

1. **Scrub & Store:** The local scrubber detects `john@doe.com`. It replaces it with a unique token `[TOKEN_991]` and stores the mapping `{"[TOKEN_991]": "john@doe.com"}` in a secure, local dictionary.
2. **LLM Processing:** The LLM sees: "Check order for `[TOKEN_991]`".
3. **Tool Execution:** The LLM outputs a tool call: `check_order(email="[TOKEN_991]")`.
4. **Re-hydration:** *Before* the tool actually executes against the database, the orchestration framework intercepts the payload, detects the token, and securely swaps `[TOKEN_991]` back to `john@doe.com`.

The LLM never saw the real email, but the backend tool executed flawlessly.
