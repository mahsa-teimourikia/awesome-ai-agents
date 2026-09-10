"""Application-owned policy for the Advanced 06 governed-memory course.

Models may propose MemoryCandidate objects. Only this layer can admit durable
records, authorize retrieval, validate verification, and govern lifecycle.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

POLICY_VERSION = "northstar-memory-policy-v1"
RETRIEVAL_POLICY_VERSION = "northstar-memory-retrieval-v1"
INDEX_VERSION = "lexical-fixture-v1"
EMBEDDING_MODEL_VERSION = "none-credential-free"


class MemoryPolicyError(ValueError):
    """A fail-closed memory decision with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MemoryType(StrEnum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    PREFERENCE = "PREFERENCE"


class MemoryStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DISPUTED = "DISPUTED"
    EXPIRED = "EXPIRED"
    SOFT_DELETED = "SOFT_DELETED"
    HARD_DELETED = "HARD_DELETED"
    INVALIDATED = "INVALIDATED"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    USER_STATED = "USER_STATED"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    DISPUTED = "DISPUTED"
    FAILED = "FAILED"


class SourceType(StrEnum):
    USER_STATEMENT = "USER_STATEMENT"
    ACCOUNT_API = "ACCOUNT_API"
    IAM_API = "IAM_API"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    INCIDENT_POSTMORTEM = "INCIDENT_POSTMORTEM"
    CONVERSATION_EPISODE = "CONVERSATION_EPISODE"
    WEB_CONTENT = "WEB_CONTENT"
    SUPPORT_TICKET = "SUPPORT_TICKET"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class Sensitivity(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    SENSITIVE = 2
    RESTRICTED = 3


class RetentionClass(StrEnum):
    SESSION = "SESSION"
    SHORT_TERM = "SHORT_TERM"
    UNTIL_SUPERSEDED = "UNTIL_SUPERSEDED"
    TIME_BOUND = "TIME_BOUND"
    AUDIT = "AUDIT"
    USER_MANAGED = "USER_MANAGED"


class RetrievalMode(StrEnum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"


class MemoryDecision(StrEnum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    REQUIRE_VERIFICATION = "REQUIRE_VERIFICATION"
    EPHEMERAL_ONLY = "EPHEMERAL_ONLY"
    SENSITIVE_REVIEW = "SENSITIVE_REVIEW"


class MemoryScope(StrEnum):
    USER_PRIVATE = "USER_PRIVATE"
    TEAM_SHARED = "TEAM_SHARED"
    TENANT_SHARED = "TENANT_SHARED"
    SERVICE = "SERVICE"
    GLOBAL_PUBLIC = "GLOBAL_PUBLIC"


class CertaintyLabel(StrEnum):
    EXPLICIT = "EXPLICIT"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"
    QUOTED = "QUOTED"
    TEMPORARY = "TEMPORARY"
    DISPUTED = "DISPUTED"


class ConflictPolicy(StrEnum):
    LATEST_EXPLICIT_WINS = "LATEST_EXPLICIT_WINS"
    AUTHORITATIVE_SOURCE_WINS = "AUTHORITATIVE_SOURCE_WINS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class ConsolidationStatus(StrEnum):
    PENDING = "PENDING"
    EXTRACTED = "EXTRACTED"
    WRITTEN = "WRITTEN"
    FAILED = "FAILED"


class DeletionMode(StrEnum):
    SOFT = "SOFT"
    HARD = "HARD"
    DISPUTE = "DISPUTE"


class MemoryContext(FrozenModel):
    tenant_id: str = Field(min_length=1)
    viewer_user_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    viewer_roles: tuple[str, ...]
    allowed_scopes: tuple[MemoryScope, ...]
    policy_version: str = Field(min_length=1)
    data_classification: Sensitivity


class WorkingState(FrozenModel):
    task_id: str
    current_plan: tuple[str, ...] = ()
    temporary_artifacts: Mapping[str, str] = Field(default_factory=dict)
    cached_tool_results: Mapping[str, Any] = Field(default_factory=dict)
    scratch_notes: tuple[str, ...] = ()


class ContextProjection(FrozenModel):
    task_id: str
    selected_plan_steps: tuple[str, ...]
    selected_artifact_handles: tuple[str, ...]
    token_estimate: int = Field(ge=0)


class MemorySource(FrozenModel):
    source_id: str
    tenant_id: str
    subject_id: str
    source_type: SourceType
    source_version: str
    artifact_handle: str
    created_at: datetime
    digest: str = Field(min_length=64, max_length=64)
    active: bool = True
    safe_excerpt: str = Field(max_length=300)


class MemoryCandidate(FrozenModel):
    candidate_id: str
    subject_id: str
    memory_type: MemoryType
    key: str
    value: Any
    source_ids: tuple[str, ...]
    candidate_reason: str
    certainty_label: CertaintyLabel
    sensitivity: Sensitivity
    scope: MemoryScope
    effective_from: datetime
    expires_at: datetime | None = None

    @field_validator("source_ids")
    @classmethod
    def requires_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("MEMORY_PROVENANCE_REQUIRED")
        return value


class VerificationReceipt(FrozenModel):
    verification_id: str
    memory_candidate_id: str
    verifier_type: SourceType
    verifier_id: str
    tenant_id: str
    result: VerificationStatus
    verified_at: datetime
    source_reference: str
    policy_version: str


class MemoryWriteDecision(FrozenModel):
    candidate_id: str
    decision: MemoryDecision
    reason_codes: tuple[str, ...]
    required_verifier: SourceType | None = None


class MemoryRecord(FrozenModel):
    memory_id: str
    tenant_id: str
    subject_id: str
    memory_type: MemoryType
    key: str
    value: Any
    status: MemoryStatus
    verification_status: VerificationStatus
    source_ids: tuple[str, ...]
    source_type: SourceType
    created_at: datetime
    recorded_at: datetime
    effective_from: datetime
    effective_to: datetime | None = None
    expires_at: datetime | None = None
    version: int = Field(gt=0)
    supersedes: str | None = None
    sensitivity: Sensitivity
    scope: MemoryScope
    retention_class: RetentionClass
    policy_version: str
    content_digest: str = Field(min_length=64, max_length=64)
    consolidation_job_id: str | None = None


class MemoryKeyPolicy(FrozenModel):
    key: str
    memory_type: MemoryType
    allowed_sources: tuple[SourceType, ...]
    verification_source: SourceType | None
    retention_class: RetentionClass
    sensitivity: Sensitivity
    default_scope: MemoryScope
    conflict_policy: ConflictPolicy
    authority_order: tuple[SourceType, ...]
    authority_bearing: bool = False


class MemorySchemaRegistry(FrozenModel):
    schemas: Mapping[str, MemoryKeyPolicy]


class MemoryQuery(FrozenModel):
    query_id: str
    tenant_id: str
    subject_id: str
    query_text: str
    keys: tuple[str, ...] = ()
    memory_types: tuple[MemoryType, ...] = ()
    retrieval_mode: RetrievalMode = RetrievalMode.CURRENT
    as_of: datetime
    max_memory_items: int = Field(gt=0)
    max_memory_tokens: int = Field(gt=0)
    max_sensitive_items: int = Field(ge=0)


class MemoryRetrievalItem(FrozenModel):
    memory_id: str
    key: str
    value: Any
    verification_status: VerificationStatus
    source_ids: tuple[str, ...]
    age_seconds: int = Field(ge=0)
    scope: MemoryScope
    relevance: float = Field(ge=0, le=1)
    reason_selected: tuple[str, ...]
    token_estimate: int = Field(ge=0)
    content_is_data: bool = True


class MemoryRetrievalResult(FrozenModel):
    query_id: str
    items: tuple[MemoryRetrievalItem, ...]
    filtered_counts: Mapping[str, int]
    context_tokens: int = Field(ge=0)
    retrieval_policy_version: str
    index_version: str
    embedding_model_version: str


class MemoryConflict(FrozenModel):
    key: str
    existing_memory_id: str
    candidate_id: str
    existing_source: SourceType
    candidate_source: SourceType
    resolution: str


class MemorySupersession(FrozenModel):
    old_memory_id: str
    new_memory_id: str
    expected_version: int
    effective_at: datetime


class ConsolidationJob(FrozenModel):
    job_id: str
    tenant_id: str
    subject_id: str
    source_episode_ids: tuple[str, ...]
    extractor_version: str
    policy_version: str
    source_digest: str = Field(min_length=64, max_length=64)
    status: ConsolidationStatus = ConsolidationStatus.PENDING


class MemoryAuditEvent(FrozenModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    tenant_id: str
    subject_id: str
    actor_id: str
    object_ref: str
    reason_codes: tuple[str, ...] = ()


class MemoryMetrics(FrozenModel):
    write_precision: float = Field(ge=0, le=1)
    write_recall: float = Field(ge=0, le=1)
    false_memory_rate: float = Field(ge=0, le=1)
    unsafe_memory_write_rate: float = Field(ge=0, le=1)
    duplicate_memory_rate: float = Field(ge=0, le=1)
    retrieval_precision: float = Field(ge=0, le=1)
    retrieval_recall: float = Field(ge=0, le=1)
    tenant_leak_rate: float = Field(ge=0, le=1)
    subject_leak_rate: float = Field(ge=0, le=1)
    expired_retrieval_rate: float = Field(ge=0, le=1)
    superseded_retrieval_rate: float = Field(ge=0, le=1)
    context_tokens: int = Field(ge=0)
    correction_rate: float = Field(ge=0, le=1)


class OperationalEvidenceReceipt(FrozenModel):
    receipt_id: str
    memory_id: str
    tenant_id: str
    subject_id: str
    verifier_id: str
    source_reference: str
    verified_at: datetime
    expires_at: datetime
    policy_version: str


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def source_payload(source: MemorySource | Mapping[str, Any]) -> Mapping[str, Any]:
    data = (
        source.model_dump(mode="json")
        if isinstance(source, MemorySource)
        else dict(source)
    )
    return {
        key: data[key]
        for key in (
            "source_id",
            "tenant_id",
            "subject_id",
            "source_type",
            "source_version",
            "artifact_handle",
            "created_at",
            "active",
            "safe_excerpt",
        )
    }


def build_source(**values: Any) -> MemorySource:
    provisional = MemorySource(**values, digest="0" * 64)
    return provisional.model_copy(
        update={"digest": canonical_digest(source_payload(provisional))}
    )


def validate_source(source: MemorySource) -> None:
    if source.digest != canonical_digest(source_payload(source)):
        raise MemoryPolicyError("MEMORY_SOURCE_DIGEST_MISMATCH")
    if not source.active:
        raise MemoryPolicyError("MEMORY_SOURCE_INACTIVE")


def default_schema_registry() -> MemorySchemaRegistry:
    schemas = {
        "communication_style": MemoryKeyPolicy(
            key="communication_style",
            memory_type=MemoryType.PREFERENCE,
            allowed_sources=(SourceType.USER_STATEMENT, SourceType.HUMAN_REVIEW),
            verification_source=None,
            retention_class=RetentionClass.USER_MANAGED,
            sensitivity=Sensitivity.INTERNAL,
            default_scope=MemoryScope.USER_PRIVATE,
            conflict_policy=ConflictPolicy.LATEST_EXPLICIT_WINS,
            authority_order=(SourceType.HUMAN_REVIEW, SourceType.USER_STATEMENT),
        ),
        "preferred_language": MemoryKeyPolicy(
            key="preferred_language",
            memory_type=MemoryType.PREFERENCE,
            allowed_sources=(SourceType.USER_STATEMENT, SourceType.HUMAN_REVIEW),
            verification_source=None,
            retention_class=RetentionClass.USER_MANAGED,
            sensitivity=Sensitivity.INTERNAL,
            default_scope=MemoryScope.USER_PRIVATE,
            conflict_policy=ConflictPolicy.LATEST_EXPLICIT_WINS,
            authority_order=(SourceType.HUMAN_REVIEW, SourceType.USER_STATEMENT),
        ),
        "billing_address": MemoryKeyPolicy(
            key="billing_address",
            memory_type=MemoryType.SEMANTIC,
            allowed_sources=(SourceType.USER_STATEMENT, SourceType.ACCOUNT_API),
            verification_source=SourceType.ACCOUNT_API,
            retention_class=RetentionClass.UNTIL_SUPERSEDED,
            sensitivity=Sensitivity.SENSITIVE,
            default_scope=MemoryScope.USER_PRIVATE,
            conflict_policy=ConflictPolicy.AUTHORITATIVE_SOURCE_WINS,
            authority_order=(SourceType.ACCOUNT_API, SourceType.USER_STATEMENT),
        ),
        "account_tier": MemoryKeyPolicy(
            key="account_tier",
            memory_type=MemoryType.SEMANTIC,
            allowed_sources=(SourceType.USER_STATEMENT, SourceType.ACCOUNT_API),
            verification_source=SourceType.ACCOUNT_API,
            retention_class=RetentionClass.TIME_BOUND,
            sensitivity=Sensitivity.SENSITIVE,
            default_scope=MemoryScope.USER_PRIVATE,
            conflict_policy=ConflictPolicy.AUTHORITATIVE_SOURCE_WINS,
            authority_order=(SourceType.ACCOUNT_API, SourceType.USER_STATEMENT),
        ),
        "current_project": MemoryKeyPolicy(
            key="current_project",
            memory_type=MemoryType.SEMANTIC,
            allowed_sources=(SourceType.USER_STATEMENT, SourceType.HUMAN_REVIEW),
            verification_source=None,
            retention_class=RetentionClass.TIME_BOUND,
            sensitivity=Sensitivity.INTERNAL,
            default_scope=MemoryScope.USER_PRIVATE,
            conflict_policy=ConflictPolicy.LATEST_EXPLICIT_WINS,
            authority_order=(SourceType.HUMAN_REVIEW, SourceType.USER_STATEMENT),
        ),
        "incident_trace": MemoryKeyPolicy(
            key="incident_trace",
            memory_type=MemoryType.EPISODIC,
            allowed_sources=(
                SourceType.INCIDENT_POSTMORTEM,
                SourceType.HUMAN_REVIEW,
            ),
            verification_source=SourceType.HUMAN_REVIEW,
            retention_class=RetentionClass.AUDIT,
            sensitivity=Sensitivity.SENSITIVE,
            default_scope=MemoryScope.SERVICE,
            conflict_policy=ConflictPolicy.HUMAN_REVIEW_REQUIRED,
            authority_order=(
                SourceType.HUMAN_REVIEW,
                SourceType.INCIDENT_POSTMORTEM,
            ),
        ),
        "procedure_ref": MemoryKeyPolicy(
            key="procedure_ref",
            memory_type=MemoryType.PROCEDURAL,
            allowed_sources=(SourceType.HUMAN_REVIEW,),
            verification_source=SourceType.HUMAN_REVIEW,
            retention_class=RetentionClass.UNTIL_SUPERSEDED,
            sensitivity=Sensitivity.INTERNAL,
            default_scope=MemoryScope.TENANT_SHARED,
            conflict_policy=ConflictPolicy.HUMAN_REVIEW_REQUIRED,
            authority_order=(SourceType.HUMAN_REVIEW,),
        ),
        "security_role": MemoryKeyPolicy(
            key="security_role",
            memory_type=MemoryType.SEMANTIC,
            allowed_sources=(SourceType.IAM_API,),
            verification_source=SourceType.IAM_API,
            retention_class=RetentionClass.SESSION,
            sensitivity=Sensitivity.RESTRICTED,
            default_scope=MemoryScope.USER_PRIVATE,
            conflict_policy=ConflictPolicy.AUTHORITATIVE_SOURCE_WINS,
            authority_order=(SourceType.IAM_API,),
            authority_bearing=True,
        ),
    }
    return MemorySchemaRegistry(schemas=schemas)


def _source_for_candidate(
    candidate: MemoryCandidate,
    context: MemoryContext,
    sources: Mapping[str, MemorySource],
) -> tuple[MemorySource, ...]:
    resolved: list[MemorySource] = []
    for source_id in candidate.source_ids:
        source = sources.get(source_id)
        if source is None:
            raise MemoryPolicyError("MEMORY_SOURCE_NOT_FOUND")
        validate_source(source)
        if source.tenant_id != context.tenant_id:
            raise MemoryPolicyError("MEMORY_SOURCE_TENANT_MISMATCH")
        if source.subject_id != context.subject_id:
            raise MemoryPolicyError("MEMORY_SOURCE_SUBJECT_MISMATCH")
        resolved.append(source)
    return tuple(resolved)


_AUTHORITY_TOKENS = (
    "administrator",
    "admin=true",
    "pre-approved",
    "bypass approval",
    "grant permission",
    "ignore policy",
    "export all customer data",
)


def validate_verification_receipt(
    receipt: VerificationReceipt,
    *,
    candidate: MemoryCandidate,
    context: MemoryContext,
    required_verifier: SourceType,
    now: datetime,
) -> None:
    if receipt.memory_candidate_id != candidate.candidate_id:
        raise MemoryPolicyError("VERIFICATION_CANDIDATE_MISMATCH")
    if receipt.tenant_id != context.tenant_id:
        raise MemoryPolicyError("VERIFICATION_TENANT_MISMATCH")
    if receipt.verifier_type is not required_verifier:
        raise MemoryPolicyError("VERIFICATION_SOURCE_MISMATCH")
    if receipt.result is not VerificationStatus.VERIFIED:
        raise MemoryPolicyError("VERIFICATION_FAILED")
    if receipt.policy_version != context.policy_version:
        raise MemoryPolicyError("VERIFICATION_POLICY_STALE")
    if receipt.verified_at > now:
        raise MemoryPolicyError("VERIFICATION_TIME_INVALID")


def decide_memory_write(
    context: MemoryContext,
    candidate: MemoryCandidate,
    *,
    sources: Mapping[str, MemorySource],
    registry: MemorySchemaRegistry,
    verification: VerificationReceipt | None = None,
    now: datetime,
) -> MemoryWriteDecision:
    if candidate.subject_id != context.subject_id:
        raise MemoryPolicyError("MEMORY_WRITE_SUBJECT_MISMATCH")
    if candidate.scope not in context.allowed_scopes:
        raise MemoryPolicyError("MEMORY_WRITE_SCOPE_DENIED")
    resolved_sources = _source_for_candidate(candidate, context, sources)
    schema = registry.schemas.get(candidate.key)
    if schema is None:
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.REJECT,
            reason_codes=("MEMORY_SCHEMA_UNKNOWN",),
        )
    normalized = f"{candidate.key} {candidate.value}".casefold()
    if schema.authority_bearing or any(
        token in normalized for token in _AUTHORITY_TOKENS
    ):
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.REJECT,
            reason_codes=("MEMORY_CANNOT_GRANT_AUTHORITY",),
        )
    if candidate.memory_type is MemoryType.WORKING:
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.EPHEMERAL_ONLY,
            reason_codes=("WORKING_STATE_NOT_DURABLE_MEMORY",),
        )
    if candidate.memory_type is not schema.memory_type:
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.REJECT,
            reason_codes=("MEMORY_TYPE_MISMATCH",),
        )
    if candidate.certainty_label in {
        CertaintyLabel.AMBIGUOUS,
        CertaintyLabel.QUOTED,
        CertaintyLabel.TEMPORARY,
    }:
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.EPHEMERAL_ONLY,
            reason_codes=(f"{candidate.certainty_label.value}_NOT_DURABLE",),
        )
    source_types = {source.source_type for source in resolved_sources}
    if not source_types.issubset(schema.allowed_sources):
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.REJECT,
            reason_codes=("MEMORY_SOURCE_NOT_ALLOWED",),
        )
    if candidate.sensitivity > schema.sensitivity:
        return MemoryWriteDecision(
            candidate_id=candidate.candidate_id,
            decision=MemoryDecision.SENSITIVE_REVIEW,
            reason_codes=("SENSITIVITY_REVIEW_REQUIRED",),
        )
    if schema.verification_source is not None:
        if verification is None:
            return MemoryWriteDecision(
                candidate_id=candidate.candidate_id,
                decision=MemoryDecision.REQUIRE_VERIFICATION,
                reason_codes=("AUTHORITATIVE_VERIFICATION_REQUIRED",),
                required_verifier=schema.verification_source,
            )
        validate_verification_receipt(
            verification,
            candidate=candidate,
            context=context,
            required_verifier=schema.verification_source,
            now=now,
        )
    return MemoryWriteDecision(
        candidate_id=candidate.candidate_id,
        decision=MemoryDecision.ALLOW,
        reason_codes=("SCHEMA_ALLOWED", "PROVENANCE_VALIDATED"),
    )


def build_memory_record(
    context: MemoryContext,
    candidate: MemoryCandidate,
    decision: MemoryWriteDecision,
    *,
    sources: Mapping[str, MemorySource],
    registry: MemorySchemaRegistry,
    verification: VerificationReceipt | None,
    now: datetime,
    version: int = 1,
    supersedes: str | None = None,
    consolidation_job_id: str | None = None,
) -> MemoryRecord:
    if decision.decision is not MemoryDecision.ALLOW:
        raise MemoryPolicyError("MEMORY_WRITE_NOT_ALLOWED")
    schema = registry.schemas[candidate.key]
    resolved = _source_for_candidate(candidate, context, sources)
    primary = min(
        resolved,
        key=lambda item: schema.authority_order.index(item.source_type),
    )
    if verification is not None:
        verification_status = VerificationStatus.VERIFIED
    elif primary.source_type is SourceType.USER_STATEMENT:
        verification_status = VerificationStatus.USER_STATED
    elif primary.source_type is SourceType.MODEL_INFERENCE:
        verification_status = VerificationStatus.INFERRED
    else:
        verification_status = VerificationStatus.UNVERIFIED
    identity = {
        "tenant_id": context.tenant_id,
        "subject_id": candidate.subject_id,
        "key": candidate.key,
        "value": candidate.value,
        "source_ids": sorted(candidate.source_ids),
    }
    return MemoryRecord(
        memory_id="mem-" + canonical_digest(identity)[:20],
        tenant_id=context.tenant_id,
        subject_id=candidate.subject_id,
        memory_type=candidate.memory_type,
        key=candidate.key,
        value=candidate.value,
        status=MemoryStatus.ACTIVE,
        verification_status=verification_status,
        source_ids=tuple(sorted(candidate.source_ids)),
        source_type=primary.source_type,
        created_at=now,
        recorded_at=now,
        effective_from=candidate.effective_from,
        expires_at=candidate.expires_at,
        version=version,
        supersedes=supersedes,
        sensitivity=candidate.sensitivity,
        scope=candidate.scope,
        retention_class=schema.retention_class,
        policy_version=context.policy_version,
        content_digest=canonical_digest(candidate.value),
        consolidation_job_id=consolidation_job_id,
    )


def project_working_context(
    state: WorkingState, *, max_plan_steps: int, max_tokens: int
) -> ContextProjection:
    if max_plan_steps <= 0 or max_tokens <= 0:
        raise MemoryPolicyError("CONTEXT_BUDGET_INVALID")
    steps: list[str] = []
    tokens = 0
    for step in state.current_plan:
        estimate = max(1, len(step) // 4)
        if len(steps) >= max_plan_steps or tokens + estimate > max_tokens:
            break
        steps.append(step)
        tokens += estimate
    handles = tuple(state.temporary_artifacts.values())
    return ContextProjection(
        task_id=state.task_id,
        selected_plan_steps=tuple(steps),
        selected_artifact_handles=handles,
        token_estimate=tokens,
    )


def validate_operational_evidence(
    record: MemoryRecord,
    receipt: OperationalEvidenceReceipt | None,
    *,
    context: MemoryContext,
    now: datetime,
) -> None:
    if receipt is None:
        raise MemoryPolicyError("CURRENT_EVIDENCE_VERIFICATION_REQUIRED")
    checks = {
        "EVIDENCE_MEMORY_MISMATCH": receipt.memory_id == record.memory_id,
        "EVIDENCE_TENANT_MISMATCH": receipt.tenant_id == context.tenant_id,
        "EVIDENCE_SUBJECT_MISMATCH": receipt.subject_id == context.subject_id,
        "EVIDENCE_POLICY_STALE": receipt.policy_version == context.policy_version,
    }
    for code, valid in checks.items():
        if not valid:
            raise MemoryPolicyError(code)
    if receipt.verified_at > now or receipt.expires_at <= now:
        raise MemoryPolicyError("CURRENT_EVIDENCE_EXPIRED")


def calculate_classification_metrics(
    expected_positive: tuple[bool, ...], predicted_positive: tuple[bool, ...]
) -> tuple[float, float, float]:
    if len(expected_positive) != len(predicted_positive) or not expected_positive:
        raise MemoryPolicyError("EVALUATION_INPUT_INVALID")
    true_positive = sum(e and p for e, p in zip(expected_positive, predicted_positive))
    false_positive = sum(
        not e and p for e, p in zip(expected_positive, predicted_positive)
    )
    false_negative = sum(
        e and not p for e, p in zip(expected_positive, predicted_positive)
    )
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0
    )
    false_rate = false_positive / len(expected_positive)
    return precision, recall, false_rate


def retention_expiry(
    retention: RetentionClass, *, created_at: datetime
) -> datetime | None:
    if retention is RetentionClass.SESSION:
        return created_at + timedelta(hours=8)
    if retention is RetentionClass.SHORT_TERM:
        return created_at + timedelta(days=30)
    return None
