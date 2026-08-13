# Agent Benchmarks

**Level:** Advanced · **Time:** 60 min · **Prerequisites:** None

**Advanced · 12** · **Reference guide (no lab/notebook by design)**

Agent benchmarks are useful instruments for selecting research directions, comparing candidate systems, and designing evaluations. They are not production certifications. A score obtained under a fixed task distribution, tool sandbox, grading setup, model version, time limit, and prompt policy does not prove reliability under an enterprise’s identities, data, workflows, latency/SLOs, adversaries, approval rules, operational failures, or changing external systems.

## Benchmark literacy: what a score does and does not mean

Before citing a score, record the exact benchmark version/split, model/provider version, prompting and tools, budget/timeout, retries, environment/browser state, pass@k or single-run protocol, grading method, cost/latency, and contamination/overlap risk. Compare like with like. A benchmark may reward task completion while failing to measure policy compliance, data boundaries, explainability, recovery, user trust, or operational cost.

## Major benchmarks

| Benchmark | Primary environment / capability | Use it when | Do not infer |
| --- | --- | --- |
| [SWE-bench](https://www.swebench.com/) | Resolve real GitHub issues in repositories; code editing/tests | Evaluating coding-agent repository repair | General agent safety, enterprise change control, or all software tasks |
| [WebArena](https://webarena.dev/) | Realistic web tasks in self-hosted websites | Web navigation, forms, multi-site task completion | Reliability on a live changing web or a user’s authenticated data |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym) | Browser-agent environments and tasks | Training/evaluating browser interaction policies | Real end-user browser safety, consent, or accessibility coverage |
| [GAIA](https://huggingface.co/spaces/gaia-benchmark/leaderboard) | General assistant questions requiring reasoning/tools/multimodality | Broad assistant capability and tool reasoning | Long-lived autonomy, operational policy compliance, or domain expertise |
| [τ-bench](https://arxiv.org/abs/2406.12045) | Tool-agent customer-service tasks with policy/database state | Tool use, policy adherence, stateful interaction | Your own tools, customers, identity model, or production workload |
| [OSWorld](https://os-world.github.io/) | Multi-app computer-use tasks in desktop OS environment | GUI/OS agent progress and recovery | Safety in a real endpoint, sensitive file access, or authorization |
| [AgentBench](https://github.com/THUDM/AgentBench) | Multiple agent environments: OS, DB, web, games, etc. | Cross-environment research comparison | A single reliable production system or consistent scoring across versions |
| Domain benchmarks | Industry task distribution and policies | Finance, healthcare, support, security, or internal workflows | Generalization beyond the domain/data and its governance constraints |
| Custom enterprise benchmark | Representative anonymized/permissioned tasks, policies, traces | Release gate for a specific system | A public leaderboard claim or universal model ranking |

## Step-by-step guide: choosing and using benchmarks

1. **Start with a production decision.** Define the task family, user impact, allowed tools/actions, data/tenant scope, success, latency/cost limits, failure severity, and human oversight—not a desired leaderboard score.
2. **Pick the nearest environment.** Use SWE-bench for repository repair, WebArena/BrowserGym for browser mechanics, OSWorld for desktop interaction, τ-bench for stateful policy/tool behavior, GAIA/AgentBench for broad research diagnostics. A nearest public benchmark is still only a proxy.
3. **Reproduce a baseline faithfully.** Pin version, seeds, model/tool configuration, environment, budget, and evaluator. Publish cost/latency and failure rate, not success only.
4. **Inspect trajectories.** Record tool arguments, retries, unauthorized attempts, context/source use, state transitions, terminal reason, and recovery. A final pass may hide unsafe or wasteful behavior.
5. **Add adversarial and operational tests.** Include prompt injection, stale/poisoned context, tool outage, duplicate action, rate/budget exhaustion, cross-tenant request, approval expiry, and rollback/recovery.
6. **Build an enterprise evaluation set.** Curate representative tasks with consent/redaction, expected outcome/evidence/tools/forbidden actions, policy labels, human rubric, and replayable deterministic fixtures. Include easy, routine, ambiguous, and high-risk slices.
7. **Use a release gate.** Require outcome plus evidence, policy, trajectory, operations, security, and human-agreement thresholds. Monitor drift after model/prompt/tool/policy/environment changes.

## Designing a custom enterprise benchmark

Use a task record such as: `{task_id, tenant_safe_fixture, input, allowed_tools, forbidden_tools, expected_outcome, evidence_requirements, policy_requirements, human_rubric, latency_budget, cost_budget, severity}`. Separate offline replay from shadow/canary production evaluation. Never populate an evaluation set with secrets, unrestricted customer data, or tasks whose “success” requires unsafe irreversible action.

Score at least five layers: outcome/grounding, trajectory/tool arguments, policy/authorization, operations (cost/latency/retry), and robustness/recovery. Add a human-labeled calibration slice for LLM judges. Track performance by task/risk/tenant/language/tool and compare against a simpler workflow or human baseline.

## State of the art and references

- [SWE-bench paper](https://arxiv.org/abs/2310.06770) · [WebArena paper](https://arxiv.org/abs/2307.13854) · [BrowserGym paper](https://arxiv.org/abs/2405.07760)
- [GAIA paper](https://arxiv.org/abs/2311.12983) · [τ-bench paper](https://arxiv.org/abs/2406.12045) · [OSWorld paper](https://arxiv.org/abs/2404.07972) · [AgentBench paper](https://arxiv.org/abs/2308.03688)
- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) · [Anthropic: demystifying agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) · [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)


## Watch For

- **Assumption failure:** The model hallucinates an unsupported parameter.
- **State leak:** Context is incorrectly preserved across runs.
- **Timeout:** The tool takes too long and the agent loops.
- **Auth bypass:** The agent attempts an action it shouldn't.


## Checkpoint

**1. What is the primary purpose of this module?**
- A) To understand the core concept.
- B) To write complex boilerplate.
- C) To ignore system errors.
- D) To bypass security.

**2. How do we mitigate the primary failure mode?**
- A) Retries.
- B) Human approval.
- C) Logging.
- D) Idempotency keys.

