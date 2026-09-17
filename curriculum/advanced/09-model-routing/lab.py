"""Credential-free deterministic lab for Advanced 09 model routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from policy import (
    ADAPTER_CONTRACT_VERSION,
    AttemptReason,
    AttemptStatus,
    CandidateArtifact,
    CapacityState,
    CircuitState,
    DataClassification,
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
    objective: RoutingObjective = RoutingObjective.BALANCED_COST,
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


class FixtureCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    case_id: str
    responses: dict[str, tuple[FixtureResponse, ...]]
    cancel_after_attempt: int | None = Field(default=None, ge=1)


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


def _promotion_route(
    registry: RegistrySnapshot,
    decision_route_ids: tuple[str, ...],
    *,
    current_route_id: str,
    used_route_ids: set[str],
    task_family: str,
) -> str | None:
    current = _route_by_id(registry, current_route_id)
    current_quality = current.workload_profiles[task_family].quality_score
    candidates = [
        _route_by_id(registry, route_id)
        for route_id in decision_route_ids
        if route_id not in used_route_ids
        and _route_by_id(registry, route_id).equivalence_group
        == current.equivalence_group
        and _route_by_id(registry, route_id).workload_profiles[task_family].quality_score
        > current_quality
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda route: (
            route.workload_profiles[task_family].quality_score,
            -route.workload_profiles[task_family].p95_latency_ms,
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
) -> RoutingRun:
    registry = registry or fixture_registry()
    requirements = requirements or support_requirements()
    context = context or default_context(case.case_id)
    gate = gate or GatePolicy(require_task_correctness=True, minimum_confidence=0.80)
    failure_policy = failure_policy or FailurePolicy()
    cancellation = cancellation or CancellationToken(context.cancelled)
    decision = select_route(registry, requirements, context, now=context.requested_at)
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

        route = _route_by_id(registry, route_id)
        profile = route.workload_profiles[requirements.task_family]
        remaining_ms = int(
            (context.deadline - context.requested_at).total_seconds() * 1000
        ) - elapsed_ms
        if profile.p95_latency_ms > remaining_ms:
            return terminal(RunStatus.DEADLINE_EXCEEDED, "DEADLINE_BLOCKED_NEXT_MODEL_CALL")
        reserved = expected_cost_usd(
            route,
            input_tokens=requirements.expected_input_tokens,
            output_tokens=requirements.upper_bound_output_tokens,
        )
        if total_cost + reserved > context.max_cost_usd:
            return terminal(RunStatus.BUDGET_EXCEEDED, "COST_BUDGET_BLOCKED_NEXT_MODEL_CALL")
        new_provider_count = len(used_providers | {route.provider})
        if new_provider_count > context.max_providers:
            return terminal(RunStatus.BUDGET_EXCEEDED, "PROVIDER_BUDGET_EXHAUSTED")

        started_at = context.requested_at + timedelta(milliseconds=elapsed_ms)
        response = client.call(route_id)
        used_route_ids.add(route_id)
        used_providers.add(route.provider)
        elapsed_ms += response.latency_ms
        cost = expected_cost_usd(
            route,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        total_cost += cost
        attempt_id = f"attempt-{context.request_id}-{len(attempts) + 1}"

        if response.error_code is not None:
            fallbacks_available = compatible_fallbacks(
                registry,
                decision,
                exclude_route_ids=tuple(used_route_ids),
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
                reason = AttemptReason.RETRY
                continue
            if failure.action is FailureAction.FALLBACK:
                route_id = fallbacks_available[0]
                fallbacks += 1
                reason = AttemptReason.PROVIDER_FALLBACK
                continue
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
        validation = validate_candidate_output(artifact, expected, gate)
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
                "FALSE_ACCEPTED_OUTPUT" if validation.false_accept else "OUTPUT_ACCEPTED",
                artifact=artifact,
            )

        promoted = _promotion_route(
            registry,
            decision.eligible_route_ids,
            current_route_id=route_id,
            used_route_ids=used_route_ids,
            task_family=requirements.task_family,
        )
        if promoted is None:
            return terminal(RunStatus.QUALITY_GATE_FAILED, "NO_SAFE_PROMOTION_ROUTE")
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

    def allow_call(self, route_id: str, *, now: datetime) -> bool:
        breaker = self._states.setdefault(route_id, _Breaker())
        if breaker.state is CircuitState.OPEN:
            if breaker.opened_at is None or now < breaker.opened_at + self.open_duration:
                return False
            breaker.state = CircuitState.HALF_OPEN
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
            gate=GatePolicy(require_task_correctness=True, minimum_confidence=0.80),
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
        require_task_correctness=False,
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
        validation = validate_candidate_output(artifact, expected, schema_gate)
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
