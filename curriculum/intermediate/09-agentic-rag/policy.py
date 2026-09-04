"""Framework-neutral policy contracts for Course 09 Agentic RAG.

The model may propose queries and routes. Application-owned code binds tenant
scope, validates sources, admits retrieval against budgets, verifies evidence,
and keeps mitigation proposals separate from execution authorization.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


IDENTIFIER_PATTERN = r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyError(ValueError):
    """A deterministic source, scope, budget, or grounding violation."""


class SourceType(str, Enum):
    INCIDENT_DB = "incident_db"
    RUNBOOK_SEARCH = "runbook_search"
    DEPENDENCY_GRAPH = "dependency_graph"
    PROVIDER_STATUS = "provider_status"
    WEB_SEARCH = "web_search"


class TrustLevel(str, Enum):
    CONTROLLED = "CONTROLLED"
    OFFICIAL = "OFFICIAL"
    VERIFIED = "VERIFIED"
    UNTRUSTED = "UNTRUSTED"


class RetrievalStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    DENIED = "DENIED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ERROR = "ERROR"


class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    MISSING_INCIDENT = "MISSING_INCIDENT"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    MISSING_MITIGATION = "MISSING_MITIGATION"
    STALE = "STALE"
    CONFLICT = "CONFLICT"


class RouteType(str, Enum):
    KNOWN_ROUTE = "KNOWN_ROUTE"
    UNKNOWN = "UNKNOWN"
    AMBIGUOUS = "AMBIGUOUS"
    MULTI_ROUTE = "MULTI_ROUTE"


class RetrievalMode(str, Enum):
    NO_RETRIEVAL = "NO_RETRIEVAL"
    SINGLE_RETRIEVAL = "SINGLE_RETRIEVAL"
    MULTI_SOURCE = "MULTI_SOURCE"
    ITERATIVE = "ITERATIVE"


class StopReason(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    FIXED_BASELINE_COMPLETE = "FIXED_BASELINE_COMPLETE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICT = "CONFLICT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXHAUSTED = "DEADLINE_EXHAUSTED"
    POLICY_DENIED = "POLICY_DENIED"


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    MISSING_CITATION = "MISSING_CITATION"
    EVIDENCE_NOT_FOUND = "EVIDENCE_NOT_FOUND"
    TENANT_MISMATCH = "TENANT_MISMATCH"
    VERSION_MISMATCH = "VERSION_MISMATCH"


class ConfidenceLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


class ProposalPolicyStatus(str, Enum):
    ALLOWED_PROPOSAL = "ALLOWED_PROPOSAL"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    DENIED = "DENIED"


class MitigationGroundingStatus(str, Enum):
    GROUNDED = "GROUNDED"
    UNSUPPORTED_PROPOSAL = "UNSUPPORTED_PROPOSAL"


class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class SourceDefinition(FrozenModel):
    source_type: SourceType
    tenant_aware: bool
    read_only: bool
    structured: bool
    freshness_seconds: int = Field(gt=0)
    estimated_cost_usd: float = Field(ge=0)
    estimated_latency_ms: float = Field(gt=0)
    allowed_data_classifications: tuple[DataClassification, ...] = Field(min_length=1)


class RetrievalContext(FrozenModel):
    """Trusted application context; never populated from retrieved content."""

    tenant_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    user_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    allowed_sources: tuple[SourceType, ...] = Field(min_length=1)
    allowed_domains: tuple[str, ...] = ()
    authorization_scope: tuple[str, ...] = Field(min_length=1)
    policy_version: str = Field(min_length=1, max_length=32)
    max_queries: int = Field(gt=0, le=100)
    max_hops: int = Field(ge=0, le=10)
    max_web_queries: int = Field(ge=0, le=10)
    max_cost_usd: float = Field(ge=0)
    deadline_ms: float = Field(gt=0)
    allow_web_search: bool = False

    @field_validator("allowed_sources", "allowed_domains", "authorization_scope")
    @classmethod
    def unique_values(cls, values: tuple[Any, ...]) -> tuple[Any, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Trusted context values must be unique")
        return values


class RetrievalQuery(FrozenModel):
    query_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    question: str = Field(min_length=1, max_length=500)
    intent: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    proposed_tenant_id: str | None = Field(
        default=None, min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN
    )
    data_classification: DataClassification = DataClassification.INTERNAL


class IncidentQueryParameters(FrozenModel):
    """Typed structured parameters. Tenant is intentionally absent."""

    service: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    region: str = Field(min_length=1, max_length=32, pattern=IDENTIFIER_PATTERN)
    start_time: str = Field(min_length=1, max_length=64)
    end_time: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=10, gt=0, le=100)


class RetrievalRequest(FrozenModel):
    request_id: str = Field(min_length=1, max_length=100, pattern=IDENTIFIER_PATTERN)
    query: RetrievalQuery
    source_type: SourceType
    tenant_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    policy_version: str = Field(min_length=1, max_length=32)
    hop: int = Field(ge=0)
    structured_parameters: IncidentQueryParameters | None = None
    outbound_query: str | None = Field(default=None, max_length=200)
    target_domain: str | None = Field(default=None, max_length=253)


class EvidenceItem(FrozenModel):
    evidence_id: str = Field(min_length=1, max_length=100, pattern=IDENTIFIER_PATTERN)
    tenant_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    source_type: SourceType
    source_id: str = Field(min_length=1, max_length=100)
    source_version: str = Field(min_length=1, max_length=64)
    observed_at: str = Field(min_length=1, max_length=64)
    event_time: str = Field(min_length=1, max_length=64)
    trust: TrustLevel
    authority: float = Field(ge=0, le=1)
    relevance_score: float = Field(ge=0, le=1)
    content: str = Field(min_length=1, max_length=4000)
    metadata: tuple[tuple[str, str], ...] = ()
    raw_artifact_handle: str = Field(min_length=1, max_length=200)
    supports_claims: tuple[str, ...] = ()
    supports_actions: tuple[str, ...] = ()
    evidence_role: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)

    @field_validator("supports_claims", "supports_actions")
    @classmethod
    def unique_gold_labels(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Evidence gold-label IDs must be unique")
        return values


class RetrievalResult(FrozenModel):
    request: RetrievalRequest
    status: RetrievalStatus
    evidence: tuple[EvidenceItem, ...] = ()
    cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    error_code: str | None = None

    @model_validator(mode="after")
    def success_has_evidence(self) -> "RetrievalResult":
        if self.status == RetrievalStatus.SUCCESS and not self.evidence:
            raise ValueError("Successful retrieval must return evidence")
        return self


class EvidenceBundle(FrozenModel):
    tenant_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    items: tuple[EvidenceItem, ...] = ()
    query_ids: tuple[str, ...] = ()
    total_cost_usd: float = Field(default=0, ge=0)
    total_latency_ms: float = Field(default=0, ge=0)
    duplicate_retrievals: int = Field(default=0, ge=0)


class EvidenceGap(FrozenModel):
    status: EvidenceStatus
    missing_evidence: tuple[str, ...] = ()
    recommended_source: SourceType | None = None
    reason: str = Field(min_length=1, max_length=500)


class RetrievalBudget(StrictModel):
    max_queries: int = Field(gt=0)
    max_hops: int = Field(ge=0)
    max_web_queries: int = Field(ge=0)
    max_cost_usd: float = Field(ge=0)
    deadline_ms: float = Field(gt=0)
    used_queries: int = Field(default=0, ge=0)
    used_hops: int = Field(default=0, ge=0)
    used_web_queries: int = Field(default=0, ge=0)
    reserved_cost_usd: float = Field(default=0, ge=0)
    reserved_latency_ms: float = Field(default=0, ge=0)
    actual_cost_usd: float = Field(default=0, ge=0)
    actual_latency_ms: float = Field(default=0, ge=0)

    @classmethod
    def from_context(cls, context: RetrievalContext) -> "RetrievalBudget":
        return cls(
            max_queries=context.max_queries,
            max_hops=context.max_hops,
            max_web_queries=context.max_web_queries,
            max_cost_usd=context.max_cost_usd,
            deadline_ms=context.deadline_ms,
        )


class RetrievalPlan(FrozenModel):
    plan_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    question: str = Field(min_length=1, max_length=500)
    mode: RetrievalMode
    queries: tuple[RetrievalQuery, ...]
    max_query_rewrites: int = Field(default=1, ge=0, le=5)
    max_corrective_retrievals: int = Field(default=1, ge=0, le=5)
    max_hops: int = Field(default=2, ge=0, le=10)


class RouteDecision(FrozenModel):
    route_type: RouteType
    proposed_sources: tuple[SourceType, ...] = ()
    reason: str = Field(min_length=1, max_length=300)


class RoutingEvaluationCase(FrozenModel):
    case_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    query: RetrievalQuery
    expected_route_type: RouteType
    expected_sources: tuple[SourceType, ...] = ()

    @field_validator("expected_sources")
    @classmethod
    def unique_expected_sources(
        cls, values: tuple[SourceType, ...]
    ) -> tuple[SourceType, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Expected route sources must be unique")
        return values

    @model_validator(mode="after")
    def route_shape_matches_outcome(self) -> "RoutingEvaluationCase":
        count = len(self.expected_sources)
        if self.expected_route_type == RouteType.KNOWN_ROUTE and count != 1:
            raise ValueError("KNOWN_ROUTE requires exactly one expected source")
        if self.expected_route_type == RouteType.MULTI_ROUTE and count < 2:
            raise ValueError("MULTI_ROUTE requires at least two expected sources")
        if self.expected_route_type in {RouteType.UNKNOWN, RouteType.AMBIGUOUS} and count:
            raise ValueError("UNKNOWN and AMBIGUOUS cases cannot declare a source")
        return self


class RoutingQualityMetrics(FrozenModel):
    exact_route_accuracy: float = Field(ge=0, le=1)
    multi_route_source_precision: float = Field(ge=0, le=1)
    multi_route_source_recall: float = Field(ge=0, le=1)
    unknown_ambiguous_accuracy: float = Field(ge=0, le=1)


class RetrievalEvaluationCase(FrozenModel):
    case_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    relevant_evidence_ids: tuple[str, ...] = Field(min_length=1)
    required_evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("relevant_evidence_ids", "required_evidence_ids")
    @classmethod
    def unique_evidence_labels(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Evaluation evidence labels must be unique")
        return values

    @model_validator(mode="after")
    def required_is_relevant(self) -> "RetrievalEvaluationCase":
        if not set(self.required_evidence_ids).issubset(self.relevant_evidence_ids):
            raise ValueError("Required evidence must also be labeled relevant")
        return self


class RetrievalQualityMetrics(FrozenModel):
    retrieval_precision: float = Field(ge=0, le=1)
    retrieval_recall: float = Field(ge=0, le=1)
    required_evidence_recall: float = Field(ge=0, le=1)


class SafetyCounters(StrictModel):
    """Observable attempted and executed boundary violations."""

    tenant_violation_attempts: int = Field(default=0, ge=0)
    tenant_violation_executions: int = Field(default=0, ge=0)
    unsafe_action_attempts: int = Field(default=0, ge=0)
    unsafe_action_executions: int = Field(default=0, ge=0)


class Claim(FrozenModel):
    claim_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    text: str = Field(min_length=1, max_length=500)
    material: bool = True


class ClaimEvidenceLink(FrozenModel):
    claim_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Claim/evidence links must be unique")
        return values


class Citation(FrozenModel):
    claim_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    evidence_id: str = Field(min_length=1, max_length=100, pattern=IDENTIFIER_PATTERN)
    source_id: str = Field(min_length=1, max_length=100)
    source_version: str = Field(min_length=1, max_length=64)


class ClaimVerification(FrozenModel):
    claim_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    status: ClaimStatus
    reason: str = Field(min_length=1, max_length=300)


class CitationReport(FrozenModel):
    verifications: tuple[ClaimVerification, ...]
    citation_completeness: float = Field(ge=0, le=1)
    unsupported_claim_rate: float = Field(ge=0, le=1)


class GroundedAnswer(FrozenModel):
    summary: str = Field(min_length=1, max_length=2000)
    candidate_claims: tuple[Claim, ...]
    verified_claims: tuple[Claim, ...]
    citations: tuple[Citation, ...]
    confidence_label: ConfidenceLabel
    stop_reason: StopReason
    missing_evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def verified_output_is_a_supported_subset(self) -> "GroundedAnswer":
        candidate_ids = {claim.claim_id for claim in self.candidate_claims}
        verified_ids = {claim.claim_id for claim in self.verified_claims}
        if not verified_ids.issubset(candidate_ids):
            raise ValueError("Verified claims must be a subset of candidate claims")
        if any(citation.claim_id not in verified_ids for citation in self.citations):
            raise ValueError("Citations may be exposed only for verified claims")
        return self


class MitigationProposal(FrozenModel):
    action: str = Field(min_length=1, max_length=100, pattern=IDENTIFIER_PATTERN)
    target: str = Field(min_length=1, max_length=200)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    grounding_status: MitigationGroundingStatus
    policy_status: ProposalPolicyStatus

    @model_validator(mode="after")
    def unsupported_is_never_authorized(self) -> "MitigationProposal":
        if (
            self.grounding_status
            == MitigationGroundingStatus.UNSUPPORTED_PROPOSAL
            and self.policy_status != ProposalPolicyStatus.DENIED
        ):
            raise ValueError("An unsupported proposal must be denied")
        return self


class RetrievalTrace(FrozenModel):
    sequence: int = Field(gt=0)
    query_id: str = Field(min_length=1, max_length=64, pattern=IDENTIFIER_PATTERN)
    route_type: RouteType
    source_type: SourceType | None = None
    result_count: int = Field(ge=0)
    evidence_ids: tuple[str, ...] = ()
    gap_decision: EvidenceStatus | None = None
    hop: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    stop_reason: StopReason | None = None


class ControllerRun(FrozenModel):
    plan: RetrievalPlan
    bundle: EvidenceBundle
    gap: EvidenceGap
    answer: GroundedAnswer
    traces: tuple[RetrievalTrace, ...]
    budget: RetrievalBudget


class EvaluationMetrics(FrozenModel):
    route_accuracy: float = Field(ge=0, le=1)
    multi_route_source_precision: float = Field(ge=0, le=1)
    multi_route_source_recall: float = Field(ge=0, le=1)
    unknown_ambiguous_accuracy: float = Field(ge=0, le=1)
    retrieval_precision: float = Field(ge=0, le=1)
    retrieval_recall: float = Field(ge=0, le=1)
    required_evidence_recall: float = Field(ge=0, le=1)
    citation_completeness: float = Field(ge=0, le=1)
    unsupported_claim_rate: float = Field(ge=0, le=1)
    duplicate_retrieval_rate: float = Field(ge=0, le=1)
    query_count: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    tenant_violation_attempts: int = Field(ge=0)
    tenant_violation_executions: int = Field(ge=0)
    unsafe_action_attempts: int = Field(ge=0)
    unsafe_action_executions: int = Field(ge=0)


def build_source_registry() -> dict[SourceType, SourceDefinition]:
    """Application-owned source capabilities. Unknown sources are absent/denied."""

    return {
        SourceType.INCIDENT_DB: SourceDefinition(
            source_type=SourceType.INCIDENT_DB,
            tenant_aware=True,
            read_only=True,
            structured=True,
            freshness_seconds=86_400,
            estimated_cost_usd=0.01,
            estimated_latency_ms=18,
            allowed_data_classifications=(
                DataClassification.INTERNAL,
                DataClassification.CONFIDENTIAL,
            ),
        ),
        SourceType.RUNBOOK_SEARCH: SourceDefinition(
            source_type=SourceType.RUNBOOK_SEARCH,
            tenant_aware=True,
            read_only=True,
            structured=False,
            freshness_seconds=604_800,
            estimated_cost_usd=0.01,
            estimated_latency_ms=22,
            allowed_data_classifications=(DataClassification.INTERNAL,),
        ),
        SourceType.DEPENDENCY_GRAPH: SourceDefinition(
            source_type=SourceType.DEPENDENCY_GRAPH,
            tenant_aware=True,
            read_only=True,
            structured=True,
            freshness_seconds=86_400,
            estimated_cost_usd=0.015,
            estimated_latency_ms=14,
            allowed_data_classifications=(DataClassification.INTERNAL,),
        ),
        SourceType.PROVIDER_STATUS: SourceDefinition(
            source_type=SourceType.PROVIDER_STATUS,
            tenant_aware=False,
            read_only=True,
            structured=True,
            freshness_seconds=3_600,
            estimated_cost_usd=0.01,
            estimated_latency_ms=30,
            allowed_data_classifications=(DataClassification.PUBLIC,),
        ),
        SourceType.WEB_SEARCH: SourceDefinition(
            source_type=SourceType.WEB_SEARCH,
            tenant_aware=False,
            read_only=True,
            structured=False,
            freshness_seconds=3_600,
            estimated_cost_usd=0.03,
            estimated_latency_ms=120,
            allowed_data_classifications=(DataClassification.PUBLIC,),
        ),
    }


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def rank_evidence(items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
    """Rank authority and time separately from semantic relevance."""

    return tuple(
        sorted(
            items,
            key=lambda item: (
                item.authority,
                _parse_time(item.event_time).timestamp(),
                _parse_time(item.observed_at).timestamp(),
                item.source_version,
                item.relevance_score,
            ),
            reverse=True,
        )
    )


def route_query(query: RetrievalQuery) -> RouteDecision:
    """Deterministic proposal router with explicit unknown/ambiguous/multi outcomes."""

    text = f"{query.intent} {query.question}".lower()
    routes: list[SourceType] = []
    if any(term in text for term in ("incident", "failed", "failure", "changed", "started")):
        routes.append(SourceType.INCIDENT_DB)
    if any(term in text for term in ("runbook", "mitigation", "procedure", "authorized")):
        routes.append(SourceType.RUNBOOK_SEARCH)
    if any(term in text for term in ("dependency", "provider", "upstream", "involved")):
        routes.extend((SourceType.DEPENDENCY_GRAPH, SourceType.PROVIDER_STATUS))
    routes = list(dict.fromkeys(routes))
    if len(routes) > 1:
        return RouteDecision(
            route_type=RouteType.MULTI_ROUTE,
            proposed_sources=tuple(routes),
            reason="The evidence question spans more than one registered source.",
        )
    if len(routes) == 1:
        return RouteDecision(
            route_type=RouteType.KNOWN_ROUTE,
            proposed_sources=tuple(routes),
            reason="Deterministic fixture rule matched one registered source.",
        )
    if any(term in text for term in ("status", "policy", "history")):
        return RouteDecision(
            route_type=RouteType.AMBIGUOUS,
            reason="The intent needs clarification before choosing a source.",
        )
    return RouteDecision(
        route_type=RouteType.UNKNOWN,
        reason="No registered source is justified by the query intent.",
    )


def evaluate_routing_quality(
    cases: tuple[RoutingEvaluationCase, ...],
    *,
    router: Callable[[RetrievalQuery], RouteDecision] = route_query,
) -> RoutingQualityMetrics:
    """Score exact route outcomes and source sets against labeled cases."""

    if not cases:
        raise PolicyError("ROUTING_EVALUATION_DATASET_REQUIRED")
    exact = 0
    multi_true_positive = 0
    multi_false_positive = 0
    multi_false_negative = 0
    uncertain_correct = 0
    uncertain_total = 0
    for case in cases:
        decision = router(case.query)
        predicted_sources = set(decision.proposed_sources)
        expected_sources = set(case.expected_sources)
        if (
            decision.route_type == case.expected_route_type
            and predicted_sources == expected_sources
        ):
            exact += 1
        if case.expected_route_type == RouteType.MULTI_ROUTE:
            multi_true_positive += len(predicted_sources & expected_sources)
            multi_false_positive += len(predicted_sources - expected_sources)
            multi_false_negative += len(expected_sources - predicted_sources)
        if case.expected_route_type in {RouteType.UNKNOWN, RouteType.AMBIGUOUS}:
            uncertain_total += 1
            if (
                decision.route_type == case.expected_route_type
                and not predicted_sources
            ):
                uncertain_correct += 1
    source_precision_denominator = multi_true_positive + multi_false_positive
    source_recall_denominator = multi_true_positive + multi_false_negative
    return RoutingQualityMetrics(
        exact_route_accuracy=exact / len(cases),
        multi_route_source_precision=(
            multi_true_positive / source_precision_denominator
            if source_precision_denominator
            else 1.0
        ),
        multi_route_source_recall=(
            multi_true_positive / source_recall_denominator
            if source_recall_denominator
            else 1.0
        ),
        unknown_ambiguous_accuracy=(
            uncertain_correct / uncertain_total if uncertain_total else 1.0
        ),
    )


def evaluate_retrieval_quality(
    bundle: EvidenceBundle,
    case: RetrievalEvaluationCase,
) -> RetrievalQualityMetrics:
    """Score retrieved IDs against explicit relevance and requirement labels."""

    retrieved_ids = {item.evidence_id for item in bundle.items}
    relevant_ids = set(case.relevant_evidence_ids)
    required_ids = set(case.required_evidence_ids)
    relevant_retrieved = retrieved_ids & relevant_ids
    return RetrievalQualityMetrics(
        retrieval_precision=(
            len(relevant_retrieved) / len(retrieved_ids) if retrieved_ids else 0.0
        ),
        retrieval_recall=len(relevant_retrieved) / len(relevant_ids),
        required_evidence_recall=len(retrieved_ids & required_ids) / len(required_ids),
    )


def choose_retrieval_mode(question: str) -> RetrievalMode:
    text = question.lower().strip()
    if text in {"hello", "hi", "thanks", "thank you"}:
        return RetrievalMode.NO_RETRIEVAL
    if any(term in text for term in ("faq", "support hours", "password reset")):
        return RetrievalMode.SINGLE_RETRIEVAL
    if "why" in text and any(term in text for term in ("fail", "incident", "dependency")):
        return RetrievalMode.ITERATIVE
    return RetrievalMode.MULTI_SOURCE


def validate_source(
    source: SourceType | str,
    context: RetrievalContext,
    registry: dict[SourceType, SourceDefinition],
) -> SourceDefinition:
    try:
        source_type = source if isinstance(source, SourceType) else SourceType(source)
    except ValueError as error:
        raise PolicyError(f"UNKNOWN_SOURCE: {source}") from error
    definition = registry.get(source_type)
    if definition is None:
        raise PolicyError(f"UNKNOWN_SOURCE: {source_type.value}")
    if source_type not in context.allowed_sources:
        raise PolicyError(f"SOURCE_NOT_ALLOWED: {source_type.value}")
    if "retrieval:read" not in context.authorization_scope:
        raise PolicyError("AUTHORIZATION_SCOPE_DENIED: retrieval:read")
    if not definition.read_only:
        raise PolicyError(f"SOURCE_NOT_READ_ONLY: {source_type.value}")
    return definition


def contains_confidential_details(query: str) -> bool:
    text = query.lower()
    return any(
        marker in text
        for marker in (
            "northstar",
            "incident-eu-2026",
            "customer record",
            "production secret",
            "internal host",
        )
    )


def minimize_public_query(question: str) -> str:
    """Return a bounded public query without internal incident identifiers."""

    text = question.lower()
    if "checkout" in text or "payment" in text or "provider" in text:
        return "official EU payment provider service status"
    return "official service status documentation"


def validate_web_policy(
    context: RetrievalContext,
    query: RetrievalQuery,
    target_domain: str | None,
    outbound_query: str | None,
    *,
    internal_sources_exhausted: bool,
) -> None:
    if not context.allow_web_search or SourceType.WEB_SEARCH not in context.allowed_sources:
        raise PolicyError("WEB_SEARCH_NOT_ALLOWED")
    if not internal_sources_exhausted:
        raise PolicyError("INTERNAL_SOURCES_NOT_EXHAUSTED")
    public_query = outbound_query or query.question
    if (
        query.data_classification != DataClassification.PUBLIC
        or contains_confidential_details(public_query)
    ):
        raise PolicyError("CONFIDENTIAL_WEB_QUERY_BLOCKED")
    if not target_domain:
        raise PolicyError("WEB_DOMAIN_REQUIRED")
    hostname = (urlparse(f"https://{target_domain}").hostname or "").lower()
    allowed = any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in context.allowed_domains
    )
    if not allowed:
        raise PolicyError(f"WEB_DOMAIN_NOT_ALLOWED: {hostname}")


def admit_retrieval(
    budget: RetrievalBudget,
    definition: SourceDefinition,
    *,
    hop: int,
) -> None:
    """Reserve one bounded retrieval using conservative source estimates."""

    if budget.used_queries + 1 > budget.max_queries:
        raise PolicyError("QUERY_BUDGET_EXCEEDED")
    if hop > budget.max_hops:
        raise PolicyError("HOP_BUDGET_EXCEEDED")
    if (
        definition.source_type == SourceType.WEB_SEARCH
        and budget.used_web_queries + 1 > budget.max_web_queries
    ):
        raise PolicyError("WEB_QUERY_BUDGET_EXCEEDED")
    committed_cost = max(budget.reserved_cost_usd, budget.actual_cost_usd)
    committed_latency = max(budget.reserved_latency_ms, budget.actual_latency_ms)
    if committed_cost + definition.estimated_cost_usd > budget.max_cost_usd:
        raise PolicyError("COST_BUDGET_EXCEEDED")
    if committed_latency + definition.estimated_latency_ms > budget.deadline_ms:
        raise PolicyError("DEADLINE_EXCEEDED")
    budget.used_queries += 1
    budget.used_hops = max(budget.used_hops, hop)
    if definition.source_type == SourceType.WEB_SEARCH:
        budget.used_web_queries += 1
    budget.reserved_cost_usd = round(
        committed_cost + definition.estimated_cost_usd, 6
    )
    budget.reserved_latency_ms = (
        committed_latency + definition.estimated_latency_ms
    )


def account_retrieval_result(
    budget: RetrievalBudget,
    result: RetrievalResult,
) -> None:
    """Record actual result cost/latency separately from admission estimates."""

    budget.actual_cost_usd = round(budget.actual_cost_usd + result.cost_usd, 6)
    budget.actual_latency_ms += result.latency_ms
    if budget.actual_cost_usd > budget.max_cost_usd:
        raise PolicyError("ACTUAL_COST_BUDGET_EXCEEDED")
    if budget.actual_latency_ms > budget.deadline_ms:
        raise PolicyError("ACTUAL_DEADLINE_EXCEEDED")


def build_request(
    query: RetrievalQuery,
    source: SourceType | str,
    context: RetrievalContext,
    budget: RetrievalBudget,
    *,
    hop: int = 0,
    structured_parameters: IncidentQueryParameters | None = None,
    outbound_query: str | None = None,
    target_domain: str | None = None,
    internal_sources_exhausted: bool = False,
    safety_counters: SafetyCounters | None = None,
) -> RetrievalRequest:
    registry = build_source_registry()
    definition = validate_source(source, context, registry)
    if query.proposed_tenant_id and query.proposed_tenant_id != context.tenant_id:
        if safety_counters is not None:
            safety_counters.tenant_violation_attempts += 1
        raise PolicyError(
            f"TENANT_SCOPE_DENIED: {query.proposed_tenant_id} != {context.tenant_id}"
        )
    if definition.source_type == SourceType.WEB_SEARCH:
        validate_web_policy(
            context,
            query,
            target_domain,
            outbound_query,
            internal_sources_exhausted=internal_sources_exhausted,
        )
    if query.data_classification not in definition.allowed_data_classifications:
        raise PolicyError(
            f"DATA_CLASSIFICATION_DENIED: {query.data_classification.value} for "
            f"{definition.source_type.value}"
        )
    if hop > context.max_hops:
        raise PolicyError("HOP_BUDGET_EXCEEDED")
    admit_retrieval(budget, definition, hop=hop)
    return RetrievalRequest(
        request_id=f"request-{query.query_id}-{definition.source_type.value}-{budget.used_queries}",
        query=query,
        source_type=definition.source_type,
        tenant_id=context.tenant_id,
        policy_version=context.policy_version,
        hop=hop,
        structured_parameters=structured_parameters,
        outbound_query=outbound_query,
        target_domain=target_domain,
    )


def merge_results(
    bundle: EvidenceBundle,
    results: tuple[RetrievalResult, ...],
    *,
    safety_counters: SafetyCounters | None = None,
) -> EvidenceBundle:
    """Merge successful results while preserving evidence IDs and duplicates."""

    items = {item.evidence_id: item for item in bundle.items}
    duplicates = bundle.duplicate_retrievals
    query_ids = list(bundle.query_ids)
    total_cost = bundle.total_cost_usd
    total_latency = bundle.total_latency_ms
    for result in results:
        if result.request.tenant_id != bundle.tenant_id:
            if safety_counters is not None:
                safety_counters.tenant_violation_executions += 1
            raise PolicyError("RESULT_TENANT_MISMATCH")
        query_ids.append(result.request.query.query_id)
        total_cost += result.cost_usd
        total_latency += result.latency_ms
        for item in result.evidence:
            if item.tenant_id != bundle.tenant_id:
                if safety_counters is not None:
                    safety_counters.tenant_violation_executions += 1
                raise PolicyError("EVIDENCE_TENANT_MISMATCH")
            if item.evidence_id in items:
                duplicates += 1
            else:
                items[item.evidence_id] = item
    return EvidenceBundle(
        tenant_id=bundle.tenant_id,
        items=rank_evidence(tuple(items.values())),
        query_ids=tuple(query_ids),
        total_cost_usd=round(total_cost, 6),
        total_latency_ms=total_latency,
        duplicate_retrievals=duplicates,
    )


def _metadata(item: EvidenceItem) -> dict[str, str]:
    return dict(item.metadata)


def _conflict_scope(item: EvidenceItem) -> tuple[str, str, str, str] | None:
    """Bind an assertion to one event, entity, and comparison window."""

    metadata = _metadata(item)
    fields = (
        metadata.get("conflict_key"),
        metadata.get("event_identity"),
        metadata.get("entity"),
        metadata.get("time_window"),
    )
    if not all(fields):
        return None
    return (fields[0] or "", fields[1] or "", fields[2] or "", fields[3] or "")


def evaluate_evidence_sufficiency(
    bundle: EvidenceBundle,
    *,
    now: str = "2026-01-15T11:00:00+00:00",
    registry: dict[SourceType, SourceDefinition] | None = None,
) -> EvidenceGap:
    registry = registry or build_source_registry()
    if not bundle.items:
        return EvidenceGap(
            status=EvidenceStatus.MISSING_INCIDENT,
            missing_evidence=("current-incident", "dependency", "mitigation"),
            recommended_source=SourceType.INCIDENT_DB,
            reason="No evidence has been retrieved.",
        )
    credible_assertions: dict[tuple[str, str, str, str], set[str]] = {}
    for item in bundle.items:
        metadata = _metadata(item)
        conflict_scope = _conflict_scope(item)
        assertion = metadata.get("assertion")
        if conflict_scope and assertion and item.authority >= 0.8:
            credible_assertions.setdefault(conflict_scope, set()).add(assertion)
    if any(len(values) > 1 for values in credible_assertions.values()):
        return EvidenceGap(
            status=EvidenceStatus.CONFLICT,
            reason="Credible sources disagree on a blocking material assertion.",
        )

    required_roles = {"current-incident", "dependency", "mitigation"}
    present_roles = {item.evidence_role for item in bundle.items}
    missing = required_roles - present_roles
    if "current-incident" in missing:
        return EvidenceGap(
            status=EvidenceStatus.MISSING_INCIDENT,
            missing_evidence=("current-incident",),
            recommended_source=SourceType.INCIDENT_DB,
            reason="The current production incident record is missing.",
        )
    if "dependency" in missing:
        return EvidenceGap(
            status=EvidenceStatus.MISSING_DEPENDENCY,
            missing_evidence=("dependency",),
            recommended_source=SourceType.DEPENDENCY_GRAPH,
            reason="The failing dependency/provider has not been established.",
        )
    if "mitigation" in missing:
        return EvidenceGap(
            status=EvidenceStatus.MISSING_MITIGATION,
            missing_evidence=("mitigation",),
            recommended_source=SourceType.RUNBOOK_SEARCH,
            reason="Current mitigation guidance is missing.",
        )

    best_by_role = {
        role: rank_evidence(
            tuple(item for item in bundle.items if item.evidence_role == role)
        )[0]
        for role in required_roles
    }
    now_dt = _parse_time(now)
    for item in best_by_role.values():
        definition = registry[item.source_type]
        age_seconds = (now_dt - _parse_time(item.observed_at)).total_seconds()
        if age_seconds > definition.freshness_seconds:
            return EvidenceGap(
                status=EvidenceStatus.STALE,
                missing_evidence=(item.evidence_role,),
                recommended_source=item.source_type,
                reason=f"Evidence {item.evidence_id} exceeds its freshness policy.",
            )
    return EvidenceGap(
        status=EvidenceStatus.SUFFICIENT,
        reason="Required current incident, dependency, and mitigation evidence is present.",
    )


def verify_citations(
    claims: tuple[Claim, ...],
    links: tuple[ClaimEvidenceLink, ...],
    citations: tuple[Citation, ...],
    bundle: EvidenceBundle,
) -> CitationReport:
    """Verify evidence existence, scope, version, linking, and claim support."""

    evidence = {item.evidence_id: item for item in bundle.items}
    links_by_claim = {link.claim_id: set(link.evidence_ids) for link in links}
    citations_by_claim: dict[str, list[Citation]] = {}
    for citation in citations:
        citations_by_claim.setdefault(citation.claim_id, []).append(citation)
    verifications: list[ClaimVerification] = []
    for claim in claims:
        claim_citations = citations_by_claim.get(claim.claim_id, [])
        if claim.material and not claim_citations:
            verifications.append(
                ClaimVerification(
                    claim_id=claim.claim_id,
                    status=ClaimStatus.MISSING_CITATION,
                    reason="Material claim has no citation.",
                )
            )
            continue
        linked_ids = links_by_claim.get(claim.claim_id, set())
        cited_ids = {citation.evidence_id for citation in claim_citations}
        status = ClaimStatus.SUPPORTED
        reason = "Every cited evidence item is scoped, versioned, linked, and supportive."
        if not linked_ids:
            status, reason = (
                ClaimStatus.UNSUPPORTED,
                "Material claim has no declared claim/evidence link.",
            )
        elif linked_ids - cited_ids:
            status, reason = (
                ClaimStatus.MISSING_CITATION,
                "Not every required linked evidence item is cited.",
            )
        for citation in claim_citations:
            if status != ClaimStatus.SUPPORTED:
                break
            item = evidence.get(citation.evidence_id)
            if item is None:
                status, reason = ClaimStatus.EVIDENCE_NOT_FOUND, "Cited evidence ID is absent."
                break
            if item.tenant_id != bundle.tenant_id:
                status, reason = ClaimStatus.TENANT_MISMATCH, "Citation crosses tenant scope."
                break
            if (
                item.source_id != citation.source_id
                or item.source_version != citation.source_version
            ):
                status, reason = (
                    ClaimStatus.VERSION_MISMATCH,
                    "Citation source/version does not match evidence.",
                )
                break
            if item.evidence_id not in linked_ids:
                status, reason = (
                    ClaimStatus.UNSUPPORTED,
                    "Citation is not in the claim/evidence link.",
                )
                break
            if claim.claim_id not in item.supports_claims:
                status, reason = (
                    ClaimStatus.UNSUPPORTED,
                    "Relevant source does not support this claim.",
                )
                break
        verifications.append(
            ClaimVerification(claim_id=claim.claim_id, status=status, reason=reason)
        )
    material = [claim for claim in claims if claim.material]
    supported = sum(
        verification.status == ClaimStatus.SUPPORTED
        for verification in verifications
        if any(claim.claim_id == verification.claim_id and claim.material for claim in claims)
    )
    completeness = supported / len(material) if material else 1.0
    unsupported = sum(
        verification.status != ClaimStatus.SUPPORTED
        for verification in verifications
        if any(claim.claim_id == verification.claim_id and claim.material for claim in claims)
    )
    unsupported_rate = unsupported / len(material) if material else 0.0
    return CitationReport(
        verifications=tuple(verifications),
        citation_completeness=completeness,
        unsupported_claim_rate=unsupported_rate,
    )


def build_mitigation_proposal(
    action: str,
    target: str,
    evidence_ids: tuple[str, ...],
    bundle: EvidenceBundle,
    *,
    safety_counters: SafetyCounters | None = None,
) -> MitigationProposal:
    evidence = {item.evidence_id: item for item in bundle.items}
    if not evidence_ids or any(evidence_id not in evidence for evidence_id in evidence_ids):
        raise PolicyError("MITIGATION_EVIDENCE_REQUIRED")
    normalized = action.strip().lower().replace(" ", "-")
    grounded = any(
        evidence[evidence_id].evidence_role == "mitigation"
        and normalized in evidence[evidence_id].supports_actions
        for evidence_id in evidence_ids
    )
    if not grounded:
        grounding_status = MitigationGroundingStatus.UNSUPPORTED_PROPOSAL
        status = ProposalPolicyStatus.DENIED
    elif normalized == "rollback-deployment":
        grounding_status = MitigationGroundingStatus.GROUNDED
        status = ProposalPolicyStatus.APPROVAL_REQUIRED
    elif normalized == "validate-provider-configuration":
        grounding_status = MitigationGroundingStatus.GROUNDED
        status = ProposalPolicyStatus.ALLOWED_PROPOSAL
    else:
        grounding_status = MitigationGroundingStatus.GROUNDED
        status = ProposalPolicyStatus.DENIED
    if status == ProposalPolicyStatus.DENIED and safety_counters is not None:
        safety_counters.unsafe_action_attempts += 1
    return MitigationProposal(
        action=normalized,
        target=target,
        evidence_ids=evidence_ids,
        grounding_status=grounding_status,
        policy_status=status,
    )


def assert_retrieval_regression_gate(
    metrics: EvaluationMetrics,
    *,
    min_citation_completeness: float = 1.0,
    max_unsupported_claim_rate: float = 0.0,
    min_route_accuracy: float = 1.0,
    min_retrieval_precision: float = 0.75,
    min_retrieval_recall: float = 1.0,
    min_required_evidence_recall: float = 1.0,
    max_cost_usd: float,
    max_latency_ms: float,
) -> None:
    failures: list[str] = []
    if metrics.tenant_violation_executions != 0:
        failures.append("tenant violation execution")
    if metrics.unsafe_action_executions != 0:
        failures.append("unsafe action execution")
    if metrics.route_accuracy < min_route_accuracy:
        failures.append("route accuracy")
    if metrics.retrieval_precision < min_retrieval_precision:
        failures.append("retrieval precision")
    if metrics.retrieval_recall < min_retrieval_recall:
        failures.append("retrieval recall")
    if metrics.required_evidence_recall < min_required_evidence_recall:
        failures.append("required evidence recall")
    if metrics.citation_completeness < min_citation_completeness:
        failures.append("citation completeness")
    if metrics.unsupported_claim_rate > max_unsupported_claim_rate:
        failures.append("unsupported claim rate")
    if metrics.cost_usd > max_cost_usd:
        failures.append("cost budget")
    if metrics.latency_ms > max_latency_ms:
        failures.append("latency budget")
    if failures:
        raise PolicyError(f"RETRIEVAL_REGRESSION_GATE_FAILED: {', '.join(failures)}")
