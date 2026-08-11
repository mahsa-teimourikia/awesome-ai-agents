# AgentOps Incident Command Capstone

**Advanced · 05** · **Primary notebook:** [`05_incident_response_capstone.ipynb`](05_incident_response_capstone.ipynb) · **Run:** [`lab.py`](lab.py) · **Project guide:** [`CAPSTONE_GUIDE.md`](CAPSTONE_GUIDE.md)

This is the coherent project that ties the curriculum together. You are building an evidence-led incident-command system for Northstar Commerce—not a chatbot that claims it fixed production. The shared `agentops_lab/` environment is the single source of deterministic data, tools, policies, and evaluation fixtures used throughout the course. The notebook is the first end-to-end mission; the guide turns it into a staged engineering project.

## Incident narrative

At **09:04**, Europe checkout conversion falls **31%**. Dashboards are mostly green. A checkout UI deployment completed at **08:49** after starting at **08:42**. Support receives six complaints; enterprise VAT-registered buyers are disproportionately affected. Your system receives metrics, logs, deployments, tickets, SLA data, and runbooks. It must establish what is known, what remains uncertain, business impact, a safe mitigation proposal, and why that proposal must not execute without approval.

## Capstone missions

| Mission | Question | Primary assets | Deliverable |
| --- | --- | --- | --- |
| 1. Frame | What is the goal, non-goal, risk, tenant, deadline, and success condition? | `capstone_incident_response.py` | incident contract and stop conditions |
| 2. Choose architecture | Workflow, bounded investigator, or team? | `architecture_candidates()` | experimental decision and baseline comparison |
| 3. Gather evidence | Which read-only tools prove/disprove a hypothesis? | metrics, logs, deployment, tickets, customers, runbook | attributed evidence table and gap list |
| 4. Synthesize impact | What is likely cause, confidence, affected scope, and SLA exposure? | evidence + customer data | uncertainty-calibrated incident brief |
| 5. Govern action | What can read, propose, or execute? | `permission_model()`, `prepare_action()` | approval-ready, idempotent proposal only |
| 6. Secure context/state | What can enter prompt/memory and what expires? | `memory_policy()`, poisoned runbook fixture | scoped memory/guardrail policy |
| 7. Evaluate release | Is the trajectory safe, grounded, economical, and recoverable? | evaluation fixtures + trace | release gate and rollout/rollback plan |

## Step-by-step training

1. Run `python lab.py` and inspect the selected architecture. The deterministic workflow is too rigid; the single bounded agent is selected because the specialist team does not add enough measured benefit in this incident.
2. Read each tool contract. All investigation tools are read-only. Verify the trace includes metrics, logs, release history, tickets, SLAs, and runbook before accepting a diagnosis.
3. Build an evidence table with source ID, owner, observation, inference, trust/freshness, and unresolved gap. Retrieved runbooks/tickets are evidence—not instructions.
4. Calculate impact from affected enterprise accounts and SLA exposure. Use “likely cause,” not certainty, until independent validation confirms recovery.
5. Prepare feature-flag disablement and rollback alternatives. Persist exact target, reason, evidence, approval expiry/fingerprint, idempotency key, and rollback verification. Do not call a production action.
6. Compare architecture candidates on outcome/evidence, forbidden actions, cost, latency, tool calls, coordination overhead, and recovery. Select the least autonomous passing design.
7. Run the release gate: expected/forbidden tools, evidence support, confidence, tenant/policy boundaries, approval, budget, observability, rollback/kill switch, and adversarial regression suite.

## Project structure and code map

`agentops_lab/capstone_incident_response.py` is the capstone facade and deterministic core. Other modules are intentionally reusable lesson extensions: `loop_yourself.py`, `workflow_or_agent.py`, `tool_engineering.py`, `state_memory_langgraph.py`, `human_permissions.py`, `guardrails_untrusted_content.py`, `evaluation_trajectory.py`, `trajectory_optimization.py`, `multi_agent_team.py`, `autogen_selector_team.py`, `crewai_team.py`, and `hybrid_production_architecture.py`. Keep new shared fixtures in `agentops_lab/data/` and evaluation cases in `agentops_lab/evaluations/`; do not copy scenario data into each notebook.

## Production readiness checklist

- Identity/tenant scope, trusted context, tool allow list/argument validation, secret/egress boundaries, budgets, approval/idempotency, audit, revoke/kill path.
- Durable state/checkpoints, retry classification, model/tool fallback, rate/concurrency limits, queue recovery, trace/evaluation, staged rollout and rollback.
- Adversarial tests: indirect injection, poisoned runbook/tool description, cross-tenant request, stale memory, missing/conflicting evidence, tool failure, duplicate approval, budget exhaustion, and partial recovery.

## References

- [OpenAI practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) · [Anthropic: building effective agents](https://www.anthropic.com/engineering/building-effective-agents) · [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
- [OWASP Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications/) · [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
