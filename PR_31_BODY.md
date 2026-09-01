## Overview
This PR hardens Course 04 (Guardrails and Untrusted Content) by enforcing deterministic containment principles. Detection is treated as an unreliable heuristic, and a strict gatekeeper architecture ensures untrusted data cannot expand tenant access, execution capability, or egress authorization.

## Architecture Updates
* **Validated Approval Context**: Replaced boolean `approved=True` fields with a cryptographically verified `ValidatedApprovalContext`. Write operations now strictly validate action, tenant, expiry, policy version, and target payload digest before execution.
* **Integrated Egress Validation**: Egress policy validation is now seamlessly integrated into `validate_tool_call()` for export operations, enforcing tenant, destination allowlist, sensitivity (RESTRICTED data), and `EgressPurpose` limits.
* **Containment over Detection**: A true "detector miss" end-to-end invariant test demonstrates that even if prompt injection bypasses regex filters, strict downstream capabilities and schema validation successfully block unauthorized execution.

## Policy & Runtime Changes
* Defined strict Pydantic v2 schemas for all tools using `ConfigDict(extra="forbid")` and tight `Literal` / `Field` constraints.
* Removed `tenant_id` from generic tool inputs, establishing `requested_tenant_id` as an explicitly untrusted parameter that can only narrow scope.
* Sanitized schema validation errors, safely returning structured hint data (field, error code, repair hint) without leaking internal Python exception strings.
* Renamed `PII_OR_SECRET_DETECTED` to `PII_PATTERN_DETECTED` to accurately reflect the heuristic nature of regex-based scanning.

## Testing & Validation
* Injected a comprehensive suite of tests in `tests/test_intermediate_invariants.py` for exact digest matches, expired approvals, incorrect actions, and stale policies.
* Expanded egress tests to cover restricted data destination validation, tenant mismatches, and purpose authorization.
* `04_guardrails_untrusted_content.ipynb` has been fully rewritten to use the hardened SOTA runtime architecture, maintaining clarity on the `REQUIRE_REVIEW` lesson regarding false positives.
* All Course 04 code executes successfully via headless validation.

## Cross-Course Asset Fixes
* **Intentional Chore**: Cleaned up the repository by moving unorganized `diagram.svg` files at the root of `05`, `06`, `08`, `09`, and `10` directories into their respective `assets/` subdirectories and securely updated relative Markdown links.
