# Deep Dive: Post-LLM Output Validation

Because LLMs are non-deterministic, probabilistic models, you cannot guarantee what text they will output. Output Validation is the process of building deterministic structural and semantic checks immediately after the LLM generates its text.

---

## 1. Structural Validation (JSON Enforcement)

The most common failure point in agentic pipelines is malformed JSON or mismatched schemas. Modern architectures (like Pydantic and provider Structured Outputs) enforce robust, typed schemas.

```python
from pydantic import BaseModel

class InvestigationResponse(BaseModel):
    summary: str
    evidence_ids: list[str]
    recommended_action: Literal["restart", "export", "monitor", "escalate"]
    confidence: float
```

If the LLM hallucinates an unsupported `recommended_action`, structural validation catches it before execution.

---

## 2. Output Validation Taxonomy

Valid Pydantic JSON does **not** mean the output is safe, grounded, or authorized. You must explicitly distinguish between different categories of failure:

| Failure Category | Example | System Action |
| :--- | :--- | :--- |
| **Schema/Structural Error** | Missing required field, malformed JSON. | **Repairable:** Sanitize error and ask model to retry. |
| **Unsupported Evidence** | Citing an `evidence_id` that was never retrieved. | **Abstain/Escalate:** The model is hallucinating data. |
| **Unauthorized Action** | Attempting a write action without the required roles. | **Deterministic Stop:** Block execution instantly. |
| **Cross-Tenant Violation** | Attempting to access data for a different tenant ID. | **Deterministic Stop:** Block execution instantly. |
| **Egress Denied** | Attempting to export records to an unapproved destination. | **Deterministic Stop:** Block execution instantly. |
| **Policy Violation** | Violating internal business logic (e.g., restarting during a blackout window). | **Deterministic Stop:** Block execution instantly. |

---

## 3. Bounded Repair Loop

For **schema/structural errors only**, you can implement a bounded repair loop:

1. Catch the schema failure (e.g., `ValidationError`).
2. **Sanitize the validation feedback.** Do not send raw internal exceptions, database traces, or stack traces back to the model.
3. Ask the model to fix the format (e.g., *"Your previous output was missing the 'confidence' field. Please provide the JSON with all required fields."*).
4. Limit retries (e.g., maximum of 3 attempts). 

**Do NOT retry policy, authorization, tenant, or egress failures.** If a model attempts a cross-tenant data export, you do not ask it to try again—you halt the trajectory and alert security.

---

## 4. Semantic Validation & Fallibility

Semantic validation involves evaluating the *meaning* or *safety* of the output, often using secondary LLMs (e.g., "Does this output perfectly align with the retrieved context?").

While these are useful signals for observability, **secondary LLM evaluators are fallible**. They can suffer from the same prompt injection and hallucination vulnerabilities as the primary model. Semantic validation is a defense-in-depth layer, but it does not replace deterministic application controls (like tenant scoping and tool authorization).

---

## 5. The "Abstain" Fallback

If an output violates a semantic guardrail, hallucinates evidence, or exhausts its repair budget, the architecture must gracefully fallback.

The agent should discard the bad output, halt the trajectory, and return a deterministic, hardcoded fallback string:
> *"I apologize, but I am having trouble processing this request right now. I will escalate this to a human support representative."*
