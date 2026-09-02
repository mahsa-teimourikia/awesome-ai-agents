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
    
    current_evidence_state = {ev.evidence_id: ev for ev in evidence_refs}
    
    return payload, decision, reviewer, current_evidence_state

def test_valid_approval_succeeds(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)
    assert cmd.tenant_id == "acme"
    assert "alice" in cmd.reviewer_ids
    assert cmd.approval_digest == payload.digest

def test_reviewer_id_mismatch(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    decision.approver_id = "bob"
    with pytest.raises(PolicyError, match="REVIEWER_ID_MISMATCH"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_approval_context_lengths_mismatch(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    with pytest.raises(PolicyError, match="APPROVAL_CONTEXT_MISMATCH"):
        validate_approval(payload, [decision, decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_unauthenticated_reviewer_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    reviewer.authenticated = False
    with pytest.raises(PolicyError, match="UNAUTHENTICATED_REVIEWER"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_unauthorized_approver_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    reviewer.roles = {"operator"} # HIGH risk requires incident_commander
    with pytest.raises(PolicyError, match="UNAUTHORIZED_REVIEWER"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_wrong_tenant_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    reviewer.tenant_id = "globex"
    with pytest.raises(PolicyError, match="WRONG_TENANT"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_expired_approval_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    payload.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(PolicyError, match="EXPIRED_APPROVAL"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_stale_evidence_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    # Modify the payload's evidence to be stale, AND update the current_evidence_state
    # to match (so we don't hit EVIDENCE_CHANGED instead).
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload.evidence_refs[0].observed_at = stale_time
    current_evidence_state["health-123"] = current_evidence_state["health-123"].model_copy(update={"observed_at": stale_time})
    with pytest.raises(PolicyError, match="STALE_EVIDENCE"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_risk_recompute_mismatch(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    # Manually downgrade risk in payload
    payload.risk_tier = RiskTier.LOW
    decision.approved_digest = payload.digest
    with pytest.raises(PolicyError, match="RISK_MISMATCH"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_proposal_digest_mismatch_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    decision.approved_digest = "tampered_digest"
    with pytest.raises(PolicyError, match="DIGEST_MISMATCH"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_rejection_never_executes(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    decision.decision = DecisionType.REJECT
    with pytest.raises(PolicyError, match="DECISION_REJECT"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_modification_creates_new_digest(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    new_proposal = payload.proposal.model_copy(update={"region": Region.GLOBAL})
    new_payload = payload.model_copy(update={"proposal": new_proposal})
    assert new_payload.digest != payload.digest

def test_escalation_never_executes(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    decision.decision = DecisionType.ESCALATE
    with pytest.raises(PolicyError, match="DECISION_ESCALATE"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_policy_version_mismatch_rejected(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    with pytest.raises(PolicyError, match="POLICY_CHANGED"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v4", current_evidence_state=current_evidence_state)

def test_two_person_rule_enforced_and_missing_required_role():
    proposal = RollbackProposal(service=Service.CHECKOUT, region=Region.GLOBAL, deployment_id="d1", reason="bug")
    context = ExecutionContext(tenant_id="acme", environment=Environment.PRODUCTION, request_id="1", policy_version="v1")
    payload = build_approval_payload(proposal, context, [])
    current_evidence_state = {}
    
    r1 = ReviewerContext(reviewer_id="alice", tenant_id="acme", roles={"incident_commander"}, authenticated=True)
    d1 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="alice", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    # 1 approver when 2 needed
    with pytest.raises(PolicyError, match="MISSING_APPROVAL"):
        validate_approval(payload, [d1], [r1], proposer_id="agent", current_policy_version="v1", current_evidence_state=current_evidence_state)
        
    # Same approver twice (SoD violation)
    with pytest.raises(PolicyError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        validate_approval(payload, [d1, d1], [r1, r1], proposer_id="agent", current_policy_version="v1", current_evidence_state=current_evidence_state)
        
    # Two distinct approvers, but missing 'sre_lead'
    r2 = ReviewerContext(reviewer_id="bob", tenant_id="acme", roles={"incident_commander"}, authenticated=True)
    d2 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="bob", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    with pytest.raises(PolicyError, match="MISSING_REQUIRED_REVIEWER_ROLE"):
        validate_approval(payload, [d1, d2], [r1, r2], proposer_id="agent", current_policy_version="v1", current_evidence_state=current_evidence_state)

    # Two distinct approvers with correct roles
    r3 = ReviewerContext(reviewer_id="charlie", tenant_id="acme", roles={"sre_lead"}, authenticated=True)
    d3 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="charlie", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    cmd = validate_approval(payload, [d1, d3], [r1, r3], proposer_id="agent", current_policy_version="v1", current_evidence_state=current_evidence_state)
    assert "alice" in cmd.reviewer_ids
    assert "charlie" in cmd.reviewer_ids

def test_separation_of_duties_proposer_cannot_approve():
    proposal = RollbackProposal(service=Service.CHECKOUT, region=Region.EU_WEST, deployment_id="d1", reason="bug")
    context = ExecutionContext(tenant_id="acme", environment=Environment.PRODUCTION, request_id="1", policy_version="v1")
    payload = build_approval_payload(proposal, context, [])
    current_evidence_state = {}
    
    r1 = ReviewerContext(reviewer_id="alice", tenant_id="acme", roles={"incident_commander"}, authenticated=True)
    d1 = ApprovalDecision(decision=DecisionType.APPROVE, approver_id="alice", approved_digest=payload.digest, reason="ok", decided_at=datetime.now(timezone.utc))
    
    # Alice proposes, Alice approves -> SoD violation
    with pytest.raises(PolicyError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        validate_approval(payload, [d1], [r1], proposer_id="alice", current_policy_version="v1", current_evidence_state={})
        
def test_duplicate_command_executes_once(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)
    
    store = ApprovalStore()
    receipt1 = store.record_execution(cmd, ExecutionStatus.EXECUTED)
    receipt2 = store.check_idempotency(cmd)
    
    assert receipt1.status == ExecutionStatus.EXECUTED
    assert receipt2.status == ExecutionStatus.ALREADY_EXECUTED
    assert receipt1.execution_id == receipt2.execution_id

def test_idempotency_conflict_different_action_digest(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)
    
    store = ApprovalStore()
    original_receipt = store.record_execution(cmd, ExecutionStatus.EXECUTED)
    
    # Tamper with the action digest via an evil command
    class EvilCommand(RollbackCommand):
        @property
        def action_digest(self) -> str:
            return "evil_action_digest"
            
    cmd_evil = EvilCommand(**cmd.model_dump())
    conflict_receipt = store.check_idempotency(cmd_evil)
    
    assert conflict_receipt.status == ExecutionStatus.CONFLICT
    assert conflict_receipt.execution_id != original_receipt.execution_id

def test_process_decision_engine(approval_setup):
    payload, decision_approve, reviewer, current_evidence_state = approval_setup
    store = ApprovalStore()
    
    # REJECT routes to Audit Event
    decision_reject = decision_approve.model_copy(update={"decision": DecisionType.REJECT})
    res_reject = process_decision(store, "run-1", payload, [decision_reject], [reviewer], "agent", "v3", current_evidence_state)
    assert isinstance(res_reject, ApprovalAuditEvent)
    assert res_reject.event_type == EventType.REJECTED
    
    # MODIFY routes to Audit Event
    decision_modify = decision_approve.model_copy(update={"decision": DecisionType.MODIFY})
    res_modify = process_decision(store, "run-1", payload, [decision_modify], [reviewer], "agent", "v3", current_evidence_state)
    assert isinstance(res_modify, ApprovalAuditEvent)
    assert res_modify.event_type == EventType.MODIFIED
    
    # ESCALATE routes to Audit Event
    decision_escalate = decision_approve.model_copy(update={"decision": DecisionType.ESCALATE})
    res_escalate = process_decision(store, "run-1", payload, [decision_escalate], [reviewer], "agent", "v3", current_evidence_state)
    assert isinstance(res_escalate, ApprovalAuditEvent)
    assert res_escalate.event_type == EventType.ESCALATED
    
    # APPROVE routes to validation and yields RollbackCommand
    res_approve = process_decision(store, "run-1", payload, [decision_approve], [reviewer], "agent", "v3", current_evidence_state)
    assert isinstance(res_approve, RollbackCommand)
    
    # FAILED validation routes to Audit Event and raises PolicyError
    decision_wrong_digest = decision_approve.model_copy(update={"approved_digest": "wrong"})
    with pytest.raises(PolicyError):
        process_decision(store, "run-1", payload, [decision_wrong_digest], [reviewer], "agent", "v3", current_evidence_state)
        
    audit_events = store.audit_events
    assert len(audit_events) == 5
    assert audit_events[-1].event_type == EventType.AUTHORIZATION_DENIED

def test_revalidate_evidence_missing(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    # Remove evidence from current state
    current_evidence_state = {}
    with pytest.raises(PolicyError, match="EVIDENCE_CHANGED"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_revalidate_evidence_version_changed(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    # Change version in current state
    current_evidence_state["health-123"] = current_evidence_state["health-123"].model_copy(update={"source_version": "v2"})
    with pytest.raises(PolicyError, match="EVIDENCE_CHANGED"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_revalidate_evidence_stale(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    # Change observed_at in current state to be stale
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2)
    current_evidence_state["health-123"] = current_evidence_state["health-123"].model_copy(update={"observed_at": stale_time})
    with pytest.raises(PolicyError, match="STALE_EVIDENCE"):
        validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)

def test_modify_is_true_new_action_path(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    
    # Simulate reviewer rejecting and wanting a modification
    decision.decision = DecisionType.MODIFY
    
    store = ApprovalStore()
    result = process_decision(store, "run-1", payload, [decision], [reviewer], "agent", "v3", current_evidence_state)
    
    # Must never return RollbackCommand
    assert isinstance(result, ApprovalAuditEvent)
    assert result.event_type == EventType.MODIFIED
    
    # Must create a new payload that will have a new digest
    new_proposal = payload.proposal.model_copy(update={"deployment_id": "deploy-fixed"})
    new_payload = payload.model_copy(update={"proposal": new_proposal})
    assert new_payload.digest != payload.digest

def test_execution_audit_events(approval_setup):
    payload, decision, reviewer, current_evidence_state = approval_setup
    cmd = validate_approval(payload, [decision], [reviewer], proposer_id="agent", current_policy_version="v3", current_evidence_state=current_evidence_state)
    
    store = ApprovalStore()
    
    # Test EXECUTION_SUCCEEDED
    store.record_execution(cmd, ExecutionStatus.EXECUTED)
    assert store.audit_events[-1].event_type == EventType.EXECUTION_SUCCEEDED
    
    # Test EXECUTION_FAILED
    store.record_execution(cmd, ExecutionStatus.FAILED_BEFORE_COMMIT)
    assert store.audit_events[-1].event_type == EventType.EXECUTION_FAILED
    
    # Test EXECUTION_OUTCOME_UNKNOWN
    store.record_execution(cmd, ExecutionStatus.UNKNOWN_OUTCOME)
    assert store.audit_events[-1].event_type == EventType.EXECUTION_OUTCOME_UNKNOWN

# ==========================================
# Course 05 Invariant Tests (Agent Evaluation)
# ==========================================
import importlib.util
import sys
import os

module_name = "policy_05"
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../curriculum/intermediate/05-agent-evaluation/policy.py'))
spec = importlib.util.spec_from_file_location(module_name, file_path)
policy_05 = importlib.util.module_from_spec(spec)
sys.modules[module_name] = policy_05
spec.loader.exec_module(policy_05)

RiskTier = policy_05.RiskTier
DatasetSplit = policy_05.DatasetSplit
StepType = policy_05.StepType
FailureClass = policy_05.FailureClass
ReleaseStatus = policy_05.ReleaseStatus
ResultStatus = policy_05.ResultStatus
EvalCase = policy_05.EvalCase
TraceStep = policy_05.TraceStep
AgentTrace = policy_05.AgentTrace
ReleaseGate = policy_05.ReleaseGate
ReleaseDecision = policy_05.ReleaseDecision
EvaluationSummary = policy_05.EvaluationSummary
evaluate_run = policy_05.evaluate_run
evaluate_release = policy_05.evaluate_release
compute_judge_calibration = policy_05.compute_judge_calibration
project_trace_for_judge = policy_05.project_trace_for_judge


import pytest

@pytest.fixture
def eval_case_05():
    return EvalCase(
        case_id="case-01",
        task="Test task",
        tenant_id="northstar",
        risk_tier=RiskTier.MODERATE,
        expected_tools=["tool_a", "tool_b"],
        forbidden_tools=["tool_bad"],
        available_evidence_ids=["ev-1", "ev-2"],
        required_evidence_ids=["ev-1"],
        expected_outcome="Success",
        max_tool_calls=5,
        max_cost_usd=0.10,
        max_latency_ms=5000.0,
        tags=["test"],
        dataset_split=DatasetSplit.DEV,
        dataset_version="1.0",
        required_tool_order=["tool_a", "tool_b"],
        allowed_retry_rules={"tool_retry": 1}
    )

def test_05_correct_outcome_plus_forbidden_attempt_blocked(eval_case_05):
    # 1. correct outcome + forbidden attempt blocked -> outcome correct, containment success, release behavior correct
    trace = AgentTrace(
        run_id="run-1", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_bad", target_tenant_id="northstar", latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=2, step_type=StepType.POLICY_DECISION, result_status=ResultStatus.POLICY_BLOCKED, latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=3, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="northstar", latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=4, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=5, step_type=StepType.TOOL_CALL, tool_name="tool_b", target_tenant_id="northstar", latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=6, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0)
        ],
        final_answer="Success achieved.", final_evidence_ids=["ev-1"], total_cost_usd=0.03, total_latency_ms=60,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert res.outcome.outcome_correct
    assert res.forbidden_attempted
    assert not res.forbidden_executed
    assert res.is_policy_compliant
    # Contains a block, which means missing trajectory success possibly depending on how we graded missing expected tools, but here we used both expected tools.
    assert res.is_fully_successful

def test_05_forbidden_action_actually_executed(eval_case_05):
    # 2. forbidden action actually executed -> hard release fail
    trace = AgentTrace(
        run_id="run-2", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_bad", target_tenant_id="northstar", latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=2, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
        ],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.01, total_latency_ms=20,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert res.forbidden_executed
    assert not res.is_policy_compliant
    
    summary = EvaluationSummary(
        dataset_version="1.0", sample_count=1, outcome_pass_rate=1.0, required_evidence_recall=1.0,
        forbidden_action_attempt_rate=1.0, forbidden_action_execution_rate=1.0, cross_tenant_violation_rate=0.0,
        p95_latency_ms=20, mean_cost_usd=0.01, cost_per_policy_compliant_success=0.0
    )
    gate = ReleaseGate(min_outcome_pass_rate=0.9, min_required_evidence_recall=0.8, max_forbidden_action_execution_rate=0.0, max_cross_tenant_violation_rate=0.0, max_p95_latency_ms=100, max_cost_per_success=1.0, max_allowed_regression_pp=0.05)
    decision = evaluate_release(summary, None, gate)
    assert decision.status == ReleaseStatus.FAIL
    assert "max_forbidden_action_execution_rate" in decision.failed_constraints

def test_05_cross_tenant_hard_fail(eval_case_05):
    # 3. cross-tenant target -> hard fail
    trace = AgentTrace(
        run_id="run-3", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="globex", latency_ms=10, cost_usd=0.01)
        ],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.01, total_latency_ms=10,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert res.cross_tenant_violation
    assert not res.is_policy_compliant

def test_05_missing_required_evidence(eval_case_05):
    # 4. missing required evidence
    trace = AgentTrace(
        run_id="run-4", case_id="case-01", tenant_id="northstar",
        steps=[],
        final_answer="Success", final_evidence_ids=[], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert res.outcome.required_evidence_recall == 0.0
    assert FailureClass.GROUNDING_FAILURE in res.all_failures

def test_05_unsupported_evidence_from_trusted_registry(eval_case_05):
    # 5. unsupported evidence from trusted evidence registry
    trace = AgentTrace(
        run_id="run-5", case_id="case-01", tenant_id="northstar",
        steps=[],
        final_answer="Success", final_evidence_ids=["ev-1", "fake-999"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert res.outcome.unsupported_evidence_count == 1
    assert FailureClass.GROUNDING_FAILURE in res.all_failures

def test_05_outcome_grader(eval_case_05):
    # 6. outcome grader
    trace = AgentTrace(
        run_id="run-6", case_id="case-01", tenant_id="northstar",
        steps=[], final_answer="Failure occurred.", final_evidence_ids=["ev-1"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert not res.outcome.outcome_correct
    assert FailureClass.OUTCOME_FAILURE in res.all_failures

def test_05_invalid_tool_order(eval_case_05):
    # 7. invalid tool order
    trace = AgentTrace(
        run_id="run-7", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_b", target_tenant_id="northstar", latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=2, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="northstar", latency_ms=10, cost_usd=0.01)
        ],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert FailureClass.TRAJECTORY_FAILURE in res.all_failures
    assert not res.is_fully_successful

def test_05_repeated_read_efficiency_and_write_safety(eval_case_05):
    # 8 & 9. repeated READ flagged only as efficiency, repeated WRITE success flagged as serious issue
    # We will simulate restart as a write
    trace = AgentTrace(
        run_id="run-8", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=2, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=3, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=4, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
            
            TraceStep(step_index=5, step_type=StepType.TOOL_CALL, tool_name="restart_service", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=6, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=7, step_type=StepType.TOOL_CALL, tool_name="restart_service", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=8, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
        ],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    dup_check = next(c for c in res.deterministic_checks if c.name == "duplicate_vs_retry")
    assert not dup_check.passed
    assert any("Inefficient duplicate READ" in f for f in dup_check.failures)
    assert any("Non-idempotent duplicate WRITE side effect" in f for f in dup_check.failures)

def test_05_timeout_retry_passes(eval_case_05):
    # 10. timeout + one allowed retry passes
    trace = AgentTrace(
        run_id="run-10", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_retry", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=2, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.TIMEOUT, latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=3, step_type=StepType.TOOL_CALL, tool_name="tool_retry", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=4, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0),
            # provide expected tools to avoid other failures
            TraceStep(step_index=5, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="northstar", latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=6, step_type=StepType.TOOL_CALL, tool_name="tool_b", target_tenant_id="northstar", latency_ms=10, cost_usd=0.0)
        ],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    dup_check = next(c for c in res.deterministic_checks if c.name == "duplicate_vs_retry")
    assert dup_check.passed

def test_05_policy_denial_not_retryable(eval_case_05):
    # 11. policy denial is not considered retryable
    trace = AgentTrace(
        run_id="run-11", case_id="case-01", tenant_id="northstar",
        steps=[
            TraceStep(step_index=1, step_type=StepType.TOOL_CALL, tool_name="tool_retry", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=2, step_type=StepType.POLICY_DECISION, result_status=ResultStatus.POLICY_BLOCKED, latency_ms=10, cost_usd=0.0),
            TraceStep(step_index=3, step_type=StepType.TOOL_CALL, tool_name="tool_retry", target_tenant_id="northstar", arguments={"x":1}, latency_ms=10, cost_usd=0.01),
            TraceStep(step_index=4, step_type=StepType.TOOL_RESULT, result_status=ResultStatus.SUCCESS, latency_ms=10, cost_usd=0.0)
        ],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    dup_check = next(c for c in res.deterministic_checks if c.name == "duplicate_vs_retry")
    assert not dup_check.passed
    assert any("Retried a policy denial" in f for f in dup_check.failures)

def test_05_tool_call_budget_fail(eval_case_05):
    # 12. tool-call budget fail
    trace = AgentTrace(
        run_id="run-12", case_id="case-01", tenant_id="northstar",
        steps=[TraceStep(step_index=i, step_type=StepType.TOOL_CALL, tool_name="tool_a", target_tenant_id="northstar", latency_ms=10, cost_usd=0.0) for i in range(10)],
        final_answer="Success", final_evidence_ids=["ev-1"], total_cost_usd=0.0, total_latency_ms=0,
        agent_version="v1", model_version="v1", prompt_version="v1", tool_version="v1", policy_version="v1"
    )
    res = evaluate_run(trace, eval_case_05)
    assert FailureClass.BUDGET_FAILURE in res.all_failures

def test_05_cost_and_latency_gate_fail(eval_case_05):
    # 13 & 14. cost gate fail & p95 latency gate fail
    summary = EvaluationSummary(
        dataset_version="1.0", sample_count=1, outcome_pass_rate=1.0, required_evidence_recall=1.0,
        forbidden_action_attempt_rate=0.0, forbidden_action_execution_rate=0.0, cross_tenant_violation_rate=0.0,
        p95_latency_ms=10000, mean_cost_usd=2.0, cost_per_policy_compliant_success=2.0
    )
    gate = ReleaseGate(min_outcome_pass_rate=0.9, min_required_evidence_recall=0.8, max_forbidden_action_execution_rate=0.0, max_cross_tenant_violation_rate=0.0, max_p95_latency_ms=5000, max_cost_per_success=1.0, max_allowed_regression_pp=0.05)
    decision = evaluate_release(summary, None, gate)
    assert decision.status == ReleaseStatus.FAIL
    assert "max_p95_latency_ms" in decision.failed_constraints
    assert "max_cost_per_success" in decision.failed_constraints

def test_05_candidate_regression(eval_case_05):
    # 15. candidate regression beyond threshold
    baseline = EvaluationSummary(
        dataset_version="1.0", sample_count=1, outcome_pass_rate=0.98, required_evidence_recall=1.0,
        forbidden_action_attempt_rate=0.0, forbidden_action_execution_rate=0.0, cross_tenant_violation_rate=0.0,
        p95_latency_ms=100, mean_cost_usd=0.1, cost_per_policy_compliant_success=0.1
    )
    summary = EvaluationSummary(
        dataset_version="1.0", sample_count=1, outcome_pass_rate=0.90, required_evidence_recall=1.0,
        forbidden_action_attempt_rate=0.0, forbidden_action_execution_rate=0.0, cross_tenant_violation_rate=0.0,
        p95_latency_ms=100, mean_cost_usd=0.1, cost_per_policy_compliant_success=0.1
    )
    gate = ReleaseGate(min_outcome_pass_rate=0.8, min_required_evidence_recall=0.8, max_forbidden_action_execution_rate=0.0, max_cross_tenant_violation_rate=0.0, max_p95_latency_ms=5000, max_cost_per_success=1.0, max_allowed_regression_pp=0.05)
    # Passed absolute min_outcome_pass_rate (0.9 > 0.8), but regression (0.98 - 0.90 = 0.08) > max (0.05)
    decision = evaluate_release(summary, baseline, gate)
    assert decision.status == ReleaseStatus.FAIL
    assert "max_allowed_regression_pp" in decision.failed_constraints

def test_05_judge_calibration():
    # 17. judge calibration produces expected confusion matrix
    y_human = ["PASS", "FAIL", "FAIL", "PASS", "UNCERTAIN"]
    y_judge = ["PASS", "PASS", "FAIL", "PASS", "FAIL"]
    cal = compute_judge_calibration(y_human, y_judge)
    assert cal.accuracy == 0.6
    assert cal.confusion_matrix["PASS"]["PASS"] == 2
    assert cal.confusion_matrix["FAIL"]["PASS"] == 1
    assert cal.confusion_matrix["FAIL"]["FAIL"] == 1
    assert cal.confusion_matrix["UNCERTAIN"]["FAIL"] == 1
