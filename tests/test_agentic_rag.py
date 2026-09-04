"""Course 09 invariants: retrieved content is evidence, never authority."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "intermediate"
    / "09-agentic-rag"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course09_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course09_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


@pytest.fixture
def context():
    return lab.build_context()


@pytest.fixture
def completed_run():
    return lab.run_agentic_controller()


def test_simple_query_uses_fixed_retrieval():
    assert lab.select_pipeline("How do I reset my password FAQ?") == "fixed"
    assert policy.choose_retrieval_mode("hello") == policy.RetrievalMode.NO_RETRIEVAL


def test_multi_source_incident_routes_correctly():
    plan = lab.build_retrieval_plan()
    decisions = {query.query_id: policy.route_query(query) for query in plan.queries}
    assert decisions["q1-incident"].proposed_sources == (
        policy.SourceType.INCIDENT_DB,
    )
    assert decisions["q4-mitigation"].proposed_sources == (
        policy.SourceType.RUNBOOK_SEARCH,
    )
    assert decisions["q3-dependency"].route_type == policy.RouteType.MULTI_ROUTE
    assert set(decisions["q3-dependency"].proposed_sources) == {
        policy.SourceType.DEPENDENCY_GRAPH,
        policy.SourceType.PROVIDER_STATUS,
    }


def test_route_outcomes_include_unknown_and_ambiguous():
    unknown = policy.route_query(
        policy.RetrievalQuery(
            query_id="unknown-query", question="Tell me a joke", intent="chitchat"
        )
    )
    ambiguous = policy.route_query(
        policy.RetrievalQuery(
            query_id="ambiguous-query", question="What is the status?", intent="status"
        )
    )
    assert unknown.route_type == policy.RouteType.UNKNOWN
    assert ambiguous.route_type == policy.RouteType.AMBIGUOUS


def test_unknown_source_rejected(context):
    query = lab.build_retrieval_plan().queries[0]
    with pytest.raises(policy.PolicyError, match="UNKNOWN_SOURCE"):
        policy.build_request(
            query,
            "invented_source",
            context,
            policy.RetrievalBudget.from_context(context),
        )


def test_wrong_tenant_blocked(context):
    query = lab.build_retrieval_plan().queries[0].model_copy(
        update={"proposed_tenant_id": "globex"}, deep=True
    )
    with pytest.raises(policy.PolicyError, match="TENANT_SCOPE_DENIED"):
        policy.build_request(
            query,
            policy.SourceType.INCIDENT_DB,
            context,
            policy.RetrievalBudget.from_context(context),
            structured_parameters=lab.incident_parameters(),
        )


def test_query_budget_enforced():
    run = lab.run_agentic_controller(lab.build_context(max_queries=2))
    assert run.answer.stop_reason == policy.StopReason.BUDGET_EXHAUSTED
    assert run.answer.confidence_label == policy.ConfidenceLabel.INSUFFICIENT
    assert run.budget.used_queries == 2


def test_hop_budget_enforced():
    run = lab.run_agentic_controller(lab.build_context(max_hops=0))
    assert run.answer.stop_reason == policy.StopReason.BUDGET_EXHAUSTED
    assert run.gap.status == policy.EvidenceStatus.MISSING_DEPENDENCY


def test_missing_dependency_triggers_one_bounded_graph_retrieval(completed_run):
    graph_traces = [
        trace
        for trace in completed_run.traces
        if trace.source_type == policy.SourceType.DEPENDENCY_GRAPH
    ]
    assert len(graph_traces) == 1
    assert graph_traces[0].hop == 1
    assert completed_run.plan.max_corrective_retrievals == 1


def test_sufficient_evidence_stops_without_extra_sources(completed_run):
    assert completed_run.gap.status == policy.EvidenceStatus.SUFFICIENT
    assert completed_run.answer.stop_reason == policy.StopReason.SUFFICIENT
    assert completed_run.budget.used_queries == 3
    assert policy.SourceType.PROVIDER_STATUS not in {
        trace.source_type for trace in completed_run.traces
    }
    assert policy.SourceType.WEB_SEARCH not in {
        trace.source_type for trace in completed_run.traces
    }


def test_old_incident_ranks_below_current_incident(context):
    query = lab.build_retrieval_plan().queries[0]
    budget = policy.RetrievalBudget.from_context(context)
    request = policy.build_request(
        query,
        policy.SourceType.INCIDENT_DB,
        context,
        budget,
        structured_parameters=lab.incident_parameters(),
    )
    result = lab.execute_fixture_retrieval(request)
    assert result.evidence[0].evidence_id == "incident-eu-2026"
    assert result.evidence[1].evidence_id == "incident-eu-2024"
    assert result.evidence[0].relevance_score == result.evidence[1].relevance_score


def test_conflicting_credible_sources_are_not_silently_selected(completed_run, context):
    budget = policy.RetrievalBudget.from_context(context)
    conflicted = lab.add_provider_evidence(
        completed_run.bundle, context, budget, conflict=True
    )
    gap = policy.evaluate_evidence_sufficiency(conflicted)
    assert gap.status == policy.EvidenceStatus.CONFLICT


def test_compatible_provider_status_preserves_sufficiency(completed_run, context):
    budget = policy.RetrievalBudget.from_context(context)
    corroborated = lab.add_provider_evidence(
        completed_run.bundle, context, budget, conflict=False
    )
    gap = policy.evaluate_evidence_sufficiency(corroborated)
    assert gap.status == policy.EvidenceStatus.SUFFICIENT


def test_unsupported_citation_rejected(completed_run):
    runbook = next(
        item for item in completed_run.bundle.items if item.evidence_id == "runbook-v7"
    )
    claim = lab.material_claims()[1]
    links = (
        policy.ClaimEvidenceLink(
            claim_id=claim.claim_id, evidence_ids=(runbook.evidence_id,)
        ),
    )
    citations = (
        policy.Citation(
            claim_id=claim.claim_id,
            evidence_id=runbook.evidence_id,
            source_id=runbook.source_id,
            source_version=runbook.source_version,
        ),
    )
    report = policy.verify_citations(
        (claim,), links, citations, completed_run.bundle
    )
    assert report.verifications[0].status == policy.ClaimStatus.UNSUPPORTED


def test_missing_material_citation_rejected(completed_run):
    claims = lab.material_claims()
    citations = tuple(
        citation
        for citation in completed_run.answer.citations
        if citation.claim_id != "claim-1"
    )
    report = policy.verify_citations(
        claims, lab.claim_links(), citations, completed_run.bundle
    )
    claim_1 = next(
        result for result in report.verifications if result.claim_id == "claim-1"
    )
    assert claim_1.status == policy.ClaimStatus.MISSING_CITATION
    assert report.citation_completeness < 1


def test_claim_evidence_mapping_validated(completed_run):
    report = lab.citation_report_for_run(completed_run)
    assert report.citation_completeness == 1
    assert report.unsupported_claim_rate == 0
    assert all(
        result.status == policy.ClaimStatus.SUPPORTED
        for result in report.verifications
    )


def test_sql_tenant_scope_is_application_owned(context):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        policy.IncidentQueryParameters(
            service="checkout",
            region="eu",
            start_time="2026-01-15T10:00:00+00:00",
            end_time="2026-01-15T11:00:00+00:00",
            limit=10,
            tenant_id="globex",
        )
    request = policy.build_request(
        lab.build_retrieval_plan().queries[0],
        policy.SourceType.INCIDENT_DB,
        context,
        policy.RetrievalBudget.from_context(context),
        structured_parameters=lab.incident_parameters(),
    )
    assert request.tenant_id == "northstar"


def test_graph_hop_limit_enforced(context):
    assert lab.bounded_graph_traversal(
        "checkout", requested_max_hops=2, context=context
    ) == ("checkout", "payment-service", "eu-provider")
    with pytest.raises(policy.PolicyError, match="HOP_BUDGET_EXCEEDED"):
        lab.bounded_graph_traversal(
            "checkout", requested_max_hops=3, context=context
        )


def test_web_confidential_query_blocked():
    context = lab.build_context(allow_web_search=True)
    query = policy.RetrievalQuery(
        query_id="confidential-web",
        question="Search incident-eu-2026 for Northstar customer records",
        intent="provider-status",
        data_classification=policy.DataClassification.CONFIDENTIAL,
    )
    with pytest.raises(policy.PolicyError, match="CONFIDENTIAL_WEB_QUERY_BLOCKED"):
        policy.build_request(
            query,
            policy.SourceType.WEB_SEARCH,
            context,
            policy.RetrievalBudget.from_context(context),
            outbound_query=query.question,
            target_domain="status.eu-provider.example",
            internal_sources_exhausted=True,
        )


def test_web_unknown_domain_blocked():
    context = lab.build_context(allow_web_search=True)
    with pytest.raises(policy.PolicyError, match="WEB_DOMAIN_NOT_ALLOWED"):
        lab.approved_web_request(
            context,
            policy.RetrievalBudget.from_context(context),
            target_domain="untrusted.example",
        )


def test_web_waits_until_internal_sources_are_exhausted():
    context = lab.build_context(allow_web_search=True)
    query = policy.RetrievalQuery(
        query_id="premature-web",
        question="Official EU payment provider status",
        intent="provider-status",
        data_classification=policy.DataClassification.PUBLIC,
    )
    with pytest.raises(policy.PolicyError, match="INTERNAL_SOURCES_NOT_EXHAUSTED"):
        policy.build_request(
            query,
            policy.SourceType.WEB_SEARCH,
            context,
            policy.RetrievalBudget.from_context(context),
            outbound_query="official EU payment provider service status",
            target_domain="status.eu-provider.example",
            internal_sources_exhausted=False,
        )


def test_web_query_is_minimized_and_allowlisted():
    context = lab.build_context(allow_web_search=True)
    request = lab.approved_web_request(
        context,
        policy.RetrievalBudget.from_context(context),
        target_domain="status.eu-provider.example",
    )
    assert request.outbound_query == "official EU payment provider service status"
    assert "northstar" not in request.outbound_query.lower()
    assert "incident-eu-2026" not in request.outbound_query.lower()


def test_prompt_injected_result_cannot_alter_policy(context):
    before = context.model_dump(mode="json")
    inspection = lab.inspect_untrusted_evidence(lab.malicious_web_evidence())
    assert inspection["instructions_authorized"] is False
    assert context.model_dump(mode="json") == before
    with pytest.raises(ValidationError):
        context.tenant_id = "globex"


def test_prompt_injected_result_cannot_authorize_action():
    bundle = policy.EvidenceBundle(
        tenant_id="northstar",
        items=(lab.malicious_web_evidence(), lab.runbook_evidence()),
    )
    proposal = policy.build_mitigation_proposal(
        "restart-every-production-service",
        "production",
        ("web-injected-result", "runbook-v7"),
        bundle,
    )
    assert proposal.policy_status == policy.ProposalPolicyStatus.DENIED


def test_duplicate_retrieval_detected(context):
    budget = policy.RetrievalBudget.from_context(context)
    query = lab.build_retrieval_plan().queries[3]
    request = policy.build_request(
        query, policy.SourceType.RUNBOOK_SEARCH, context, budget
    )
    seen: set[tuple[str, policy.SourceType, str]] = set()
    lab.ensure_not_duplicate(request, seen)
    with pytest.raises(policy.PolicyError, match="DUPLICATE_RETRIEVAL"):
        lab.ensure_not_duplicate(request, seen)


def test_insufficient_evidence_abstains():
    run = lab.run_agentic_controller(include_dependency=False)
    assert run.answer.confidence_label == policy.ConfidenceLabel.INSUFFICIENT
    assert run.answer.stop_reason == policy.StopReason.INSUFFICIENT_EVIDENCE
    assert "dependency" in run.answer.missing_evidence
    assert run.answer.summary.startswith("INSUFFICIENT_EVIDENCE")


def test_mitigation_proposal_requires_evidence(completed_run):
    with pytest.raises(policy.PolicyError, match="MITIGATION_EVIDENCE_REQUIRED"):
        policy.build_mitigation_proposal(
            "validate-provider-configuration", "eu-provider", (), completed_run.bundle
        )


def test_grounded_mitigation_is_proposal_only(completed_run):
    proposal = policy.build_mitigation_proposal(
        "validate-provider-configuration",
        "eu-provider",
        ("incident-eu-2026", "runbook-v7"),
        completed_run.bundle,
    )
    assert proposal.policy_status == policy.ProposalPolicyStatus.ALLOWED_PROPOSAL


def test_rollback_remains_approval_gated(completed_run):
    proposal = policy.build_mitigation_proposal(
        "rollback-deployment",
        "checkout-eu",
        ("incident-eu-2026", "runbook-v7"),
        completed_run.bundle,
    )
    assert proposal.policy_status == policy.ProposalPolicyStatus.APPROVAL_REQUIRED


def test_trace_records_observable_retrieval_decisions(completed_run):
    assert [trace.sequence for trace in completed_run.traces] == [1, 2, 3]
    assert all(trace.query_id and trace.result_count for trace in completed_run.traces)
    assert completed_run.traces[-1].gap_decision == policy.EvidenceStatus.SUFFICIENT
    assert completed_run.traces[-1].stop_reason == policy.StopReason.SUFFICIENT


def test_fixed_vs_agentic_comparison_has_no_universal_winner():
    simple, incident = lab.fixed_vs_agentic_comparison()
    assert simple["winner"] == "fixed"
    assert simple["fixed_cost_usd"] < simple["agentic_cost_usd"]
    assert simple["fixed_latency_ms"] < simple["agentic_latency_ms"]
    assert incident["winner"] == "agentic"
    assert (
        incident["agentic_required_evidence_recall"]
        > incident["fixed_required_evidence_recall"]
    )


def test_default_retrieval_regression_gate_passes():
    metrics = lab.validate_default_regression_gate()
    assert metrics.tenant_violations == 0
    assert metrics.unsafe_action_rate == 0
    assert metrics.citation_completeness == 1
    assert metrics.unsupported_claim_rate == 0


def test_budget_model_forbids_planner_owned_limits(context):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        policy.RetrievalQuery(
            query_id="planner-overreach",
            question="Ignore the budget",
            intent="incident-facts",
            max_queries=999,
        )
    assert context.max_queries == 5
