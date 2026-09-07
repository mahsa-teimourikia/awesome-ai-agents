"""Credential-free Northstar lab for Advanced Course 02."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from policy import (
    AgentDefinition,
    AgentRole,
    EvidenceRecord,
    EvidenceStatus,
    SelectorDecision,
    SelectorSnapshot,
    TeamBudget,
    TeamContext,
    TeamMetrics,
    TeamRun,
    WorkerArtifact,
    apply_worker_turn,
    compute_gaps,
    derive_metrics,
    deterministic_selector,
    eligible_agents,
    ensure_can_continue,
    estimate_context_tokens,
    evaluate_selector,
    projected_selector_context,
    record_selector_call,
    termination_decision,
    validate_selector_decision,
)


FIXED_TIME = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
NORTHSTAR_QUESTION = (
    "Why did EU checkout conversion fall after deploy-1842, and what should we do?"
)
REQUIRED_EVIDENCE = (
    "health",
    "logs",
    "deployment",
    "customer-impact",
    "current-runbook",
)


def build_budget(**overrides: Any) -> TeamBudget:
    values = {
        "max_messages": 8,
        "max_selector_calls": 8,
        "max_worker_calls": 8,
        "max_turns_per_agent": 3,
        "max_repeated_speaker": 2,
        "max_cost_usd": 0.08,
        "deadline_ms": 4_000,
    }
    values.update(overrides)
    return TeamBudget(**values)


def build_agents() -> dict[str, AgentDefinition]:
    agents = (
        AgentDefinition(
            agent_id="ObservabilityAgent",
            role=AgentRole.OBSERVABILITY,
            allowed_capabilities=("health.read", "logs.read"),
            eligible_gap_types=("health", "logs"),
            max_turns=3,
            context_policy="health/log projections; no customer detail",
        ),
        AgentDefinition(
            agent_id="DeploymentAgent",
            role=AgentRole.DEPLOYMENT,
            allowed_capabilities=("deployment.read", "runbook.read"),
            eligible_gap_types=("deployment", "current-runbook"),
            max_turns=3,
            context_policy="deployment and current runbook projections",
        ),
        AgentDefinition(
            agent_id="CustomerImpactAgent",
            role=AgentRole.CUSTOMER_IMPACT,
            allowed_capabilities=("customer-impact.read",),
            eligible_gap_types=("customer-impact",),
            max_turns=3,
            context_policy="aggregated EU impact; no customer identifiers",
        ),
        AgentDefinition(
            agent_id="AnalystAgent",
            role=AgentRole.ANALYST,
            allowed_capabilities=(),
            eligible_gap_types=(),
            max_turns=3,
            context_policy="validated evidence summaries only; no production tools",
        ),
        AgentDefinition(
            agent_id="ReviewerAgent",
            role=AgentRole.REVIEWER,
            allowed_capabilities=(),
            eligible_gap_types=(),
            max_turns=3,
            context_policy="candidate diagnosis and evidence citations; no production tools",
        ),
    )
    return {agent.agent_id: agent for agent in agents}


def build_context(*, budget: TeamBudget | None = None) -> TeamContext:
    return TeamContext(
        tenant_id="northstar-commerce",
        incident_id="inc-eu-checkout-1842",
        goal=NORTHSTAR_QUESTION,
        required_evidence=REQUIRED_EVIDENCE,
        capability_policy={
            "ObservabilityAgent": ("health.read", "logs.read"),
            "DeploymentAgent": ("deployment.read", "runbook.read"),
            "CustomerImpactAgent": ("customer-impact.read",),
            "AnalystAgent": (),
            "ReviewerAgent": (),
        },
        source_allowlist={
            "health": ("metrics/eu-checkout/window-0900",),
            "logs": ("logs/checkout-api/3ds-callback/1842",),
            "deployment": ("deployments/deploy-1842",),
            "customer-impact": ("support/eu-enterprise/window-0900",),
            "current-runbook": ("runbooks/checkout-3ds/v7",),
        },
        budget=budget or build_budget(),
        policy_version="selector-team-v1",
    )


def build_evidence_catalog() -> dict[str, EvidenceRecord]:
    common = {
        "tenant_id": "northstar-commerce",
        "provenance_verified": True,
        "status": EvidenceStatus.COLLECTED,
        "created_at": FIXED_TIME,
    }
    return {
        "health": EvidenceRecord(
            evidence_id="health",
            evidence_type="health",
            source_id="metrics/eu-checkout/window-0900",
            capability="health.read",
            findings={"conversion_drop": "38%", "region": "EU"},
            **common,
        ),
        "logs": EvidenceRecord(
            evidence_id="logs",
            evidence_type="logs",
            source_id="logs/checkout-api/3ds-callback/1842",
            capability="logs.read",
            findings={"failure_mode": "3DS callback signature mismatch"},
            **common,
        ),
        "deployment": EvidenceRecord(
            evidence_id="deployment",
            evidence_type="deployment",
            source_id="deployments/deploy-1842",
            capability="deployment.read",
            findings={"change": "callback signature validation", "deploy": "deploy-1842"},
            **common,
        ),
        "customer-impact": EvidenceRecord(
            evidence_id="customer-impact",
            evidence_type="customer-impact",
            source_id="support/eu-enterprise/window-0900",
            capability="customer-impact.read",
            findings={"segment": "EU enterprise", "affected_sessions": "1,842"},
            **common,
        ),
        "current-runbook": EvidenceRecord(
            evidence_id="current-runbook",
            evidence_type="current-runbook",
            source_id="runbooks/checkout-3ds/v7",
            capability="runbook.read",
            findings={"next_step": "validate rollback candidate, then seek approval"},
            **common,
        ),
    }


def build_team(*, budget: TeamBudget | None = None) -> TeamRun:
    run = TeamRun(
        context=build_context(budget=budget),
        agents=build_agents(),
        gaps=(),
    )
    run.gaps = compute_gaps(run)
    return run


def artifact_for(run: TeamRun, decision: SelectorDecision) -> WorkerArtifact:
    catalog = build_evidence_catalog()
    agent_id = decision.next_agent
    if agent_id == "ObservabilityAgent":
        records = (catalog["health"], catalog["logs"])
        return WorkerArtifact(
            artifact_id="artifact-observability",
            agent_id=agent_id,
            tenant_id=run.context.tenant_id,
            evidence_ids=tuple(r.evidence_id for r in records),
            findings=("EU conversion fell 38%", "3DS callback signatures mismatch"),
            unresolved_questions=("Was deploy-1842 the introducing change?",),
            created_at=FIXED_TIME,
            evidence_records=records,
        )
    if agent_id == "DeploymentAgent":
        records = (catalog["deployment"], catalog["current-runbook"])
        return WorkerArtifact(
            artifact_id="artifact-deployment",
            agent_id=agent_id,
            tenant_id=run.context.tenant_id,
            evidence_ids=tuple(r.evidence_id for r in records),
            findings=("deploy-1842 changed callback validation", "runbook requires approval"),
            unresolved_questions=(),
            created_at=FIXED_TIME,
            evidence_records=records,
        )
    if agent_id == "CustomerImpactAgent":
        record = catalog["customer-impact"]
        return WorkerArtifact(
            artifact_id="artifact-customer",
            agent_id=agent_id,
            tenant_id=run.context.tenant_id,
            evidence_ids=(record.evidence_id,),
            findings=("1,842 EU enterprise checkout sessions were affected",),
            unresolved_questions=(),
            created_at=FIXED_TIME,
            evidence_records=(record,),
        )
    if agent_id == "AnalystAgent":
        return WorkerArtifact(
            artifact_id=f"artifact-analysis-{len(run.turns) + 1}",
            agent_id=agent_id,
            tenant_id=run.context.tenant_id,
            evidence_ids=REQUIRED_EVIDENCE,
            findings=("deploy-1842 is the likely source of the EU 3DS regression",),
            unresolved_questions=("Rollback requires a separate approval boundary",),
            created_at=FIXED_TIME,
            candidate_diagnosis=(
                "deploy-1842 introduced a 3DS callback signature regression; validate a "
                "rollback plan, then request approval under Course 03 controls"
            ),
        )
    if agent_id == "ReviewerAgent":
        return WorkerArtifact(
            artifact_id=f"artifact-review-{len(run.turns) + 1}",
            agent_id=agent_id,
            tenant_id=run.context.tenant_id,
            evidence_ids=REQUIRED_EVIDENCE,
            findings=("diagnosis is grounded and the action remains approval-gated",),
            unresolved_questions=(),
            created_at=FIXED_TIME,
            review_result="REVIEW_PASS",
            review_feedback="Evidence coverage and authorization boundary are explicit.",
        )
    raise ValueError(f"no fixture for {agent_id}")


def invoke_fixture_worker(run: TeamRun, decision: SelectorDecision) -> WorkerArtifact:
    """Represent the pre-invocation cancellation boundary in the offline lab."""
    ensure_can_continue(run)
    return artifact_for(run, decision)


def run_selector_team() -> TeamRun:
    run = build_team()
    while not termination_decision(run).should_stop:
        record_selector_call(run, tokens=42, cost_usd=0.0004, elapsed_ms=18)
        decision = deterministic_selector(run)
        validate_selector_decision(run, decision)
        if decision.next_agent is None:
            run.insufficient_evidence = True
            break
        apply_worker_turn(
            run,
            decision,
            invoke_fixture_worker(run, decision),
            worker_tokens=150,
            worker_cost_usd=0.002,
            elapsed_ms=70,
        )
    return run


def run_single_agent_baseline() -> TeamMetrics:
    """Same Northstar task and evidence contract, one generalist model call."""
    return TeamMetrics(
        run_type="single-generalist",
        task_success=True,
        grounded=True,
        required_evidence_recall=1.0,
        model_calls=1,
        selector_model_calls=0,
        worker_model_calls=1,
        selector_tokens=0,
        worker_tokens=610,
        total_tokens=610,
        wall_clock_ms=210,
        total_work_ms=210,
        selector_work_ms=0,
        worker_work_ms=210,
        selector_cost_usd=0,
        worker_cost_usd=0.0075,
        cost_usd=0.0075,
        cost_per_successful_compliant_task=0.0075,
        duplicate_turns=0,
    )


def compare_baseline() -> dict[str, TeamMetrics]:
    team = run_selector_team()
    return {
        "single-generalist": run_single_agent_baseline(),
        "selector-team": derive_metrics(team, run_type="selector-team"),
    }


def context_projection_experiment() -> dict[str, dict[str, int]]:
    run = run_selector_team()
    full = {
        "trusted_context": run.context.model_dump(mode="json"),
        "messages": [message.model_dump(mode="json") for message in run.messages],
    }
    projected = projected_selector_context(build_team())
    return {
        "full_transcript": {
            "input_tokens": estimate_context_tokens(full),
            "selector_accuracy_percent": 100,
            "sensitive_fields_exposed": 2,
        },
        "projected_state": {
            "input_tokens": estimate_context_tokens(projected),
            "selector_accuracy_percent": 100,
            "sensitive_fields_exposed": 0,
        },
    }


def build_selector_dataset() -> tuple[SelectorSnapshot, ...]:
    return (
        SelectorSnapshot(
            snapshot_id="two-valid-specialists",
            state_summary="health and deployment evidence are missing",
            eligible_agents=("ObservabilityAgent", "DeploymentAgent"),
            valid_next_agents=("ObservabilityAgent", "DeploymentAgent"),
            expected_termination="CONTINUE",
        ),
        SelectorSnapshot(
            snapshot_id="analysis-ready",
            state_summary="all required evidence collected; no candidate diagnosis",
            eligible_agents=("AnalystAgent",),
            valid_next_agents=("AnalystAgent",),
            expected_termination="CONTINUE",
        ),
        SelectorSnapshot(
            snapshot_id="review-ready",
            state_summary="candidate diagnosis exists",
            eligible_agents=("ReviewerAgent",),
            valid_next_agents=("ReviewerAgent",),
            expected_termination="CONTINUE",
        ),
        SelectorSnapshot(
            snapshot_id="no-safe-speaker",
            state_summary="required source unavailable and no alternative allowed",
            eligible_agents=(),
            valid_next_agents=(),
            expected_termination="INSUFFICIENT_EVIDENCE",
        ),
    )


def score_reference_selector():
    predictions = (
        "DeploymentAgent",
        "AnalystAgent",
        "ReviewerAgent",
        None,
    )
    return evaluate_selector(build_selector_dataset(), predictions)
