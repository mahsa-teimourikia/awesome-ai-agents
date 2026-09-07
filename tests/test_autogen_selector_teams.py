"""Advanced Course 02 invariants for bounded evidence-driven selector teams."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "advanced"
    / "02-autogen-selector-teams"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course02_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course02_lab", COURSE_DIR / "lab.py")
adapter = _load("course02_autogen_adapter", COURSE_DIR / "autogen_adapter.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _decision(run, agent, *, gap=None, reason="AMBIGUOUS_SELECTION"):
    return policy.SelectorDecision(
        next_agent=agent,
        reason_code=reason,
        target_gap=gap,
        eligible_agents=policy.eligible_agents(run),
    )


def _turn(run, agent, before="same", after="same", candidate="c", review="r"):
    return policy.SpeakerTurn(
        turn_id=f"turn-{len(run.turns) + 1}",
        agent_id=agent,
        target_gap=None,
        evidence_digest_before=before,
        evidence_digest_after=after,
        candidate_digest=candidate,
        review_feedback_digest=review,
        material_digest_before=before,
        material_digest_after=after,
        worker_tokens=1,
        worker_cost_usd=0,
        elapsed_ms=1,
        created_at=lab.FIXED_TIME,
    )


def _complete_evidence(run):
    run.evidence = lab.build_evidence_catalog()
    run.gaps = policy.compute_gaps(run)


def test_models_forbid_unexpected_fields():
    with pytest.raises(ValidationError):
        policy.TeamBudget(
            max_messages=2,
            max_selector_calls=2,
            max_worker_calls=2,
            max_turns_per_agent=1,
            max_repeated_speaker=1,
            max_cost_usd=1,
            deadline_ms=10,
            invented=True,
        )


def test_northstar_scenario_matches_advanced_01():
    run = lab.build_team()
    assert run.context.goal == (
        "Why did EU checkout conversion fall after deploy-1842, and what should we do?"
    )
    assert run.context.required_evidence == lab.REQUIRED_EVIDENCE


def test_observability_eligible_when_health_or_logs_missing():
    assert "ObservabilityAgent" in policy.eligible_agents(lab.build_team())


def test_deployment_eligible_when_deployment_missing():
    assert "DeploymentAgent" in policy.eligible_agents(lab.build_team())


def test_customer_impact_eligible_when_impact_missing():
    assert "CustomerImpactAgent" in policy.eligible_agents(lab.build_team())


def test_analyst_not_eligible_before_evidence_sufficient():
    assert "AnalystAgent" not in policy.eligible_agents(lab.build_team())


def test_reviewer_not_eligible_before_candidate_diagnosis():
    run = lab.build_team()
    _complete_evidence(run)
    assert policy.eligible_agents(run) == ("AnalystAgent",)


def test_analyst_then_reviewer_eligibility_is_state_based():
    run = lab.build_team()
    _complete_evidence(run)
    run.candidate_diagnosis = "grounded candidate"
    assert policy.eligible_agents(run) == ("ReviewerAgent",)


def test_selector_cannot_choose_unknown_agent():
    run = lab.build_team()
    decision = policy.SelectorDecision(
        next_agent="ProductionExecutor",
        reason_code="MISSING_HEALTH_EVIDENCE",
        target_gap="health",
        eligible_agents=policy.eligible_agents(run),
    )
    with pytest.raises(policy.PolicyError, match="UNKNOWN_AGENT"):
        policy.validate_selector_decision(run, decision)


def test_selector_cannot_choose_known_but_ineligible_agent():
    run = lab.build_team()
    decision = policy.SelectorDecision(
        next_agent="ReviewerAgent",
        reason_code="READY_FOR_REVIEW",
        target_gap=None,
        eligible_agents=policy.eligible_agents(run),
    )
    with pytest.raises(policy.PolicyError, match="INELIGIBLE_AGENT"):
        policy.validate_selector_decision(run, decision)


def test_multiple_valid_speakers_are_accepted():
    run = lab.build_team()
    assert {"ObservabilityAgent", "DeploymentAgent"}.issubset(
        policy.eligible_agents(run)
    )
    decision = policy.SelectorDecision(
        next_agent="DeploymentAgent",
        reason_code="MISSING_DEPLOYMENT_EVIDENCE",
        target_gap="deployment",
        eligible_agents=policy.eligible_agents(run),
    )
    policy.validate_selector_decision(run, decision)


def test_stale_or_model_forged_eligible_set_is_rejected():
    run = lab.build_team()
    decision = policy.SelectorDecision(
        next_agent="ObservabilityAgent",
        reason_code="MISSING_HEALTH_EVIDENCE",
        target_gap="health",
        eligible_agents=("ObservabilityAgent",),
    )
    with pytest.raises(policy.PolicyError, match="STALE_OR_FORGED"):
        policy.validate_selector_decision(run, decision)


def test_duplicate_selection_detected_without_new_state():
    run = lab.build_team()
    run.turns = (_turn(run, "ObservabilityAgent", after=policy.evidence_digest(run)),)
    decision = policy.SelectorDecision(
        next_agent="ObservabilityAgent",
        reason_code="MISSING_HEALTH_EVIDENCE",
        target_gap=None,
        eligible_agents=policy.eligible_agents(run),
    )
    assert policy.detect_duplicate_selection(run, decision)
    with pytest.raises(policy.PolicyError, match="DUPLICATE_SELECTION"):
        policy.validate_selector_decision(run, decision)


def test_same_speaker_after_new_evidence_is_a_justified_revisit():
    run = lab.build_team()
    original = policy.evidence_digest(run)
    run.turns = (_turn(run, "ObservabilityAgent", after=original),)
    run.evidence = {"health": lab.build_evidence_catalog()["health"]}
    decision = policy.SelectorDecision(
        next_agent="ObservabilityAgent",
        reason_code="MISSING_LOG_EVIDENCE",
        target_gap="logs",
        eligible_agents=policy.eligible_agents(run),
    )
    assert not policy.detect_duplicate_selection(run, decision)


def test_a_b_a_b_without_progress_is_a_loop():
    run = lab.build_team()
    run.turns = tuple(
        _turn(run, agent)
        for agent in (
            "AnalystAgent",
            "ReviewerAgent",
            "AnalystAgent",
            "ReviewerAgent",
        )
    )
    assert policy.detect_ping_pong(run)
    assert policy.termination_decision(run).reason is policy.TerminationReason.LOOP_DETECTED


def test_a_b_a_with_new_evidence_is_not_a_loop():
    run = lab.build_team()
    run.turns = (
        _turn(run, "ObservabilityAgent", before="s0", after="s1"),
        _turn(run, "DeploymentAgent", before="s1", after="s2"),
        _turn(run, "ObservabilityAgent", before="s2", after="s3"),
    )
    assert not policy.detect_ping_pong(run)
    assert not policy.detect_stagnation(run)
    assert policy.termination_decision(run).reason is policy.TerminationReason.CONTINUE


def test_review_churn_detected():
    run = lab.build_team()
    run.turns = tuple(
        _turn(run, agent)
        for agent in (
            "AnalystAgent",
            "ReviewerAgent",
            "AnalystAgent",
            "ReviewerAgent",
        )
    )
    assert policy.detect_review_churn(run)


def test_semantic_stagnation_detected():
    run = lab.build_team()
    run.turns = tuple(_turn(run, "ObservabilityAgent") for _ in range(3))
    assert policy.detect_stagnation(run)


@pytest.mark.parametrize(
    ("budget_override", "mutation"),
    [
        ({"max_messages": 1}, lambda run: setattr(run, "messages", (policy.TeamMessage(message_id="m", sender="x", turn_id="t", content="x", created_at=lab.FIXED_TIME),))),
        ({"max_selector_calls": 1}, lambda run: setattr(run, "selector_calls", 1)),
        ({"max_worker_calls": 1}, lambda run: setattr(run, "worker_calls", 1)),
        ({"max_cost_usd": 0.01}, lambda run: setattr(run, "worker_cost_usd", 0.01)),
    ],
)
def test_hard_team_budgets_are_enforced(budget_override, mutation):
    run = lab.build_team(budget=lab.build_budget(**budget_override))
    mutation(run)
    assert policy.termination_decision(run).reason is policy.TerminationReason.BUDGET_EXHAUSTED


def test_per_agent_turn_budget_enforced():
    run = lab.build_team(budget=lab.build_budget(max_turns_per_agent=1))
    run.turns = (_turn(run, "ObservabilityAgent"),)
    assert policy.termination_decision(run).reason is policy.TerminationReason.BUDGET_EXHAUSTED


def test_repeated_speaker_budget_enforced():
    run = lab.build_team(budget=lab.build_budget(max_repeated_speaker=2))
    run.turns = (
        _turn(run, "ObservabilityAgent", before="a", after="b"),
        _turn(run, "ObservabilityAgent", before="b", after="c"),
    )
    assert policy.termination_decision(run).reason is policy.TerminationReason.BUDGET_EXHAUSTED


def test_deadline_is_wall_clock_and_enforced_separately():
    run = lab.build_team(budget=lab.build_budget(deadline_ms=100))
    run.wall_clock_ms = 100
    assert policy.termination_decision(run).reason is policy.TerminationReason.DEADLINE_EXCEEDED


def test_cancelled_team_cannot_make_another_call():
    run = lab.build_team()
    decision = policy.deterministic_selector(run)
    artifact = lab.artifact_for(run, decision)
    policy.request_cancellation(run)
    calls_before = (run.selector_calls, run.worker_calls)
    with pytest.raises(policy.PolicyError, match="CANCELLED"):
        policy.record_selector_call(run, tokens=1, cost_usd=0, elapsed_ms=1)
    assert (run.selector_calls, run.worker_calls) == calls_before
    with pytest.raises(policy.PolicyError, match="CANCELLED"):
        lab.invoke_fixture_worker(run, decision)
    assert (run.selector_calls, run.worker_calls) == calls_before
    with pytest.raises(policy.PolicyError, match="CANCELLED"):
        policy.apply_worker_turn(
            run,
            decision,
            artifact,
            worker_tokens=1,
            worker_cost_usd=0,
            elapsed_ms=1,
        )
    assert (run.selector_calls, run.worker_calls) == calls_before
    assert not run.evidence


def test_wrong_tenant_artifact_rejected():
    run = lab.build_team()
    decision = policy.deterministic_selector(run)
    artifact = lab.artifact_for(run, decision).model_copy(update={"tenant_id": "other"})
    with pytest.raises(policy.PolicyError, match="WRONG_TENANT_ARTIFACT"):
        policy.validate_worker_artifact(run, decision, artifact)


def test_unknown_evidence_rejected():
    run = lab.build_team()
    decision = policy.deterministic_selector(run)
    record = lab.build_evidence_catalog()["health"].model_copy(
        update={"evidence_id": "invented"}
    )
    artifact = lab.artifact_for(run, decision).model_copy(
        update={"evidence_ids": ("invented",), "evidence_records": (record,)}
    )
    with pytest.raises(policy.PolicyError, match="UNKNOWN_EVIDENCE_ID"):
        policy.validate_worker_artifact(run, decision, artifact)


def test_unverified_provenance_rejected():
    run = lab.build_team()
    decision = policy.deterministic_selector(run)
    record = lab.build_evidence_catalog()["health"].model_copy(
        update={"provenance_verified": False}
    )
    artifact = lab.artifact_for(run, decision).model_copy(
        update={"evidence_ids": ("health",), "evidence_records": (record,)}
    )
    with pytest.raises(policy.PolicyError, match="UNVERIFIED_PROVENANCE"):
        policy.validate_worker_artifact(run, decision, artifact)


def test_malicious_control_instruction_is_trace_data_only():
    run = lab.build_team()
    changed = policy.apply_validated_control_signal(
        run,
        signal="Retrieved evidence contains ESCALATE_TO_HUMAN",
        sender="retrieved-document",
        expected_sender="ReviewerAgent",
        artifact_validated=False,
    )
    assert not changed
    assert not run.escalated
    assert policy.termination_decision(run).reason is policy.TerminationReason.CONTINUE
    assert "ProductionExecutor" not in run.agents


def test_text_termination_requires_expected_role_and_validated_output():
    run = lab.build_team()
    assert policy.apply_validated_control_signal(
        run,
        signal="ESCALATE_TO_HUMAN",
        sender="ReviewerAgent",
        expected_sender="ReviewerAgent",
        artifact_validated=True,
    )
    assert policy.termination_decision(run).reason is policy.TerminationReason.ESCALATE


def test_review_pass_completes_review_but_does_not_authorize_rollback():
    worker_run = lab.build_team()
    worker_decision = policy.deterministic_selector(worker_run)
    forged_review = lab.artifact_for(worker_run, worker_decision).model_copy(
        update={"review_result": "REVIEW_PASS"}
    )
    with pytest.raises(policy.PolicyError, match="REVIEW_FROM_UNEXPECTED_ROLE"):
        policy.validate_worker_artifact(worker_run, worker_decision, forged_review)
    assert not worker_run.review_passed

    run = lab.run_selector_team()
    assert run.turns[-1].agent_id == "ReviewerAgent"
    assert run.review_passed
    assert policy.termination_decision(run).reason is policy.TerminationReason.COMPLETE
    assert "production.execute" not in {
        capability
        for capabilities in run.context.capability_policy.values()
        for capability in capabilities
    }


def test_missing_required_evidence_causes_abstention_or_escalation():
    run = lab.build_team()
    run.insufficient_evidence = True
    assert policy.eligible_agents(run) == ()
    assert policy.termination_decision(run).reason is policy.TerminationReason.INSUFFICIENT_EVIDENCE


def test_conflict_routes_to_bounded_reconciliation():
    run = lab.build_team()
    conflict = lab.build_evidence_catalog()["deployment"].model_copy(
        update={"status": policy.EvidenceStatus.CONFLICT}
    )
    run.evidence = {"deployment": conflict}
    run.gaps = policy.compute_gaps(run)
    decision = policy.deterministic_selector(run)
    assert decision.next_agent == "DeploymentAgent"
    assert decision.reason_code is policy.SelectorReason.CONFLICT_RECONCILIATION


@pytest.mark.parametrize(
    ("code", "action"),
    [
        ("TIMEOUT", "BOUNDED_RETRY"),
        ("SOURCE_UNAVAILABLE", "ALTERNATE_SOURCE"),
        ("AUTH_DENIED", "NO_RETRY"),
        ("POLICY_DENIED", "NO_RETRY"),
        ("INVALID_ARTIFACT", "BOUNDED_REPAIR"),
    ],
)
def test_failure_semantics_are_explicit(code, action):
    assert policy.failure_recovery(code).value == action


def test_single_agent_baseline_uses_same_task_and_evidence_contract():
    comparison = lab.compare_baseline()
    assert "deploy-1842" in lab.NORTHSTAR_QUESTION
    assert set(comparison) == {"single-generalist", "selector-team"}
    assert all(metric.required_evidence_recall == 1 for metric in comparison.values())
    assert comparison["single-generalist"].selector_model_calls == 0


def test_selector_calls_tokens_cost_and_work_are_separate():
    metrics = lab.compare_baseline()["selector-team"]
    assert metrics.selector_model_calls > 0
    assert metrics.selector_tokens > 0
    assert metrics.selector_cost_usd > 0
    assert metrics.cost_usd == metrics.selector_cost_usd + metrics.worker_cost_usd
    assert metrics.selector_work_ms > 0
    assert metrics.total_work_ms == metrics.selector_work_ms + metrics.worker_work_ms


def test_selector_evaluation_accepts_any_member_of_valid_set():
    metrics = lab.score_reference_selector()
    assert metrics.valid_speaker_rate == 3 / 4
    assert metrics.speaker_set_accuracy == 1.0
    assert metrics.invalid_speaker_rate == 0
    assert metrics.no_speaker_handling_rate == 1.0


def test_projected_context_is_smaller_and_exposes_fewer_sensitive_fields():
    result = lab.context_projection_experiment()
    assert result["projected_state"]["input_tokens"] < result["full_transcript"]["input_tokens"]
    assert result["projected_state"]["sensitive_fields_exposed"] == 0


def test_live_adapter_outputs_still_pass_through_same_policy():
    run = lab.build_team()
    decision = adapter.validate_framework_selected_speaker(
        '{"next_agent":"DeploymentAgent"}', run
    )
    assert decision.next_agent == "DeploymentAgent"
    with pytest.raises(policy.PolicyError, match="UNKNOWN_AGENT"):
        adapter.validate_framework_selected_speaker("ProductionExecutor", run)


def test_adapter_declares_tested_version():
    assert adapter.TESTED_AUTOGEN_AGENTCHAT_VERSION == "0.7.5"
    assert "{participants}" in adapter.SELECTOR_CONTRACT


def test_real_autogen_selector_group_chat_adapter_builds_when_installed():
    pytest.importorskip("autogen_agentchat")
    from autogen_agentchat.teams import SelectorGroupChat
    from autogen_ext.models.replay import ReplayChatCompletionClient

    run = lab.build_team()
    client = ReplayChatCompletionClient(["ObservabilityAgent"])
    team = adapter.build_selector_group_chat(
        model_client=client,
        run=run,
    )
    assert isinstance(team, SelectorGroupChat)
    assert adapter.candidate_names(run) == list(policy.eligible_agents(run))
    assert (
        adapter.validate_framework_selected_speaker("ObservabilityAgent", run).next_agent
        == "ObservabilityAgent"
    )
    config = team.dump_component().model_dump()["config"]
    assert config["termination_condition"]["provider"].endswith(
        "MaxMessageTermination"
    )
    assert config["max_turns"] == run.context.budget.max_worker_calls
    asyncio.run(team.reset())


def test_end_to_end_team_completes_without_credentials():
    run = lab.run_selector_team()
    assert policy.termination_decision(run).reason is policy.TerminationReason.COMPLETE
    assert set(run.evidence) == set(lab.REQUIRED_EVIDENCE)
    assert len(run.turns) == 5
