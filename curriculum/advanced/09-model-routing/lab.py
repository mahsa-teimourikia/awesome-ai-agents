"""Credential-free deterministic lab for Advanced 09 model routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from policy import (
    ADAPTER_CONTRACT_VERSION,
    AcceptedEvidence,
    AttemptReason,
    AttemptStatus,
    CandidateArtifact,
    CapacityState,
    CircuitState,
    DataClassification,
    EvidenceRegistry,
    ExpectedArtifact,
    FailureAction,
    FailurePolicy,
    GatePolicy,
    HealthStatus,
    InputModality,
    ModelRoute,
    OutputType,
    ProviderCatalogRecord,
    ProviderErrorCode,
    RegistrySnapshot,
    RetentionRequirement,
    RouteAttempt,
    RouteHealth,
    RouteLifecycle,
    RoutePricing,
    RoutingContext,
    RoutingMetrics,
    RoutingObjective,
    RoutingRun,
    RunStatus,
    TaskRequirements,
    WorkloadProfile,
    canonical_digest,
    compatible_fallbacks,
    decide_failure_action,
    evaluate_eligibility,
    expected_cost_usd,
    select_route,
    validate_candidate_output,
)

FIXED_TIME = datetime(2026, 9, 1, 16, 0, tzinfo=UTC)
TENANT = "northstar-commerce"


def _profile(
    task_family: str,
    *,
    quality: float,
    p50: int,
    p95: int,
    success: float,
) -> WorkloadProfile:
    return WorkloadProfile(
        task_family=task_family,
        quality_score=quality,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        success_rate=success,
        timeout_rate=max(0, 1 - success) / 3,
        rate_limit_rate=max(0, 1 - success) / 3,
        provider_error_rate=max(0, 1 - success) / 3,
        sample_size=500,
        measured_at=FIXED_TIME - timedelta(days=1),
        evaluator_version="northstar-eval-v1",
    )


def _route(
    *,
    route_id: str,
    provider: str,
    model_fixture_id: str,
    deployment_id: str,
    region: str,
    group: str,
    input_modalities: tuple[InputModality, ...] = (InputModality.TEXT,),
    output_types: tuple[OutputType, ...] = (OutputType.TEXT, OutputType.STRUCTURED),
    structured: bool = True,
    tools: bool = False,
    parallel_tools: bool = False,
    reasoning: bool = False,
    max_context: int = 32_000,
    max_output: int = 4_000,
    classifications: tuple[DataClassification, ...] = (
        DataClassification.PUBLIC,
        DataClassification.INTERNAL,
        DataClassification.SENSITIVE,
    ),
    zdr: bool = True,
    lifecycle: RouteLifecycle = RouteLifecycle.ACTIVE,
    input_price: float,
    output_price: float,
    profiles: tuple[WorkloadProfile, ...],
    health: HealthStatus = HealthStatus.HEALTHY,
    circuit: CircuitState = CircuitState.CLOSED,
    remaining_rpm: int = 200,
    remaining_tpm: int = 500_000,
) -> ModelRoute:
    return ModelRoute(
        route_id=route_id,
        provider=provider,
        model_fixture_id=model_fixture_id,
        deployment_id=deployment_id,
        deployment_region=region,
        equivalence_group=group,
        input_modalities=input_modalities,
        output_types=output_types,
        supports_structured_outputs=structured,
        supports_tool_calling=tools,
        supports_parallel_tools=parallel_tools,
        supports_streaming=True,
        supports_reasoning_controls=reasoning,
        tool_protocols=("northstar-tools-v1",) if tools else (),
        maximum_context_tokens=max_context,
        maximum_output_tokens=max_output,
        allowed_data_classifications=classifications,
        zero_data_retention_eligible=zdr,
        lifecycle=lifecycle,
        pricing=RoutePricing(
            input_usd_per_million=input_price,
            output_usd_per_million=output_price,
            effective_at=FIXED_TIME - timedelta(days=30),
        ),
        workload_profiles={profile.task_family: profile for profile in profiles},
        health=RouteHealth(
            status=health,
            circuit_state=circuit,
            last_updated_at=FIXED_TIME,
        ),
        capacity=CapacityState(
            remaining_requests_per_minute=remaining_rpm,
            remaining_tokens_per_minute=remaining_tpm,
            queue_depth=0,
            available_concurrency=20,
            last_updated_at=FIXED_TIME,
        ),
        provider_metadata_version=f"{provider}-fixture-2026-09",
        provider_metadata_effective_at=FIXED_TIME - timedelta(days=7),
        provider_metadata_last_verified_at=FIXED_TIME,
    )


def fixture_registry() -> RegistrySnapshot:
    support_fast = _profile(
        "support_extraction", quality=0.88, p50=180, p95=420, success=0.94
    )
    support_fast_b = _profile(
        "support_extraction", quality=0.90, p50=220, p95=520, success=0.95
    )
    support_balanced = _profile(
        "support_extraction", quality=0.98, p50=420, p95=900, success=0.985
    )
    architecture = _profile(
        "architecture_reasoning", quality=0.95, p50=900, p95=1800, success=0.97
    )
    vision = _profile(
        "image_analysis", quality=0.94, p50=600, p95=1200, success=0.96
    )
    return RegistrySnapshot(
        effective_at=FIXED_TIME - timedelta(days=7),
        last_verified_at=FIXED_TIME,
        routes=(
            _route(
                route_id="route-fast-eu-a",
                provider="provider-a",
                model_fixture_id="model-fast-v1",
                deployment_id="fast-eu-a-2026-09",
                region="eu-west",
                group="support-json-v1",
                input_price=0.20,
                output_price=0.80,
                profiles=(support_fast,),
            ),
            _route(
                route_id="route-fast-eu-b",
                provider="provider-b",
                model_fixture_id="model-fast-v1",
                deployment_id="fast-eu-b-2026-09",
                region="eu-central",
                group="support-json-v1",
                input_price=0.25,
                output_price=0.90,
                profiles=(support_fast_b,),
            ),
            _route(
                route_id="route-balanced-eu",
                provider="provider-a",
                model_fixture_id="model-balanced-v2",
                deployment_id="balanced-eu-2026-09",
                region="eu-west",
                group="support-json-v1",
                tools=True,
                parallel_tools=True,
                reasoning=True,
                max_context=128_000,
                max_output=16_000,
                input_price=1.50,
                output_price=5.00,
                profiles=(support_balanced,),
            ),
            _route(
                route_id="route-reasoning-eu",
                provider="provider-a",
                model_fixture_id="model-reasoning-v3",
                deployment_id="reasoning-eu-2026-09",
                region="eu-west",
                group="architecture-reasoning-v1",
                tools=True,
                parallel_tools=True,
                reasoning=True,
                max_context=196_000,
                max_output=32_000,
                input_price=3.00,
                output_price=12.00,
                profiles=(architecture,),
            ),
            _route(
                route_id="route-vision-eu",
                provider="provider-c",
                model_fixture_id="model-vision-v2",
                deployment_id="vision-eu-2026-09",
                region="eu-north",
                group="image-analysis-v1",
                input_modalities=(InputModality.TEXT, InputModality.IMAGE),
                reasoning=True,
                max_context=64_000,
                max_output=8_000,
                input_price=2.00,
                output_price=6.00,
                profiles=(vision,),
            ),
            _route(
                route_id="route-fast-us-cheap",
                provider="provider-b",
                model_fixture_id="model-fast-v1",
                deployment_id="fast-us-2026-09",
                region="us-east",
                group="support-json-v1",
                classifications=(DataClassification.PUBLIC, DataClassification.INTERNAL),
                zdr=False,
                input_price=0.10,
                output_price=0.40,
                profiles=(support_fast,),
            ),
            _route(
                route_id="route-legacy-eu",
                provider="provider-a",
                model_fixture_id="model-fast-v0",
                deployment_id="legacy-eu-2025-01",
                region="eu-west",
                group="support-json-v1",
                lifecycle=RouteLifecycle.DEPRECATED,
                input_price=0.05,
                output_price=0.20,
                profiles=(support_fast,),
            ),
        ),
    )


def support_requirements(
    *,
    minimum_quality: float = 0.80,
    classification: DataClassification = DataClassification.SENSITIVE,
) -> TaskRequirements:
    return TaskRequirements(
        task_family="support_extraction",
        required_input_modalities=(InputModality.TEXT,),
        required_output_type=OutputType.STRUCTURED,
        structured_schema_id="support-ticket-v1",
        minimum_context_tokens=8_000,
        minimum_output_tokens=200,
        expected_input_tokens=1_000,
        expected_output_tokens=200,
        upper_bound_output_tokens=400,
        minimum_quality=minimum_quality,
        minimum_success_rate=0.90,
        data_classification=classification,
        required_equivalence_group="support-json-v1",
    )


def default_context(
    request_id: str,
    *,
    classification: DataClassification = DataClassification.SENSITIVE,
    objective: RoutingObjective = RoutingObjective.COST_FIRST,
    allowed_providers: tuple[str, ...] = ("provider-a", "provider-b", "provider-c"),
    allowed_regions: tuple[str, ...] = ("eu-west", "eu-central", "eu-north"),
    max_cost_usd: float = 0.02,
    latency_slo_ms: int = 1_500,
    deadline_ms: int = 3_000,
    cancelled: bool = False,
    sticky_route_id: str | None = None,
) -> RoutingContext:
    return RoutingContext(
        request_id=request_id,
        tenant_id=TENANT,
        data_classification=classification,
        allowed_providers=allowed_providers,
        allowed_regions=allowed_regions,
        retention_requirement=RetentionRequirement.ZERO_DATA_RETENTION,
        latency_slo_ms=latency_slo_ms,
        max_cost_usd=max_cost_usd,
        objective=objective,
        requested_at=FIXED_TIME,
        deadline=FIXED_TIME + timedelta(milliseconds=deadline_ms),
        sticky_route_id=sticky_route_id,
        cancelled=cancelled,
    )


def expected_support_artifact() -> ExpectedArtifact:
    return ExpectedArtifact(
        schema_id="support-ticket-v1",
        required_keys=("customer", "priority"),
        allowed_priorities=("low", "medium", "high", "urgent"),
        expected_data={"customer": "Ada", "priority": "urgent"},
        required_evidence_ids=("ticket-42",),
    )


def accepted_support_evidence(
    request_id: str,
    *,
    tenant_id: str = TENANT,
    evidence_id: str = "ticket-42",
    facts: dict[str, Any] | None = None,
    provenance_valid: bool = True,
) -> EvidenceRegistry:
    """Build the trusted evidence receipt used by the support fixture."""

    structured_facts = facts or {"customer": "Ada", "priority": "urgent"}
    source_id = "support-system/ticket-42"
    source_version = "version-7"
    receipt = AcceptedEvidence(
        evidence_id=evidence_id,
        request_id=request_id,
        tenant_id=tenant_id,
        source_id=source_id,
        source_version=source_version,
        digest=canonical_digest(
            {
                "source_id": source_id,
                "source_version": source_version,
                "structured_facts": structured_facts,
            }
        ),
        structured_facts=structured_facts,
        provenance_valid=provenance_valid,
        accepted_at=FIXED_TIME,
    )
    return EvidenceRegistry(receipts={receipt.evidence_id: receipt})


class FixtureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    structured_data: dict[str, Any] | None = None
    schema_id: str | None = "support-ticket-v1"
    evidence_ids: tuple[str, ...] = ("ticket-42",)
    confidence: float = Field(default=0.95, ge=0, le=1)
    error_code: ProviderErrorCode | None = None
    retry_after_ms: int | None = Field(default=None, ge=0)
    latency_ms: int = Field(default=200, ge=0)
    input_tokens: int = Field(default=1_000, ge=0)
    output_tokens: int = Field(default=200, ge=0)


class RouteStateUpdate(BaseModel):
    """Deterministic change applied immediately before a numbered model call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lifecycle: RouteLifecycle | None = None
    health_status: HealthStatus | None = None
    circuit_state: CircuitState | None = None
    health_age_seconds: int | None = Field(default=None, ge=0)
    capacity_age_seconds: int | None = Field(default=None, ge=0)
    remaining_requests_per_minute: int | None = Field(default=None, ge=0)
    remaining_tokens_per_minute: int | None = Field(default=None, ge=0)
    available_concurrency: int | None = Field(default=None, ge=0)


class FixtureCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    case_id: str
    responses: dict[str, tuple[FixtureResponse, ...]]
    cancel_after_attempt: int | None = Field(default=None, ge=1)
    route_state_updates: dict[int, dict[str, RouteStateUpdate]] = Field(
        default_factory=dict
    )


@dataclass
class CancellationToken:
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True


class DeterministicModelClient:
    """Replays labelled fixture outcomes; it does not measure model quality."""

    def __init__(self, case: FixtureCase) -> None:
        self.case = case
        self.calls_by_route: dict[str, int] = {}
        self.total_calls = 0

    def call(self, route_id: str) -> FixtureResponse:
        index = self.calls_by_route.get(route_id, 0)
        responses = self.case.responses.get(route_id)
        if not responses:
            responses = (
                FixtureResponse(
                    structured_data={"customer": "Ada", "priority": "urgent"}
                ),
            )
        response = responses[min(index, len(responses) - 1)]
        self.calls_by_route[route_id] = index + 1
        self.total_calls += 1
        return response


def _route_by_id(registry: RegistrySnapshot, route_id: str) -> ModelRoute:
    return next(route for route in registry.routes if route.route_id == route_id)


def _snapshot_registry(
    registry: RegistrySnapshot,
    live_routes: dict[str, ModelRoute],
    breakers: CircuitBreakerRegistry,
    *,
    now: datetime,
) -> RegistrySnapshot:
    routes = []
    for original in registry.routes:
        route = live_routes[original.route_id]
        breakers.refresh_state(route.route_id, now=now)
        health = route.health.model_copy(
            update={"circuit_state": breakers.state(route.route_id)}
        )
        routes.append(route.model_copy(update={"health": health}))
    return registry.model_copy(update={"routes": tuple(routes)})


def _apply_route_state_updates(
    live_routes: dict[str, ModelRoute],
    updates: dict[str, RouteStateUpdate],
    *,
    now: datetime,
    breakers: CircuitBreakerRegistry,
) -> None:
    for route_id, update in updates.items():
        route = live_routes[route_id]
        health_changes: dict[str, Any] = {}
        if update.health_status is not None:
            health_changes["status"] = update.health_status
            health_changes["last_updated_at"] = now
        if update.health_age_seconds is not None:
            health_changes["last_updated_at"] = now - timedelta(
                seconds=update.health_age_seconds
            )
        capacity_changes: dict[str, Any] = {}
        for field_name in (
            "remaining_requests_per_minute",
            "remaining_tokens_per_minute",
            "available_concurrency",
        ):
            value = getattr(update, field_name)
            if value is not None:
                capacity_changes[field_name] = value
                capacity_changes["last_updated_at"] = now
        if update.capacity_age_seconds is not None:
            capacity_changes["last_updated_at"] = now - timedelta(
                seconds=update.capacity_age_seconds
            )
        changes: dict[str, Any] = {}
        if update.lifecycle is not None:
            changes["lifecycle"] = update.lifecycle
        if health_changes:
            changes["health"] = route.health.model_copy(update=health_changes)
        if capacity_changes:
            changes["capacity"] = route.capacity.model_copy(update=capacity_changes)
        if changes:
            live_routes[route_id] = route.model_copy(update=changes)
        if update.circuit_state is not None:
            breakers.set_state(route_id, update.circuit_state, now=now)


def _consume_capacity(
    live_routes: dict[str, ModelRoute],
    route_id: str,
    response: FixtureResponse,
    *,
    now: datetime,
) -> None:
    """Consume the lab's application ledger initialized from provider signals."""

    route = live_routes[route_id]
    capacity = route.capacity.model_copy(
        update={
            "remaining_requests_per_minute": max(
                0, route.capacity.remaining_requests_per_minute - 1
            ),
            "remaining_tokens_per_minute": max(
                0,
                route.capacity.remaining_tokens_per_minute
                - response.input_tokens
                - response.output_tokens,
            ),
            "last_updated_at": now,
        }
    )
    live_routes[route_id] = route.model_copy(update={"capacity": capacity})


def _remaining_context(
    context: RoutingContext,
    *,
    total_cost: float,
) -> RoutingContext | None:
    remaining = context.max_cost_usd - total_cost
    if remaining <= 0:
        return None
    return context.model_copy(update={"max_cost_usd": remaining})


def _provider_budget_allows(
    route: ModelRoute,
    *,
    used_providers: set[str],
    context: RoutingContext,
) -> bool:
    return len(used_providers | {route.provider}) <= context.max_providers


def _promotion_route(
    registry: RegistrySnapshot,
    eligible_route_ids: tuple[str, ...],
    *,
    current_route_id: str,
    used_route_ids: set[str],
    used_providers: set[str],
    context: RoutingContext,
    requirements: TaskRequirements,
) -> str | None:
    current = _route_by_id(registry, current_route_id)
    current_quality = current.workload_profiles[requirements.task_family].quality_score
    candidates = [
        _route_by_id(registry, route_id)
        for route_id in eligible_route_ids
        if route_id not in used_route_ids
        and _route_by_id(registry, route_id).equivalence_group
        == current.equivalence_group
        and _route_by_id(registry, route_id).adapter_contract_version
        == current.adapter_contract_version
        and _provider_budget_allows(
            _route_by_id(registry, route_id),
            used_providers=used_providers,
            context=context,
        )
        and _route_by_id(registry, route_id)
        .workload_profiles[requirements.task_family]
        .quality_score
        > current_quality
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda route: (
            route.workload_profiles[requirements.task_family].quality_score,
            -route.workload_profiles[requirements.task_family].p95_latency_ms,
            -expected_cost_usd(
                route,
                input_tokens=requirements.expected_input_tokens,
                output_tokens=requirements.upper_bound_output_tokens,
            ),
        ),
    ).route_id


def run_routing_case(
    case: FixtureCase,
    *,
    registry: RegistrySnapshot | None = None,
    requirements: TaskRequirements | None = None,
    context: RoutingContext | None = None,
    gate: GatePolicy | None = None,
    failure_policy: FailurePolicy | None = None,
    cancellation: CancellationToken | None = None,
    evidence_registry: EvidenceRegistry | None = None,
    breaker_registry: CircuitBreakerRegistry | None = None,
) -> RoutingRun:
    registry = registry or fixture_registry()
    requirements = requirements or support_requirements()
    context = context or default_context(case.case_id)
    gate = gate or GatePolicy(minimum_confidence=0.80)
    failure_policy = failure_policy or FailurePolicy()
    cancellation = cancellation or CancellationToken(context.cancelled)
    evidence_registry = evidence_registry or accepted_support_evidence(
        context.request_id,
        tenant_id=context.tenant_id,
    )
    breakers = breaker_registry or CircuitBreakerRegistry()
    for route in registry.routes:
        breakers.seed_state(
            route.route_id,
            route.health.circuit_state,
            now=context.requested_at,
        )
    live_routes = {route.route_id: route for route in registry.routes}
    initial_registry = _snapshot_registry(
        registry,
        live_routes,
        breakers,
        now=context.requested_at,
    )
    decision = select_route(
        initial_registry, requirements, context, now=context.requested_at
    )
    if context.cancelled:
        return RoutingRun(
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            status=RunStatus.CANCELLED,
            initial_decision=decision,
            final_route_id=None,
            artifact=None,
            attempts=(),
            total_cost_usd=0,
            budget_overrun_usd=0,
            total_latency_ms=0,
            false_accepts=0,
            false_promotions=0,
            promotion_count=0,
            fallback_count=0,
            terminal_reason="CANCELLED_BEFORE_FIRST_MODEL_CALL",
        )
    if decision.selected_route_id is None:
        return RoutingRun(
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            status=RunStatus.NO_ELIGIBLE_ROUTE,
            initial_decision=decision,
            final_route_id=None,
            artifact=None,
            attempts=(),
            total_cost_usd=0,
            budget_overrun_usd=0,
            total_latency_ms=0,
            false_accepts=0,
            false_promotions=0,
            promotion_count=0,
            fallback_count=0,
            terminal_reason="NO_ELIGIBLE_ROUTE",
        )

    client = DeterministicModelClient(case)
    expected = expected_support_artifact()
    attempts: list[RouteAttempt] = []
    used_route_ids: set[str] = set()
    used_providers: set[str] = set()
    retry_counts: dict[str, int] = {}
    route_id = decision.selected_route_id
    reason = AttemptReason.INITIAL
    elapsed_ms = 0
    total_cost = 0.0
    false_accepts = 0
    false_promotions = 0
    promotions = 0
    fallbacks = 0
    fallback_primary_route_id: str | None = None
    promotion_origin_route_id: str | None = None
    applied_state_updates: set[int] = set()

    def terminal(
        status: RunStatus,
        terminal_reason: str,
        *,
        artifact: CandidateArtifact | None = None,
    ) -> RoutingRun:
        return RoutingRun(
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            status=status,
            initial_decision=decision,
            final_route_id=(route_id if attempts else None),
            artifact=artifact,
            attempts=tuple(attempts),
            total_cost_usd=total_cost,
            budget_overrun_usd=max(0, total_cost - context.max_cost_usd),
            total_latency_ms=elapsed_ms,
            false_accepts=false_accepts,
            false_promotions=false_promotions,
            promotion_count=promotions,
            fallback_count=fallbacks,
            terminal_reason=terminal_reason,
        )

    while True:
        if cancellation.cancelled:
            return terminal(RunStatus.CANCELLED, "CANCELLED_BEFORE_NEXT_MODEL_CALL")
        if len(attempts) >= context.max_attempts:
            return terminal(RunStatus.BUDGET_EXCEEDED, "ATTEMPT_BUDGET_EXHAUSTED")

        call_number = len(attempts) + 1
        now = context.requested_at + timedelta(milliseconds=elapsed_ms)
        if call_number not in applied_state_updates:
            _apply_route_state_updates(
                live_routes,
                case.route_state_updates.get(call_number, {}),
                now=now,
                breakers=breakers,
            )
            applied_state_updates.add(call_number)

        runtime_context = _remaining_context(context, total_cost=total_cost)
        if runtime_context is None:
            return terminal(RunStatus.BUDGET_EXCEEDED, "COST_BUDGET_EXHAUSTED")
        current_registry = _snapshot_registry(
            registry,
            live_routes,
            breakers,
            now=now,
        )
        current_report = evaluate_eligibility(
            current_registry,
            requirements,
            runtime_context,
            now=now,
        )
        currently_eligible = set(current_report.eligible_route_ids)
        route = _route_by_id(current_registry, route_id)
        route_admitted = route_id in currently_eligible and _provider_budget_allows(
            route,
            used_providers=used_providers,
            context=context,
        )

        if not route_admitted:
            replacement: str | None = None
            if reason is AttemptReason.CASCADE_PROMOTION:
                origin = promotion_origin_route_id or route_id
                replacement = _promotion_route(
                    current_registry,
                    current_report.eligible_route_ids,
                    current_route_id=origin,
                    used_route_ids=used_route_ids,
                    used_providers=used_providers,
                    context=context,
                    requirements=requirements,
                )
                if replacement is None:
                    return terminal(
                        RunStatus.QUALITY_GATE_FAILED,
                        "NO_CURRENTLY_ELIGIBLE_PROMOTION_ROUTE",
                    )
            elif reason in (
                AttemptReason.PROVIDER_FALLBACK,
                AttemptReason.RETRY,
            ):
                primary_id = fallback_primary_route_id or route_id
                candidates = compatible_fallbacks(
                    current_registry,
                    requirements,
                    runtime_context,
                    primary_route_id=primary_id,
                    now=now,
                    exclude_route_ids=tuple(used_route_ids | {route_id}),
                )
                candidates = tuple(
                    candidate
                    for candidate in candidates
                    if _provider_budget_allows(
                        _route_by_id(current_registry, candidate),
                        used_providers=used_providers,
                        context=context,
                    )
                )
                if candidates and fallbacks < context.max_fallbacks:
                    replacement = candidates[0]
                    if reason is not AttemptReason.PROVIDER_FALLBACK:
                        fallbacks += 1
                    reason = AttemptReason.PROVIDER_FALLBACK
                else:
                    return terminal(
                        RunStatus.PROVIDER_FAILURE,
                        "NO_CURRENTLY_ELIGIBLE_FALLBACK_ROUTE",
                    )
            else:
                refreshed = select_route(
                    current_registry,
                    requirements,
                    runtime_context,
                    now=now,
                )
                replacement = refreshed.selected_route_id
                if replacement is None:
                    return terminal(
                        RunStatus.NO_ELIGIBLE_ROUTE,
                        "NO_ROUTE_ADMITTED_AT_EXECUTION_TIME",
                    )
                reason = AttemptReason.POLICY_REROUTE
            route_id = replacement
            continue

        if not breakers.allow_call(route_id, now=now):
            return terminal(
                RunStatus.PROVIDER_FAILURE,
                "CIRCUIT_BLOCKED_NEXT_MODEL_CALL",
            )

        profile = route.workload_profiles[requirements.task_family]
        remaining_ms = int((context.deadline - now).total_seconds() * 1000)
        if profile.p95_latency_ms > remaining_ms:
            return terminal(RunStatus.DEADLINE_EXCEEDED, "DEADLINE_BLOCKED_NEXT_MODEL_CALL")
        reserved = expected_cost_usd(
            route,
            input_tokens=requirements.expected_input_tokens,
            output_tokens=requirements.upper_bound_output_tokens,
        )
        if total_cost + reserved > context.max_cost_usd:
            return terminal(RunStatus.BUDGET_EXCEEDED, "COST_BUDGET_BLOCKED_NEXT_MODEL_CALL")

        started_at = now
        response = client.call(route_id)
        used_route_ids.add(route_id)
        used_providers.add(route.provider)
        elapsed_ms += response.latency_ms
        finished_at = context.requested_at + timedelta(milliseconds=elapsed_ms)
        cost = expected_cost_usd(
            route,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        total_cost += cost
        _consume_capacity(
            live_routes,
            route_id,
            response,
            now=finished_at,
        )
        attempt_id = f"attempt-{context.request_id}-{len(attempts) + 1}"

        provider_failure = response.error_code is not None
        if provider_failure and response.error_code in failure_policy.fallback_errors:
            breakers.record_failure(route_id, now=finished_at)
        elif not provider_failure:
            breakers.record_success(route_id)

        if (
            response.input_tokens > route.maximum_context_tokens
            or response.output_tokens > route.maximum_output_tokens
        ):
            attempts.append(
                RouteAttempt(
                    attempt_id=attempt_id,
                    request_id=context.request_id,
                    route_id=route_id,
                    provider=route.provider,
                    model_fixture_id=route.model_fixture_id,
                    reason=reason,
                    started_at=started_at,
                    latency_ms=response.latency_ms,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    reserved_cost_usd=reserved,
                    cost_usd=cost,
                    status=AttemptStatus.INVALID_USAGE,
                    error_code=response.error_code,
                )
            )
            return terminal(
                RunStatus.PROVIDER_FAILURE,
                "ACTUAL_TOKEN_USAGE_EXCEEDS_ROUTE_LIMIT",
            )

        if total_cost > context.max_cost_usd:
            attempts.append(
                RouteAttempt(
                    attempt_id=attempt_id,
                    request_id=context.request_id,
                    route_id=route_id,
                    provider=route.provider,
                    model_fixture_id=route.model_fixture_id,
                    reason=reason,
                    started_at=started_at,
                    latency_ms=response.latency_ms,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    reserved_cost_usd=reserved,
                    cost_usd=cost,
                    status=AttemptStatus.BUDGET_OVERRUN,
                    error_code=response.error_code,
                )
            )
            return terminal(
                RunStatus.BUDGET_OVERRUN,
                "ACTUAL_COST_EXCEEDED_REQUEST_BUDGET",
            )

        if response.error_code is not None:
            post_call_context = _remaining_context(context, total_cost=total_cost)
            current_registry = _snapshot_registry(
                registry,
                live_routes,
                breakers,
                now=finished_at,
            )
            raw_fallbacks = compatible_fallbacks(
                current_registry,
                requirements,
                post_call_context or runtime_context,
                primary_route_id=route_id,
                now=finished_at,
                exclude_route_ids=tuple(used_route_ids),
            )
            fallbacks_available = tuple(
                candidate
                for candidate in raw_fallbacks
                if _provider_budget_allows(
                    _route_by_id(current_registry, candidate),
                    used_providers=used_providers,
                    context=context,
                )
            )
            provider_budget_blocked = bool(raw_fallbacks) and not bool(
                fallbacks_available
            )
            retries = retry_counts.get(route_id, 0)
            failure = decide_failure_action(
                response.error_code,
                request_id=context.request_id,
                retry_count=retries,
                retry_after_ms=response.retry_after_ms,
                remaining_deadline_ms=max(0, remaining_ms - response.latency_ms),
                fallback_available=bool(fallbacks_available)
                and fallbacks < context.max_fallbacks,
                policy=failure_policy,
            )
            attempts.append(
                RouteAttempt(
                    attempt_id=attempt_id,
                    request_id=context.request_id,
                    route_id=route_id,
                    provider=route.provider,
                    model_fixture_id=route.model_fixture_id,
                    reason=reason,
                    started_at=started_at,
                    latency_ms=response.latency_ms,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    reserved_cost_usd=reserved,
                    cost_usd=cost,
                    status=(
                        AttemptStatus.RETRYABLE_FAILURE
                        if failure.action is not FailureAction.TERMINATE
                        else AttemptStatus.TERMINAL_FAILURE
                    ),
                    error_code=response.error_code,
                )
            )
            if case.cancel_after_attempt == len(attempts):
                cancellation.cancel()
            if failure.action is FailureAction.RETRY:
                elapsed_ms += failure.delay_ms
                retry_counts[route_id] = retries + 1
                fallback_primary_route_id = route_id
                reason = AttemptReason.RETRY
                continue
            if failure.action is FailureAction.FALLBACK:
                route_id = fallbacks_available[0]
                fallback_primary_route_id = attempts[-1].route_id
                fallbacks += 1
                reason = AttemptReason.PROVIDER_FALLBACK
                continue
            if provider_budget_blocked:
                return terminal(
                    RunStatus.BUDGET_EXCEEDED,
                    "PROVIDER_BUDGET_EXHAUSTED",
                )
            return terminal(
                RunStatus.PROVIDER_FAILURE,
                failure.reason_codes[0],
            )

        artifact = CandidateArtifact(
            artifact_id=f"artifact-{case.case_id}-{len(attempts) + 1}",
            request_id=context.request_id,
            route_id=route_id,
            schema_id=response.schema_id,
            structured_data=response.structured_data or {},
            evidence_ids=response.evidence_ids,
            confidence=response.confidence,
        )
        validation = validate_candidate_output(
            artifact,
            expected,
            gate,
            tenant_id=context.tenant_id,
            evidence_registry=evidence_registry,
        )
        false_accepts += int(validation.false_accept)
        false_promotions += int(validation.false_promotion)
        attempts.append(
            RouteAttempt(
                attempt_id=attempt_id,
                request_id=context.request_id,
                route_id=route_id,
                provider=route.provider,
                model_fixture_id=route.model_fixture_id,
                reason=reason,
                started_at=started_at,
                latency_ms=response.latency_ms,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                reserved_cost_usd=reserved,
                cost_usd=cost,
                status=(
                    AttemptStatus.ACCEPTED
                    if validation.accepted
                    else AttemptStatus.QUALITY_REJECTED
                ),
                validation_reason_codes=validation.reason_codes,
            )
        )
        if case.cancel_after_attempt == len(attempts):
            cancellation.cancel()
        if validation.accepted:
            return terminal(
                RunStatus.SUCCEEDED,
                "OUTPUT_ACCEPTED",
                artifact=artifact,
            )

        current_registry = _snapshot_registry(
            registry,
            live_routes,
            breakers,
            now=finished_at,
        )
        promotion_context = _remaining_context(context, total_cost=total_cost)
        if promotion_context is None:
            return terminal(
                RunStatus.BUDGET_EXCEEDED,
                "COST_BUDGET_BLOCKED_PROMOTION",
            )
        promotion_report = evaluate_eligibility(
            current_registry,
            requirements,
            promotion_context,
            now=finished_at,
        )
        promoted = _promotion_route(
            current_registry,
            promotion_report.eligible_route_ids,
            current_route_id=route_id,
            used_route_ids=used_route_ids,
            used_providers=used_providers,
            context=context,
            requirements=requirements,
        )
        if promoted is None:
            origin = _route_by_id(current_registry, route_id)
            stronger_ids = {
                candidate.route_id
                for candidate in current_registry.routes
                if candidate.route_id not in used_route_ids
                and candidate.equivalence_group == origin.equivalence_group
                and candidate.adapter_contract_version
                == origin.adapter_contract_version
                and requirements.task_family in candidate.workload_profiles
                and candidate.workload_profiles[
                    requirements.task_family
                ].quality_score
                > origin.workload_profiles[requirements.task_family].quality_score
            }
            blocked_reasons = {
                reason_code
                for result in promotion_report.routes
                if result.route_id in stronger_ids
                for reason_code in result.reason_codes
            }
            if "COST_CEILING_EXCEEDED" in blocked_reasons:
                return terminal(
                    RunStatus.BUDGET_EXCEEDED,
                    "COST_BUDGET_BLOCKED_PROMOTION",
                )
            if "REQUEST_DEADLINE_INFEASIBLE" in blocked_reasons:
                return terminal(
                    RunStatus.DEADLINE_EXCEEDED,
                    "DEADLINE_BLOCKED_PROMOTION",
                )
            return terminal(RunStatus.QUALITY_GATE_FAILED, "NO_SAFE_PROMOTION_ROUTE")
        promotion_origin_route_id = route_id
        route_id = promoted
        promotions += 1
        reason = AttemptReason.CASCADE_PROMOTION


@dataclass
class _Breaker:
    state: CircuitState = CircuitState.CLOSED
    failures: list[datetime] = field(default_factory=list)
    opened_at: datetime | None = None
    half_open_probe_in_flight: bool = False


class CircuitBreakerRegistry:
    """Route-specific CLOSED/OPEN/HALF_OPEN circuit breaker fixture."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        failure_window_seconds: int = 30,
        open_seconds: int = 60,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.failure_window = timedelta(seconds=failure_window_seconds)
        self.open_duration = timedelta(seconds=open_seconds)
        self._states: dict[str, _Breaker] = {}

    def state(self, route_id: str) -> CircuitState:
        return self._states.setdefault(route_id, _Breaker()).state

    def refresh_state(self, route_id: str, *, now: datetime) -> CircuitState:
        breaker = self._states.setdefault(route_id, _Breaker())
        if (
            breaker.state is CircuitState.OPEN
            and breaker.opened_at is not None
            and now >= breaker.opened_at + self.open_duration
        ):
            breaker.state = CircuitState.HALF_OPEN
            breaker.half_open_probe_in_flight = False
        return breaker.state

    def seed_state(
        self,
        route_id: str,
        state: CircuitState,
        *,
        now: datetime,
    ) -> None:
        if route_id not in self._states:
            self.set_state(route_id, state, now=now)

    def set_state(
        self,
        route_id: str,
        state: CircuitState,
        *,
        now: datetime,
    ) -> None:
        breaker = self._states.setdefault(route_id, _Breaker())
        breaker.state = state
        breaker.opened_at = now if state is CircuitState.OPEN else None
        breaker.half_open_probe_in_flight = False
        if state is CircuitState.CLOSED:
            breaker.failures.clear()

    def allow_call(self, route_id: str, *, now: datetime) -> bool:
        breaker = self._states.setdefault(route_id, _Breaker())
        self.refresh_state(route_id, now=now)
        if breaker.state is CircuitState.OPEN:
            return False
        if breaker.state is CircuitState.HALF_OPEN:
            if breaker.half_open_probe_in_flight:
                return False
            breaker.half_open_probe_in_flight = True
        return True

    def record_failure(self, route_id: str, *, now: datetime) -> None:
        breaker = self._states.setdefault(route_id, _Breaker())
        if breaker.state is CircuitState.HALF_OPEN:
            breaker.state = CircuitState.OPEN
            breaker.opened_at = now
            breaker.half_open_probe_in_flight = False
            return
        breaker.failures = [
            occurred
            for occurred in breaker.failures
            if occurred >= now - self.failure_window
        ]
        breaker.failures.append(now)
        if len(breaker.failures) >= self.failure_threshold:
            breaker.state = CircuitState.OPEN
            breaker.opened_at = now

    def record_success(self, route_id: str) -> None:
        breaker = self._states.setdefault(route_id, _Breaker())
        breaker.state = CircuitState.CLOSED
        breaker.failures.clear()
        breaker.opened_at = None
        breaker.half_open_probe_in_flight = False


def route_from_provider_catalog(
    record: ProviderCatalogRecord,
    *,
    route_id: str,
    region: str,
    equivalence_group: str,
    pricing: RoutePricing,
    profiles: tuple[WorkloadProfile, ...],
    allowed_data_classifications: tuple[DataClassification, ...],
    zero_data_retention_eligible: bool,
    health: RouteHealth,
    capacity: CapacityState,
) -> ModelRoute:
    """Overlay application policy on provider technical metadata.

    Provider metadata can describe capability; it cannot grant tenant, region,
    retention, or data-classification eligibility.
    """

    return ModelRoute(
        route_id=route_id,
        provider=record.provider,
        model_fixture_id=record.model_fixture_id,
        deployment_id=record.deployment_id,
        deployment_region=region,
        equivalence_group=equivalence_group,
        adapter_contract_version=ADAPTER_CONTRACT_VERSION,
        input_modalities=record.input_modalities,
        output_types=record.output_types,
        supports_structured_outputs=OutputType.STRUCTURED in record.output_types,
        supports_tool_calling=OutputType.TOOL_CALL in record.output_types,
        supports_parallel_tools=False,
        supports_streaming=True,
        supports_reasoning_controls=False,
        maximum_context_tokens=record.maximum_context_tokens,
        maximum_output_tokens=record.maximum_output_tokens,
        allowed_data_classifications=allowed_data_classifications,
        zero_data_retention_eligible=zero_data_retention_eligible,
        lifecycle=RouteLifecycle.ACTIVE,
        pricing=pricing,
        workload_profiles={profile.task_family: profile for profile in profiles},
        health=health,
        capacity=capacity,
        provider_metadata_version=record.provider_metadata_version,
        provider_metadata_effective_at=record.effective_at,
        provider_metadata_last_verified_at=record.last_verified_at,
    )


def labelled_cases() -> tuple[FixtureCase, ...]:
    correct = FixtureResponse(
        structured_data={"customer": "Ada", "priority": "urgent"},
        confidence=0.95,
        latency_ms=180,
    )
    stronger = FixtureResponse(
        structured_data={"customer": "Ada", "priority": "urgent"},
        confidence=0.99,
        latency_ms=420,
        output_tokens=240,
    )
    return (
        FixtureCase(case_id="easy-fast-pass", responses={"route-fast-eu-a": (correct,)}),
        FixtureCase(
            case_id="schema-valid-task-incorrect",
            responses={
                "route-fast-eu-a": (
                    FixtureResponse(
                        structured_data={"customer": "Ada", "priority": "low"},
                        confidence=0.94,
                    ),
                ),
                "route-balanced-eu": (stronger,),
            },
        ),
        FixtureCase(
            case_id="invalid-schema-promotes",
            responses={
                "route-fast-eu-a": (
                    FixtureResponse(
                        structured_data={"customer": "Ada"},
                        confidence=0.91,
                    ),
                ),
                "route-balanced-eu": (stronger,),
            },
        ),
        FixtureCase(
            case_id="false-promotion-low-confidence",
            responses={
                "route-fast-eu-a": (
                    correct.model_copy(update={"confidence": 0.70}),
                ),
                "route-balanced-eu": (stronger,),
            },
        ),
        FixtureCase(
            case_id="compatible-provider-fallback",
            responses={
                "route-fast-eu-a": (
                    FixtureResponse(error_code=ProviderErrorCode.MODEL_UNAVAILABLE),
                ),
                "route-fast-eu-b": (correct,),
            },
        ),
    )


def metrics_from_runs(runs: tuple[RoutingRun, ...]) -> RoutingMetrics:
    return RoutingMetrics(
        requests=len(runs),
        successful_compliant_tasks=sum(
            run.status is RunStatus.SUCCEEDED and not run.false_accepts for run in runs
        ),
        false_accepts=sum(run.false_accepts for run in runs),
        false_promotions=sum(run.false_promotions for run in runs),
        promotions=sum(run.promotion_count for run in runs),
        provider_fallbacks=sum(run.fallback_count for run in runs),
        total_calls=sum(len(run.attempts) for run in runs),
        total_cost_usd=sum(run.total_cost_usd for run in runs),
        latencies_ms=tuple(run.total_latency_ms for run in runs),
    )


def evaluation_fixture() -> dict[str, RoutingMetrics]:
    """Same labelled tasks; deterministic mechanics, not live-model quality."""

    registry = fixture_registry()
    requirements = support_requirements()
    cases = labelled_cases()
    governed_runs = tuple(
        run_routing_case(
            case,
            registry=registry,
            requirements=requirements,
            context=default_context(case.case_id),
            gate=GatePolicy(minimum_confidence=0.80),
        )
        for case in cases
    )

    # Cheapest/schema-only baseline makes one fast attempt and never recovers.
    expected = expected_support_artifact()
    baseline_cost = 0.0
    baseline_latencies: list[int] = []
    baseline_success = 0
    baseline_false_accepts = 0
    fast_route = _route_by_id(registry, "route-fast-eu-a")
    schema_gate = GatePolicy(
        require_semantic_constraints=False,
        require_grounding=False,
    )
    for case in cases:
        response = case.responses.get("route-fast-eu-a", (FixtureResponse(),))[0]
        baseline_latencies.append(response.latency_ms)
        baseline_cost += expected_cost_usd(
            fast_route,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        if response.error_code is not None:
            continue
        artifact = CandidateArtifact(
            artifact_id=f"baseline-{case.case_id}",
            request_id=case.case_id,
            route_id=fast_route.route_id,
            schema_id=response.schema_id,
            structured_data=response.structured_data or {},
            evidence_ids=response.evidence_ids,
            confidence=response.confidence,
        )
        validation = validate_candidate_output(
            artifact,
            expected,
            schema_gate,
            tenant_id=TENANT,
            evidence_registry=accepted_support_evidence(
                case.case_id,
                tenant_id=TENANT,
            ),
        )
        baseline_false_accepts += int(validation.false_accept)
        baseline_success += int(validation.accepted and validation.task_correct)
    baseline = RoutingMetrics(
        requests=len(cases),
        successful_compliant_tasks=baseline_success,
        false_accepts=baseline_false_accepts,
        false_promotions=0,
        promotions=0,
        provider_fallbacks=0,
        total_calls=len(cases),
        total_cost_usd=baseline_cost,
        latencies_ms=tuple(baseline_latencies),
    )
    return {
        "cheapest_schema_only": baseline,
        "governed": metrics_from_runs(governed_runs),
    }


def demo_summary() -> dict[str, Any]:
    registry = fixture_registry()
    requirements = support_requirements()
    context = default_context("demo-support-42")
    report = evaluate_eligibility(registry, requirements, context, now=FIXED_TIME)
    decision = select_route(registry, requirements, context, now=FIXED_TIME)
    run = run_routing_case(
        labelled_cases()[1],
        registry=registry,
        requirements=requirements,
        context=context,
    )
    metrics = evaluation_fixture()
    return {
        "eligible_routes": report.eligible_route_ids,
        "selected_route": decision.selected_route_id,
        "run_status": run.status.value,
        "attempt_reasons": [attempt.reason.value for attempt in run.attempts],
        "governed_task_success_rate": metrics["governed"].task_success_rate,
        "schema_only_false_accept_rate": metrics[
            "cheapest_schema_only"
        ].false_accept_rate,
        "production_provider_calls": 0,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(demo_summary(), indent=2))
