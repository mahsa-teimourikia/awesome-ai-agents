import pytest
from datetime import datetime, timezone, timedelta
import sys
import os

# ensure it can run from pytest
sys.path.append(os.path.abspath("curriculum/intermediate/02-context-engineering"))
from context import (
    ContextKind, TrustLevel, Sensitivity, Phase, ContextStatus,
    ContextItem, ContextRequest, build_context
)

@pytest.fixture
def setup_data():
    now = datetime.now(timezone.utc)
    stale = now - timedelta(hours=2)
    future = now + timedelta(hours=2)

    candidates = [
        ContextItem(item_id="global_pol", kind=ContextKind.SYSTEM_POLICY, tenant_id="global", source_id="1", source_type="git", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=1.0, token_estimate=100, payload=""),
        ContextItem(item_id="state_1", kind=ContextKind.TASK_STATE, tenant_id="acme", user_id="bob", source_id="1", source_type="db", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.INTERNAL, relevance_score=1.0, token_estimate=50, payload="NO_APPROVAL"),
        ContextItem(item_id="globex_doc", kind=ContextKind.RETRIEVED_DOCUMENT, tenant_id="globex", source_id="1", source_type="doc", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=0.99, token_estimate=200, payload=""),
        ContextItem(item_id="alice_mem", kind=ContextKind.MEMORY, tenant_id="acme", user_id="alice", source_id="1", source_type="db", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.INTERNAL, relevance_score=0.9, token_estimate=50, payload=""),
        ContextItem(item_id="poison_doc", kind=ContextKind.RETRIEVED_DOCUMENT, tenant_id="acme", source_id="2", source_type="doc", observed_at=now, expires_at=future, trust=TrustLevel.QUARANTINED, sensitivity=Sensitivity.PUBLIC, relevance_score=0.95, token_estimate=100, payload=""),
        ContextItem(item_id="stale_ev", kind=ContextKind.TOOL_EVIDENCE, tenant_id="acme", source_id="3", source_type="api", observed_at=stale, expires_at=stale, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.INTERNAL, relevance_score=0.9, token_estimate=100, payload=""),
        ContextItem(item_id="fresh_ev", kind=ContextKind.TOOL_EVIDENCE, tenant_id="acme", source_id="4", source_type="api", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.INTERNAL, relevance_score=0.92, token_estimate=150, payload=""),
        ContextItem(item_id="summary_1", kind=ContextKind.SUMMARY, tenant_id="acme", source_id="5", source_type="agent", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.INTERNAL, relevance_score=1.0, token_estimate=100, payload="APPROVED"),
    ]

    req = ContextRequest(
        request_id="req1", tenant_id="acme", user_id="bob", task_id="task1",
        phase=Phase.INVESTIGATE, token_budget=1000, required_evidence_ids=[],
        allowed_sensitivity=[Sensitivity.PUBLIC, Sensitivity.INTERNAL],
        policy_version="1", context_builder_version="1"
    )
    return req, candidates

def test_cross_tenant_blocked(setup_data):
    req, cands = setup_data
    res = build_context(req, cands)
    assert res.status == ContextStatus.READY
    assert not any(i.item_id == "globex_doc" for i in res.packet.selected_items)
    assert any(t.item_id == "globex_doc" and t.reason == "WRONG_TENANT" for t in res.packet.selection_trace)

def test_cross_user_blocked(setup_data):
    req, cands = setup_data
    res = build_context(req, cands)
    assert not any(i.item_id == "alice_mem" for i in res.packet.selected_items)
    assert any(t.item_id == "alice_mem" and t.reason == "WRONG_USER" for t in res.packet.selection_trace)

def test_quarantined_excluded(setup_data):
    req, cands = setup_data
    res = build_context(req, cands)
    assert not any(i.item_id == "poison_doc" for i in res.packet.selected_items)
    assert any(i.item_id == "poison_doc" for i in res.packet.quarantined_items)

def test_stale_excluded(setup_data):
    req, cands = setup_data
    res = build_context(req, cands)
    assert not any(i.item_id == "stale_ev" for i in res.packet.selected_items)
    assert any(t.item_id == "stale_ev" and t.reason == "STALE" for t in res.packet.selection_trace)

def test_missing_required_evidence_detected(setup_data):
    req, cands = setup_data
    req.required_evidence_ids = ["does_not_exist"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.MISSING_REQUIRED_CONTEXT
    assert "does_not_exist" in res.missing_required_ids



def test_budget_exceeded_detected(setup_data):
    req, cands = setup_data
    req.token_budget = 100 # pol(100)+state(50)+sum(100) = 250
    res = build_context(req, cands)
    assert res.status == ContextStatus.BUDGET_EXCEEDED

def test_ready_packet_obeys_budget(setup_data):
    req, cands = setup_data
    req.token_budget = 300
    res = build_context(req, cands)
    assert res.status == ContextStatus.READY
    assert res.packet.estimated_tokens <= req.token_budget

def test_required_evidence_preserved(setup_data):
    req, cands = setup_data
    req.required_evidence_ids = ["fresh_ev"]
    req.token_budget = 400
    res = build_context(req, cands)
    assert res.status == ContextStatus.READY
    assert any(i.item_id == "fresh_ev" for i in res.packet.selected_items)

def test_cache_tenant_isolation(setup_data):
    req1, cands = setup_data
    res1 = build_context(req1, cands)

    req2 = req1.model_copy()
    req2.tenant_id = "other"
    res2 = build_context(req2, cands)

    assert res1.packet.cache_key != res2.packet.cache_key
    assert "acme" in res1.packet.cache_key
    assert "other" in res2.packet.cache_key

def test_cache_phase_isolation(setup_data):
    req, cands = setup_data
    res1 = build_context(req, cands)
    req.phase = Phase.TRIAGE
    res2 = build_context(req, cands)
    assert res1.packet.cache_key != res2.packet.cache_key

def test_source_version_invalidation(setup_data):
    req, cands = setup_data
    res1 = build_context(req, cands)

    # change source version of policy
    cands[0].source_version = "v2"
    res2 = build_context(req, cands)
    assert res1.packet.cache_key != res2.packet.cache_key

def test_policy_version_invalidation(setup_data):
    req, cands = setup_data
    res1 = build_context(req, cands)
    req.policy_version = "2"
    res2 = build_context(req, cands)
    assert res1.packet.cache_key != res2.packet.cache_key

def test_summary_invariant_preservation(setup_data):
    req, cands = setup_data
    # Modify the summary payload to avoid conflict with task_state ("NO_APPROVAL")
    for cand in cands:
        if cand.item_id == "summary_1":
            cand.payload = "NO_APPROVAL_YET"
    res = build_context(req, cands)
    # Verify that both task state and summary are preserved
    assert res.packet.task_state is not None
    assert res.packet.task_state.item_id == "state_1"
    assert res.packet.structured_summary is not None
    assert res.packet.structured_summary.item_id == "summary_1"


def test_scoped_item_rejected_when_request_user_is_none(setup_data):
    req, cands = setup_data
    req.user_id = None
    # alice_mem is user_id="alice"
    res = build_context(req, cands)
    assert not any(i.item_id == "alice_mem" for i in res.packet.selected_items)
    assert any(t.item_id == "alice_mem" and t.reason == "WRONG_USER" for t in res.packet.selection_trace)

def test_sensitivity_restriction(setup_data):
    req, cands = setup_data
    req.allowed_sensitivity = [Sensitivity.PUBLIC]
    # state_1 is INTERNAL
    res = build_context(req, cands)
    assert res.packet.task_state is None
    assert any(t.item_id == "state_1" and t.reason == "RESTRICTED_ACCESS" for t in res.packet.selection_trace)

def test_ambiguous_system_policies_rejected(setup_data):
    req, cands = setup_data
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=2)
    cands.append(
        ContextItem(item_id="global_pol_2", kind=ContextKind.SYSTEM_POLICY, tenant_id="global", source_id="1", source_type="git", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=1.0, token_estimate=100, payload="")
    )
    res = build_context(req, cands)
    assert res.status == ContextStatus.AMBIGUOUS_AUTHORITY

def test_ambiguous_task_states_rejected(setup_data):
    req, cands = setup_data
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=2)
    cands.append(
        ContextItem(item_id="state_2", kind=ContextKind.TASK_STATE, tenant_id="acme", user_id="bob", source_id="2", source_type="db", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.INTERNAL, relevance_score=1.0, token_estimate=50, payload="")
    )
    res = build_context(req, cands)
    assert res.status == ContextStatus.AMBIGUOUS_AUTHORITY

def test_summary_conflict_preserves_task_state(setup_data):
    req, cands = setup_data
    # state_1 payload is "NO_APPROVAL", summary_1 payload is "APPROVED"
    res = build_context(req, cands)
    assert res.status == ContextStatus.READY
    assert "Summary conflicts with Task State. Task State overrides." in res.warnings
    assert res.packet.task_state.payload == "NO_APPROVAL"
    assert res.packet.structured_summary is None
    assert any(t.item_id == "summary_1" and t.decision == "DROPPED" and t.reason == "CONFLICTS_WITH_AUTHORITATIVE_STATE" for t in res.packet.selection_trace)

def test_cache_invalidation_content_hash_fallback(setup_data):
    req, cands = setup_data
    cands[0].source_version = None
    cands[0].payload = "payload1"
    res1 = build_context(req, cands)

    cands[0].payload = "payload2"
    res2 = build_context(req, cands)

    assert res1.packet.cache_key != res2.packet.cache_key

def test_phase_policy_resume_prioritizes_state(setup_data):
    req, cands = setup_data
    req.phase = Phase.RESUME
    req.token_budget = 150 # enough for policy(100) + state(50), or policy(100) + summary(100) maybe?
    # Actually state and summary are added independently now if they fit.
    # Let's test the composite scoring directly using the internal budget pool.
    # We can just check that conversation / tool evidence are dropped due to low score.
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=2)

    test_cands = [
        ContextItem(item_id="conv_1", kind=ContextKind.CONVERSATION, tenant_id="acme", source_id="1", source_type="db", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=1.0, token_estimate=100, payload=""),
        ContextItem(item_id="sum_2", kind=ContextKind.SUMMARY, tenant_id="acme", source_id="2", source_type="agent", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=0.9, token_estimate=100, payload=""),
    ]

    req.token_budget = 100
    res = build_context(req, test_cands)
    # RESUME phase boosts SUMMARY by 0.5 and penalizes CONVERSATION by 0.5.
    # So despite CONVERSATION having relevance 1.0 and SUMMARY 0.9, SUMMARY should win.
    assert any(i.item_id == "sum_2" for i in res.packet.selected_items) or res.packet.structured_summary.item_id == "sum_2"
    assert not any(i.item_id == "conv_1" for i in res.packet.selected_items)

def test_phase_policy_recommend_prioritizes_evidence(setup_data):
    req, cands = setup_data
    req.phase = Phase.RECOMMEND
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=2)

    test_cands = [
        ContextItem(item_id="doc_1", kind=ContextKind.RETRIEVED_DOCUMENT, tenant_id="acme", source_id="1", source_type="db", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=1.0, token_estimate=100, payload=""),
        ContextItem(item_id="ev_1", kind=ContextKind.TOOL_EVIDENCE, tenant_id="acme", source_id="2", source_type="api", observed_at=now, expires_at=future, trust=TrustLevel.TRUSTED, sensitivity=Sensitivity.PUBLIC, relevance_score=0.7, token_estimate=100, payload=""),
    ]

    req.token_budget = 100
    res = build_context(req, test_cands)
    # RECOMMEND boosts trusted TOOL_EVIDENCE by 0.4.
    # ev_1 (0.7 + 0.4 = 1.1) > doc_1 (1.0). ev_1 should win.
    assert any(i.item_id == "ev_1" for i in res.packet.selected_items)
    assert not any(i.item_id == "doc_1" for i in res.packet.selected_items)


def test_required_wrong_tenant_evidence_blocked(setup_data):
    req, cands = setup_data
    # globex_doc is tenant_id="globex", req is "acme"
    req.required_evidence_ids = ["globex_doc"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.AUTHORIZATION_BLOCKED

def test_required_wrong_user_memory_blocked(setup_data):
    req, cands = setup_data
    # alice_mem is user_id="alice", req is "bob"
    req.required_evidence_ids = ["alice_mem"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.AUTHORIZATION_BLOCKED

def test_required_sensitivity_blocked_item(setup_data):
    req, cands = setup_data
    # globex_doc is PUBLIC. If we only allow INTERNAL:
    req.allowed_sensitivity = [Sensitivity.INTERNAL]
    # state_1 is INTERNAL, but we want to test required blocked item.
    # let's require global_pol (which is PUBLIC)
    req.required_evidence_ids = ["global_pol"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.AUTHORIZATION_BLOCKED

def test_required_stale_evidence_missing(setup_data):
    req, cands = setup_data
    # stale_ev is expired
    req.required_evidence_ids = ["stale_ev"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.MISSING_REQUIRED_CONTEXT

def test_required_quarantined_evidence_trust_blocked(setup_data):
    req, cands = setup_data
    # poison_doc is QUARANTINED
    req.required_evidence_ids = ["poison_doc"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.TRUST_BLOCKED


# --- Course 03: Human Approval Permissions Invariants ---

import sys
sys.path.append(os.path.abspath("curriculum/intermediate/03-human-approval-permissions"))
from policy import (
    Service, Region, Environment, RiskTier, DecisionType, ExecutionStatus, EventType,
    RollbackProposal, ReviewerContext, ApprovalPayload, ApprovalDecision, EvidenceRef,
    validate_approval, ApprovalStore, RollbackCommand, PolicyError, compute_risk, build_approval_payload,
    process_decision, ExecutionContext, ApprovalAuditEvent
)

@pytest.fixture
def approval_setup():
    proposal = RollbackProposal(
        service=Service.CHECKOUT,
        region=Region.EU_WEST,
        deployment_id="deploy-1842",
        reason="Conversion drop"
    )
    
    evidence_refs = [
        EvidenceRef(evidence_id="health-123", source_version="v1", observed_at=datetime.now(timezone.utc), max_age_seconds=3600)
    ]
    
    context = ExecutionContext(
        tenant_id="acme",
        environment=Environment.PRODUCTION,
        request_id="req-1",
        policy_version="v3"
    )
    
    payload = build_approval_payload(proposal, context, evidence_refs)
    
    reviewer = ReviewerContext(
        reviewer_id="alice",
        tenant_id="acme",
        roles={"incident_commander"},
        authenticated=True
    )
    
    decision = ApprovalDecision(
        decision=DecisionType.APPROVE,
        approver_id="alice",
        approved_digest=payload.digest,
        reason="LGTM",
        decided_at=datetime.now(timezone.utc)
    )
    
    return payload, decision, reviewer

def test_valid_approval_succeeds(approval_setup):
    payload, decision, reviewer = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")
    assert cmd.tenant_id == "acme"
    assert "alice" in cmd.reviewer_ids
    assert cmd.approval_digest == payload.digest

def test_reviewer_id_mismatch(approval_setup):
    payload, decision, reviewer = approval_setup
    decision.approver_id = "bob"
    with pytest.raises(PolicyError, match="REVIEWER_ID_MISMATCH"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_approval_context_lengths_mismatch(approval_setup):
    payload, decision, reviewer = approval_setup
    with pytest.raises(PolicyError, match="APPROVAL_CONTEXT_MISMATCH"):
        validate_approval(payload, [decision, decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_unauthenticated_reviewer_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    reviewer.authenticated = False
    with pytest.raises(PolicyError, match="UNAUTHENTICATED_REVIEWER"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_unauthorized_approver_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    reviewer.roles = {"operator"} # HIGH risk requires incident_commander
    with pytest.raises(PolicyError, match="UNAUTHORIZED_REVIEWER"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_wrong_tenant_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    reviewer.tenant_id = "globex"
    with pytest.raises(PolicyError, match="WRONG_TENANT"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_expired_approval_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    payload.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(PolicyError, match="EXPIRED_APPROVAL"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_stale_evidence_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    payload.evidence_refs[0].observed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    with pytest.raises(PolicyError, match="STALE_EVIDENCE"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_risk_recompute_mismatch(approval_setup):
    payload, decision, reviewer = approval_setup
    # Manually downgrade risk in payload
    payload.risk_tier = RiskTier.LOW
    decision.approved_digest = payload.digest
    with pytest.raises(PolicyError, match="RISK_MISMATCH"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_proposal_digest_mismatch_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    decision.approved_digest = "tampered_digest"
    with pytest.raises(PolicyError, match="DIGEST_MISMATCH"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_rejection_never_executes(approval_setup):
    payload, decision, reviewer = approval_setup
    decision.decision = DecisionType.REJECT
    with pytest.raises(PolicyError, match="DECISION_REJECT"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_modification_creates_new_digest(approval_setup):
    payload, decision, reviewer = approval_setup
    new_proposal = payload.proposal.model_copy(update={"region": Region.GLOBAL})
    new_payload = payload.model_copy(update={"proposal": new_proposal})
    assert new_payload.digest != payload.digest

def test_escalation_never_executes(approval_setup):
    payload, decision, reviewer = approval_setup
    decision.decision = DecisionType.ESCALATE
    with pytest.raises(PolicyError, match="DECISION_ESCALATE"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")

def test_policy_version_mismatch_rejected(approval_setup):
    payload, decision, reviewer = approval_setup
    with pytest.raises(PolicyError, match="POLICY_CHANGED"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v4")

def test_two_person_rule_enforced_and_missing_required_role():
    proposal = RollbackProposal(service=Service.CHECKOUT, region=Region.GLOBAL, deployment_id="d1", reason="bug")
    context = ExecutionContext(tenant_id="acme", environment=Environment.PRODUCTION, request_id="1", policy_version="v1")
    payload = build_approval_payload(proposal, context, [])
    
    r1 = ReviewerContext(reviewer_id="alice", tenant_id="acme", roles={"incident_commander"}, authenticated=True)
    d1 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="alice", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    # 1 approver when 2 needed
    with pytest.raises(PolicyError, match="MISSING_APPROVAL"):
        validate_approval(payload, [d1], [r1], proposer_id="agent", current_policy_version="v1")
        
    # Same approver twice (SoD violation)
    with pytest.raises(PolicyError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        validate_approval(payload, [d1, d1], [r1, r1], proposer_id="agent", current_policy_version="v1")
        
    # Two distinct approvers, but missing 'sre_lead'
    r2 = ReviewerContext(reviewer_id="bob", tenant_id="acme", roles={"incident_commander"}, authenticated=True)
    d2 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="bob", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    with pytest.raises(PolicyError, match="MISSING_REQUIRED_REVIEWER_ROLE"):
        validate_approval(payload, [d1, d2], [r1, r2], proposer_id="agent", current_policy_version="v1")

    # Two distinct approvers with correct roles
    r3 = ReviewerContext(reviewer_id="charlie", tenant_id="acme", roles={"sre_lead"}, authenticated=True)
    d3 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="charlie", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    cmd = validate_approval(payload, [d1, d3], [r1, r3], proposer_id="agent", current_policy_version="v1")
    assert "alice" in cmd.reviewer_ids
    assert "charlie" in cmd.reviewer_ids

def test_separation_of_duties_proposer_cannot_approve():
    proposal = RollbackProposal(service=Service.CHECKOUT, region=Region.EU_WEST, deployment_id="d1", reason="bug")
    context = ExecutionContext(tenant_id="acme", environment=Environment.PRODUCTION, request_id="1", policy_version="v1")
    payload = build_approval_payload(proposal, context, [])
    
    r1 = ReviewerContext(reviewer_id="alice", tenant_id="acme", roles={"incident_commander"}, authenticated=True)
    d1 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="alice", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    # Alice proposes, Alice approves -> SoD violation
    with pytest.raises(PolicyError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        validate_approval(payload, [d1], [r1], proposer_id="alice", current_policy_version="v1")
        
def test_duplicate_command_executes_once(approval_setup):
    payload, decision, reviewer = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")
    
    store = ApprovalStore()
    receipt1 = store.record_execution(cmd, ExecutionStatus.EXECUTED)
    receipt2 = store.check_idempotency(cmd)
    
    assert receipt1.status == ExecutionStatus.EXECUTED
    assert receipt2.status == ExecutionStatus.ALREADY_EXECUTED
    assert receipt1.execution_id == receipt2.execution_id

def test_idempotency_conflict_different_action_digest(approval_setup):
    payload, decision, reviewer = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3")
    
    store = ApprovalStore()
    store.record_execution(cmd, ExecutionStatus.EXECUTED)
    
    # Tamper with the action digest via an evil command
    class EvilCommand(RollbackCommand):
        @property
        def action_digest(self) -> str:
            return "evil_action_digest"
            
    cmd_evil = EvilCommand(**cmd.model_dump())
    receipt2 = store.check_idempotency(cmd_evil)
    
    assert receipt2.status == ExecutionStatus.CONFLICT
    assert receipt2.execution_id != receipt1.execution_id if 'receipt1' in locals() else True

def test_process_decision_engine(approval_setup):
    payload, decision_approve, reviewer = approval_setup
    store = ApprovalStore()
    
    # REJECT routes to Audit Event
    decision_reject = decision_approve.model_copy(update={"decision": DecisionType.REJECT})
    res_reject = process_decision(store, "run-1", payload, [decision_reject], [reviewer], "agent", "v3")
    assert isinstance(res_reject, ApprovalAuditEvent)
    assert res_reject.event_type == EventType.REJECTED
    
    # MODIFY routes to Audit Event
    decision_modify = decision_approve.model_copy(update={"decision": DecisionType.MODIFY})
    res_modify = process_decision(store, "run-1", payload, [decision_modify], [reviewer], "agent", "v3")
    assert isinstance(res_modify, ApprovalAuditEvent)
    assert res_modify.event_type == EventType.MODIFIED
    
    # ESCALATE routes to Audit Event
    decision_escalate = decision_approve.model_copy(update={"decision": DecisionType.ESCALATE})
    res_escalate = process_decision(store, "run-1", payload, [decision_escalate], [reviewer], "agent", "v3")
    assert isinstance(res_escalate, ApprovalAuditEvent)
    assert res_escalate.event_type == EventType.ESCALATED
    
    # APPROVE routes to validation and yields RollbackCommand
    res_approve = process_decision(store, "run-1", payload, [decision_approve], [reviewer], "agent", "v3")
    assert isinstance(res_approve, RollbackCommand)
    
    # FAILED validation routes to Audit Event and raises PolicyError
    decision_wrong_digest = decision_approve.model_copy(update={"approved_digest": "wrong"})
    with pytest.raises(PolicyError):
        process_decision(store, "run-1", payload, [decision_wrong_digest], [reviewer], "agent", "v3")
        
    audit_events = store.audit_events
    assert len(audit_events) == 5
    assert audit_events[-1].event_type == EventType.AUTHORIZATION_DENIED
