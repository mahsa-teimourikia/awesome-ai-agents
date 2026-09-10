"""Advanced Course 05 incident-response capstone invariants."""

from __future__ import annotations

from datetime import timedelta
import importlib.util
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "advanced"
    / "05-incident-response"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course05_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course05_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _admitted():
    alert = lab.admit_fixture_alert()
    state = lab.new_run_state(alert.context)
    registry = policy.EvidenceRegistry(
        incident_id=alert.context.incident_id, tenant_id=alert.context.tenant_id
    )
    return alert, state, registry


def _investigated(*, resolve_gap: bool = True):
    alert, state, registry = _admitted()
    lab.initial_investigation(state, registry)
    if resolve_gap:
        lab.resolve_provider_gap(state, registry)
    impact = lab.build_impact_assessment(state, registry)
    brief = lab.build_incident_brief(state, registry, impact)
    return alert, state, registry, impact, brief


def _proposal_path():
    alert, state, registry, impact, brief = _investigated()
    proposal = lab.build_mitigation_proposal(state, registry)
    review = lab.review_proposal(proposal, registry)
    approval = lab.build_approval_receipt(proposal)
    policy.acquire_coordinator_lease(
        state, coordinator_id="coordinator-1", now=lab.FIXED_TIME
    )
    return alert, state, registry, proposal, review, approval


def test_models_forbid_extra_fields():
    payload = lab.webhook_payload()
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.IncidentEvent(**payload, hidden_authority=True)


def test_valid_webhook_is_admitted_with_trusted_context():
    alert = lab.admit_fixture_alert()
    assert alert.disposition is policy.AdmissionDisposition.ADMITTED
    assert alert.context.tenant_id == lab.TENANT_ID
    assert alert.context.service_id == lab.SERVICE_ID
    assert set(alert.context.investigation_capabilities).issubset(
        policy.READ_ONLY_CAPABILITIES
    )


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"event_type": "noise"}, "UNSUPPORTED_EVENT_TYPE"),
        ({"tenant_id": "globex"}, "TENANT_MAPPING_MISMATCH"),
        ({"service_id": "billing"}, "SERVICE_MAPPING_MISMATCH"),
    ],
)
def test_invalid_webhook_fields_are_rejected(change, error):
    payload = lab.webhook_payload()
    payload.update(change)
    with pytest.raises(policy.PolicyError, match=error):
        lab.admit_fixture_alert(payload=payload, signature=policy.sign_webhook(payload))


def test_invalid_webhook_signature_is_rejected():
    with pytest.raises(policy.PolicyError, match="INVALID_WEBHOOK_SIGNATURE"):
        lab.admit_fixture_alert(signature="not-valid")


def test_duplicate_webhook_is_deduplicated():
    registry = policy.AlertRegistry()
    first = lab.admit_fixture_alert(registry=registry)
    second = lab.admit_fixture_alert(registry=registry)
    assert first.disposition is policy.AdmissionDisposition.ADMITTED
    assert second.disposition is policy.AdmissionDisposition.DUPLICATE
    assert len(registry.processed_keys) == 1


def test_stale_event_does_not_reopen_resolved_incident():
    registry = policy.AlertRegistry(
        terminal_incidents={lab.INCIDENT_ID: lab.FIXED_TIME}
    )
    result = lab.admit_fixture_alert(registry=registry)
    assert result.disposition is policy.AdmissionDisposition.STALE


def test_state_machine_rejects_skipping_to_resolved():
    _, state, _ = _admitted()
    with pytest.raises(policy.PolicyError, match="INVALID_STATE_TRANSITION"):
        policy.transition_incident(state, policy.IncidentStatus.RESOLVED)


def test_investigation_context_rejects_write_capability():
    alert = lab.admit_fixture_alert()
    with pytest.raises(ValidationError, match="INVESTIGATION_WRITE_CAPABILITY_DENIED"):
        alert.context.model_copy(
            update={
                "investigation_capabilities": (
                    *alert.context.investigation_capabilities,
                    policy.Capability.DEPLOYMENT_ROLLBACK,
                )
            }
        ).model_validate(
            {
                **alert.context.model_dump(),
                "investigation_capabilities": [policy.Capability.DEPLOYMENT_ROLLBACK],
            }
        )


@pytest.mark.parametrize(
    "capability",
    [
        policy.Capability.DEPLOYMENT_ROLLBACK,
        policy.Capability.FEATURE_FLAG_WRITE,
        policy.Capability.SERVICE_RESTART,
        policy.Capability.CACHE_FLUSH,
    ],
)
def test_read_only_phase_denies_every_write(capability):
    alert = lab.admit_fixture_alert()
    with pytest.raises(policy.PolicyError, match="INVESTIGATION_WRITE_DENIED"):
        policy.require_investigation_capability(alert.context, capability)


def test_unknown_tool_has_no_capability():
    with pytest.raises(ValueError):
        policy.Capability("shell.exec")


def test_evidence_provenance_and_event_time_are_preserved():
    _, state, registry = _admitted()
    record = lab.collect_evidence(state, registry, "ev-deploy")
    assert registry.records[record.evidence_id].digest == record.digest
    assert record.event_time < record.retrieved_at
    assert record.source_version == "registry-v5"
    assert policy.build_timeline(registry).evidence_ids == ("ev-deploy",)


def test_stale_evidence_is_rejected():
    alert, _, registry = _admitted()
    original = lab.fixture_evidence(alert.context)["ev-metrics"]
    stale = policy.build_evidence_record(
        **{
            **original.model_dump(exclude={"digest"}),
            "retrieved_at": lab.FIXED_TIME - timedelta(minutes=3),
        }
    )
    with pytest.raises(policy.PolicyError, match="STALE_EVIDENCE"):
        policy.accept_evidence(registry, alert.context, stale, now=lab.FIXED_TIME)


def test_investigation_deadline_stops_next_retrieval():
    _, state, registry = _admitted()
    with pytest.raises(policy.PolicyError, match="INVESTIGATION_DEADLINE_EXCEEDED"):
        lab.collect_evidence(
            state,
            registry,
            "ev-metrics",
            now=lab.FIXED_TIME + timedelta(milliseconds=1),
        )
    assert state.tool_calls == 0


def test_wrong_tenant_evidence_is_rejected():
    alert, _, registry = _admitted()
    original = lab.fixture_evidence(alert.context)["ev-metrics"]
    wrong = original.model_copy(update={"tenant_id": "globex"})
    with pytest.raises(policy.PolicyError, match="EVIDENCE_TENANT_MISMATCH"):
        policy.accept_evidence(registry, alert.context, wrong, now=lab.FIXED_TIME)


def test_cross_tenant_customer_account_is_rejected():
    alert, _, registry = _admitted()
    original = lab.fixture_evidence(alert.context)["ev-tickets"]
    wrong = policy.build_evidence_record(
        **{
            **original.model_dump(exclude={"digest"}),
            "customer_account_id": "acct-globex-1",
        }
    )
    with pytest.raises(policy.PolicyError, match="CROSS_TENANT_ACCOUNT_REJECTED"):
        policy.accept_evidence(registry, alert.context, wrong, now=lab.FIXED_TIME)


def test_prompt_injection_in_log_cannot_change_policy():
    _, state, registry = _admitted()
    record = lab.collect_evidence(state, registry, "ev-logs")
    assert "restart Redis" in record.safe_excerpt
    assert policy.Capability.SERVICE_RESTART not in state.context.investigation_capabilities
    with pytest.raises(policy.PolicyError, match="INVESTIGATION_WRITE_DENIED"):
        policy.require_investigation_capability(
            state.context, policy.Capability.SERVICE_RESTART
        )


def test_ticket_text_cannot_authorize_write():
    _, state, registry = _admitted()
    lab.collect_evidence(state, registry, "ev-tickets")
    assert not hasattr(state, "approved")
    with pytest.raises(policy.PolicyError, match="INVESTIGATION_WRITE_DENIED"):
        policy.require_investigation_capability(
            state.context, policy.Capability.FEATURE_FLAG_WRITE
        )


def test_observation_is_separate_from_inference():
    alert = lab.admit_fixture_alert()
    record = lab.fixture_evidence(alert.context)["ev-deploy"]
    assert "caused" not in record.safe_excerpt.casefold()
    assert "inference" not in policy.EvidenceRecord.model_fields
    assert "statement" in policy.Hypothesis.model_fields


def test_deployment_timing_alone_does_not_confirm_root_cause():
    _, state, registry = _admitted()
    lab.collect_evidence(state, registry, "ev-deploy")
    hypothesis = policy.Hypothesis(
        hypothesis_id="h",
        statement="deployment caused outage",
        supporting_evidence_ids=("ev-deploy",),
        status=policy.HypothesisStatus.PARTIALLY_SUPPORTED,
    )
    claim = policy.Claim(
        claim_id="root",
        kind=policy.ClaimKind.CONFIRMED_ROOT_CAUSE,
        text="deployment caused outage",
        evidence_ids=("ev-deploy",),
        hypothesis_id="h",
    )
    with pytest.raises(policy.PolicyError, match="ROOT_CAUSE_NOT_CONFIRMED"):
        policy.validate_claim(claim, registry=registry, hypotheses={"h": hypothesis})


def test_missing_provider_status_creates_a_gap():
    _, state, registry = _admitted()
    hypotheses = lab.initial_investigation(state, registry)
    assert state.status is policy.IncidentStatus.EVIDENCE_INCOMPLETE
    assert state.gaps[0].resolved_by is None
    assert hypotheses[0].status is policy.HypothesisStatus.PARTIALLY_SUPPORTED


def test_bounded_corrective_retrieval_resolves_gap_and_competing_hypotheses():
    _, state, registry = _admitted()
    lab.initial_investigation(state, registry)
    hypotheses = lab.resolve_provider_gap(state, registry)
    assert state.replans == 1
    assert state.gaps[0].resolved_by == "ev-provider"
    assert hypotheses[0].status is policy.HypothesisStatus.SUPPORTED
    assert hypotheses[1].status is policy.HypothesisStatus.CONTRADICTED
    assert hypotheses[2].status is policy.HypothesisStatus.CONTRADICTED


def test_unavailable_gap_source_escalates_without_fabricating_answer():
    _, state, registry = _admitted()
    lab.initial_investigation(state, registry)
    calls_before = state.tool_calls
    with pytest.raises(policy.PolicyError, match="SOURCE_UNAVAILABLE"):
        lab.resolve_provider_gap(state, registry, provider_available=False)
    assert state.status is policy.IncidentStatus.ESCALATED
    assert state.tool_calls == calls_before


def test_conflicting_authoritative_facts_require_reconciliation():
    alert, state, registry = _admitted()
    healthy = lab.collect_evidence(state, registry, "ev-provider")
    degraded = policy.build_evidence_record(
        **{
            **healthy.model_dump(exclude={"digest", "evidence_id", "source_id"}),
            "evidence_id": "ev-provider-secondary",
            "source_id": "synthetic-probe:3ds-eu",
            "structured_facts": {
                **healthy.structured_facts,
                "healthy": False,
            },
        }
    )
    policy.accept_evidence(registry, alert.context, degraded, now=lab.FIXED_TIME)
    with pytest.raises(policy.PolicyError, match="CONFLICTING_EVIDENCE"):
        policy.detect_conflicting_fact(
            registry,
            evidence_ids=(healthy.evidence_id, degraded.evidence_id),
            fact_name="healthy",
        )


def test_replan_budget_stops_unbounded_corrective_retrieval():
    _, state, registry = _admitted()
    lab.initial_investigation(state, registry)
    state.replans = lab.DEFAULT_BUDGET.max_replans
    with pytest.raises(policy.PolicyError, match="REPLAN_BUDGET_EXCEEDED"):
        lab.resolve_provider_gap(state, registry)


def test_unsupported_claim_is_rejected():
    _, _, registry = _admitted()
    claim = policy.Claim(
        claim_id="unsupported",
        kind=policy.ClaimKind.INFERENCE,
        text="Redis failed",
        evidence_ids=("made-up",),
    )
    with pytest.raises(policy.PolicyError, match="INVALID_EVIDENCE"):
        policy.validate_claim(claim, registry=registry, hypotheses={})


@pytest.mark.parametrize(
    ("availability", "accounts", "duration", "security", "expected"),
    [
        (0.6, 1, 1, False, policy.IncidentSeverity.SEV1),
        (0.2, 24, 16, False, policy.IncidentSeverity.SEV2),
        (0.01, 1, 2, False, policy.IncidentSeverity.SEV3),
        (0.01, 1, 2, True, policy.IncidentSeverity.SEV1),
    ],
)
def test_severity_is_derived_deterministically(
    availability, accounts, duration, security, expected
):
    assert (
        policy.derive_severity(
            availability_impact=availability,
            affected_accounts=accounts,
            duration_minutes=duration,
            security_or_regulatory=security,
        )
        is expected
    )


def test_impact_and_potential_sla_exposure_are_deterministic():
    _, state, registry, impact, _ = _investigated()
    assert state.severity is policy.IncidentSeverity.SEV2
    assert impact.affected_accounts_count == 24
    assert impact.potential_sla_exposure_usd == 5000
    assert impact.evidence_ids == ("ev-metrics", "ev-impact", "ev-sla")


def test_sla_contract_version_is_required():
    with pytest.raises(ValidationError):
        policy.SlaContract(
            contract_id="sla",
            contract_version="",
            effective_from=lab.FIXED_TIME,
            effective_to=lab.FIXED_TIME + timedelta(days=1),
            threshold_minutes=15,
            credit_rate=0.1,
            monthly_fee_usd=50000,
        )


def test_incident_brief_preserves_unresolved_gap():
    _, state, registry = _admitted()
    lab.initial_investigation(state, registry)
    impact = lab.build_impact_assessment(state, registry)
    brief = lab.build_incident_brief(state, registry, impact)
    assert brief.unresolved_gaps[0].gap_id == "gap-provider-health"
    assert "leading hypothesis" in brief.claims[1].text


def test_proposal_requires_resolved_gap():
    _, state, registry = _admitted()
    lab.initial_investigation(state, registry)
    with pytest.raises(policy.PolicyError, match="UNRESOLVED_EVIDENCE_GAP"):
        lab.build_mitigation_proposal(state, registry)


def test_mitigation_uses_typed_exact_target_not_shell():
    _, _, _, proposal, _, _ = _proposal_path()
    assert isinstance(proposal.typed_parameters, policy.RollbackDeploymentArgs)
    assert proposal.target == lab.TARGET_DEPLOYMENT
    with pytest.raises(ValidationError):
        policy.MitigationProposal.model_validate(
            {**proposal.model_dump(), "action_type": "git revert deploy-1842"}
        )


def test_proposal_is_bound_to_evidence_snapshot():
    alert, state, registry, proposal, review, approval = _proposal_path()
    original = registry.records["ev-metrics"]
    changed = policy.build_evidence_record(
        **{
            **original.model_dump(exclude={"digest"}),
            "structured_facts": {**original.structured_facts, "error_rate": 0.2},
        }
    )
    registry.records["ev-metrics"] = changed
    with pytest.raises(policy.PolicyError, match="PROPOSAL_EVIDENCE_STALE"):
        policy.validate_proposal(proposal, context=alert.context, registry=registry)
    with pytest.raises(policy.PolicyError, match="PROPOSAL_EVIDENCE_STALE"):
        lab.execute_mitigation(
            state,
            proposal,
            review,
            approval,
            lab.OrchestratorStore(),
            registry,
        )
    assert state.mitigation_attempts == 0


def test_review_pass_is_not_approval():
    _, state, registry, proposal, review, _ = _proposal_path()
    assert review.status is policy.MitigationStatus.REVIEW_PASS
    with pytest.raises(policy.PolicyError, match="APPROVAL_REQUIRED"):
        lab.execute_mitigation(
            state, proposal, review, None, lab.OrchestratorStore(), registry
        )


def test_execution_requires_the_active_coordinator_lease():
    _, state, registry, _, _ = _investigated()
    proposal = lab.build_mitigation_proposal(state, registry)
    review = lab.review_proposal(proposal, registry)
    approval = lab.build_approval_receipt(proposal)
    with pytest.raises(policy.PolicyError, match="COORDINATOR_LEASE_REQUIRED"):
        lab.execute_mitigation(
            state,
            proposal,
            review,
            approval,
            lab.OrchestratorStore(),
            registry,
        )


@pytest.mark.parametrize(
    ("update", "error"),
    [
        ({"target": "deploy-1841"}, "APPROVAL_TARGET_MISMATCH"),
        ({"tenant_id": "globex"}, "APPROVAL_TENANT_MISMATCH"),
        ({"policy_version": "stale"}, "APPROVAL_POLICY_STALE"),
        (
            {
                "issued_at": lab.FIXED_TIME - timedelta(hours=1),
                "expires_at": lab.FIXED_TIME - timedelta(minutes=1),
            },
            "APPROVAL_EXPIRED",
        ),
    ],
)
def test_invalid_approval_bindings_are_rejected(update, error):
    alert, _, _, proposal, review, approval = _proposal_path()
    changed = approval.model_copy(update=update)
    with pytest.raises(policy.PolicyError, match=error):
        policy.validate_approval(
            changed,
            proposal,
            review,
            alert.context,
            now=lab.FIXED_TIME,
            authorized_approvers=lab.AUTHORIZED_APPROVERS,
        )


def test_changed_proposal_digest_invalidates_approval():
    alert, _, _, proposal, review, approval = _proposal_path()
    changed = proposal.model_copy(update={"proposal_digest": "f" * 64})
    with pytest.raises(policy.PolicyError, match="REVIEW_PROPOSAL_MISMATCH"):
        policy.validate_approval(
            approval,
            changed,
            review,
            alert.context,
            now=lab.FIXED_TIME,
            authorized_approvers=lab.AUTHORIZED_APPROVERS,
        )


def test_same_mitigation_retry_is_idempotent():
    _, state, registry, proposal, review, approval = _proposal_path()
    store = lab.OrchestratorStore()
    first = lab.execute_mitigation(state, proposal, review, approval, store, registry)
    second = lab.execute_mitigation(state, proposal, review, approval, store, registry)
    assert first == second
    assert state.mitigation_attempts == 1


def test_different_mitigation_has_different_logical_identity():
    _, _, _, proposal, _, _ = _proposal_path()
    changed = proposal.model_copy(
        update={"target": "deploy-1843", "proposal_digest": "a" * 64}
    )
    assert policy.logical_mitigation_id(changed) != policy.logical_mitigation_id(proposal)


def test_unknown_execution_outcome_requires_reconciliation_not_blind_retry():
    _, state, registry, proposal, review, approval = _proposal_path()
    store = lab.OrchestratorStore()
    unknown = lab.execute_mitigation(
        state, proposal, review, approval, store, registry, simulate_unknown=True
    )
    duplicate = lab.execute_mitigation(
        state, proposal, review, approval, store, registry
    )
    assert duplicate.status is policy.ExecutionStatus.UNKNOWN_OUTCOME
    reconciled = lab.reconcile_unknown_outcome(
        state,
        unknown,
        store,
        provider_current_deployment=lab.RESTORED_DEPLOYMENT,
    )
    assert reconciled.status is policy.ExecutionStatus.RECONCILED
    assert state.mitigation_attempts == 1


def test_execution_success_does_not_resolve_incident():
    _, state, registry, proposal, review, approval = _proposal_path()
    lab.execute_mitigation(
        state, proposal, review, approval, lab.OrchestratorStore(), registry
    )
    assert state.status is policy.IncidentStatus.VERIFYING


def test_verification_pass_is_required_for_resolved():
    run = lab.run_capstone()
    assert run.execution.status is policy.ExecutionStatus.SUCCEEDED
    assert run.verification.status is policy.VerificationStatus.PASS
    assert run.state.status is policy.IncidentStatus.RESOLVED


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (
            {"error_rate": 0.08, "conversion_rate": 0.97, "p99_latency_ms": 800},
            policy.VerificationStatus.FAIL,
        ),
        (
            {"error_rate": 0.01, "conversion_rate": 0.97, "p99_latency_ms": 2200},
            policy.VerificationStatus.REGRESSION,
        ),
    ],
)
def test_failed_or_regressive_verification_reopens_investigation(values, expected):
    _, state, registry, proposal, review, approval = _proposal_path()
    lab.execute_mitigation(
        state, proposal, review, approval, lab.OrchestratorStore(), registry
    )
    result = lab.verify_recovery(state, provider_healthy=True, **values)
    assert result.status is expected
    assert state.status is policy.IncidentStatus.EVIDENCE_INCOMPLETE


def test_restart_preserves_state_budget_and_approval(tmp_path):
    _, state, _, proposal, _, approval = _proposal_path()
    state.proposal = proposal
    state.approval_receipt = approval
    state.mitigation_attempts = 1
    path = tmp_path / "incident-state.json"
    lab.save_state(state, path)
    restored = lab.load_state(path)
    assert restored.context == state.context
    assert restored.approval_receipt == approval
    assert restored.mitigation_attempts == 1
    assert restored.accepted_evidence_ids == state.accepted_evidence_ids


def test_approval_is_revalidated_after_restart(tmp_path):
    alert, state, _, proposal, review, approval = _proposal_path()
    state.approval_receipt = approval
    path = tmp_path / "incident-state.json"
    lab.save_state(state, path)
    restored = lab.load_state(path)
    with pytest.raises(policy.PolicyError, match="APPROVAL_EXPIRED"):
        policy.validate_approval(
            restored.approval_receipt,
            proposal,
            review,
            alert.context,
            now=approval.expires_at + timedelta(seconds=1),
            authorized_approvers=lab.AUTHORIZED_APPROVERS,
        )


def test_manual_takeover_stops_next_automated_action():
    _, state, registry, proposal, review, approval = _proposal_path()
    lab.activate_manual_control(state, "engineer-1")
    with pytest.raises(policy.PolicyError, match="MANUAL_TAKEOVER"):
        lab.execute_mitigation(
            state,
            proposal,
            review,
            approval,
            lab.OrchestratorStore(),
            registry,
        )
    assert state.audit_events[-1].event_type == "MANUAL_TAKEOVER"


def test_coordinator_lease_prevents_duplicate_active_worker():
    _, state, _ = _admitted()
    policy.acquire_coordinator_lease(
        state, coordinator_id="worker-a", now=lab.FIXED_TIME
    )
    with pytest.raises(policy.PolicyError, match="COORDINATOR_LEASE_HELD"):
        policy.acquire_coordinator_lease(
            state, coordinator_id="worker-b", now=lab.FIXED_TIME
        )


def test_external_update_uses_verified_projection_without_internal_details():
    _, state, _, _, brief = _investigated()
    external = lab.external_status_update(brief, state)
    assert "leading_hypothesis" not in external
    assert "customer" not in str(external).casefold()
    assert "deploy-1842" not in str(external)


def test_model_failure_never_fabricates_resolution():
    _, state, registry = _admitted()
    lab.initial_investigation(state, registry)

    class BrokenResponses:
        def parse(self, **kwargs):
            raise RuntimeError("provider unavailable")

    class BrokenClient:
        responses = BrokenResponses()

    with pytest.raises(policy.PolicyError, match="MODEL_UNAVAILABLE"):
        lab.optional_openai_hypothesis(
            BrokenClient(), model="configured-by-operator", registry=registry
        )
    assert state.status is not policy.IncidentStatus.RESOLVED


def test_model_budget_is_checked_before_provider_call():
    class CountingResponses:
        calls = 0

        def parse(self, **kwargs):
            self.calls += 1
            raise AssertionError("provider must not be called")

    class CountingClient:
        responses = CountingResponses()

    _, state, registry = _admitted()
    budget = lab.DEFAULT_BUDGET.model_copy(update={"max_model_calls": 0})
    with pytest.raises(policy.PolicyError, match="MODEL_CALL_BUDGET_EXCEEDED"):
        lab.optional_openai_hypothesis(
            CountingClient(),
            model="configured-by-operator",
            registry=registry,
            state=state,
            budget=budget,
        )
    assert CountingClient.responses.calls == 0
    assert state.model_calls == 0


def test_model_estimate_admits_call_and_actual_cost_is_accounted():
    class Result:
        output_parsed = lab.HypothesisDraft(
            statement="No accepted evidence yet.",
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
            missing_evidence_types=["METRICS"],
        )

    class Responses:
        def parse(self, **kwargs):
            return Result()

    class Client:
        responses = Responses()

    _, state, registry = _admitted()
    draft = lab.optional_openai_hypothesis(
        Client(),
        model="configured-by-operator",
        registry=registry,
        state=state,
        estimated_cost_usd=0.01,
        actual_cost_usd=0.013,
    )
    assert draft.statement == "No accepted evidence yet."
    assert state.model_calls == 1
    assert state.cost_usd == pytest.approx(0.013)


def test_fixture_metrics_separate_safety_from_speed():
    run = lab.run_capstone()
    assert run.metrics.unsupported_claim_rate == 0
    assert run.metrics.unsafe_action_executions == 0
    assert run.metrics.time_to_verified_recovery_ms is not None
    rows = lab.same_incident_baseline()
    assert {row.architecture for row in rows} == {
        "fixed-runbook-baseline",
        "bounded-agent-assisted",
    }
    assert rows[1].time_to_brief_ms > rows[0].time_to_brief_ms


def test_audit_records_boundaries_without_hidden_reasoning():
    run = lab.run_capstone()
    event_types = {event.event_type for event in run.state.audit_events}
    assert {
        "ALERT_ADMITTED",
        "EVIDENCE_ACCEPTED",
        "HYPOTHESIS_UPDATED",
        "BRIEF_CREATED",
        "PROPOSAL_CREATED",
        "EXECUTION_ATTEMPTED",
        "INCIDENT_RESOLVED",
    }.issubset(event_types)
    assert "chain_of_thought" not in policy.AuditEvent.model_fields
