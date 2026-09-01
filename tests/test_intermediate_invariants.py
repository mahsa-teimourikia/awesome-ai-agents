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

def test_required_quarantined_evidence_detected(setup_data):
    req, cands = setup_data
    req.required_evidence_ids = ["poison_doc"]
    res = build_context(req, cands)
    assert res.status == ContextStatus.MISSING_REQUIRED_CONTEXT
    assert "poison_doc" in res.missing_required_ids

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
    res = build_context(req, cands)
    # Verify that both task state and summary are preserved
    assert res.packet.task_state is not None
    assert res.packet.task_state.item_id == "state_1"
    assert res.packet.structured_summary is not None
    assert res.packet.structured_summary.item_id == "summary_1"
