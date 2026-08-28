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
    res = c5.AgentRunResult(
        final_answer="The root cause is dep_eu_114",
        evidence_retrieved=[],
        evidence_ids=[],
        steps=1,
        tool_calls=1
    )
    with pytest.raises(AssertionError, match="deployment tool was never executed"):
        c5.verify_grounding(res)

    # Now provide the evidence
    res.evidence_retrieved = [
        c5.DeploymentResult(evidence_id='1', latest_deployment_id='dep_eu_114', deployed_minutes_ago=5, author='bot')
    ]
    # Should pass without assertion error
    c5.verify_grounding(res)
    
    # Verify that causal language is rejected
    res.evidence_retrieved.append(c5.HealthResult(evidence_id='2', status='DEGRADED', error_rate_pct=15.0, symptom='None'))
    res.final_answer = "Deployment dep_eu_114 caused the DEGRADED state."
    with pytest.raises(AssertionError, match="proven causality"):
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
    approval = c6.Approval(proposal_digest='abc', approver_id='a', expires_at_unix=9999999999)
    # Model should forbid injecting tenant_id
    with pytest.raises(ValidationError) as exc:
        c6.IssueRefundArgs(
            transaction_id='tx_123', amount_cents=500, reason='x', 
            idempotency_key='k', approval=approval, tenant_id='hacker_tenant'
        )
    assert 'Extra inputs are not permitted' in str(exc.value)

def test_c6_cross_tenant_refund_denied():
    approval = c6.Approval(proposal_digest='abc', approver_id='a', expires_at_unix=9999999999)
    cmd = c6.RefundCommand(
        tenant_id='acme_inc', 
        transaction_id='tx_789_other_tenant', 
        amount_cents=500, reason='x', idempotency_key='k2', approval=approval
    )
    with pytest.raises(PermissionError, match="belongs to a different tenant"):
        c6._issue_refund_impl(cmd)

def test_c6_expired_approval_denied():
    prop = c6.RefundProposal(transaction_id='t', amount_cents=1, reason='r')
    approval = c6.Approval(proposal_digest=c6.hash_proposal(prop), approver_id='a', expires_at_unix=100) # expired
    with pytest.raises(ValueError, match="expired"):
        c6.validate_approval(prop, approval, current_time_unix=200)

def test_c6_mutated_proposal_invalidates_approval():
    prop = c6.RefundProposal(transaction_id='t', amount_cents=100, reason='r')
    approval = c6.Approval(proposal_digest=c6.hash_proposal(prop), approver_id='a', expires_at_unix=time.time()+1000)
    
    # Mutate proposal (e.g. LLM attempts to refund more)
    prop.amount_cents = 50000 
    with pytest.raises(ValueError, match="mismatch"):
        c6.validate_approval(prop, approval, current_time_unix=time.time())

def test_c6_idempotency_produces_only_one_logical_refund():
    approval = c6.Approval(proposal_digest='abc', approver_id='a', expires_at_unix=9999999999)
    cmd = c6.RefundCommand(
        tenant_id='acme_inc', transaction_id='tx_123_acme_inc', 
        amount_cents=500, reason='x', idempotency_key='idemp_key_1', approval=approval
    )
    res1 = c6._issue_refund_impl(cmd)
    assert res1.status == 'success'
    
    # Second call with same idempotency key
    res2 = c6._issue_refund_impl(cmd)
    assert res2.status == 'duplicate'

# =======================
# COURSE 07 TESTS
# =======================

def test_c7_commit_action_without_approval_denied():
    action = c7.UIAction(action_type='submit_commit', target_id='btn', value=None)
    with pytest.raises(PermissionError, match="requires an explicit human approval token"):
        c7.validate_approval(action, None)

def test_c7_modified_payload_invalidates_approval():
    action = c7.UIAction(action_type='submit_commit', target_id='btn', value='Safe text')
    approval = c7.grant_human_approval(action)
    
    # Attacker mutates action
    action.value = 'Malicious text'
    with pytest.raises(PermissionError, match="mismatch"):
        c7.validate_approval(action, approval)

def test_c7_stale_snapshot_denied():
    action = c7.UIAction(action_type='click', target_id='btn', value=None)
    ctrl = c7.ControllerState(allowed_origins=['https://safe.com'], current_origin='https://safe.com', snapshot_id='snap_2')
    
    with pytest.raises(ValueError, match="Stale state"):
        c7.validate_policy(action, agent_snapshot_id='snap_1', controller=ctrl)

def test_c7_unallowlisted_origin_denied():
    action = c7.UIAction(action_type='click', target_id='btn', value=None)
    ctrl = c7.ControllerState(allowed_origins=['https://safe.com'], current_origin='https://evil.com', snapshot_id='snap_1')
    
    with pytest.raises(PermissionError, match="not in the allowlist"):
        c7.validate_policy(action, agent_snapshot_id='snap_1', controller=ctrl)
