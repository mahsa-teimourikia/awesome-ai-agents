# 03 — Guardrails and untrusted content

**Notebook:** [`12_agentops_guardrails_untrusted_content.ipynb`](12_agentops_guardrails_untrusted_content.ipynb)  
**Implementation:** [`shared/agentops_lab/guardrails_untrusted_content.py`](../../shared/agentops_lab/guardrails_untrusted_content.py)

Retrieve a poisoned runbook, treat it as data rather than authority, and enforce
tool-level approval checks. The lesson separates trusted instructions from
untrusted retrieved text and tool responses.
