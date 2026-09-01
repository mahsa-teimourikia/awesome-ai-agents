# Deep Dive: Deterministic, Semantic, and Trajectory Evaluation

In traditional software, evaluating code is often binary. A unit test asserts `2 + 2 == 4`. In Agentic Engineering, outputs are stochastic. A correct final answer is only part of the story.

A robust Agent Evaluation Subsystem must measure outcome, evidence, trajectory, safety, robustness, cost, and latency. **A good final answer does not mean a good agent run.**

---

## 1. Deterministic Evaluators First

Before engaging expensive and subjective LLM graders, you must evaluate deterministic facts deterministically.

An LLM Judge should **not** be used to check if a tenant ID matches, if a forbidden tool was used, or if a cost budget was exceeded. These are objective facts present in the agent's observable trace.

**Examples of Deterministic Graders:**
*   `check_forbidden_tools()`: Did the agent attempt an unauthorized write?
*   `check_tenant_isolation()`: Did the agent attempt to query another tenant's data?
*   `check_required_evidence()`: Did the final answer cite the mandatory logs?
*   `check_latency_budget()`: Did the run exceed the p95 SLA?

Deterministic graders run fast, cost nothing, and provide a 100% reliable foundation for Release Gates.

---

## 2. Semantic Judges

LLM judges are widely used for semantic dimensions where deterministic graders are insufficient.

You use a capable LLM to grade ambiguous criteria:
*   **Diagnosis Quality**: Did the agent correctly interpret the complex logs?
*   **Helpfulness**: Is the tone appropriate and the summary clear?
*   **Evidence Sufficiency**: Does the cited evidence logically support the conclusion?
*   **Uncertainty Calibration**: Did the agent correctly express doubt when the evidence was conflicting?

### Structured Rubrics
Binary rubrics (True/False) are useful for crisp criteria. Ordinal, pairwise, or categorical scoring can be appropriate depending on the task.

**Example Semantic Rubric Score:**
```json
{
  "diagnosis_supported": true,
  "addresses_user_goal": true,
  "uncertainty_calibrated": false,
  "overall_label": "FAIL",
  "justification": "The diagnosis was correct, but the agent was overly confident despite missing secondary logs."
}
```

### Trace Projection
Do **not** send entire raw traces to the Judge LLM by default. Large raw outputs confuse the judge and waste tokens. 
You must project the trace: include only relevant tool names, arguments (redacting secrets/PII), statuses, and evidence IDs.

### Judge Calibration
A larger or more expensive model (e.g., GPT-4o, Claude 3.5) does not automatically imply a reliable evaluator. 
Judge scales require anchoring and calibration. You must maintain a small human-labeled reference set and compute the Judge's **accuracy, precision, and recall** against human labels to ensure its scores remain meaningful.

---

## 3. Trajectory Grading

Outcome scoring checks the final answer. Trajectory evaluation scores the *path* the agent took.

You evaluate the observable actions and state transitions, **not** the hidden chain-of-thought storage. Chain-of-thought is an internal mechanism; the trajectory is the actual impact on your systems.

**Key Trajectory Metrics:**
*   **Failed Calls vs Bounded Retries**: A tool timeout followed by a successful retry is acceptable.
*   **Unnecessary Duplicates**: Calling the same tool with the same arguments three times in a row, when all succeeded, is a non-idempotent duplicate side effect.
*   **Tool Order**: Did the agent query the database before authenticating?

---

## 4. Operational Metrics

Enterprise evaluation requires measuring the operational reality of the agent.

*   **Cost per Policy-Compliant Success**: `total_cost / number_of_compliant_successes`. An agent that gets the right answer but loops inefficiently will destroy your budget at scale.
*   **Tail Latency**: Averages hide failures. You must track p95 and p99 latency percentiles to ensure the agent doesn't hang in production.

---

## 5. Release Gates

Evaluation culminates in a Release Gate—code that automatically decides if an agent version can proceed to production.

Release decisions are driven by hard constraints, not a human glance at a dashboard. Safety failures (e.g., a cross-tenant violation) **must not be averaged away**. Even if an agent improves outcome pass rate by 5%, a single forbidden action violation means a `FAIL`.

**Example Gate:**
*   `min_outcome_pass_rate`: 90%
*   `max_forbidden_action_rate`: 0% (Strict zero tolerance)
*   `max_cost_per_success`: $0.50

A Release Decision returns `PASS`, `FAIL`, or `NEEDS_REVIEW` along with a list of failed constraints and regressions compared to the baseline agent.
