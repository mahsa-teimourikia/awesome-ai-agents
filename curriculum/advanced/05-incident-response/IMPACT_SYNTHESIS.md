# Deep Dive: Impact Synthesis

Impact synthesis converts accepted operational and business evidence into a scoped `ImpactAssessment`. A model can explain the result, but deterministic code owns counts, percentages, severity, duration, and contractual calculations.

## Platform tenant is not customer account

`tenant_id` identifies the organization whose incident the platform is handling. `customer_account_id` identifies one of that organization's customers. Mixing these concepts can leak data or corrupt blast-radius calculations.

The lab prefers aggregate projections: affected account count, tier counts, region, failed transactions, and conversion change. It does not enumerate customer PII. Records for another platform tenant are rejected; Globex and Acme appear only in adversarial tests.

## Deterministic inputs

`ImpactAssessment` cites the accepted metrics, customer-impact aggregate, and SLA evidence used to produce:

- affected service and region;
- affected account and tier counts;
- failed transaction count;
- conversion impact;
- potential SLA exposure.

The model must not recreate authoritative math from prose or memory. A concise generated summary may sit on top of the typed assessment after the same evidence and tenant checks.

## Severity policy

Severity is derived from structured dimensions: availability impact, affected accounts, duration, and security or regulatory implications. The fixture maps those inputs to `SEV1`, `SEV2`, or `SEV3` through policy code. Model language such as “this feels critical” cannot alter the state.

Severity may be recalculated as accepted evidence changes, with the transition written to the audit trail. Escalation and de-escalation are policy events, not silent edits to prose.

## Versioned SLA evidence

A contractual record includes contract ID and version, effective dates, threshold minutes, credit formula, and monthly fee. The calculator first checks that the terms were effective when the incident began. Missing version or an invalid effective window fails validation.

The output is **potential SLA exposure**, not “money owed.” Final liability may depend on exclusions, recovery evidence, contract interpretation, and a separate business or legal process.

## Incident brief language

A sound brief distinguishes verified observations from a leading hypothesis:

```text
Verified impact: EU checkout conversion is down 31%; 24 Northstar accounts affected.
Leading hypothesis: deploy-1842 regressed the EU 3DS adapter.
Contradiction: Redis saturation is not present.
Unknowns: none currently blocking; provider health was checked.
Potential SLA exposure: deterministic estimate from contract 2026-v3.
Next decision: independent review of an exact rollback proposal.
```

During the outage this is an incident brief, not a postmortem. Confirmed root cause and corrected diagnosis history belong in a post-recovery artifact.
