# Deep Dive: Governed Enterprise Evaluation

## Build evidence, not a bag of examples

A release suite needs immutable case identity, governed expected behavior, held-out
splits, risk slices, a resettable versioned environment, reproducible run manifests,
and explicit metric denominators. A few copied production traces are useful teaching
fixtures, not automatically a “golden dataset.”

Use multiple sources:

```text
production-derived + expert-authored + adversarial
                   + validated synthetic + regression
```

Production traces add realism but inherit selection bias and sensitive data. Synthetic
cases expand boundaries but do not supply independent ground truth. Rare catastrophic
cases should be deliberately overrepresented in a safety suite even when their
production prevalence is low. Keep workload-representative and challenge-suite
aggregates separate.

## Case lifecycle

```text
CANDIDATE -> REVIEWED -> ACTIVE -> DEPRECATED -> RETIRED
```

An active case records its source, reviewer, risk tags, expected authoritative state,
policy/tool/environment versions, and digest. A changed expectation creates a reviewed
new version; do not silently edit the answer because a candidate failed.

Production-derived data requires minimization, structured and free-text detection,
redaction, post-transformation scanning, approved purpose, access and retention
controls, regional/contractual review, and a human quality check. Deterministic hashes
of guessable identifiers are pseudonyms, not anonymity. Use a managed keyed HMAC or
generated surrogate only when stable linkage is actually required.

## Environment fidelity

Use a deterministic controlled test double appropriate to the behavior under test:

- fixtures for simple lookups;
- state machines for workflow transitions;
- a reset SQLite sandbox for transactional behavior;
- fake providers for timeouts, 429/500 responses, partial failures, and unknown outcomes;
- record/replay snapshots for volatile external data.

Record environment and fixture versions, tool contracts, knowledge snapshot, cache
policy, and seed. Reset independent cases and verify that A→B and B→A produce equivalent
results. Persistent-memory scenarios should explicitly identify scenario, episode, and
sequence rather than leak state accidentally.

## Run and result manifests

`BenchmarkRunManifest` binds the benchmark/dataset/evaluator versions to environment,
agent configuration, split, seed, and start time. The agent configuration digest covers
model/deployment, prompt, tools, policy, router, and memory configuration.

`CaseResult` distinguishes:

```text
PASS | FAIL | ABSTAIN | TIMEOUT | INSUFFICIENT_EVIDENCE | INVALID_RUN
```

Harness startup, fixture, tool-simulation, and evaluator failures are measurement
failures. Report them separately instead of lowering agent quality. A high invalid-run
rate makes the benchmark untrustworthy even when the valid subset looks strong.

## Release governance

Compare baseline and candidate on identical case and environment versions. Cluster
regressions by stable reason codes and retain safe representative failure artifacts.
Use `SHADOW`, `ADVISORY`, and `BLOCKING` modes according to metric maturity and risk.

A release exception is an audited decision with owner, rationale, mitigation, exact
scope, issuance, and expiry—not a disabled test. Revisit expired exceptions and retain
the history of benchmark, gate, exception, and release changes.
