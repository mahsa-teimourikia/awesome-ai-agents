# Agent Benchmarks and Enterprise Evals

**Advanced · 12** · **Time:** 90–120 min · **Prerequisites:** Advanced 09–11
**Notebook:** [`12_agent_benchmarks.ipynb`](12_agent_benchmarks.ipynb) · **Implementation:** [`policy.py`](policy.py) + [`lab.py`](lab.py)

Public benchmarks provide useful capability evidence. They do not, by themselves,
establish that an agent is safe, reliable, economical, or effective on a particular
enterprise workload. In this course you build the missing measurement system.

## Learning outcomes

By the end, you can:

- explain the distinct roles of capability benchmarks, enterprise workload evals,
  safety suites, regression suites, load tests, and production monitoring;
- govern versioned cases, environments, evaluator logic, held-out splits, leakage,
  sensitive data, and benchmark changes;
- evaluate authoritative outcomes and observable trajectories without relying on
  hidden chain-of-thought or self-declared grounding;
- report valid-run rates, Wilson intervals, per-slice support, operational costs,
  and cost per successful compliant task with explicit denominators;
- compare a baseline and candidate on the same cases, surface regressions, and
  apply risk-specific shadow, advisory, or blocking release policy; and
- close the loop from offline evaluation through shadow, canary, production
  monitoring, curated failure cases, and the next benchmark version.

## The central model

```text
public benchmark       -> capability evidence under stated assumptions
enterprise eval        -> workload and policy evidence in a versioned environment
production monitoring  -> operational evidence from changing real conditions
```

No one layer substitutes for the others. Public benchmarks remain useful for model
screening, research progress, capability comparison, and regression checks. An
enterprise suite adds private contracts and risk slices; monitoring tests whether
those assumptions continue to hold after release.

The authority boundary remains application-owned:

```text
agent under test -> proposes, calls tools, emits observable artifacts
trusted harness  -> resets state, validates evidence, checks outcomes and policy
release policy   -> compares versions and decides SHADOW / WARN / BLOCK
```

An agent saying `SUCCESS`, a tool being blocked by IAM, a judge assigning a high
score, or a benchmark leaderboard position does not authorize release.

## Evaluation-system architecture

```text
Versioned cases + held-out split + environment manifest
                         |
                         v
                  Agent under test
                         |
        observable events, artifacts, usage, receipts
                         |
                         v
            Deterministic application evaluators
       outcome | authorization | evidence | budgets | order
                         |
            optional calibrated semantic evaluators
                         |
                         v
        case results -> slice metrics -> paired comparison
                         |
                         v
          application-owned release policy and audit
```

Semantic evaluators are fallible measurement components, as taught in Advanced 11.
They cannot override deterministic authorization, tenant, approval, or secret gates.

## Public benchmark literacy

Public benchmarks test particular capabilities under standardized environments and
assumptions; they are not one interchangeable score.

| Benchmark | Evidence it can provide | Important boundary |
| --- | --- | --- |
| SWE-bench | Whether a system can resolve repository issues under its harness | Does not test your internal architecture, IAM, deployment, or review process |
| WebArena | Functional completion of web tasks in self-hosted, reproducible sites | Controlled sites do not reproduce every changing production website condition |
| GAIA | General-assistant questions involving reasoning, tools, browsing, and multimodality | Does not encode your private workflows or risk policy |
| τ-bench | Tool-agent-user interaction under domain policies | Its simulated domains and policies are not your production contracts |
| BrowserGym | A common environment and tooling for web-agent research | An environment layer is not an enterprise release policy |
| OSWorld | Open-ended computer tasks in a multimodal operating-system environment | OS task success does not establish authority for your systems |
| AgentBench | Agent capability across multiple interactive environments | Breadth across its environments does not prove workload-specific readiness |

Publicly available cases create a **contamination risk** when model training data is
unknown; they do not prove that a particular model memorized a particular case. This
course therefore records exposure as `PUBLIC_SOURCE`, `CONTROLLED_ENVIRONMENT`, or
`PRIVATE_HELD_OUT` instead of inventing unsupported HIGH/MEDIUM/LOW labels.

Private data is not automatically unexposed. Prompt development, few-shot examples,
fine-tuning, rubric work, debugging, repeated CI use, memory, and caches can all leak
evaluation cases. Keep a visible development set and a held-out validation/challenge
set, and rotate hidden challenges where practical.

Read [Public Benchmarks](PUBLIC_BENCHMARKS.md) for the taxonomy and claim boundaries.

## Dataset and case governance

`policy.py` binds each active case to:

```text
case_id + case_version + case_digest
source and provenance
development / validation / challenge split
risk and scenario slices
policy + environment + fixture versions
expected authoritative state
required and forbidden tools
partial-order constraints
cost and deadline budgets
reviewer and lifecycle status
```

A production failure is a **case candidate**, not ground truth. The lifecycle is:

```text
failure -> minimize and sanitize -> investigate -> establish expected behavior
        -> human review -> ACTIVE in a new dataset version -> later RETIRED
```

Expected-output changes require an explicit reason such as a changed product
requirement, changed policy, corrected ground truth, or fixed test bug. Benchmark
data, rubrics, environments, risk tags, and release thresholds are reviewed like
code because changing them can change whether software ships.

### Dataset sources

A mature suite combines:

- production-derived cases, which add workload realism but carry selection bias;
- expert-authored cases for requirements and rare domain behavior;
- adversarial and regression cases for known safety boundaries; and
- validated synthetic augmentation for boundaries and rare events.

Synthetic generation can propose useful cases. It must not independently establish
its own expected answer. The agent under test must not author, label, and approve the
test that judges it.

### Sensitive-data handling

The fixture demonstrates recursive structured-field removal, free-text redaction,
post-transformation scanning, and keyed stable pseudonyms. A keyed pseudonym is still
**pseudonymization**, not anonymization. Prefer data minimization: retain a tenant
class or policy profile rather than a production tenant identity when identity is not
needed.

Real trace use also needs approved purpose, access control, retention, regional and
contractual constraints, key management, and legal/compliance review. The lab is an
educational detector, not a production DLP product.

Read [Enterprise Evals](ENTERPRISE_EVALS.md) for lifecycle and environment guidance.

## Observable trajectory evaluation

The benchmark evaluates tool calls, tool results, explicit proposals, evidence IDs,
approvals, execution receipts, state transitions, and final artifacts. It does not ask
for or score private reasoning transcripts.

Cases specify sets and partial orders rather than one brittle exact sequence:

```text
required:  metrics.read, mitigation.propose
allowed:   logs.search
forbidden: production.rollback
order:     metrics.read BEFORE mitigation.propose
```

Two safe agents may order independent reads differently. The harness checks only
ordering that the contract makes material.

Grounding is also verified, not self-declared:

```text
claim -> cited evidence ID -> known tenant/version/digest -> support relation
```

An unauthorized action attempted and blocked by platform controls is still an agent
policy failure. It proves containment worked; it does not prove the agent behaved
safely. Hard failures are never averaged away by better style, cost, or task success.

Read [Trajectory Analysis](TRAJECTORY_ANALYSIS.md) for the observable-event model.

## Northstar benchmark fixture

The credential-free fixture contains 20 governed cases:

1. grounded and unsupported diagnosis;
2. safe mitigation and unauthorized mutation;
3. cross-tenant evidence and prompt injection in logs;
4. duplicate and stale events;
5. approval expiry and unknown provider outcomes;
6. provider timeout and reconciliation;
7. stale memory and wrong model routing;
8. proactive P1 alerts and notification storms;
9. long-running restart and evaluator abstention; and
10. high-cost and low-cost successful work.

Four cases are visible development fixtures. Sixteen validation/challenge cases feed
release metrics. Every case starts from a reset environment; the manifest records the
dataset, evaluator, policy, tools, knowledge snapshot, cache policy, agent configuration
digest, and deterministic seed.

The frozen candidate deliberately creates this comparison:

```text
3 improvements
1 critical cross-tenant regression
87.5% compliant success
release decision: BLOCK
```

The repaired profile removes the critical regression and passes the same blocking
policy. These fixture outputs validate evaluation plumbing and policy behavior—not
real model intelligence, routing accuracy, or generalization.

## Metrics with explicit meaning

The lab reports:

- task success and **compliant success** (`correct outcome AND every hard gate`);
- Wilson intervals and sample size for binary rates;
- invalid-run and harness-failure rates outside the agent-quality denominator;
- slice support, success, compliant success, and critical failures;
- wall-clock p50/p95 separately from model/tool/queue work;
- model calls, tool calls, retries, handoffs, and duplicate work; and
- model + tool + evaluator cost per successful compliant task.

Fewer calls are not automatically better. The trajectory report exposes missing,
unnecessary, forbidden, and duplicate calls. The release policy decides which
trade-offs matter. Multi-agent, routing, memory, proactive, long-running, and world-
model systems should add the domain metrics taught in Advanced 01–10.

Paired comparison runs baseline and candidate on identical cases and environment
versions:

```text
PASS -> FAIL = regression
FAIL -> PASS = improvement
harness-invalid on either side = invalid comparison
```

`+20` routine improvements cannot offset one cross-tenant regression. Quality, safety,
cost, latency, and reliability form a multi-objective decision—not an arbitrary
weighted average.

## Release modes and lifecycle

Start new or noisy metrics in `SHADOW`, promote understood signals to `ADVISORY`, and
make mature deterministic gates `BLOCKING`. Schema, tenant, authorization, approval,
and secret regressions can block while unstable semantic style changes warn or route
to human review.

```text
OFFLINE -> SHADOW -> CANARY -> PRODUCTION -> MONITOR
   ^                                         |
   +-- curated failures and disagreements <--+
```

Do not rerun until green. For stochastic cases, record repeated-run success
probability, variance, and flaky-case rate. Keep deterministic cases single-run.
Benchmark drift is also a product concern: monitor changing tools, policies, languages,
segments, and workflows while retaining deliberately overrepresented rare safety cases.

Exceptions require an owner, reason, mitigation, scope, issuance, and expiry. The
fixture refuses to waive critical safety regressions. Never silently disable the case.

## Run the course

From the repository root:

```bash
PYTHONPATH=. uv run --extra contributor --extra core \
  pytest -q tests/test_agent_benchmarks.py

PYTHONPATH=. uv run --extra core \
  python curriculum/advanced/12-agent-benchmarks/lab.py

PYTHONPATH=. uv run --extra core --extra contributor \
  python scripts/execute-notebooks.py --timeout 90 \
  curriculum/advanced/12-agent-benchmarks
```

## Failure patterns to recognize

| Failure | Why it misleads | Control |
| --- | --- | --- |
| One aggregate score | Easy cases hide severe slices | Slice support and hard gates |
| Exact tool sequence | Rejects valid independent orderings | Required/allowed/forbidden sets + partial order |
| `grounded=True` | Self-assertion is not evidence | Validate cited evidence and support |
| `SUCCESS` text | Output is not authoritative state | Check trusted environment state/receipt |
| IAM blocked the tool | Containment is mistaken for safe intent | Score agent behavior and platform containment separately |
| Private dataset | Privacy is mistaken for held-out status | Track every development exposure |
| Hash an ID | Pseudonymization is called anonymization | Minimize; use managed keyed pseudonyms if needed |
| Rerun until pass | Flakiness disappears from reports | Repeated trials with variance where appropriate |
| Harness crash = agent fail | Measurement error pollutes quality | Invalid-run and infrastructure-health accounting |
| Candidate changes cases | Test gaming changes the gate | Independent ownership and reviewed dataset versions |

## Exercises

1. Add an approval-order case: validated approval must precede an exact write, and a
   changed proposal must invalidate the receipt.
2. Add five trials for a stochastic candidate and report success probability, variance,
   and flaky-case rate without majority-vote hiding.
3. Freeze outputs, change the evaluator version, and compare old vs new measurements
   without overwriting history.
4. Add a representative workload weighting and show both weighted and unweighted
   results so rare critical slices stay visible.
5. Create an `ADVISORY` semantic metric and promote it to `BLOCKING` only after its
   evaluator reliability and operational response are defined.

## Checkpoint

**A candidate improves 12 routine cases but newly accesses one foreign tenant. Overall
compliant success still exceeds the threshold. What should a blocking safety policy do?**

<details>
<summary>Answer</summary>

Block the release. The cross-tenant regression is a hard gate with its own zero-failure
budget; it is not averaged against routine improvements.

</details>

**A sandbox database crashes for 4 of 20 cases. Should those four count as agent
failures?**

<details>
<summary>Answer</summary>

No. Report them as invalid/harness failures, expose a 20% invalid-run rate, repair the
harness, and avoid a release claim until valid support meets policy.

</details>

## Authoritative references

- [SWE-bench paper](https://proceedings.iclr.cc/paper_files/paper/2024/file/edac78c3e300629acfe6cbe9ca88fb84-Paper-Conference.pdf) and [official site](https://www.swebench.com/)
- [WebArena project](https://webarena.dev/og/)
- [GAIA paper](https://openreview.net/forum?id=fibxvahvs3)
- [τ-bench repository](https://github.com/sierra-research/tau-bench)
- [BrowserGym repository](https://github.com/ServiceNow/BrowserGym)
- [OSWorld project](https://os-world.github.io/)
- [AgentBench repository](https://github.com/THUDM/AgentBench)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST AI 600-1: Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)

Public benchmark APIs, datasets, leaderboards, and environments evolve. Pin the exact
version and inspect its current documentation before using a score in a decision.
