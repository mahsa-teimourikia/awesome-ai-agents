import pytest
import time
import sys
import importlib.util
from pathlib import Path

def load_policy(course_folder, module_name):
    path = Path(__file__).parent.parent / 'curriculum' / 'beginner' / course_folder / 'policy.py'
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

c4 = load_policy('04-tools-and-structured-outputs', 'c4_policy')
c5 = load_policy('05-agent-development-frameworks', 'c5_policy')
c6 = load_policy('06-building-your-first-agent', 'c6_policy')
c7 = load_policy('07-computer-using-agents', 'c7_policy')

# =======================
# COURSE 04 TESTS
# =======================

def test_c4_unknown_tool_denied():
    ctx = c4.ExecutionContext(tenant_id='northstar', roles=['order:read'])
    res = c4.dispatch_tool('non_existent', '{}', ctx)
    assert res.error_type == 'UNKNOWN_TOOL'

def test_c4_cross_tenant_resource_denied():
    # ORD-789 belongs to 'other_tenant'
    ctx = c4.ExecutionContext(tenant_id='northstar', roles=['order:read'])
    res = c4.dispatch_tool('get_order', '{"order_id": "ORD-789"}', ctx)
    assert res.error_type == 'AUTH_ERROR'
    assert 'Cross-tenant' in res.message

def test_c4_internal_exception_returns_internal_tool_error():
    ctx = c4.ExecutionContext(tenant_id='northstar', roles=['order:read'])
    res = c4.dispatch_tool('crash_test', '{"order_id": "ORD-123"}', ctx)
    assert res.error_type == 'INTERNAL_TOOL_ERROR'

def test_c4_raw_exception_text_not_exposed():
    ctx = c4.ExecutionContext(tenant_id='northstar', roles=['order:read'])
    res = c4.dispatch_tool('crash_test', '{"order_id": "ORD-123"}', ctx)
    # The actual exception says "Database connection suddenly dropped!"
    assert 'Database connection suddenly dropped' not in res.message
    assert res.message == 'The tool failed unexpectedly.'

# =======================
# COURSE 05 TESTS
# =======================

def test_c5_grounding_invariant_enforcement():
    # If final answer cites dep_eu_114, it must be in the retrieved evidence list
    rec = c5.IncidentRecommendation(
        summary="Test summary",
        cited_evidence_ids=["missing_evidence"],
        suspected_deployment_id=None,
        attribution_strength="correlated",
        recommended_action="observe"
    )
    res = c5.AgentRunResult(
        recommendation=rec,
        evidence_retrieved=[],
        evidence_ids=[],
        steps=1,
        tool_calls=1
    )
    
    # 1. Missing evidence ID citation
    with pytest.raises(AssertionError, match="never retrieved"):
        c5.verify_grounding(res)

    # Now provide the evidence
    rec.cited_evidence_ids = ["health:123"]
    res.evidence_retrieved = [
        c5.HealthResult(evidence_id='health:123', status='DEGRADED', error_rate_pct=15.0, symptom='None')
    ]
    c5.verify_grounding(res)
    
    # 2. Suspected deployment but not retrieved
    rec.suspected_deployment_id = "dep_123"
    with pytest.raises(AssertionError, match="Suspected deployment dep_123 was not retrieved"):
        c5.verify_grounding(res)
        
    res.evidence_retrieved.append(
        c5.DeploymentResult(evidence_id='dep:123', latest_deployment_id='dep_123', deployed_minutes_ago=5, author='bot')
    )
    rec.cited_evidence_ids.append("dep:123")
    c5.verify_grounding(res)
    
    # 3. Asserting verified causality
    rec.attribution_strength = "verified"
    with pytest.raises(AssertionError, match="Temporal correlation .* cannot establish 'verified' causality"):
        c5.verify_grounding(res)
        
    rec.attribution_strength = "correlated"
    c5.verify_grounding(res)
    
    # 4. Requesting a rollback without supporting deployment evidence
    rec.recommended_action = "consider_rollback"
    rec.suspected_deployment_id = None
    with pytest.raises(AssertionError, match="Rollback recommended without a suspected deployment"):
        c5.verify_grounding(res)

def test_c5_model_decision_no_shared_state():
    # Verify mutable default fix: Instances should not share the tool_calls list
    decision1 = c5.ModelDecision(decision_summary="First decision")
    decision2 = c5.ModelDecision(decision_summary="Second decision")
    
    decision1.tool_calls.append(c5.ToolCall(name="mock", arguments_json="{}"))
    assert len(decision1.tool_calls) == 1
    assert len(decision2.tool_calls) == 0

# =======================
# COURSE 06 TESTS
# =======================

def test_c6_tenant_id_rejected_as_extra_field():
    from pydantic import ValidationError
    # Model should forbid injecting tenant_id
    with pytest.raises(ValidationError) as exc:
        c6.IssueRefundArgs(
            customer_id='c1', transaction_id='tx_123', amount_cents=500, 
            idempotency_key='k', tenant_id='hacker_tenant'
        )
    assert 'Extra inputs are not permitted' in str(exc.value)

def test_c6_cross_tenant_refund_denied():
    # Attempting to refund a transaction belonging to AcmeCorp using Northstar's tenant_id
    cmd = c6.RefundCommand(
        tenant_id='Northstar', 
        customer_id='C-99',
        transaction_id='TX-801', 
        amount_cents=5000, 
        idempotency_key='k2'
    )
    with pytest.raises(c6.AuthorizationError, match="belongs to another organization"):
        c6._issue_refund_impl(cmd)

def test_c6_approval_rejection_denied():
    prop = c6.RefundProposal(customer_id='C-55', transaction_id='TX-901', amount_cents=10000, reason='r')
    approval = c6.Approval(proposal_digest=c6.hash_proposal(prop), approver_id='MGR-1', decision=c6.ApprovalDecision.REJECT, expires_at=time.time()+1000)
    with pytest.raises(ValueError, match="not to approve"):
        c6.validate_approval(prop, approval, current_time_unix=time.time())

def test_c6_expired_approval_denied():
    prop = c6.RefundProposal(customer_id='C-55', transaction_id='TX-901', amount_cents=10000, reason='r')
    approval = c6.Approval(proposal_digest=c6.hash_proposal(prop), approver_id='MGR-1', decision=c6.ApprovalDecision.APPROVE, expires_at=100) # expired
    with pytest.raises(ValueError, match="expired"):
        c6.validate_approval(prop, approval, current_time_unix=200)

def test_c6_mutated_proposal_invalidates_approval():
    prop = c6.RefundProposal(customer_id='C-55', transaction_id='TX-901', amount_cents=10000, reason='r')
    approval = c6.Approval(proposal_digest=c6.hash_proposal(prop), approver_id='MGR-1', decision=c6.ApprovalDecision.APPROVE, expires_at=time.time()+1000)
    
    # Mutate proposal (e.g. LLM attempts to refund more)
    prop.amount_cents = 50000 
    with pytest.raises(ValueError, match="mismatch"):
        c6.validate_approval(prop, approval, current_time_unix=time.time())

def test_c6_unauthorized_approver_denied():
    prop = c6.RefundProposal(customer_id='C-55', transaction_id='TX-901', amount_cents=10000, reason='r')
    approval = c6.Approval(proposal_digest=c6.hash_proposal(prop), approver_id='HACKER-1', decision=c6.ApprovalDecision.APPROVE, expires_at=time.time()+1000)
    with pytest.raises(c6.AuthorizationError, match="Unauthorized approver"):
        c6.validate_approval(prop, approval, current_time_unix=time.time())

def test_c6_idempotency_produces_only_one_logical_refund():
    cmd = c6.RefundCommand(
        tenant_id='Northstar', customer_id='C-55', transaction_id='TX-902', 
        amount_cents=10000, idempotency_key='idemp_key_1'
    )
    res1 = c6._issue_refund_impl(cmd)
    assert res1.status == 'success'
    
    # Second call with same idempotency key
    res2 = c6._issue_refund_impl(cmd)
    assert res2.status == 'already_processed'

# =======================
# COURSE 07 TESTS
# =======================

def test_c7_commit_action_without_approval_denied():
    ctrl = c7.ControllerState(allowed_origins=['https://safe.com'])
    ctrl.latest_snapshot_id = 'snap_1'
    action = c7.SubmitAction(snapshot_id='snap_1', action_type='submit', target_role='button', target_name='Submit', case_id='c', escalation_note='note', risk_level='COMMIT')
    assert c7.validate_approval(action, ctrl, None).status == 'APPROVAL_REQUIRED'

def test_c7_modified_payload_invalidates_approval():
    ctrl = c7.ControllerState(allowed_origins=['https://safe.com'])
    ctrl.latest_snapshot_id = 'snap_1'
    action = c7.SubmitAction(snapshot_id='snap_1', action_type='submit', target_role='button', target_name='Submit', case_id='c', escalation_note='Safe text', risk_level='COMMIT')
    approval = c7.grant_human_approval(action)
    
    # Attacker mutates action
    action.escalation_note = 'Malicious text'
    assert c7.validate_approval(action, ctrl, approval).status == 'APPROVAL_INVALID'

def test_c7_stale_snapshot_denied():
    ctrl = c7.ControllerState(allowed_origins=['https://safe.com'])
    ctrl.latest_snapshot_id = 'snap_1'
    action = c7.ClickAction(snapshot_id='snap_2', action_type='click', target_role='button', target_name='btn', target_id='btn')
    assert c7.validate_policy(action, 'https://safe.com', ctrl).status == 'STALE_SNAPSHOT'

def test_c7_unallowlisted_origin_denied():
    ctrl = c7.ControllerState(allowed_origins=['https://safe.com'])
    ctrl.latest_snapshot_id = 'snap_1'
    action = c7.ClickAction(snapshot_id='snap_1', action_type='click', target_role='button', target_name='btn', target_id='btn')
    assert c7.validate_policy(action, 'https://evil.com', ctrl).status == 'ORIGIN_DISALLOWED'
