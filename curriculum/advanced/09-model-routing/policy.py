"""Typed, application-owned policy for Advanced 09 model routing.

Provider catalogs and model output are untrusted inputs. The application owns
task requirements, tenant policy, eligibility, optimization, validation,
budgets, failure handling, and terminal state.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

REGISTRY_VERSION = "northstar-model-registry-v1"
PRICING_VERSION = "northstar-fixture-pricing-v1"
ROUTING_POLICY_VERSION = "northstar-routing-policy-v1"
VALIDATOR_VERSION = "northstar-support-validator-v1"
ADAPTER_CONTRACT_VERSION = "northstar-common-artifact-v1"


class RoutingPolicyError(ValueError):
    """Fail-closed routing outcome with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InputModality(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"


class OutputType(StrEnum):
    TEXT = "TEXT"
    STRUCTURED = "STRUCTURED"
    TOOL_CALL = "TOOL_CALL"


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class RetentionRequirement(StrEnum):
    STANDARD = "STANDARD"
    ZERO_DATA_RETENTION = "ZERO_DATA_RETENTION"


class RouteLifecycle(StrEnum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DRAINING = "DRAINING"
    DISABLED = "DISABLED"


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RoutingObjective(StrEnum):
    BALANCED_COST = "BALANCED_COST"
    QUALITY_FIRST = "QUALITY_FIRST"
    LATENCY_FIRST = "LATENCY_FIRST"


class ProviderErrorCode(StrEnum):
    RATE_LIMIT = "RATE_LIMIT"
    TRANSIENT_PROVIDER = "TRANSIENT_PROVIDER"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTH_FAILURE = "AUTH_FAILURE"
    POLICY_DENIED = "POLICY_DENIED"
    CONTEXT_TOO_LARGE = "CONTEXT_TOO_LARGE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    CONTENT_REJECTED = "CONTENT_REJECTED"


class FailureAction(StrEnum):
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    TERMINATE = "TERMINATE"


class AttemptReason(StrEnum):
    INITIAL = "INITIAL"
    CASCADE_PROMOTION = "CASCADE_PROMOTION"
    PROVIDER_FALLBACK = "PROVIDER_FALLBACK"
    RETRY = "RETRY"
    POLICY_REROUTE = "POLICY_REROUTE"


class AttemptStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    CANCELLED = "CANCELLED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"


class RunStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    NO_ELIGIBLE_ROUTE = "NO_ELIGIBLE_ROUTE"
    QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    CANCELLED = "CANCELLED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"


class RoutePricing(FrozenModel):
    input_usd_per_million: float = Field(ge=0)
    output_usd_per_million: float = Field(ge=0)
    cached_input_usd_per_million: float | None = Field(default=None, ge=0)
    pricing_version: str = PRICING_VERSION
    effective_at: datetime


class WorkloadProfile(FrozenModel):
    task_family: str = Field(min_length=1)
    quality_score: float = Field(ge=0, le=1)
    p50_latency_ms: int = Field(gt=0)
    p95_latency_ms: int = Field(gt=0)
    success_rate: float = Field(ge=0, le=1)
    timeout_rate: float = Field(ge=0, le=1)
    rate_limit_rate: float = Field(ge=0, le=1)
    provider_error_rate: float = Field(ge=0, le=1)
    sample_size: int = Field(gt=0)
    measured_at: datetime
    evaluator_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_latency(self) -> "WorkloadProfile":
        if self.p95_latency_ms < self.p50_latency_ms:
            raise ValueError("PROFILE_LATENCY_ORDER_INVALID")
        return self


class RouteHealth(FrozenModel):
    status: HealthStatus
    circuit_state: CircuitState = CircuitState.CLOSED
    last_updated_at: datetime


class CapacityState(FrozenModel):
    remaining_requests_per_minute: int = Field(ge=0)
    remaining_tokens_per_minute: int = Field(ge=0)
    queue_depth: int = Field(ge=0)
    available_concurrency: int = Field(ge=0)
    last_updated_at: datetime


class ModelRoute(FrozenModel):
    route_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model_fixture_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    deployment_region: str = Field(min_length=1)
    equivalence_group: str = Field(min_length=1)
    adapter_contract_version: str = ADAPTER_CONTRACT_VERSION
    input_modalities: tuple[InputModality, ...]
    output_types: tuple[OutputType, ...]
    supports_structured_outputs: bool
    supports_tool_calling: bool
    supports_parallel_tools: bool
    supports_streaming: bool
    supports_reasoning_controls: bool
    tool_protocols: tuple[str, ...] = ()
    maximum_context_tokens: int = Field(gt=0)
    maximum_output_tokens: int = Field(gt=0)
    allowed_data_classifications: tuple[DataClassification, ...]
    zero_data_retention_eligible: bool
    lifecycle: RouteLifecycle
    pricing: RoutePricing
    workload_profiles: Mapping[str, WorkloadProfile]
    health: RouteHealth
    capacity: CapacityState
    provider_metadata_version: str = Field(min_length=1)
    provider_metadata_effective_at: datetime
    provider_metadata_last_verified_at: datetime

    @model_validator(mode="after")
    def provider_metadata_order(self) -> "ModelRoute":
        if self.provider_metadata_last_verified_at < self.provider_metadata_effective_at:
            raise ValueError("PROVIDER_METADATA_VERIFICATION_INVALID")
        return self


class RegistrySnapshot(FrozenModel):
    registry_version: str = REGISTRY_VERSION
    effective_at: datetime
    last_verified_at: datetime
    routes: tuple[ModelRoute, ...]

    @model_validator(mode="after")
    def valid_registry(self) -> "RegistrySnapshot":
        if self.last_verified_at < self.effective_at:
            raise ValueError("REGISTRY_VERIFICATION_INVALID")
        route_ids = [route.route_id for route in self.routes]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("DUPLICATE_ROUTE_ID")
        return self


class ProviderCatalogRecord(FrozenModel):
    """Provider-supplied technical metadata before application policy overlay."""

    provider: str = Field(min_length=1)
    model_fixture_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    input_modalities: tuple[InputModality, ...]
    output_types: tuple[OutputType, ...]
    maximum_context_tokens: int = Field(gt=0)
    maximum_output_tokens: int = Field(gt=0)
    provider_metadata_version: str = Field(min_length=1)
    effective_at: datetime
    last_verified_at: datetime

    @model_validator(mode="after")
    def verified_after_effective(self) -> "ProviderCatalogRecord":
        if self.last_verified_at < self.effective_at:
            raise ValueError("PROVIDER_METADATA_VERIFICATION_INVALID")
        return self


class TaskRequirements(FrozenModel):
    task_family: str = Field(min_length=1)
    required_input_modalities: tuple[InputModality, ...] = (InputModality.TEXT,)
    required_output_type: OutputType = OutputType.TEXT
    structured_schema_id: str | None = None
    requires_tools: bool = False
    required_tool_protocol: str | None = None
    requires_parallel_tools: bool = False
    requires_streaming: bool = False
    requires_reasoning: bool = False
    minimum_context_tokens: int = Field(ge=0)
    minimum_output_tokens: int = Field(gt=0)
    expected_input_tokens: int = Field(gt=0)
    expected_output_tokens: int = Field(gt=0)
    upper_bound_output_tokens: int = Field(gt=0)
    minimum_quality: float = Field(ge=0, le=1)
    minimum_success_rate: float = Field(ge=0, le=1)
    data_classification: DataClassification
    required_equivalence_group: str | None = None

    @model_validator(mode="after")
    def coherent_requirements(self) -> "TaskRequirements":
        if self.required_output_type is OutputType.STRUCTURED and not self.structured_schema_id:
            raise ValueError("STRUCTURED_SCHEMA_REQUIRED")
        if self.requires_tools and not self.required_tool_protocol:
            raise ValueError("TOOL_PROTOCOL_REQUIRED")
        if self.upper_bound_output_tokens < self.expected_output_tokens:
            raise ValueError("OUTPUT_TOKEN_BOUND_INVALID")
        return self


class RoutingContext(FrozenModel):
    request_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    data_classification: DataClassification
    allowed_providers: tuple[str, ...]
    allowed_regions: tuple[str, ...]
    retention_requirement: RetentionRequirement
    latency_slo_ms: int = Field(gt=0)
    max_cost_usd: float = Field(gt=0)
    objective: RoutingObjective
    requested_at: datetime
    deadline: datetime
    policy_version: str = ROUTING_POLICY_VERSION
    session_id: str | None = None
    sticky_route_id: str | None = None
    cancelled: bool = False
    max_attempts: int = Field(default=3, ge=1)
    max_providers: int = Field(default=2, ge=1)
    max_fallbacks: int = Field(default=1, ge=0)
    max_state_age_seconds: int = Field(default=120, gt=0)

    @model_validator(mode="after")
    def valid_deadline(self) -> "RoutingContext":
        if self.deadline <= self.requested_at:
            raise ValueError("ROUTING_DEADLINE_INVALID")
        return self


class RouteEligibility(FrozenModel):
    route_id: str
    eligible: bool
    reason_codes: tuple[str, ...]
    expected_quality: float | None = None
    expected_success_rate: float | None = None
    expected_cost_usd: float | None = None
    reserved_cost_usd: float | None = None
    expected_p95_latency_ms: int | None = None


class EligibilityReport(FrozenModel):
    request_id: str
    tenant_id: str
    registry_version: str
    policy_version: str
    evaluated_at: datetime
    routes: tuple[RouteEligibility, ...]

    @property
    def eligible_route_ids(self) -> tuple[str, ...]:
        return tuple(item.route_id for item in self.routes if item.eligible)


class RoutingDecision(FrozenModel):
    request_id: str
    tenant_id: str
    selected_route_id: str | None
    eligible_route_ids: tuple[str, ...]
    rejected_routes: Mapping[str, tuple[str, ...]]
    reason_codes: tuple[str, ...]
    expected_quality: float | None
    expected_success_rate: float | None
    expected_cost_usd: float | None
    reserved_cost_usd: float | None
    expected_p95_latency_ms: int | None
    registry_version: str
    pricing_version: str | None
    policy_version: str
    decided_at: datetime


class CandidateArtifact(FrozenModel):
    artifact_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)
    schema_id: str | None
    structured_data: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    normalized_tool_calls: tuple[Mapping[str, Any], ...] = ()
    confidence: float = Field(ge=0, le=1)
    adapter_contract_version: str = ADAPTER_CONTRACT_VERSION


class ExpectedArtifact(FrozenModel):
    schema_id: str
    required_keys: tuple[str, ...]
    allowed_priorities: tuple[str, ...]
    expected_data: Mapping[str, Any]
    required_evidence_ids: tuple[str, ...]


class GatePolicy(FrozenModel):
    require_schema: bool = True
    require_semantic_constraints: bool = True
    require_grounding: bool = True
    require_task_correctness: bool = False
    minimum_confidence: float = Field(default=0, ge=0, le=1)
    validator_version: str = VALIDATOR_VERSION


class ValidationResult(FrozenModel):
    artifact_id: str
    schema_valid: bool
    semantic_valid: bool
    grounded: bool
    task_correct: bool
    accepted: bool
    false_accept: bool
    false_promotion: bool
    reason_codes: tuple[str, ...]
    validator_version: str


class FailurePolicy(FrozenModel):
    max_retries_per_route: int = Field(default=1, ge=0)
    base_backoff_ms: int = Field(default=100, ge=0)
    maximum_backoff_ms: int = Field(default=1000, ge=0)
    jitter_ms: int = Field(default=50, ge=0)
    retryable_errors: tuple[ProviderErrorCode, ...] = (
        ProviderErrorCode.RATE_LIMIT,
        ProviderErrorCode.TRANSIENT_PROVIDER,
        ProviderErrorCode.TIMEOUT,
    )
    fallback_errors: tuple[ProviderErrorCode, ...] = (
        ProviderErrorCode.RATE_LIMIT,
        ProviderErrorCode.TRANSIENT_PROVIDER,
        ProviderErrorCode.TIMEOUT,
        ProviderErrorCode.MODEL_UNAVAILABLE,
    )


class FailureDecision(FrozenModel):
    action: FailureAction
    delay_ms: int
    reason_codes: tuple[str, ...]


class RouteAttempt(FrozenModel):
    attempt_id: str
    request_id: str
    route_id: str
    provider: str
    model_fixture_id: str
    reason: AttemptReason
    started_at: datetime
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    status: AttemptStatus
    error_code: ProviderErrorCode | None = None
    validation_reason_codes: tuple[str, ...] = ()


class RoutingRun(FrozenModel):
    request_id: str
    tenant_id: str
    status: RunStatus
    initial_decision: RoutingDecision
    final_route_id: str | None
    artifact: CandidateArtifact | None
    attempts: tuple[RouteAttempt, ...]
    total_cost_usd: float = Field(ge=0)
    total_latency_ms: int = Field(ge=0)
    false_accepts: int = Field(ge=0)
    false_promotions: int = Field(ge=0)
    promotion_count: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    terminal_reason: str


class RoutingMetrics(FrozenModel):
    requests: int = Field(gt=0)
    successful_compliant_tasks: int = Field(ge=0)
    false_accepts: int = Field(ge=0)
    false_promotions: int = Field(ge=0)
    promotions: int = Field(ge=0)
    provider_fallbacks: int = Field(ge=0)
    total_calls: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0)
    latencies_ms: tuple[int, ...]

    @property
    def task_success_rate(self) -> float:
        return self.successful_compliant_tasks / self.requests

    @property
    def false_accept_rate(self) -> float:
        return self.false_accepts / self.requests

    @property
    def false_promotion_rate(self) -> float:
        return self.false_promotions / self.requests

    @property
    def promotion_rate(self) -> float:
        return self.promotions / self.requests

    @property
    def average_calls_per_request(self) -> float:
        return self.total_calls / self.requests

    @property
    def average_cost_usd(self) -> float:
        return self.total_cost_usd / self.requests

    @property
    def cost_per_successful_compliant_task(self) -> float:
        if not self.successful_compliant_tasks:
            return 0.0
        return self.total_cost_usd / self.successful_compliant_tasks

    @property
    def p95_latency_ms(self) -> int:
        ordered = sorted(self.latencies_ms)
        index = max(0, int((len(ordered) * 0.95) + 0.999999) - 1)
        return ordered[index]


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def expected_cost_usd(
    route: ModelRoute,
    *,
    input_tokens: int,
    output_tokens: int,
) -> float:
    return (
        input_tokens * route.pricing.input_usd_per_million
        + output_tokens * route.pricing.output_usd_per_million
    ) / 1_000_000


def _route_by_id(registry: RegistrySnapshot, route_id: str) -> ModelRoute:
    for route in registry.routes:
        if route.route_id == route_id:
            return route
    raise RoutingPolicyError("ROUTE_NOT_FOUND")


def evaluate_eligibility(
    registry: RegistrySnapshot,
    requirements: TaskRequirements,
    context: RoutingContext,
    *,
    now: datetime,
) -> EligibilityReport:
    """Apply technical and organizational constraints before optimization."""

    decisions: list[RouteEligibility] = []
    for route in registry.routes:
        reasons: list[str] = []
        profile = route.workload_profiles.get(requirements.task_family)
        expected_cost = expected_cost_usd(
            route,
            input_tokens=requirements.expected_input_tokens,
            output_tokens=requirements.expected_output_tokens,
        )
        reserved_cost = expected_cost_usd(
            route,
            input_tokens=requirements.expected_input_tokens,
            output_tokens=requirements.upper_bound_output_tokens,
        )

        if context.cancelled:
            reasons.append("REQUEST_CANCELLED")
        if requirements.data_classification is not context.data_classification:
            reasons.append("DATA_CLASSIFICATION_MISMATCH")
        if route.lifecycle is RouteLifecycle.DRAINING:
            if context.sticky_route_id != route.route_id:
                reasons.append("ROUTE_DRAINING_NEW_WORK_DENIED")
        elif route.lifecycle is not RouteLifecycle.ACTIVE:
            reasons.append(f"ROUTE_{route.lifecycle.value}")
        if route.provider not in context.allowed_providers:
            reasons.append("PROVIDER_POLICY_DENIED")
        if route.deployment_region not in context.allowed_regions:
            reasons.append("DATA_RESIDENCY_DENIED")
        if context.data_classification not in route.allowed_data_classifications:
            reasons.append("DATA_CLASSIFICATION_DENIED")
        if (
            context.retention_requirement is RetentionRequirement.ZERO_DATA_RETENTION
            and not route.zero_data_retention_eligible
        ):
            reasons.append("RETENTION_REQUIREMENT_DENIED")
        if not set(requirements.required_input_modalities).issubset(route.input_modalities):
            reasons.append("INPUT_MODALITY_UNSUPPORTED")
        if requirements.required_output_type not in route.output_types:
            reasons.append("OUTPUT_TYPE_UNSUPPORTED")
        if (
            requirements.required_output_type is OutputType.STRUCTURED
            and not route.supports_structured_outputs
        ):
            reasons.append("STRUCTURED_OUTPUT_UNSUPPORTED")
        if requirements.requires_tools and not route.supports_tool_calling:
            reasons.append("TOOL_CALLING_UNSUPPORTED")
        if (
            requirements.required_tool_protocol
            and requirements.required_tool_protocol not in route.tool_protocols
        ):
            reasons.append("TOOL_PROTOCOL_UNSUPPORTED")
        if requirements.requires_parallel_tools and not route.supports_parallel_tools:
            reasons.append("PARALLEL_TOOLS_UNSUPPORTED")
        if requirements.requires_streaming and not route.supports_streaming:
            reasons.append("STREAMING_UNSUPPORTED")
        if requirements.requires_reasoning and not route.supports_reasoning_controls:
            reasons.append("REASONING_CONTROL_UNSUPPORTED")
        if route.maximum_context_tokens < requirements.minimum_context_tokens:
            reasons.append("CONTEXT_LIMIT_INSUFFICIENT")
        if route.maximum_output_tokens < requirements.minimum_output_tokens:
            reasons.append("OUTPUT_LIMIT_INSUFFICIENT")
        if (
            requirements.required_equivalence_group
            and route.equivalence_group != requirements.required_equivalence_group
        ):
            reasons.append("ROUTE_GROUP_INCOMPATIBLE")
        if profile is None:
            reasons.append("WORKLOAD_PROFILE_MISSING")
        elif profile.quality_score < requirements.minimum_quality:
            reasons.append("QUALITY_THRESHOLD_NOT_MET")
        if (
            profile is not None
            and profile.success_rate < requirements.minimum_success_rate
        ):
            reasons.append("RELIABILITY_THRESHOLD_NOT_MET")
        if profile is not None and profile.p95_latency_ms > context.latency_slo_ms:
            reasons.append("LATENCY_SLO_NOT_MET")
        if reserved_cost > context.max_cost_usd:
            reasons.append("COST_CEILING_EXCEEDED")
        if route.health.status is HealthStatus.UNAVAILABLE:
            reasons.append("ROUTE_UNAVAILABLE")
        if route.health.status is HealthStatus.RATE_LIMITED:
            reasons.append("ROUTE_RATE_LIMITED")
        if route.health.circuit_state is CircuitState.OPEN:
            reasons.append("CIRCUIT_OPEN")
        maximum_age = timedelta(seconds=context.max_state_age_seconds)
        if now - route.health.last_updated_at > maximum_age:
            reasons.append("HEALTH_STATE_STALE")
        if now - route.capacity.last_updated_at > maximum_age:
            reasons.append("CAPACITY_STATE_STALE")
        if route.capacity.remaining_requests_per_minute < 1:
            reasons.append("REQUEST_CAPACITY_EXHAUSTED")
        token_reserve = requirements.expected_input_tokens + requirements.upper_bound_output_tokens
        if route.capacity.remaining_tokens_per_minute < token_reserve:
            reasons.append("TOKEN_CAPACITY_EXHAUSTED")
        if route.capacity.available_concurrency < 1:
            reasons.append("CONCURRENCY_EXHAUSTED")
        if profile is not None and now + timedelta(milliseconds=profile.p95_latency_ms) > context.deadline:
            reasons.append("REQUEST_DEADLINE_INFEASIBLE")

        decisions.append(
            RouteEligibility(
                route_id=route.route_id,
                eligible=not reasons,
                reason_codes=tuple(reasons) if reasons else ("ELIGIBLE",),
                expected_quality=profile.quality_score if profile else None,
                expected_success_rate=profile.success_rate if profile else None,
                expected_cost_usd=expected_cost,
                reserved_cost_usd=reserved_cost,
                expected_p95_latency_ms=profile.p95_latency_ms if profile else None,
            )
        )
    return EligibilityReport(
        request_id=context.request_id,
        tenant_id=context.tenant_id,
        registry_version=registry.registry_version,
        policy_version=context.policy_version,
        evaluated_at=now,
        routes=tuple(decisions),
    )


def select_route(
    registry: RegistrySnapshot,
    requirements: TaskRequirements,
    context: RoutingContext,
    *,
    now: datetime,
) -> RoutingDecision:
    report = evaluate_eligibility(registry, requirements, context, now=now)
    eligible = [item for item in report.routes if item.eligible]
    rejected = {
        item.route_id: item.reason_codes for item in report.routes if not item.eligible
    }
    if not eligible:
        return RoutingDecision(
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            selected_route_id=None,
            eligible_route_ids=(),
            rejected_routes=rejected,
            reason_codes=("NO_ELIGIBLE_ROUTE",),
            expected_quality=None,
            expected_success_rate=None,
            expected_cost_usd=None,
            reserved_cost_usd=None,
            expected_p95_latency_ms=None,
            registry_version=registry.registry_version,
            pricing_version=None,
            policy_version=context.policy_version,
            decided_at=now,
        )

    reasons: tuple[str, ...]
    sticky = next(
        (item for item in eligible if item.route_id == context.sticky_route_id), None
    )
    if sticky is not None:
        selected = sticky
        reasons = ("STICKY_ROUTE_REUSED",)
    else:
        if context.objective is RoutingObjective.QUALITY_FIRST:
            key = lambda item: (
                -(item.expected_quality or 0),
                item.expected_cost_usd or 0,
                item.expected_p95_latency_ms or 0,
                item.route_id,
            )
        elif context.objective is RoutingObjective.LATENCY_FIRST:
            key = lambda item: (
                item.expected_p95_latency_ms or 0,
                item.expected_cost_usd or 0,
                -(item.expected_quality or 0),
                item.route_id,
            )
        else:
            key = lambda item: (
                item.expected_cost_usd or 0,
                item.expected_p95_latency_ms or 0,
                -(item.expected_quality or 0),
                item.route_id,
            )
        selected = min(eligible, key=key)
        reasons = (
            "STICKY_ROUTE_INELIGIBLE",
            "OPTIMIZED_WITHIN_ELIGIBLE_SET",
        ) if context.sticky_route_id else ("OPTIMIZED_WITHIN_ELIGIBLE_SET",)

    route = _route_by_id(registry, selected.route_id)
    return RoutingDecision(
        request_id=context.request_id,
        tenant_id=context.tenant_id,
        selected_route_id=selected.route_id,
        eligible_route_ids=tuple(item.route_id for item in eligible),
        rejected_routes=rejected,
        reason_codes=reasons,
        expected_quality=selected.expected_quality,
        expected_success_rate=selected.expected_success_rate,
        expected_cost_usd=selected.expected_cost_usd,
        reserved_cost_usd=selected.reserved_cost_usd,
        expected_p95_latency_ms=selected.expected_p95_latency_ms,
        registry_version=registry.registry_version,
        pricing_version=route.pricing.pricing_version,
        policy_version=context.policy_version,
        decided_at=now,
    )


def validate_candidate_output(
    artifact: CandidateArtifact,
    expected: ExpectedArtifact,
    gate: GatePolicy,
) -> ValidationResult:
    schema_valid = (
        artifact.schema_id == expected.schema_id
        and set(expected.required_keys).issubset(artifact.structured_data)
    )
    priority = artifact.structured_data.get("priority")
    semantic_valid = (
        bool(artifact.structured_data.get("customer"))
        and priority in expected.allowed_priorities
    )
    grounded = set(expected.required_evidence_ids).issubset(artifact.evidence_ids)
    task_correct = (
        schema_valid
        and semantic_valid
        and grounded
        and dict(artifact.structured_data) == dict(expected.expected_data)
    )
    checks = [artifact.confidence >= gate.minimum_confidence]
    if gate.require_schema:
        checks.append(schema_valid)
    if gate.require_semantic_constraints:
        checks.append(semantic_valid)
    if gate.require_grounding:
        checks.append(grounded)
    if gate.require_task_correctness:
        checks.append(task_correct)
    accepted = all(checks)
    reasons: list[str] = []
    if not schema_valid:
        reasons.append("SCHEMA_INVALID")
    if not semantic_valid:
        reasons.append("SEMANTIC_CONSTRAINT_FAILED")
    if not grounded:
        reasons.append("GROUNDING_FAILED")
    if not task_correct:
        reasons.append("TASK_CORRECTNESS_FAILED")
    if artifact.confidence < gate.minimum_confidence:
        reasons.append("CONFIDENCE_BELOW_THRESHOLD")
    if accepted:
        reasons.append("AUTOMATED_GATE_ACCEPTED")
    return ValidationResult(
        artifact_id=artifact.artifact_id,
        schema_valid=schema_valid,
        semantic_valid=semantic_valid,
        grounded=grounded,
        task_correct=task_correct,
        accepted=accepted,
        false_accept=accepted and not task_correct,
        false_promotion=(not accepted) and task_correct,
        reason_codes=tuple(reasons),
        validator_version=gate.validator_version,
    )


TERMINAL_PROVIDER_ERRORS = {
    ProviderErrorCode.INVALID_REQUEST,
    ProviderErrorCode.AUTH_FAILURE,
    ProviderErrorCode.POLICY_DENIED,
    ProviderErrorCode.CONTEXT_TOO_LARGE,
    ProviderErrorCode.CONTENT_REJECTED,
}


def decide_failure_action(
    error_code: ProviderErrorCode,
    *,
    request_id: str,
    retry_count: int,
    retry_after_ms: int | None,
    remaining_deadline_ms: int,
    fallback_available: bool,
    policy: FailurePolicy,
) -> FailureDecision:
    if error_code in TERMINAL_PROVIDER_ERRORS:
        return FailureDecision(
            action=FailureAction.TERMINATE,
            delay_ms=0,
            reason_codes=(f"{error_code.value}_TERMINAL",),
        )
    if error_code in policy.retryable_errors and retry_count < policy.max_retries_per_route:
        exponential = min(
            policy.maximum_backoff_ms,
            policy.base_backoff_ms * (2**retry_count),
        )
        jitter = int(canonical_digest((request_id, retry_count))[:8], 16) % (
            policy.jitter_ms + 1
        )
        delay = retry_after_ms if retry_after_ms is not None else exponential + jitter
        if delay < remaining_deadline_ms:
            return FailureDecision(
                action=FailureAction.RETRY,
                delay_ms=delay,
                reason_codes=("BOUNDED_RETRY_WITH_JITTER",),
            )
    if error_code in policy.fallback_errors and fallback_available:
        return FailureDecision(
            action=FailureAction.FALLBACK,
            delay_ms=0,
            reason_codes=("COMPATIBLE_FALLBACK_REQUIRED",),
        )
    return FailureDecision(
        action=FailureAction.TERMINATE,
        delay_ms=0,
        reason_codes=("NO_SAFE_RECOVERY_PATH",),
    )


def compatible_fallbacks(
    registry: RegistrySnapshot,
    decision: RoutingDecision,
    *,
    exclude_route_ids: Sequence[str],
) -> tuple[str, ...]:
    if decision.selected_route_id is None:
        return ()
    primary = _route_by_id(registry, decision.selected_route_id)
    excluded = set(exclude_route_ids)
    return tuple(
        route_id
        for route_id in decision.eligible_route_ids
        if route_id not in excluded
        and _route_by_id(registry, route_id).equivalence_group
        == primary.equivalence_group
        and _route_by_id(registry, route_id).adapter_contract_version
        == primary.adapter_contract_version
    )
