## Overview
This PR completes the final hardening of Course 04 (Guardrails and Untrusted Content) by introducing a deterministic containment policy layer. Detection is now properly framed as an unreliable heuristic, and strict gatekeeper architecture ensures untrusted data cannot expand tenant access, execution capability, or egress authorization.

## Architecture Updates
* **Course 04 Poisoned-Content Overhaul**: Rewrote the core containment narrative. Untrusted content is eligible for delimited inclusion but remains untrusted; it is never declared "safe" solely because a regex detector found nothing.
* **Deterministic Policy Layer**: Added robust structural, authority, approval, and egress validation stages into a unified `validate_tool_call()` gateway. The model is completely stripped of the authority to dictate data sensitivity, tenant boundaries, or final destination logic.
* **Typed Tool Schemas**: Defined strict Pydantic v2 schemas for all tools using `ConfigDict(extra="forbid")` and tight `Literal` / `Field` constraints. Validation errors are sanitized and safely returned as structured hint data.
* **Approval Validation**: Cryptographically verified `ValidatedApprovalContext` replaces boolean fields. Write operations strictly validate action, tenant, expiry, policy version, and canonical target payload digest before execution.
* **Integrated Egress Controls**: Egress policy validation is now seamlessly integrated into `validate_tool_call()`. Egress strictly uses the trusted `resource_sensitivity` parameter (e.g., `RESTRICTED`) rather than trusting the model's requested arguments, blocking sensitivity-downgrade bypasses.
* **Output Validation**: Enforces strict content scanning on model-generated tool outputs to catch indirect prompt injections that bypass inputs but appear in RAG or Tool returns.
* **Adversarial Tests**: Comprehensive end-to-end invariant tests verify exact digest matches, expired approvals, incorrect actions, stale policies, and "detector miss" scenarios where downstream invariants safely catch prompt injections.
* **Intentional Cross-Course Diagram-Path Fixes**: Cleaned up the repository by moving unorganized `diagram.svg` files at the root of `05`, `06`, `08`, `09`, and `10` directories into their respective `assets/` subdirectories and securely updated relative Markdown links.
