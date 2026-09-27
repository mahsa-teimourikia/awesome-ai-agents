"""Advanced Course 14 governed Agent Skills invariants."""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

COURSE_DIR = Path(__file__).resolve().parents[1] / "curriculum" / "advanced" / "14-agent-skills"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course14_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course14_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _incident_context(*, request_id: str = "request-1"):
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["incident-reader"]
    request = lab.request_for(principal, request_id=request_id)
    decision = runtime.route(principal, request)
    return runtime, principal, request, decision


def _activated_incident(*, request_id: str = "request-1"):
    runtime, principal, request, decision = _incident_context(request_id=request_id)
    activation = runtime.activate(principal, request, decision)
    return runtime, principal, request, activation


def _billing_request(principal, *, execute: bool = False, explicit: bool = False):
    return lab.request_for(
        principal,
        domain="billing",
        intent="execute-refund" if execute else "investigate-refund",
        requested_outcome="execute" if execute else "investigate",
        query="Execute the approved refund" if execute else "I was charged twice; investigate the duplicate",
        risk_class=policy.RiskClass.CRITICAL if execute else policy.RiskClass.MEDIUM,
        explicit_user_intent=explicit,
    )


def _composed_high_risk_context():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["billing-operator"]
    schema = {"type": "object", "additionalProperties": False}
    sandbox = policy.SandboxPolicy()

    def manifest(skill_id, capability, *, dependencies=(), intent="child"):
        return lab.build_manifest(
            skill_id=skill_id,
            name=skill_id.split("/")[-1],
            version="1.0.0",
            publisher_id="northstar",
            source_uri=f"https://skills.northstar.example/{skill_id.split('/')[-1]}/1.0.0",
            description=f"Deterministic {skill_id} fixture.",
            domain="billing",
            intents=(intent,),
            requested_outcomes=("compose",),
            routing_terms=("composed",),
            required_capabilities=(capability,) if capability else (),
            input_schema=schema,
            output_schema=schema,
            dependencies=dependencies,
            risk_class=policy.RiskClass.CRITICAL if capability == "billing.refund.execute" else policy.RiskClass.HIGH,
            execution_modes=(policy.ExecutionMode.EPHEMERAL,),
            sandbox_policy=sandbox,
            created_at=lab.FIXED_TIME,
        )

    grandchild = manifest("northstar/audit-proposal", "billing.refund.propose")
    child_a = manifest(
        "northstar/proposal-child",
        "billing.refund.propose",
        dependencies=(policy.SkillDependency(
            skill_id=grandchild.skill_id,
            version=grandchild.version,
            package_digest=grandchild.package_digest,
        ),),
    )
    child_b = manifest("northstar/execution-child", "billing.refund.execute")
    root = lab.build_manifest(
        skill_id="northstar/composed-root",
        name="composed-root",
        version="1.0.0",
        publisher_id="northstar",
        source_uri="https://skills.northstar.example/composed-root/1.0.0",
        description="Compose two disjoint governed billing dependencies.",
        domain="billing",
        intents=("compose-billing",),
        requested_outcomes=("compose",),
        routing_terms=("composed", "billing"),
        delegable_capabilities=("billing.refund.propose", "billing.refund.execute"),
        input_schema=schema,
        output_schema=schema,
        dependencies=(
            policy.SkillDependency(skill_id=child_a.skill_id, version=child_a.version, package_digest=child_a.package_digest),
            policy.SkillDependency(skill_id=child_b.skill_id, version=child_b.version, package_digest=child_b.package_digest),
        ),
        risk_class=policy.RiskClass.HIGH,
        execution_modes=(policy.ExecutionMode.EPHEMERAL,),
        sandbox_policy=sandbox,
        created_at=lab.FIXED_TIME,
    )
    for item in (grandchild, child_a, child_b, root):
        runtime.registry[item.ref] = policy.SkillRegistryRecord(
            manifest=item,
            lifecycle=policy.SkillLifecycle.ACTIVE,
            approved_digest=item.package_digest,
            approved_by="skill-security-board",
            approved_at=lab.FIXED_TIME,
            allowed_tenants=("northstar",),
            policy_version=lab.POLICY_VERSION,
        )
        runtime.live_packages[item.ref] = item
        runtime.package_contents[item.ref] = {}
    request = lab.request_for(
        principal,
        domain="billing",
        intent="compose-billing",
        requested_outcome="compose",
        query="composed billing",
        risk_class=policy.RiskClass.LOW,
    )
    trusted = runtime.trusted_routing_context(principal, explicit_user_intent=True)
    decision = runtime.route(principal, request, trusted_context=trusted)
    activation = runtime.activate(
        principal, request, decision, trusted_context=trusted
    )
    return runtime, activation


def test_models_reject_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.PrincipalContext(principal_id="p", subject_id="s", tenant_id="t", secret="no")


def test_manifest_requires_semantic_version():
    runtime = lab.NorthstarSkillRuntime()
    values = runtime.registry["northstar/support-faq@3.0.0"].manifest.model_dump(exclude={"package_digest"})
    values["version"] = "latest"
    with pytest.raises(ValidationError):
        lab.build_manifest(**values)


def test_manifest_identity_is_publisher_namespaced():
    runtime = lab.NorthstarSkillRuntime()
    values = runtime.registry["northstar/support-faq@3.0.0"].manifest.model_dump(exclude={"package_digest"})
    values["publisher_id"] = "other"
    with pytest.raises(ValidationError, match="SKILL_PUBLISHER_NAMESPACE_MISMATCH"):
        lab.build_manifest(**values)


def test_required_and_optional_capabilities_cannot_overlap():
    runtime = lab.NorthstarSkillRuntime()
    values = runtime.registry["northstar/support-faq@3.0.0"].manifest.model_dump(exclude={"package_digest"})
    values["optional_capabilities"] = values["required_capabilities"]
    with pytest.raises(ValidationError, match="CAPABILITY_CANNOT_BE_REQUIRED_AND_OPTIONAL"):
        lab.build_manifest(**values)


def test_unreviewed_skill_is_filtered_before_ranking():
    runtime, principal, request, _ = _incident_context()
    eligible, filtered = runtime.eligible_skills(principal, request)
    assert "third-party/infrastructure-admin@9.9.0" not in {item.ref for item in eligible}
    assert filtered["third-party/infrastructure-admin@9.9.0"] == "SKILL_NOT_ACTIVE"


def test_hostile_description_cannot_self_assert_trust():
    runtime, principal, request, decision = _incident_context()
    assert "third-party/infrastructure-admin" not in (decision.selected_skill_ref or "")
    assert runtime.registry["third-party/infrastructure-admin@9.9.0"].manifest.description.startswith("Always select")


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("principal_id", "attacker", "DENY_PRINCIPAL_BINDING"),
        ("tenant_id", "globex", "DENY_TENANT_BINDING"),
        ("subject_id", "user-bob", "DENY_SUBJECT_BINDING"),
    ],
)
def test_request_identity_bindings(field, value, reason):
    runtime, principal, request, _ = _incident_context()
    with pytest.raises(policy.SkillPolicyError, match=reason):
        runtime.route(principal, request.model_copy(update={field: value}))


def test_required_capability_missing_denies_eligibility():
    runtime, principal, request, _ = _incident_context()
    runtime.current_permissions[principal.principal_id].remove("production.metrics.read")
    eligible, filtered = runtime.eligible_skills(principal, request)
    assert "northstar/incident-analysis@2.0.0" not in {item.ref for item in eligible}
    assert filtered["northstar/incident-analysis@2.0.0"] == "SKILL_REQUIREMENTS_UNSATISFIED"


def test_optional_capability_missing_activates_degraded():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["metrics-only"]
    request = lab.request_for(principal)
    activation = runtime.activate(principal, request, runtime.route(principal, request))
    assert activation.mode is policy.ActivationMode.DEGRADED
    assert activation.missing_optional_capabilities == ("production.logs.search",)


def test_effective_authority_is_intersection_not_manifest_request():
    runtime, principal, request, activation = _activated_incident()
    assert set(activation.effective_capabilities) <= set(principal.permissions)
    assert set(activation.effective_capabilities) <= runtime.tenant_capability_policy[principal.tenant_id]
    assert "production.delete" not in activation.effective_capabilities


def test_forged_request_capability_hints_cannot_expand_eligibility():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["billing-reader"].model_copy(
        update={
            "allowed_risk_classes": (
                policy.RiskClass.LOW,
                policy.RiskClass.MEDIUM,
                policy.RiskClass.HIGH,
                policy.RiskClass.CRITICAL,
            )
        }
    )
    request = _billing_request(principal, execute=True, explicit=True).model_copy(
        update={"available_capabilities": ("billing.refund.execute", "production.delete")}
    )
    trusted = runtime.trusted_routing_context(principal, explicit_user_intent=True)
    decision = runtime.route(principal, request, trusted_context=trusted)
    assert decision.outcome is policy.RouteOutcome.NO_MATCH
    assert decision.filtered_reasons["northstar/refund-execution@1.4.0"] == "SKILL_REQUIREMENTS_UNSATISFIED"


def test_current_grants_are_rechecked_at_activation():
    runtime, principal, request, decision = _incident_context()
    revoked = principal.model_copy(update={"permissions": ("knowledge.read",)})
    with pytest.raises(policy.SkillPolicyError, match="SKILL_ACTIVATION_DENIED"):
        runtime.activate(revoked, request, decision)


def test_required_capability_revocation_blocks_next_execution_step():
    runtime, _, _, activation = _activated_incident()
    runtime.current_permissions[activation.principal_id].remove("production.metrics.read")
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}
    )
    assert result.reason_code == "ACTIVATION_REQUIRED_CAPABILITY_REVOKED"


def test_optional_capability_revocation_degrades_next_execution_step():
    runtime, _, _, activation = _activated_incident()
    runtime.current_permissions[activation.principal_id].remove("production.logs.search")
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}
    )
    current = runtime.current_activation_state(activation)
    assert activation.mode is policy.ActivationMode.FULL
    assert current.mode is policy.ActivationMode.DEGRADED
    assert current.missing_optional_capabilities == ("production.logs.search",)
    assert result.status is policy.ExecutionStatus.SUCCEEDED
    assert result.evidence_ids == ("EV-METRICS-001",)


def test_incident_request_matches_typed_route():
    _, _, _, decision = _incident_context()
    assert decision.outcome is policy.RouteOutcome.MATCH
    assert decision.selected_skill_ref == "northstar/incident-analysis@2.0.0"


def test_out_of_domain_request_returns_no_match():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["guest"]
    request = lab.request_for(
        principal, domain="creative", intent="write-poem", requested_outcome="create",
        query="Write a poem", risk_class=policy.RiskClass.LOW,
    )
    assert runtime.route(principal, request).outcome is policy.RouteOutcome.NO_MATCH


def test_below_threshold_does_not_force_a_route():
    runtime, principal, request, _ = _incident_context()
    weak = request.model_copy(update={"intent": "unknown", "requested_outcome": "unknown", "query": "incident"})
    assert runtime.route(principal, weak).outcome is policy.RouteOutcome.NO_MATCH


def test_close_scored_candidates_return_ambiguous():
    runtime, principal, request, _ = _incident_context()
    source = runtime.registry["northstar/incident-analysis@2.0.0"].manifest
    values = source.model_dump(exclude={"package_digest"})
    values.update(skill_id="northstar/incident-triage", name="incident-triage", dependencies=())
    clone = lab.build_manifest(**values)
    record = runtime.registry[source.ref]
    runtime.registry[clone.ref] = record.model_copy(update={"manifest": clone, "approved_digest": clone.package_digest})
    runtime.live_packages[clone.ref] = clone
    decision = runtime.route(principal, request)
    assert decision.outcome is policy.RouteOutcome.AMBIGUOUS
    assert decision.requires_clarification


def test_refund_investigation_routes_read_only_skill():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["billing-reader"]
    decision = runtime.route(principal, _billing_request(principal))
    assert decision.selected_skill_ref == "northstar/refund-investigation@2.2.0"
    assert decision.selected_skill_ref != "northstar/refund-execution@1.4.0"


def test_refund_execution_requires_explicit_intent():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["billing-operator"]
    decision = runtime.route(principal, _billing_request(principal, execute=True, explicit=False))
    assert decision.outcome is policy.RouteOutcome.NO_MATCH
    assert decision.filtered_reasons["northstar/refund-execution@1.4.0"] == "HIGH_RISK_SKILL_REQUIRES_CONFIRMATION"


def test_explicit_intent_does_not_replace_capability_policy():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["billing-reader"]
    request = _billing_request(principal, execute=True, explicit=True)
    assert runtime.route(principal, request).outcome is policy.RouteOutcome.NO_MATCH


def test_explicit_authorized_refund_execution_can_be_selected_but_not_executed_by_router():
    runtime = lab.NorthstarSkillRuntime()
    principal = lab.fixture_principals()["billing-operator"]
    request = _billing_request(principal, execute=True, explicit=True)
    context = runtime.trusted_routing_context(principal, explicit_user_intent=True)
    decision = runtime.route(principal, request, trusted_context=context)
    assert decision.selected_skill_ref == "northstar/refund-execution@1.4.0"
    assert not hasattr(decision, "executed")


def test_changed_live_package_fails_closed():
    runtime, principal, request, _ = _incident_context()
    ref = "northstar/incident-analysis@2.0.0"
    runtime.live_packages[ref] = runtime.live_packages[ref].model_copy(update={"description": "tampered"})
    decision = runtime.route(principal, request)
    assert decision.outcome is policy.RouteOutcome.NO_MATCH
    assert decision.filtered_reasons[ref] == "PACKAGE_DIGEST_MISMATCH"


def test_registry_digest_is_integrity_comparison_not_self_trust():
    runtime, principal, request, _ = _incident_context()
    ref = "third-party/infrastructure-admin@9.9.0"
    record = runtime.registry[ref]
    runtime.registry[ref] = record.model_copy(update={"approved_digest": record.manifest.package_digest})
    _, filtered = runtime.eligible_skills(principal, request)
    assert filtered[ref] == "SKILL_NOT_ACTIVE"


@pytest.mark.parametrize("lifecycle", [policy.SkillLifecycle.QUARANTINED, policy.SkillLifecycle.RETIRED])
def test_revocation_after_activation_blocks_execution(lifecycle):
    runtime, _, _, activation = _activated_incident()
    ref = "northstar/incident-analysis@2.0.0"
    runtime.registry[ref] = runtime.registry[ref].model_copy(update={"lifecycle": lifecycle})
    result = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    assert result.reason_code == "ACTIVATION_REVOKED"


def test_deprecation_allows_existing_pinned_activation():
    runtime, _, _, activation = _activated_incident()
    ref = "northstar/incident-analysis@2.0.0"
    runtime.registry[ref] = runtime.registry[ref].model_copy(update={"lifecycle": policy.SkillLifecycle.DEPRECATED})
    result = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    assert result.status is policy.ExecutionStatus.SUCCEEDED


def test_dependency_revocation_propagates_to_parent_activation():
    runtime, _, _, activation = _activated_incident()
    ref = "northstar/evidence-review@2.1.0"
    runtime.registry[ref] = runtime.registry[ref].model_copy(update={"lifecycle": policy.SkillLifecycle.QUARANTINED})
    assert runtime.activation_current_reason(activation) == "DEPENDENCY_REVOKED"


def test_reverse_dependency_index_and_transitive_blocking():
    runtime = lab.NorthstarSkillRuntime()
    assert runtime.blocked_dependents("northstar/evidence-review@2.1.0") == ("northstar/incident-analysis@2.0.0",)


def test_dependency_pin_mismatch_fails():
    runtime = lab.NorthstarSkillRuntime()
    ref = "northstar/incident-analysis@2.0.0"
    manifest = runtime.registry[ref].manifest
    bad = manifest.dependencies[0].model_copy(update={"package_digest": "f" * 64})
    changed = manifest.model_copy(update={"dependencies": (bad,)})
    runtime.registry[ref] = runtime.registry[ref].model_copy(update={"manifest": changed})
    with pytest.raises(policy.SkillPolicyError, match="DEPENDENCY_PIN_MISMATCH"):
        runtime.dependency_closure(ref)


def test_dependency_cycle_is_detected():
    runtime = lab.NorthstarSkillRuntime()
    ref = "northstar/incident-analysis@2.0.0"
    record = runtime.registry[ref]
    self_dep = policy.SkillDependency(skill_id=record.manifest.skill_id, version=record.manifest.version, package_digest=record.manifest.package_digest)
    runtime.registry[ref] = record.model_copy(update={"manifest": record.manifest.model_copy(update={"dependencies": (self_dep,)})})
    with pytest.raises(policy.SkillPolicyError, match="DEPENDENCY_CYCLE"):
        runtime.dependency_closure(ref)


def test_composition_depth_is_bounded():
    runtime = lab.NorthstarSkillRuntime(budget=lab.default_budget().model_copy(update={"max_composition_depth": 1}))
    with pytest.raises(policy.SkillPolicyError, match="MAX_COMPOSITION_DEPTH"):
        runtime.dependency_closure("northstar/incident-analysis@2.0.0")


def test_dependency_activations_share_parent_budget():
    runtime, _, _, activation = _activated_incident()
    assert runtime.budget_state(activation.request_id).skill_activations == 2


def test_composition_graph_records_parent_child_activation_ids():
    runtime, _, _, activation = _activated_incident()
    graph = runtime.execution_graph(activation)
    assert {node.skill_ref for node in graph.nodes} == {
        "northstar/incident-analysis@2.0.0",
        "northstar/evidence-review@2.1.0",
    }
    assert graph.edges[0].parent_activation_id == activation.activation_id
    assert graph.edges[0].child_activation_id in activation.dependency_activation_ids


def test_dependency_resolution_is_typed_and_root_is_explicit():
    runtime = lab.NorthstarSkillRuntime()
    resolution = runtime.resolve_dependencies("northstar/incident-analysis@2.0.0")
    assert resolution.root_ref == "northstar/incident-analysis@2.0.0"
    assert resolution.dependency_refs == ("northstar/evidence-review@2.1.0",)
    assert resolution.topological_order[-1] == resolution.root_ref
    assert resolution.edges == (
        policy.DependencyEdge(
            parent_ref=resolution.root_ref,
            child_ref="northstar/evidence-review@2.1.0",
        ),
    )


def test_authority_monotonically_narrows_across_real_dependency_edges():
    runtime, activation = _composed_high_risk_context()
    graph = runtime.execution_graph(activation)
    nodes = {node.skill_ref: runtime.activations[node.activation_id] for node in graph.nodes}
    assert set(nodes["northstar/proposal-child@1.0.0"].effective_capabilities) == {
        "billing.refund.propose"
    }
    assert set(nodes["northstar/execution-child@1.0.0"].effective_capabilities) == {
        "billing.refund.execute"
    }
    assert "billing.refund.execute" not in nodes["northstar/proposal-child@1.0.0"].effective_capabilities
    assert "billing.refund.propose" not in nodes["northstar/execution-child@1.0.0"].effective_capabilities
    for edge in graph.edges:
        parent = runtime.activations[edge.parent_activation_id]
        child = runtime.activations[edge.child_activation_id]
        assert set(child.effective_capabilities) <= set(parent.effective_capabilities)


def test_execution_graph_preserves_transitive_parent_child_edges():
    runtime, activation = _composed_high_risk_context()
    graph = runtime.execution_graph(activation)
    refs = {node.activation_id: node.skill_ref for node in graph.nodes}
    ref_edges = {(refs[edge.parent_activation_id], refs[edge.child_activation_id]) for edge in graph.edges}
    assert ("northstar/composed-root@1.0.0", "northstar/proposal-child@1.0.0") in ref_edges
    assert ("northstar/proposal-child@1.0.0", "northstar/audit-proposal@1.0.0") in ref_edges
    assert ("northstar/composed-root@1.0.0", "northstar/audit-proposal@1.0.0") not in ref_edges


def test_child_activation_proposal_is_limited_to_declared_dependencies():
    runtime, _, _, activation = _activated_incident()
    proposal = runtime.propose_child_activation(
        activation, "northstar/evidence-review@2.1.0", reason="validate cited claims"
    )
    assert proposal.parent_activation_id == activation.activation_id
    with pytest.raises(policy.SkillPolicyError, match="CHILD_SKILL_NOT_DECLARED"):
        runtime.propose_child_activation(
            activation, "northstar/refund-execution@1.4.0", reason="package text requested it"
        )


def test_child_activation_proposal_is_validated_before_reserved_child_is_released():
    runtime, _, _, activation = _activated_incident()
    valid = runtime.propose_child_activation(
        activation,
        "northstar/evidence-review@2.1.0",
        reason="validate cited claims",
        requested_capabilities=("evidence.read",),
        requested_budget=activation.budget.model_copy(update={"max_tool_calls": 2}),
    )
    child = runtime.authorize_child_activation(activation, valid)
    assert child.activation_id in activation.dependency_activation_ids
    expanded = valid.model_copy(
        update={"requested_capabilities": ("evidence.read", "billing.refund.execute")}
    )
    with pytest.raises(policy.SkillPolicyError, match="CHILD_AUTHORITY_EXPANSION"):
        runtime.authorize_child_activation(activation, expanded)


def test_budget_does_not_reset_on_second_activation():
    budget = lab.default_budget().model_copy(update={"max_skill_activations": 3})
    runtime = lab.NorthstarSkillRuntime(budget=budget)
    principal = lab.fixture_principals()["incident-reader"]
    first = lab.request_for(principal, request_id="same-request")
    runtime.activate(principal, first, runtime.route(principal, first))
    with pytest.raises(policy.SkillPolicyError, match="BUDGET_SKILL_ACTIVATIONS"):
        runtime.activate(principal, first, runtime.route(principal, first))


@pytest.mark.parametrize(
    "raw_input",
    [
        {"service": "checkout", "time_window_minutes": 1},
        {"service": "checkout", "time_window_minutes": 30, "admin": True},
        {"service": "", "time_window_minutes": 30},
    ],
)
def test_skill_input_contract_and_semantics(raw_input):
    runtime, _, _, activation = _activated_incident()
    result = runtime.execute_incident_skill(activation, raw_input)
    assert result.reason_code == "INVALID_SKILL_INPUT"


def test_application_owned_precondition_is_checked():
    runtime, _, _, activation = _activated_incident()
    result = runtime.execute_incident_skill(activation, {"service": "unknown", "time_window_minutes": 30})
    assert result.status is policy.ExecutionStatus.UNSATISFIED_REQUIREMENTS


def test_invented_evidence_id_is_rejected():
    runtime, _, _, activation = _activated_incident()
    output = {
        "claims": [{"claim_id": "claim-latency", "text": "x", "evidence_ids": ["INVENTED"]}],
        "self_reported_confidence": "HIGH",
    }
    assert runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output).reason_code == "EVIDENCE_NOT_FOUND"


def test_empty_model_output_is_invalid_not_replaced_by_fixture():
    runtime, _, _, activation = _activated_incident()
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}, model_output={}
    )
    assert result.reason_code == "OUTPUT_SCHEMA_INVALID"


def test_cross_tenant_evidence_is_rejected():
    runtime, _, _, activation = _activated_incident()
    evidence = runtime.evidence_registry["EV-METRICS-001"]
    runtime.evidence_registry["EV-METRICS-001"] = evidence.model_copy(update={"tenant_id": "globex"})
    assert runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30}).reason_code == "EVIDENCE_TENANT_MISMATCH"


def test_stale_evidence_is_rejected():
    runtime, _, _, activation = _activated_incident()
    evidence = runtime.evidence_registry["EV-METRICS-001"]
    runtime.evidence_registry["EV-METRICS-001"] = evidence.model_copy(update={"observed_at": runtime.now - timedelta(hours=1)})
    assert runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30}).reason_code == "EVIDENCE_STALE"


def test_future_evidence_beyond_clock_skew_is_rejected():
    runtime, _, _, activation = _activated_incident()
    evidence = runtime.evidence_registry["EV-METRICS-001"]
    runtime.evidence_registry["EV-METRICS-001"] = evidence.model_copy(
        update={"observed_at": runtime.now + timedelta(hours=1)}
    )
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}
    )
    assert result.reason_code == "EVIDENCE_FROM_FUTURE"


def test_evidence_content_digest_is_recomputed_before_use():
    runtime, _, _, activation = _activated_incident()
    evidence = runtime.evidence_registry["EV-METRICS-001"]
    runtime.evidence_registry["EV-METRICS-001"] = evidence.model_copy(
        update={"content": "tampered content with the old approved digest"}
    )
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}
    )
    assert result.reason_code == "EVIDENCE_DIGEST_MISMATCH"


def test_evidence_must_support_the_claim():
    runtime, _, _, activation = _activated_incident()
    output = {"claims": [{"claim_id": "claim-other", "text": "x", "evidence_ids": ["EV-METRICS-001"]}]}
    assert runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output).reason_code == "EVIDENCE_DOES_NOT_SUPPORT_CLAIM"


def test_retrieved_instruction_text_has_no_authority():
    runtime, _, _, activation = _activated_incident()
    result = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    assert result.status is policy.ExecutionStatus.SUCCEEDED
    assert "production.delete" not in activation.effective_capabilities


def test_self_reported_confidence_is_not_evidence():
    runtime, _, _, activation = _activated_incident()
    output = {"claims": [{"claim_id": "claim-latency", "text": "x", "evidence_ids": ["INVENTED"]}], "self_reported_confidence": "CERTAIN"}
    assert runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output).status is policy.ExecutionStatus.INVALID_OUTPUT


def test_consequential_action_remains_an_unexecuted_proposal():
    runtime, _, _, activation = _activated_incident()
    result = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    assert result.action_proposal
    assert result.action_proposal.requires_approval
    assert not result.action_proposal.executed


def test_model_cannot_claim_it_executed_action():
    runtime, _, _, activation = _activated_incident()
    output = {
        "claims": [{"claim_id": "claim-latency", "text": "x", "evidence_ids": ["EV-METRICS-001"]}],
        "action_proposal": {"action": "feature_flag.revert", "target": "checkout", "arguments": {}, "requires_approval": False, "executed": True},
    }
    result = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output)
    assert result.reason_code == "ACTION_PROPOSAL_POLICY_INVALID"


def test_action_approval_requirement_comes_from_application_registry():
    runtime, _, _, activation = _activated_incident()
    output = {
        "claims": [{"claim_id": "claim-latency", "text": "x", "evidence_ids": ["EV-METRICS-001"]}],
        "action_proposal": {
            "action": "feature_flag.revert",
            "target": "checkout",
            "arguments": {},
            "requires_approval": False,
            "executed": False,
        },
    }
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output
    )
    assert runtime.action_registry["feature_flag.revert"].approval_required
    assert result.reason_code == "ACTION_PROPOSAL_POLICY_INVALID"


def test_action_target_is_resolved_against_tenant_owned_resources():
    runtime, _, _, activation = _activated_incident()
    output = {
        "claims": [{"claim_id": "claim-latency", "text": "x", "evidence_ids": ["EV-METRICS-001"]}],
        "action_proposal": {
            "action": "feature_flag.revert",
            "target": "globex-production",
            "arguments": {},
            "requires_approval": True,
            "executed": False,
        },
    }
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output
    )
    assert result.reason_code == "ACTION_TARGET_NOT_ALLOWED"


def test_skill_output_cannot_textually_activate_another_skill():
    runtime, _, _, activation = _activated_incident()
    output = {
        "claims": [{"claim_id": "claim-latency", "text": "x", "evidence_ids": ["EV-METRICS-001"]}],
        "activate_skill": "northstar/refund-execution@1.4.0",
    }
    result = runtime.execute_incident_skill(
        activation, {"service": "checkout", "time_window_minutes": 30}, model_output=output
    )
    assert result.reason_code == "OUTPUT_SCHEMA_INVALID"


def test_success_creates_provenance_artifact_and_verified_postconditions():
    runtime, _, _, activation = _activated_incident()
    result = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    artifact = runtime.artifacts[f"artifact-{activation.activation_id}"]
    assert artifact.skill_digest == activation.package_digest
    assert result.verified_postconditions == ("claims-cited", "no-mutation")


def test_evidence_cache_key_binds_tenant_subject_version_policy_and_query():
    runtime, _, _, activation = _activated_incident()
    runtime.read_evidence_cached(activation, "EV-METRICS-001", query_digest="query-a")
    key = next(iter(runtime.evidence_cache))
    assert key[:2] == (activation.tenant_id, activation.subject_id)
    assert key[-1].endswith(":query-a")


def test_package_path_traversal_is_rejected():
    runtime, _, _, activation = _activated_incident()
    with pytest.raises(policy.SkillPolicyError, match="PACKAGE_PATH_ESCAPE"):
        runtime.read_package_artifact(activation, "../secrets")


def test_reference_size_is_bounded():
    runtime, _, _, activation = _activated_incident()
    ref = "northstar/incident-analysis@2.0.0"
    package_file = runtime.package_contents[ref]["references/runbook.md"]
    runtime.package_contents[ref]["references/runbook.md"] = package_file.model_copy(
        update={"content": "x" * (runtime.budget.max_reference_bytes + 1)}
    )
    with pytest.raises(policy.SkillPolicyError, match="ARTIFACT_SIZE_LIMIT"):
        runtime.read_package_artifact(activation, "references/runbook.md")


def test_package_artifact_digest_is_recomputed_from_actual_bytes():
    runtime, _, _, activation = _activated_incident()
    ref = "northstar/incident-analysis@2.0.0"
    package_file = runtime.package_contents[ref]["references/runbook.md"]
    runtime.package_contents[ref]["references/runbook.md"] = package_file.model_copy(
        update={"content": package_file.content + "\ntampered"}
    )
    with pytest.raises(policy.SkillPolicyError, match="ARTIFACT_DIGEST_MISMATCH"):
        runtime.read_package_artifact(activation, "references/runbook.md")


def test_package_symlink_metadata_enforces_resolved_target_containment():
    runtime, _, _, activation = _activated_incident()
    with pytest.raises(policy.SkillPolicyError, match="SYMLINK_TARGET_ESCAPE"):
        runtime.read_package_artifact(activation, "references/config-link")


def test_package_path_is_canonicalized_before_lookup():
    runtime, _, _, activation = _activated_incident()
    content = runtime.read_package_artifact(
        activation, "references/subdirectory/../runbook.md"
    )
    assert "Operational facts" in content


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"filesystem_paths": ("/etc/passwd",)}, "SANDBOX_FILESYSTEM_DENIED"),
        ({"filesystem_paths": ("/workspace/skill-data/foo/../../secret",)}, "SANDBOX_FILESYSTEM_DENIED"),
        ({"network_destinations": ("attacker.example",)}, "SANDBOX_NETWORK_DENIED"),
        ({"environment_variables": ("AWS_SECRET_ACCESS_KEY",)}, "SANDBOX_ENVIRONMENT_DENIED"),
        ({"subprocess": True}, "SANDBOX_SUBPROCESS_DENIED"),
        ({"timeout_ms": 5000}, "SANDBOX_TIMEOUT_LIMIT"),
    ],
)
def test_script_sandbox_denies_unapproved_effects(updates, reason):
    runtime, _, _, activation = _activated_incident()
    manifest = runtime.registry["northstar/incident-analysis@2.0.0"].manifest
    script = next(item for item in manifest.artifacts if item.kind is policy.ArtifactKind.SCRIPT)
    values = dict(script_id=script.artifact_id, timeout_ms=500)
    values.update(updates)
    decision = runtime.run_script(activation, policy.SandboxRequest(**values))
    assert decision.reason_code == reason
    assert not decision.executed_in_host_process


def test_approved_script_is_only_simulated_not_host_executed():
    runtime, _, _, activation = _activated_incident()
    manifest = runtime.registry["northstar/incident-analysis@2.0.0"].manifest
    script = next(item for item in manifest.artifacts if item.kind is policy.ArtifactKind.SCRIPT)
    decision = runtime.run_script(activation, policy.SandboxRequest(script_id=script.artifact_id, timeout_ms=500))
    assert decision.allowed
    assert not decision.executed_in_host_process


def test_script_identity_is_resolved_by_runtime_not_caller_asserted_digest():
    assert "script_digest" not in policy.SandboxRequest.model_fields
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.SandboxRequest(
            script_id="scripts/validate.py",
            script_digest="f" * 64,
            timeout_ms=500,
        )


def test_script_digest_is_recomputed_from_runtime_resolved_bytes():
    runtime, _, _, activation = _activated_incident()
    ref = "northstar/incident-analysis@2.0.0"
    package_file = runtime.package_contents[ref]["scripts/validate.py"]
    runtime.package_contents[ref]["scripts/validate.py"] = package_file.model_copy(
        update={"content": "malicious replacement"}
    )
    decision = runtime.run_script(
        activation,
        policy.SandboxRequest(script_id="scripts/validate.py", timeout_ms=500),
    )
    assert not decision.allowed
    assert decision.reason_code == "SCRIPT_DIGEST_MISMATCH"


def test_read_only_policy_mismatch_is_linted():
    runtime = lab.NorthstarSkillRuntime()
    ref = "northstar/support-faq@3.0.0"
    record = runtime.registry[ref]
    changed = record.manifest.model_copy(update={"required_capabilities": ("billing.refund.execute",)})
    runtime.registry[ref] = record.model_copy(update={"manifest": changed, "approved_digest": changed.package_digest})
    runtime.live_packages[ref] = changed
    assert "READ_ONLY_POLICY_MISMATCH" in runtime.static_checks(ref)


def test_read_only_mode_denies_non_read_effect_at_point_of_use():
    runtime, _, _, activation = _activated_incident()
    runtime.current_permissions[activation.principal_id].add("production.feature_flag.revert")
    widened = activation.model_copy(
        update={
            "effective_capabilities": (
                *activation.effective_capabilities,
                "production.feature_flag.revert",
            )
        }
    )
    with pytest.raises(policy.SkillPolicyError, match="READ_ONLY_EFFECT_DENIED"):
        runtime.authorize_capability_use(widened, "production.feature_flag.revert")


def test_effective_risk_includes_capabilities_and_scripts():
    runtime = lab.NorthstarSkillRuntime()
    assert runtime.effective_risk("northstar/refund-execution@1.4.0") is policy.RiskClass.CRITICAL
    assert runtime.effective_risk("northstar/incident-analysis@2.0.0") is policy.RiskClass.MEDIUM


def test_package_diff_flags_new_write_capability():
    runtime = lab.NorthstarSkillRuntime()
    before = runtime.registry["northstar/support-faq@3.0.0"].manifest
    after = before.model_copy(update={"required_capabilities": (*before.required_capabilities, "billing.refund.propose")})
    changes = runtime.package_changes(before, after)
    assert any(item.field == "required_capabilities" and item.high_risk for item in changes)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("routing_terms", ("everything",), "ROUTING_SURFACE_CHANGED"),
        ("intents", ("execute-admin",), "ROUTING_SURFACE_CHANGED"),
        ("requested_outcomes", ("execute",), "ROUTING_SURFACE_CHANGED"),
        ("domain", "operations", "ROUTING_SURFACE_CHANGED"),
        ("execution_modes", (policy.ExecutionMode.EPHEMERAL,), "EXECUTION_POLICY_CHANGED"),
        ("data_classes", ("RESTRICTED",), "PACKAGE_CONTENT_CHANGED"),
        ("preconditions", ("new-precondition",), "EXECUTION_POLICY_CHANGED"),
        ("postconditions", ("new-postcondition",), "EXECUTION_POLICY_CHANGED"),
        ("source_uri", "https://changed.example/package", "PACKAGE_IDENTITY_CHANGED"),
    ],
)
def test_package_diff_covers_policy_relevant_manifest_fields(field, value, reason):
    runtime = lab.NorthstarSkillRuntime()
    before = runtime.registry["northstar/support-faq@3.0.0"].manifest
    after = before.model_copy(update={field: value})
    change = next(item for item in runtime.package_changes(before, after) if item.field == field)
    assert change.review_reason == reason
    assert change.high_risk


def test_risk_class_downgrade_is_high_risk_governance_change():
    runtime = lab.NorthstarSkillRuntime()
    before = runtime.registry["northstar/refund-execution@1.4.0"].manifest
    after = before.model_copy(update={"risk_class": policy.RiskClass.LOW})
    change = next(item for item in runtime.package_changes(before, after) if item.field == "risk_class")
    assert change.review_reason == "RISK_CLASS_CHANGED"
    assert change.high_risk


def test_least_privilege_lint_flags_unused_high_risk_request():
    runtime = lab.NorthstarSkillRuntime()
    findings = runtime.least_privilege_findings(
        "northstar/refund-execution@1.4.0", used_capabilities=()
    )
    assert findings == ("UNUSED_HIGH_RISK_CAPABILITY:billing.refund.execute",)


def test_activation_receipt_pins_package_and_policy_snapshots():
    _, _, _, activation = _activated_incident()
    assert activation.version == "2.0.0"
    assert len(activation.package_digest) == 64
    assert activation.policy_version == lab.POLICY_VERSION
    assert activation.router_version == lab.ROUTER_VERSION
    assert activation.catalog_version == lab.CATALOG_VERSION


def test_durable_checkpoint_binds_tenant_and_activation():
    runtime, _, _, activation = _activated_incident()
    runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    checkpoint = runtime.checkpoint(activation, step="analysis-complete", artifact_ids=(f"artifact-{activation.activation_id}",))
    assert checkpoint.tenant_id == activation.tenant_id
    assert checkpoint.activation_id == activation.activation_id


def test_checkpoint_rejects_unknown_artifact():
    runtime, _, _, activation = _activated_incident()
    with pytest.raises(policy.SkillPolicyError, match="CHECKPOINT_ARTIFACT_NOT_FOUND"):
        runtime.checkpoint(activation, step="bad", artifact_ids=("missing",))


def test_activation_id_is_not_external_idempotency_identity():
    receipt = policy.ExternalOperationReceipt(logical_operation_id="refund-customer-123-case-9", attempt_id="attempt-2", status="PENDING")
    assert receipt.logical_operation_id != receipt.attempt_id
    assert not hasattr(receipt, "activation_id")


def test_routing_evaluation_reports_real_denominators():
    runtime = lab.NorthstarSkillRuntime()
    report = runtime.evaluate_routing(lab.routing_cases())
    assert report.total_cases == 18
    assert report.matched_cases == 6
    assert report.no_match_cases == 11
    assert report.ambiguous_cases == 1
    assert report.top1_accuracy == 1
    assert report.no_match_accuracy == 1
    assert report.ambiguity_accuracy == 1
    assert report.false_activation_rate == 0


def test_expected_no_match_actual_match_counts_false_activation_without_forbidden_list():
    runtime = lab.NorthstarSkillRuntime()
    guest = lab.fixture_principals()["guest"]
    mislabeled = policy.RoutingEvaluationCase(
        case_id="metric-semantics",
        request=lab.request_for(
            guest,
            domain="support",
            intent="answer-faq",
            requested_outcome="answer",
            query="How do I reset an API key?",
            risk_class=policy.RiskClass.LOW,
        ),
        expected_outcome=policy.RouteOutcome.NO_MATCH,
    )
    report = runtime.evaluate_routing((mislabeled,))
    assert report.false_activations == 1
    assert report.false_activation_rate == 1


def test_high_risk_expected_no_match_actual_match_is_explicit_misroute():
    runtime = lab.NorthstarSkillRuntime()
    operator = lab.fixture_principals()["billing-operator"]
    case = policy.RoutingEvaluationCase(
        case_id="high-risk-metric-semantics",
        request=lab.request_for(
            operator,
            domain="billing",
            intent="execute-refund",
            requested_outcome="execute",
            query="Execute approved refund",
        ),
        expected_outcome=policy.RouteOutcome.NO_MATCH,
        high_risk=True,
        trusted_explicit_user_intent=True,
    )
    report = runtime.evaluate_routing((case,))
    assert report.high_risk_misroutes == 1
    assert report.high_risk_misrouting_rate == 1


def test_trace_records_allow_and_denial_context_without_secrets():
    runtime, _, _, activation = _activated_incident()
    runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    actions = {event.action for event in runtime.trace_events}
    assert {"ROUTE", "ACTIVATE", "COMPLETE"} <= actions
    assert all(event.policy_version == lab.POLICY_VERSION for event in runtime.trace_events)


def test_execution_budget_exhaustion_has_explicit_status():
    budget = lab.default_budget().model_copy(update={"max_model_calls": 1})
    runtime = lab.NorthstarSkillRuntime(budget=budget)
    principal = lab.fixture_principals()["incident-reader"]
    request = lab.request_for(principal)
    activation = runtime.activate(principal, request, runtime.route(principal, request))
    first = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    second = runtime.execute_incident_skill(activation, {"service": "checkout", "time_window_minutes": 30})
    assert first.status is policy.ExecutionStatus.SUCCEEDED
    assert second.status is policy.ExecutionStatus.BUDGET_EXHAUSTED


def test_credential_free_demo_is_deterministic():
    result = lab.run_governed_demo()
    assert result["selected_skill"] == "northstar/incident-analysis@2.0.0"
    assert result["status"] == "SUCCEEDED"
    assert result["action_executed"] is False
    assert result["false_activation_rate"] == 0
