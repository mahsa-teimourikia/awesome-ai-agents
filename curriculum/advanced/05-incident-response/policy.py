"""Application-owned controls for the Advanced 05 incident-response capstone.

Models may synthesize hypotheses, briefs, and proposals. This module owns trusted
incident identity, evidence admission, authorization, state transitions, and the
conditions under which an incident may become RESOLVED.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
import hashlib
import hmac
import json
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


POLICY_VERSION = "northstar-incident-policy-v1"
WEBHOOK_SECRET = "fixture-signing-secret"


class PolicyError(ValueError):
    """A fail-closed decision with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MutableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class IncidentStatus(StrEnum):
    TRIGGERED = "TRIGGERED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    IMPACT_ASSESSED = "IMPACT_ASSESSED"
    MITIGATION_PROPOSED = "MITIGATION_PROPOSED"
    WAITING_REVIEW = "WAITING_REVIEW"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    DEGRADED = "DEGRADED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"
    MANUAL_CONTROL = "MANUAL_CONTROL"


class IncidentSeverity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class EvidenceType(StrEnum):
    METRICS = "METRICS"
    LOGS = "LOGS"
    DEPLOYMENT = "DEPLOYMENT"
    TICKET_AGGREGATE = "TICKET_AGGREGATE"
    PROVIDER_STATUS = "PROVIDER_STATUS"
    RUNBOOK = "RUNBOOK"
    CUSTOMER_IMPACT = "CUSTOMER_IMPACT"
    SLA_CONTRACT = "SLA_CONTRACT"
    VERIFICATION = "VERIFICATION"


class EvidenceTrust(StrEnum):
    AUTHORITATIVE = "AUTHORITATIVE"
    CORROBORATING = "CORROBORATING"
    UNTRUSTED_CONTEXT = "UNTRUSTED_CONTEXT"


class EvidenceStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"


class HypothesisStatus(StrEnum):
    UNTESTED = "UNTESTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class MitigationRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MitigationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    REVIEW_PASS = "REVIEW_PASS"
    REVIEW_FAIL = "REVIEW_FAIL"
    NEEDS_REVISION = "NEEDS_REVISION"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RECONCILED = "RECONCILED"
    INEFFECTIVE = "INEFFECTIVE"


class ApprovalStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"


class VerificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REGRESSION = "REGRESSION"
    INSUFFICIENT = "INSUFFICIENT"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"


class FailureCode(StrEnum):
    INVALID_WEBHOOK = "INVALID_WEBHOOK"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    STALE_EVENT = "STALE_EVENT"
    AUTH_DENIED = "AUTH_DENIED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_INVALID = "APPROVAL_INVALID"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    MITIGATION_INEFFECTIVE = "MITIGATION_INEFFECTIVE"
    MANUAL_TAKEOVER = "MANUAL_TAKEOVER"
    CANCELLED = "CANCELLED"


class Capability(StrEnum):
    METRICS_READ = "metrics.read"
    LOGS_READ = "logs.read"
    DEPLOYMENTS_READ = "deployments.read"
    TICKETS_READ = "tickets.read"
    PROVIDER_STATUS_READ = "provider-status.read"
    RUNBOOK_READ = "runbook.read"
    CUSTOMER_IMPACT_READ = "customer-impact.read"
    SLA_READ = "sla.read"
    DEPLOYMENT_ROLLBACK = "deployment.rollback"
    FEATURE_FLAG_WRITE = "feature-flag.write"
    SERVICE_RESTART = "service.restart"
    CACHE_FLUSH = "cache.flush"


READ_ONLY_CAPABILITIES = frozenset(
    {
        Capability.METRICS_READ,
        Capability.LOGS_READ,
        Capability.DEPLOYMENTS_READ,
        Capability.TICKETS_READ,
        Capability.PROVIDER_STATUS_READ,
        Capability.RUNBOOK_READ,
        Capability.CUSTOMER_IMPACT_READ,
        Capability.SLA_READ,
    }
)


class IncidentContext(FrozenModel):
    incident_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    service_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    region: str = Field(min_length=1)
    trigger_source: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)
    triggered_at: datetime
    caller_identity: str = Field(min_length=1)
    caller_roles: tuple[str, ...]
    policy_version: str = Field(min_length=1)
    investigation_capabilities: tuple[Capability, ...]

    @field_validator("investigation_capabilities")
    @classmethod
    def investigation_is_read_only(
        cls, capabilities: tuple[Capability, ...]
    ) -> tuple[Capability, ...]:
        if not set(capabilities).issubset(READ_ONLY_CAPABILITIES):
            raise ValueError("INVESTIGATION_WRITE_CAPABILITY_DENIED")
        return capabilities


class IncidentEvent(FrozenModel):
    event_type: str
    source_event_id: str
    incident_id: str
    tenant_id: str
    service_id: str
    environment: str
    region: str
    occurred_at: datetime


class AdmissionDisposition(StrEnum):
    ADMITTED = "ADMITTED"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"


class AdmissionResult(FrozenModel):
    disposition: AdmissionDisposition
    context: IncidentContext
    event: IncidentEvent


class AlertRegistry(MutableModel):
    processed_keys: set[str] = Field(default_factory=set)
    terminal_incidents: dict[str, datetime] = Field(default_factory=dict)


class EvidenceRecord(FrozenModel):
    evidence_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    source_type: EvidenceType
    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    event_time: datetime
    observed_at: datetime
    retrieved_at: datetime
    artifact_handle: str = Field(min_length=1)
    digest: str = Field(min_length=64, max_length=64)
    authority: EvidenceTrust
    freshness: EvidenceStatus
    structured_facts: Mapping[str, Any]
    safe_excerpt: str = Field(max_length=500)
    customer_account_id: str | None = None


class EvidenceRegistry(MutableModel):
    incident_id: str
    tenant_id: str
    records: dict[str, EvidenceRecord] = Field(default_factory=dict)


class EvidenceTimeline(FrozenModel):
    incident_id: str
    evidence_ids: tuple[str, ...]


class EvidenceGap(FrozenModel):
    gap_id: str
    question: str
    required_type: EvidenceType
    resolved_by: str | None = None


class Hypothesis(FrozenModel):
    hypothesis_id: str
    statement: str
    supporting_evidence_ids: tuple[str, ...] = ()
    contradicting_evidence_ids: tuple[str, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    status: HypothesisStatus = HypothesisStatus.UNTESTED


class ClaimKind(StrEnum):
    OBSERVATION = "OBSERVATION"
    INFERENCE = "INFERENCE"
    CONFIRMED_ROOT_CAUSE = "CONFIRMED_ROOT_CAUSE"


class Claim(FrozenModel):
    claim_id: str
    kind: ClaimKind
    text: str
    evidence_ids: tuple[str, ...]
    hypothesis_id: str | None = None


class EvidenceRelation(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"


class ClaimEvidenceLink(FrozenModel):
    claim_id: str
    evidence_id: str
    relation: EvidenceRelation


class SlaContract(FrozenModel):
    contract_id: str
    contract_version: str = Field(min_length=1)
    effective_from: datetime
    effective_to: datetime
    threshold_minutes: int = Field(gt=0)
    credit_rate: float = Field(ge=0, le=1)
    monthly_fee_usd: float = Field(ge=0)

    @model_validator(mode="after")
    def valid_window(self) -> "SlaContract":
        if self.effective_to <= self.effective_from:
            raise ValueError("SLA_EFFECTIVE_WINDOW_INVALID")
        return self


class ImpactAssessment(FrozenModel):
    affected_services: tuple[str, ...]
    affected_region: str
    affected_accounts_count: int = Field(ge=0)
    affected_tier_counts: Mapping[str, int]
    failed_transactions: int = Field(ge=0)
    conversion_impact: float = Field(ge=0, le=1)
    potential_sla_exposure_usd: float = Field(ge=0)
    evidence_ids: tuple[str, ...]


class IncidentBrief(FrozenModel):
    incident_id: str
    severity: IncidentSeverity
    status: IncidentStatus
    started_at: datetime
    affected_services: tuple[str, ...]
    customer_impact: str
    leading_hypothesis: Hypothesis
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    unresolved_gaps: tuple[EvidenceGap, ...]
    impact: ImpactAssessment
    next_decision: str
    claims: tuple[Claim, ...]


class RollbackDeploymentArgs(FrozenModel):
    service_id: str
    deployment_id: str


class MitigationAction(StrEnum):
    ROLLBACK_DEPLOYMENT = "ROLLBACK_DEPLOYMENT"
    DISABLE_FEATURE_FLAG = "DISABLE_FEATURE_FLAG"


class MitigationProposal(FrozenModel):
    proposal_id: str
    incident_id: str
    tenant_id: str
    action_type: MitigationAction
    target: str
    typed_parameters: RollbackDeploymentArgs
    evidence_ids: tuple[str, ...]
    expected_effect: str
    blast_radius: str
    rollback_plan: str
    verification_plan: str
    risk_tier: MitigationRisk
    evidence_snapshot_digest: str = Field(min_length=64, max_length=64)
    proposal_digest: str = Field(min_length=64, max_length=64)
    status: MitigationStatus = MitigationStatus.PROPOSED


class ReviewDecision(FrozenModel):
    proposal_id: str
    proposal_digest: str
    status: MitigationStatus
    reviewer_id: str
    reason_codes: tuple[str, ...]

    @field_validator("status")
    @classmethod
    def review_status_only(cls, status: MitigationStatus) -> MitigationStatus:
        if status not in {
            MitigationStatus.REVIEW_PASS,
            MitigationStatus.REVIEW_FAIL,
            MitigationStatus.NEEDS_REVISION,
        }:
            raise ValueError("INVALID_REVIEW_STATUS")
        return status


class ApprovalReceipt(FrozenModel):
    approval_id: str
    incident_id: str
    tenant_id: str
    proposal_id: str
    proposal_digest: str = Field(min_length=64, max_length=64)
    action: MitigationAction
    target: str
    approver_id: str
    policy_version: str
    issued_at: datetime
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.VALID


class ExecutionReceipt(FrozenModel):
    logical_operation_id: str
    attempt_id: str
    provider_operation_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None = None
    target: str
    proposal_digest: str


class VerificationResult(FrozenModel):
    status: VerificationStatus
    error_rate: float = Field(ge=0, le=1)
    conversion_rate: float = Field(ge=0, le=1)
    p99_latency_ms: int = Field(ge=0)
    provider_healthy: bool
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


class IncidentBudget(FrozenModel):
    max_tool_calls: int = Field(gt=0)
    max_queries_per_source: int = Field(gt=0)
    max_replans: int = Field(ge=0)
    max_model_calls: int = Field(ge=0)
    max_cost_usd: float = Field(ge=0)
    investigation_deadline_ms: int = Field(gt=0)
    max_mitigation_attempts: int = Field(gt=0)
    max_architecture_transitions: int = Field(ge=0)


class IncidentMetrics(FrozenModel):
    time_to_first_evidence_ms: int | None = Field(default=None, ge=0)
    time_to_credible_hypothesis_ms: int | None = Field(default=None, ge=0)
    time_to_incident_brief_ms: int | None = Field(default=None, ge=0)
    time_to_proposal_ms: int | None = Field(default=None, ge=0)
    time_to_approval_ms: int | None = Field(default=None, ge=0)
    time_to_verified_recovery_ms: int | None = Field(default=None, ge=0)
    tool_calls: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    duplicate_retrievals: int = Field(ge=0)
    unsupported_claim_rate: float = Field(ge=0, le=1)
    false_root_cause_rate: float = Field(ge=0, le=1)
    unsafe_action_attempts: int = Field(ge=0)
    unsafe_action_executions: int = Field(ge=0)
    human_override_rate: float = Field(ge=0, le=1)
    mitigation_success_rate: float = Field(ge=0, le=1)


class AuditEvent(FrozenModel):
    incident_id: str
    event_type: str
    occurred_at: datetime
    actor_id: str
    object_ref: str
    reason_codes: tuple[str, ...] = ()


class IncidentRunState(MutableModel):
    context: IncidentContext
    status: IncidentStatus = IncidentStatus.TRIGGERED
    severity: IncidentSeverity = IncidentSeverity.SEV3
    accepted_evidence_ids: tuple[str, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    gaps: tuple[EvidenceGap, ...] = ()
    proposal: MitigationProposal | None = None
    approval_receipt: ApprovalReceipt | None = None
    execution_receipts: tuple[ExecutionReceipt, ...] = ()
    verification: VerificationResult | None = None
    tool_calls: int = 0
    model_calls: int = 0
    cost_usd: float = 0
    replans: int = 0
    mitigation_attempts: int = 0
    architecture_transitions: int = 0
    coordinator_id: str | None = None
    lease_expires_at: datetime | None = None
    processed_event_ids: tuple[str, ...] = ()
    audit_events: tuple[AuditEvent, ...] = ()


_FRESHNESS = {
    EvidenceType.METRICS: timedelta(minutes=2),
    EvidenceType.LOGS: timedelta(minutes=5),
    EvidenceType.PROVIDER_STATUS: timedelta(minutes=5),
    EvidenceType.TICKET_AGGREGATE: timedelta(minutes=15),
    EvidenceType.CUSTOMER_IMPACT: timedelta(minutes=15),
    EvidenceType.DEPLOYMENT: timedelta(hours=1),
    EvidenceType.RUNBOOK: timedelta(days=30),
    EvidenceType.SLA_CONTRACT: timedelta(days=365),
    EvidenceType.VERIFICATION: timedelta(minutes=2),
}


_ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.TRIGGERED: frozenset({IncidentStatus.TRIAGED}),
    IncidentStatus.TRIAGED: frozenset({IncidentStatus.INVESTIGATING}),
    IncidentStatus.INVESTIGATING: frozenset(
        {IncidentStatus.EVIDENCE_INCOMPLETE, IncidentStatus.IMPACT_ASSESSED}
    ),
    IncidentStatus.EVIDENCE_INCOMPLETE: frozenset(
        {IncidentStatus.INVESTIGATING, IncidentStatus.IMPACT_ASSESSED}
    ),
    IncidentStatus.IMPACT_ASSESSED: frozenset({IncidentStatus.MITIGATION_PROPOSED}),
    IncidentStatus.MITIGATION_PROPOSED: frozenset({IncidentStatus.WAITING_REVIEW}),
    IncidentStatus.WAITING_REVIEW: frozenset({IncidentStatus.WAITING_APPROVAL}),
    IncidentStatus.WAITING_APPROVAL: frozenset({IncidentStatus.EXECUTING}),
    IncidentStatus.EXECUTING: frozenset(
        {IncidentStatus.VERIFYING, IncidentStatus.DEGRADED}
    ),
    IncidentStatus.DEGRADED: frozenset({IncidentStatus.VERIFYING}),
    IncidentStatus.VERIFYING: frozenset(
        {IncidentStatus.RESOLVED, IncidentStatus.EVIDENCE_INCOMPLETE}
    ),
    IncidentStatus.RESOLVED: frozenset(),
    IncidentStatus.ESCALATED: frozenset(),
    IncidentStatus.CANCELLED: frozenset(),
    IncidentStatus.MANUAL_CONTROL: frozenset(),
}


def transition_incident(state: IncidentRunState, target: IncidentStatus) -> None:
    """Apply an application-owned state transition and fail closed on skips."""
    if target == state.status:
        return
    if target in {IncidentStatus.CANCELLED, IncidentStatus.MANUAL_CONTROL}:
        if state.status in {
            IncidentStatus.RESOLVED,
            IncidentStatus.ESCALATED,
            IncidentStatus.CANCELLED,
            IncidentStatus.MANUAL_CONTROL,
        }:
            raise PolicyError("INVALID_STATE_TRANSITION")
        state.status = target
        return
    if target is IncidentStatus.ESCALATED:
        if state.status in {
            IncidentStatus.RESOLVED,
            IncidentStatus.CANCELLED,
            IncidentStatus.MANUAL_CONTROL,
        }:
            raise PolicyError("INVALID_STATE_TRANSITION")
        state.status = target
        return
    if target not in _ALLOWED_TRANSITIONS[state.status]:
        raise PolicyError("INVALID_STATE_TRANSITION")
    state.status = target


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def sign_webhook(payload: Mapping[str, Any], secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(
        secret.encode(), canonical_digest(payload).encode(), hashlib.sha256
    ).hexdigest()


def admit_webhook(
    payload: Mapping[str, Any],
    *,
    signature: str,
    registry: AlertRegistry,
    expected_tenant: str,
    expected_service: str,
    caller_identity: str,
    caller_roles: tuple[str, ...],
    now: datetime,
    secret: str = WEBHOOK_SECRET,
) -> AdmissionResult:
    required = {
        "event_type",
        "source_event_id",
        "incident_id",
        "tenant_id",
        "service_id",
        "environment",
        "region",
        "occurred_at",
    }
    if set(payload) != required:
        raise PolicyError("INVALID_WEBHOOK_SCHEMA")
    if payload["event_type"] != "incident.triggered":
        raise PolicyError("UNSUPPORTED_EVENT_TYPE")
    if not hmac.compare_digest(signature, sign_webhook(payload, secret)):
        raise PolicyError("INVALID_WEBHOOK_SIGNATURE")
    if payload["tenant_id"] != expected_tenant:
        raise PolicyError("TENANT_MAPPING_MISMATCH")
    if payload["service_id"] != expected_service:
        raise PolicyError("SERVICE_MAPPING_MISMATCH")
    event = IncidentEvent.model_validate(payload)
    if event.occurred_at > now + timedelta(minutes=1):
        raise PolicyError("FUTURE_EVENT")
    context = IncidentContext(
        incident_id=event.incident_id,
        tenant_id=event.tenant_id,
        service_id=event.service_id,
        environment=str(payload["environment"]),
        region=str(payload["region"]),
        trigger_source="pagerduty-fixture",
        source_event_id=event.source_event_id,
        triggered_at=event.occurred_at,
        caller_identity=caller_identity,
        caller_roles=caller_roles,
        policy_version=POLICY_VERSION,
        investigation_capabilities=tuple(READ_ONLY_CAPABILITIES),
    )
    key = f"{event.incident_id}:{event.source_event_id}"
    if key in registry.processed_keys:
        return AdmissionResult(
            disposition=AdmissionDisposition.DUPLICATE, context=context, event=event
        )
    terminal_at = registry.terminal_incidents.get(event.incident_id)
    if terminal_at is not None and event.occurred_at <= terminal_at:
        return AdmissionResult(
            disposition=AdmissionDisposition.STALE, context=context, event=event
        )
    registry.processed_keys.add(key)
    return AdmissionResult(
        disposition=AdmissionDisposition.ADMITTED, context=context, event=event
    )


def require_investigation_capability(
    context: IncidentContext, capability: Capability
) -> None:
    if capability not in READ_ONLY_CAPABILITIES:
        raise PolicyError("INVESTIGATION_WRITE_DENIED")
    if capability not in context.investigation_capabilities:
        raise PolicyError("AUTH_DENIED")


def evidence_payload(record: EvidenceRecord | Mapping[str, Any]) -> Mapping[str, Any]:
    data = record.model_dump(mode="json") if isinstance(record, EvidenceRecord) else dict(record)
    return {
        "incident_id": data["incident_id"],
        "tenant_id": data["tenant_id"],
        "source_type": str(data["source_type"]),
        "source_id": data["source_id"],
        "source_version": data["source_version"],
        "event_time": str(data["event_time"]),
        "observed_at": str(data["observed_at"]),
        "retrieved_at": str(data["retrieved_at"]),
        "artifact_handle": data["artifact_handle"],
        "authority": str(data["authority"]),
        "structured_facts": data["structured_facts"],
        "safe_excerpt": data["safe_excerpt"],
        "customer_account_id": data.get("customer_account_id"),
    }


def build_evidence_record(**values: Any) -> EvidenceRecord:
    payload = dict(values)
    payload["digest"] = "0" * 64
    provisional = EvidenceRecord(**payload)
    return provisional.model_copy(
        update={"digest": canonical_digest(evidence_payload(provisional))}
    )


def accept_evidence(
    registry: EvidenceRegistry,
    context: IncidentContext,
    record: EvidenceRecord,
    *,
    now: datetime,
) -> None:
    if record.incident_id != context.incident_id:
        raise PolicyError("EVIDENCE_INCIDENT_MISMATCH")
    if record.tenant_id != context.tenant_id:
        raise PolicyError("EVIDENCE_TENANT_MISMATCH")
    if registry.incident_id != context.incident_id or registry.tenant_id != context.tenant_id:
        raise PolicyError("EVIDENCE_REGISTRY_SCOPE_MISMATCH")
    if record.customer_account_id and not record.customer_account_id.startswith("acct-ns-"):
        raise PolicyError("CROSS_TENANT_ACCOUNT_REJECTED")
    if record.digest != canonical_digest(evidence_payload(record)):
        raise PolicyError("EVIDENCE_DIGEST_MISMATCH")
    if record.freshness is not EvidenceStatus.ACCEPTED:
        raise PolicyError("EVIDENCE_NOT_ACCEPTED")
    if now - record.retrieved_at > _FRESHNESS[record.source_type]:
        raise PolicyError("STALE_EVIDENCE")
    if record.retrieved_at < record.observed_at:
        raise PolicyError("EVIDENCE_TIME_INVALID")
    existing = registry.records.get(record.evidence_id)
    if existing is not None and existing != record:
        raise PolicyError("EVIDENCE_CONFLICT")
    registry.records[record.evidence_id] = record


def build_timeline(registry: EvidenceRegistry) -> EvidenceTimeline:
    ordered = sorted(registry.records.values(), key=lambda item: item.event_time)
    return EvidenceTimeline(
        incident_id=registry.incident_id,
        evidence_ids=tuple(item.evidence_id for item in ordered),
    )


def evidence_snapshot_digest(
    registry: EvidenceRegistry, evidence_ids: tuple[str, ...]
) -> str:
    records = []
    for evidence_id in sorted(evidence_ids):
        record = registry.records.get(evidence_id)
        if record is None:
            raise PolicyError("INVALID_EVIDENCE")
        records.append((record.evidence_id, record.digest))
    return canonical_digest(records)


def detect_conflicting_fact(
    registry: EvidenceRegistry,
    *,
    evidence_ids: tuple[str, ...],
    fact_name: str,
) -> None:
    """Reject contradictory values asserted by accepted authoritative sources."""
    values: set[str] = set()
    for evidence_id in evidence_ids:
        record = registry.records.get(evidence_id)
        if record is None:
            raise PolicyError("INVALID_EVIDENCE")
        if record.authority is EvidenceTrust.AUTHORITATIVE:
            if fact_name not in record.structured_facts:
                raise PolicyError("EVIDENCE_FACT_MISSING")
            values.add(canonical_digest(record.structured_facts[fact_name]))
    if len(values) > 1:
        raise PolicyError("CONFLICTING_EVIDENCE")


def validate_claim(
    claim: Claim,
    *,
    registry: EvidenceRegistry,
    hypotheses: Mapping[str, Hypothesis],
) -> None:
    if not claim.evidence_ids:
        raise PolicyError("UNSUPPORTED_CLAIM")
    for evidence_id in claim.evidence_ids:
        if evidence_id not in registry.records:
            raise PolicyError("INVALID_EVIDENCE")
    if claim.kind is ClaimKind.CONFIRMED_ROOT_CAUSE:
        hypothesis = hypotheses.get(claim.hypothesis_id or "")
        if hypothesis is None:
            raise PolicyError("ROOT_CAUSE_HYPOTHESIS_REQUIRED")
        if (
            hypothesis.status is not HypothesisStatus.SUPPORTED
            or hypothesis.missing_evidence
            or hypothesis.contradicting_evidence_ids
            or len(hypothesis.supporting_evidence_ids) < 3
        ):
            raise PolicyError("ROOT_CAUSE_NOT_CONFIRMED")
        if not set(claim.evidence_ids).issubset(hypothesis.supporting_evidence_ids):
            raise PolicyError("CITATION_LAUNDERING")


def derive_severity(
    *,
    availability_impact: float,
    affected_accounts: int,
    duration_minutes: int,
    security_or_regulatory: bool,
) -> IncidentSeverity:
    if security_or_regulatory or availability_impact >= 0.5 or affected_accounts >= 100:
        return IncidentSeverity.SEV1
    if availability_impact >= 0.1 or affected_accounts >= 10 or duration_minutes >= 15:
        return IncidentSeverity.SEV2
    return IncidentSeverity.SEV3


def calculate_potential_sla_exposure(
    contract: SlaContract, *, incident_started_at: datetime, now: datetime
) -> float:
    if not (contract.effective_from <= incident_started_at < contract.effective_to):
        raise PolicyError("SLA_CONTRACT_NOT_EFFECTIVE")
    duration = int((now - incident_started_at).total_seconds() // 60)
    if duration <= contract.threshold_minutes:
        return 0
    return round(contract.monthly_fee_usd * contract.credit_rate, 2)


def validate_brief(brief: IncidentBrief, registry: EvidenceRegistry) -> None:
    if brief.incident_id != registry.incident_id:
        raise PolicyError("BRIEF_INCIDENT_MISMATCH")
    hypotheses = {brief.leading_hypothesis.hypothesis_id: brief.leading_hypothesis}
    for claim in brief.claims:
        validate_claim(claim, registry=registry, hypotheses=hypotheses)
    claimed = set(brief.supporting_evidence_ids) | set(brief.contradicting_evidence_ids)
    if not claimed.issubset(registry.records):
        raise PolicyError("INVALID_EVIDENCE")
    if not set(brief.impact.evidence_ids).issubset(registry.records):
        raise PolicyError("IMPACT_EVIDENCE_INVALID")


def proposal_payload(proposal: MitigationProposal | Mapping[str, Any]) -> Mapping[str, Any]:
    data = (
        proposal.model_dump(mode="json")
        if isinstance(proposal, MitigationProposal)
        else dict(proposal)
    )
    return {
        "proposal_id": data["proposal_id"],
        "incident_id": data["incident_id"],
        "tenant_id": data["tenant_id"],
        "action_type": str(data["action_type"]),
        "target": data["target"],
        "typed_parameters": data["typed_parameters"],
        "evidence_ids": data["evidence_ids"],
        "expected_effect": data["expected_effect"],
        "blast_radius": data["blast_radius"],
        "rollback_plan": data["rollback_plan"],
        "verification_plan": data["verification_plan"],
        "risk_tier": str(data["risk_tier"]),
        "evidence_snapshot_digest": data["evidence_snapshot_digest"],
    }


def validate_proposal(
    proposal: MitigationProposal,
    *,
    context: IncidentContext,
    registry: EvidenceRegistry,
) -> None:
    if proposal.incident_id != context.incident_id:
        raise PolicyError("PROPOSAL_INCIDENT_MISMATCH")
    if proposal.tenant_id != context.tenant_id:
        raise PolicyError("PROPOSAL_TENANT_MISMATCH")
    if proposal.target != proposal.typed_parameters.deployment_id:
        raise PolicyError("PROPOSAL_TARGET_MISMATCH")
    if proposal.typed_parameters.service_id != context.service_id:
        raise PolicyError("PROPOSAL_SERVICE_MISMATCH")
    expected_snapshot = evidence_snapshot_digest(registry, proposal.evidence_ids)
    if proposal.evidence_snapshot_digest != expected_snapshot:
        raise PolicyError("PROPOSAL_EVIDENCE_STALE")
    if proposal.proposal_digest != canonical_digest(proposal_payload(proposal)):
        raise PolicyError("PROPOSAL_DIGEST_MISMATCH")


def validate_approval(
    approval: ApprovalReceipt,
    proposal: MitigationProposal,
    review: ReviewDecision,
    context: IncidentContext,
    *,
    now: datetime,
    authorized_approvers: frozenset[str],
) -> None:
    if review.status is not MitigationStatus.REVIEW_PASS:
        raise PolicyError("REVIEW_NOT_PASSED")
    if (
        review.proposal_id != proposal.proposal_id
        or review.proposal_digest != proposal.proposal_digest
    ):
        raise PolicyError("REVIEW_PROPOSAL_MISMATCH")
    checks = {
        "APPROVAL_INCIDENT_MISMATCH": approval.incident_id == context.incident_id,
        "APPROVAL_TENANT_MISMATCH": approval.tenant_id == context.tenant_id,
        "APPROVAL_PROPOSAL_MISMATCH": approval.proposal_id == proposal.proposal_id,
        "APPROVAL_DIGEST_MISMATCH": approval.proposal_digest == proposal.proposal_digest,
        "APPROVAL_ACTION_MISMATCH": approval.action == proposal.action_type,
        "APPROVAL_TARGET_MISMATCH": approval.target == proposal.target,
        "APPROVAL_POLICY_STALE": approval.policy_version == context.policy_version,
        "APPROVER_NOT_AUTHORIZED": approval.approver_id in authorized_approvers,
    }
    for code, valid in checks.items():
        if not valid:
            raise PolicyError(code)
    if approval.status is not ApprovalStatus.VALID:
        raise PolicyError("APPROVAL_INVALID")
    if approval.issued_at > now or approval.expires_at <= now:
        raise PolicyError("APPROVAL_EXPIRED")
    if approval.expires_at <= approval.issued_at:
        raise PolicyError("APPROVAL_WINDOW_INVALID")


def logical_mitigation_id(proposal: MitigationProposal) -> str:
    return "mitigation:" + canonical_digest(
        {
            "incident_id": proposal.incident_id,
            "tenant_id": proposal.tenant_id,
            "action": proposal.action_type,
            "target": proposal.target,
            "proposal_digest": proposal.proposal_digest,
        }
    )[:24]


def acquire_coordinator_lease(
    state: IncidentRunState,
    *,
    coordinator_id: str,
    now: datetime,
    ttl_seconds: int = 60,
) -> None:
    if (
        state.coordinator_id
        and state.coordinator_id != coordinator_id
        and state.lease_expires_at
        and state.lease_expires_at > now
    ):
        raise PolicyError("COORDINATOR_LEASE_HELD")
    state.coordinator_id = coordinator_id
    state.lease_expires_at = now + timedelta(seconds=ttl_seconds)


def require_active_coordinator(
    state: IncidentRunState, *, coordinator_id: str, now: datetime
) -> None:
    if state.coordinator_id != coordinator_id:
        raise PolicyError("COORDINATOR_LEASE_REQUIRED")
    if state.lease_expires_at is None or state.lease_expires_at <= now:
        raise PolicyError("COORDINATOR_LEASE_EXPIRED")


def require_automation_active(state: IncidentRunState) -> None:
    if state.status is IncidentStatus.MANUAL_CONTROL:
        raise PolicyError("MANUAL_TAKEOVER")
    if state.status is IncidentStatus.CANCELLED:
        raise PolicyError("CANCELLED")


def apply_verification(
    state: IncidentRunState, result: VerificationResult
) -> None:
    """Only trusted verification can drive the terminal RESOLVED transition."""
    state.verification = result
    if result.status.value == VerificationStatus.PASS.value:
        transition_incident(state, IncidentStatus.RESOLVED)
    elif result.status.value in {
        VerificationStatus.FAIL.value,
        VerificationStatus.REGRESSION.value,
    }:
        transition_incident(state, IncidentStatus.EVIDENCE_INCOMPLETE)
    else:
        transition_incident(state, IncidentStatus.ESCALATED)
