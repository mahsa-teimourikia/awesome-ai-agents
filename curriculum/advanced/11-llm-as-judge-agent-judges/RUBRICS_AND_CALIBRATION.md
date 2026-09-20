# Rubrics, agreement, and calibration

An unanchored “score this 1–5” prompt is not a measurement design. Begin with the decision the evaluation informs, separate criteria, define observable anchors, and identify which facts code can verify directly.

## Criterion-level results before aggregation

Do not collapse task correctness, grounding, authorization, safety, style, and efficiency into one score. A useful result resembles:

```text
authorization       FAIL   deterministic hard gate
outcome_binding     PASS   provider receipt op-123
grounding           4/5    semantic judgment
explanation_quality 3/5    semantic judgment
uncertainty         ABSTAIN missing provider-health evidence
```

Application policy aggregates these results. A failed authorization or safety gate forces overall failure regardless of an average. Valid JSON, citation existence, tenant match, allowlist adherence, latency, cost, approvals, and operation receipts are deterministic checks—not questions for an LLM.

Anchors should describe observable qualities. Appropriate uncertainty means identifying limits, alternative hypotheses, and missing evidence; an invented “93% confidence” is not inherently strong uncertainty handling.

## Reference design

Use three distinct stages:

```text
development/calibration set → refine rubric and prompt
held-out validation set      → estimate performance
production observations      → monitor drift and slices
```

Never report final performance only on examples used in the prompt, few-shot examples, or rubric development. Record those memberships so evaluation leakage is visible.

Human labels are reference measurements, not automatic truth. Keep individual rater labels, expertise, disagreement, and an adjudicated label. Ambiguity can be legitimate: `AMBIGUOUS`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` avoid manufacturing a 1–5 score.

## Agreement

Agreement asks whether judge labels resemble reference labels. Report several views:

- exact agreement;
- within-one agreement for an ordinal scale;
- mean absolute error;
- weighted Cohen's κ for two ordinal label streams;
- confusion matrix and false-pass/false-fail rates for the policy decision; and
- criterion, scenario, language, risk, and demographic slices appropriate to the system.

Unweighted κ treats 5→4 and 5→1 alike. Quadratic or linear weighting reflects ordinal distance, but the choice must be documented. For more than two human raters, consider Fleiss' κ, Krippendorff's α, or an intraclass correlation according to the sampling and label design.

There is no universal “good κ” threshold. Interpret judge performance relative to human reliability, prevalence, sample uncertainty, risk, and the decision consequence.

## Confidence calibration

Calibration asks whether confidence corresponds to empirical correctness. If a judge assigns 0.8 confidence across many comparable cases, about 80% should be correct for that probability to be calibrated.

The lab reports:

- **Brier score:** mean squared error between confidence and binary correctness;
- **expected calibration error (ECE):** a binned summary of the gap between confidence and observed correctness.

A judge may agree frequently but be overconfident, or disagree more often while expressing calibrated uncertainty. Agreement and calibration therefore need separate reports and acceptance limits.

## Versioning and drift

Every result binds the dataset, rubric, judge provider/model/deployment, model version, prompt version, inference settings, evaluator code, and evidence snapshot. Temperature zero can reduce variability where supported; it does not promise reproducibility across service or model changes.

Before upgrading a judge, rerun the same frozen validation set and compare agreement, pass rate, criteria, slices, and test–retest stability. When changing a rubric, replay old and new rubrics on the same frozen cases. Historical scores from different rubric versions are not directly interchangeable.

Use application-specific thresholds for false passes, false fails, agreement, calibration error, sample size, and critical slices. Start in shadow mode, progress through a constrained canary, and use blocking mode only when the evidence supports that consequence.
