"""Application-owned contracts and policy for Advanced 08 proactive agents.

Raw events and model output are untrusted inputs. Deterministic application code
admits events, derives severity, evaluates triggers, routes proposals, and
authorizes bounded proactive actions.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVENT_POLICY_VERSION = "northstar-event-admission-v1"
FINGERPRINT_VERSION = "northstar-event-fingerprint-v1"
TRIGGER_POLICY_VERSION = "northstar-proactive-trigger-v1"
SEVERITY_POLICY_VERSION = "northstar-severity-v1"
ROUTING_POLICY_VERSION = "northstar-notification-routing-v1"


class ProactivePolicyError(ValueError):
    """A fail-closed policy result with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EventType(StrEnum):
    METRIC_OBSERVATION = "METRIC_OBSERVATION"
    INCIDENT_RECOVERED = "INCIDENT_RECOVERED"
    CERTIFICATE_EXPIRY = "CERTIFICATE_EXPIRY"
    BACKUP_COMPLETED = "BACKUP_COMPLETED"
    EXPECTED_EVENT_MISSING = "EXPECTED_EVENT_MISSING"
    TREND_SIGNAL = "TREND_SIGNAL"
    PREDICTIVE_SIGNAL = "PREDICTIVE_SIGNAL"


class SensorQuality(StrEnum):
    GOOD = "GOOD"
    MISSING = "MISSING"
    STALE = "STALE"
    INVALID = "INVALID"


class EventStatus(StrEnum):
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"
    OUT_OF_ORDER = "OUT_OF_ORDER"


class IncidentStatus(StrEnum):
    NORMAL = "NORMAL"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SUPPRESSED = "SUPPRESSED"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"


class Severity(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


SEVERITY_RANK = {
    Severity.P1: 1,
    Severity.P2: 2,
    Severity.P3: 3,
    Severity.P4: 4,
}


class TriggerStatus(StrEnum):
    NOT_TRIGGERED = "NOT_TRIGGERED"
    PENDING = "PENDING"
    ACTIVATED = "ACTIVATED"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class ProactiveActionType(StrEnum):
    NOTIFY = "NOTIFY"
    CREATE_TASK = "CREATE_TASK"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    START_READ_ONLY_INVESTIGATION = "START_READ_ONLY_INVESTIGATION"
    RUN_PREAUTHORIZED_WORKFLOW = "RUN_PREAUTHORIZED_WORKFLOW"
    DEFER = "DEFER"
    SUPPRESS = "SUPPRESS"


class RoutingAction(StrEnum):
    SEND_NOW = "SEND_NOW"
    DEFER = "DEFER"
    DIGEST = "DIGEST"
    FALLBACK_CHANNEL = "FALLBACK_CHANNEL"
    SUPPRESS = "SUPPRESS"
    ESCALATE = "ESCALATE"


class NotificationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ROUTED = "ROUTED"
    DEFERRED = "DEFERRED"
    SCHEDULED = "SCHEDULED"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class DeliveryStatus(StrEnum):
    DELIVERED = "DELIVERED"
    UNKNOWN = "UNKNOWN"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    RECONCILED = "RECONCILED"
    DEAD_LETTERED = "DEAD_LETTERED"


class DigestStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    SUPERSEDED = "SUPERSEDED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class SuppressionReason(StrEnum):
    DUPLICATE = "DUPLICATE"
    HYSTERESIS_NOT_MET = "HYSTERESIS_NOT_MET"
    DEBOUNCE_NOT_MET = "DEBOUNCE_NOT_MET"
    COOLDOWN = "COOLDOWN"
    QUIET_HOURS = "QUIET_HOURS"
    RATE_LIMIT = "RATE_LIMIT"
    INCIDENT_ACKNOWLEDGED = "INCIDENT_ACKNOWLEDGED"
    STALE_EVENT = "STALE_EVENT"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    LOW_SEVERITY = "LOW_SEVERITY"
    SENSOR_QUALITY_INVALID = "SENSOR_QUALITY_INVALID"


class AuditEventType(StrEnum):
    EVENT_ADMITTED = "EVENT_ADMITTED"
    EVENT_REJECTED = "EVENT_REJECTED"
    EVENT_DUPLICATED = "EVENT_DUPLICATED"
    INCIDENT_CORRELATED = "INCIDENT_CORRELATED"
    TRIGGER_ACTIVATED = "TRIGGER_ACTIVATED"
    NOTIFICATION_PROPOSED = "NOTIFICATION_PROPOSED"
    NOTIFICATION_DEFERRED = "NOTIFICATION_DEFERRED"
    NOTIFICATION_DELIVERED = "NOTIFICATION_DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    DELIVERY_FAILED = "DELIVERY_FAILED"


SafeFact = str | int | float | bool | None


def _require_aware(value: datetime, code: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(code)
    return value


class EventEnvelope(FrozenModel):
    event_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    event_type: EventType
    event_time: datetime
    received_at: datetime
    payload_digest: str = Field(min_length=64, max_length=64)
    correlation_key: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    safe_facts: Mapping[str, SafeFact]
    schema_version: str = "northstar-event-envelope-v1"

    @field_validator("event_time", "received_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return _require_aware(value, "EVENT_TIMEZONE_REQUIRED")

    @model_validator(mode="after")
    def valid_transport_times(self) -> "EventEnvelope":
        if self.received_at < self.event_time:
            raise ValueError("EVENT_RECEIVED_BEFORE_OCCURRED")
        return self


class EventFingerprint(FrozenModel):
    dedupe_key: str = Field(min_length=64, max_length=64)
    fingerprint_version: str = Field(min_length=1)
    normalized_fields: Mapping[str, SafeFact]


class IncidentAggregate(FrozenModel):
    incident_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    correlation_key: str = Field(min_length=1)
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int = Field(ge=1)
    duplicate_delivery_count: int = Field(ge=0)
    severity: Severity
    affected_services: tuple[str, ...]
    status: IncidentStatus
    state_version: int = Field(ge=1)
    last_sequence: int = Field(ge=0)
    last_event_time: datetime
    last_notified_severity: Severity | None = None
    last_notification_at: datetime | None = None
    resolved_at: datetime | None = None


class TriggerPolicy(FrozenModel):
    policy_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    event_type: EventType
    metric_name: str | None = None
    activation_threshold: float | None = None
    recovery_threshold: float | None = None
    sustain_duration_seconds: int = Field(default=120, ge=0)
    recovery_duration_seconds: int = Field(default=120, ge=0)
    maximum_sensor_age_seconds: int = Field(default=120, gt=0)
    minimum_severity: Severity
    allowed_proactive_action: ProactiveActionType
    required_capabilities: tuple[str, ...]
    cooldown_seconds: int = Field(default=900, ge=0)
    correlation_window_seconds: int = Field(default=1800, gt=0)
    policy_version: str = TRIGGER_POLICY_VERSION

    @model_validator(mode="after")
    def ordered_thresholds(self) -> "TriggerPolicy":
        if self.event_type is EventType.METRIC_OBSERVATION and (
            self.activation_threshold is None or self.recovery_threshold is None
        ):
            raise ValueError("METRIC_THRESHOLDS_REQUIRED")
        if (
            self.activation_threshold is not None
            and self.recovery_threshold is not None
            and self.recovery_threshold >= self.activation_threshold
        ):
            raise ValueError("HYSTERESIS_THRESHOLDS_INVALID")
        return self


class TriggerDecision(FrozenModel):
    trigger_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    status: TriggerStatus
    severity: Severity
    proposed_action: ProactiveActionType
    reason_codes: tuple[str, ...]
    decided_at: datetime
    policy_version: str = TRIGGER_POLICY_VERSION


class NotificationProposal(FrozenModel):
    proposal_id: str = Field(min_length=1)
    logical_notification_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    recipient_scope: str = Field(min_length=1)
    severity: Severity
    category: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    evidence_ids: tuple[str, ...]
    interruptible: bool
    delivery_deadline: datetime
    created_at: datetime
    required_capability: str = "notify.oncall"
    severity_policy_version: str = SEVERITY_POLICY_VERSION


class RecipientPreference(FrozenModel):
    tenant_id: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    workday_start: time = time(8, 0)
    workday_end: time = time(18, 0)
    working_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)
    preferred_channel: str = "slack"
    digest_channel: str = "email"
    opted_out_categories: tuple[str, ...] = ()

    @field_validator("timezone")
    @classmethod
    def valid_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("IANA_TIMEZONE_REQUIRED") from error
        return value

    @field_validator("working_weekdays")
    @classmethod
    def valid_weekdays(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("WORKDAY_INVALID")
        return value


class OnCallAssignment(FrozenModel):
    tenant_id: str = Field(min_length=1)
    schedule_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    valid_from: datetime
    valid_until: datetime
    channel: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_window(self) -> "OnCallAssignment":
        if self.valid_until <= self.valid_from:
            raise ValueError("ON_CALL_WINDOW_INVALID")
        return self


class RoutingDecision(FrozenModel):
    routing_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    action: RoutingAction
    recipient_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    deliver_at: datetime
    reason_codes: tuple[str, ...]
    mandatory_policy_applied: bool
    routing_policy_version: str = ROUTING_POLICY_VERSION


class DeliveryAttempt(FrozenModel):
    attempt_id: str = Field(min_length=1)
    logical_notification_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    attempt_number: int = Field(ge=1)
    created_at: datetime


class DeliveryReceipt(FrozenModel):
    logical_notification_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    provider_message_id: str | None = None
    status: DeliveryStatus
    sent_at: datetime | None = None
    reason_codes: tuple[str, ...] = ()


class DigestItem(FrozenModel):
    digest_item_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    logical_notification_id: str = Field(min_length=1)
    status: DigestStatus
    title: str = Field(min_length=1)
    occurrence_count: int = Field(ge=1)
    deliver_at: datetime
    state_version: int = Field(ge=1)


class EscalationPolicy(FrozenModel):
    policy_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    severity: Severity
    acknowledgment_timeout_seconds: int = Field(gt=0)
    escalation_roles: tuple[str, ...]
    policy_version: str = ROUTING_POLICY_VERSION


class ProactiveRunState(FrozenModel):
    run_id: str = Field(min_length=1)
    event_status: EventStatus
    incident_id: str | None
    trigger_status: TriggerStatus | None
    notification_id: str | None
    suppression_reason: SuppressionReason | None
    model_calls: int = Field(ge=0)
    terminal_reason: str


class ProactiveMetrics(FrozenModel):
    labelled_events: int = Field(gt=0)
    trigger_true_positives: int = Field(ge=0)
    trigger_false_positives: int = Field(ge=0)
    trigger_false_negatives: int = Field(ge=0)
    p1_events: int = Field(ge=0)
    p1_misses: int = Field(ge=0)
    delivered_notifications: int = Field(ge=0)
    useful_notifications: int = Field(ge=0)
    duplicate_deliveries: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    mean_detection_latency_seconds: float = Field(ge=0)
    mean_notification_latency_seconds: float = Field(ge=0)
    estimated_model_cost_usd: float = Field(ge=0)

    @property
    def trigger_precision(self) -> float:
        denominator = self.trigger_true_positives + self.trigger_false_positives
        return self.trigger_true_positives / denominator if denominator else 0.0

    @property
    def trigger_recall(self) -> float:
        denominator = self.trigger_true_positives + self.trigger_false_negatives
        return self.trigger_true_positives / denominator if denominator else 0.0

    @property
    def p1_miss_rate(self) -> float:
        return self.p1_misses / self.p1_events if self.p1_events else 0.0

    @property
    def notification_precision(self) -> float:
        return (
            self.useful_notifications / self.delivered_notifications
            if self.delivered_notifications
            else 0.0
        )


class BackpressureAction(StrEnum):
    PROCESS_NOW = "PROCESS_NOW"
    BATCH = "BATCH"
    SHED = "SHED"


class BackpressurePolicy(FrozenModel):
    tenant_id: str = Field(min_length=1)
    batch_depth: int = Field(default=100, ge=1)
    shed_depth: int = Field(default=1000, ge=1)
    maximum_consumer_lag_seconds: int = Field(default=60, ge=1)

    @model_validator(mode="after")
    def ordered_depths(self) -> "BackpressurePolicy":
        if self.shed_depth <= self.batch_depth:
            raise ValueError("BACKPRESSURE_DEPTHS_INVALID")
        return self


class BackpressureDecision(FrozenModel):
    action: BackpressureAction
    preserve_event: bool
    reason_codes: tuple[str, ...]


def evaluate_backpressure(
    event: EventEnvelope,
    *,
    queue_depth: int,
    consumer_lag_seconds: int,
    policy: BackpressurePolicy,
) -> BackpressureDecision:
    """Prioritize mandatory events; batch or shed only lower-severity work."""

    if event.tenant_id != policy.tenant_id:
        raise ProactivePolicyError("BACKPRESSURE_TENANT_MISMATCH")
    severity = derive_severity(event)
    overloaded = (
        queue_depth >= policy.shed_depth
        or consumer_lag_seconds >= policy.maximum_consumer_lag_seconds
    )
    if severity is Severity.P1:
        return BackpressureDecision(
            action=BackpressureAction.PROCESS_NOW,
            preserve_event=True,
            reason_codes=("MANDATORY_P1_PRIORITY",),
        )
    if overloaded:
        return BackpressureDecision(
            action=BackpressureAction.SHED,
            preserve_event=False,
            reason_codes=("LOW_PRIORITY_LOAD_SHEDDING",),
        )
    if queue_depth >= policy.batch_depth:
        return BackpressureDecision(
            action=BackpressureAction.BATCH,
            preserve_event=True,
            reason_codes=("AGGREGATE_BEFORE_MODEL",),
        )
    return BackpressureDecision(
        action=BackpressureAction.PROCESS_NOW,
        preserve_event=True,
        reason_codes=("CAPACITY_AVAILABLE",),
    )


def canonical_digest(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def build_event(**values: Any) -> EventEnvelope:
    payload = dict(values)
    payload["payload_digest"] = canonical_digest(payload["safe_facts"])
    return EventEnvelope(**payload)


def admit_event(
    event: EventEnvelope,
    *,
    authenticated_tenant: str,
    trusted_sources: Mapping[str, Sequence[str]],
    now: datetime,
    maximum_lateness: timedelta = timedelta(minutes=15),
) -> None:
    """Validate transport identity and freshness before any state mutation."""

    checks = {
        "EVENT_TENANT_DENIED": event.tenant_id == authenticated_tenant,
        "EVENT_SOURCE_DENIED": event.source in trusted_sources,
        "EVENT_SOURCE_VERSION_DENIED": event.source in trusted_sources
        and event.source_version in trusted_sources[event.source],
        "EVENT_PAYLOAD_DIGEST_MISMATCH": event.payload_digest
        == canonical_digest(event.safe_facts),
        "EVENT_FROM_FUTURE": event.event_time <= now,
        "EVENT_RECEIPT_FROM_FUTURE": event.received_at <= now,
        "STALE_EVENT": now - event.event_time <= maximum_lateness,
    }
    for code, allowed in checks.items():
        if not allowed:
            raise ProactivePolicyError(code)


APPROVED_FINGERPRINT_FIELDS = (
    "service",
    "metric",
    "region",
    "environment",
    "certificate_id",
    "backup_job",
    "value",
    "quality",
    "affected_customer_pct",
    "days_remaining",
    "hours_to_full",
)


def fingerprint_event(event: EventEnvelope) -> EventFingerprint:
    """Hash only normalized, bounded fields—not request IDs or free-form text."""

    normalized: dict[str, SafeFact] = {
        "tenant_id": event.tenant_id.strip().lower(),
        "event_type": event.event_type.value,
        "correlation_key": event.correlation_key.strip().lower(),
        "event_time": event.event_time.astimezone(UTC).isoformat(),
    }
    for field_name in APPROVED_FINGERPRINT_FIELDS:
        value = event.safe_facts.get(field_name)
        if isinstance(value, str):
            normalized[field_name] = " ".join(value.strip().lower().split())
        elif value is not None:
            normalized[field_name] = value
    return EventFingerprint(
        dedupe_key=canonical_digest(
            {"version": FINGERPRINT_VERSION, "fields": normalized}
        ),
        fingerprint_version=FINGERPRINT_VERSION,
        normalized_fields=normalized,
    )


def derive_severity(event: EventEnvelope) -> Severity:
    """Derive authoritative severity from typed facts, never payload instructions."""

    if event.event_type is EventType.INCIDENT_RECOVERED:
        return Severity.P4
    if event.event_type is EventType.EXPECTED_EVENT_MISSING:
        return Severity.P2
    if event.event_type in {EventType.TREND_SIGNAL, EventType.PREDICTIVE_SIGNAL}:
        return Severity.P3
    if event.event_type is EventType.CERTIFICATE_EXPIRY:
        days = float(event.safe_facts.get("days_remaining", 365))
        return Severity.P2 if days <= 7 else Severity.P3

    error_rate = float(event.safe_facts.get("value") or 0)
    affected_pct = float(event.safe_facts.get("affected_customer_pct", 0))
    if error_rate >= 0.60 or affected_pct >= 50:
        return Severity.P1
    if error_rate >= 0.30 or affected_pct >= 20:
        return Severity.P2
    if error_rate >= 0.10:
        return Severity.P3
    return Severity.P4


def is_more_severe(candidate: Severity, current: Severity) -> bool:
    return SEVERITY_RANK[candidate] < SEVERITY_RANK[current]


def is_at_least(candidate: Severity, threshold: Severity) -> bool:
    return SEVERITY_RANK[candidate] <= SEVERITY_RANK[threshold]


def evaluate_metric_trigger(
    *,
    incident: IncidentAggregate,
    event: EventEnvelope,
    policy: TriggerPolicy,
    sustained_breach_seconds: float,
    sustained_recovery_seconds: float,
    now: datetime,
) -> TriggerDecision:
    try:
        quality = SensorQuality(
            str(event.safe_facts.get("quality", SensorQuality.GOOD))
        )
    except ValueError:
        quality = SensorQuality.INVALID
    severity = derive_severity(event)
    value = event.safe_facts.get("value")
    if quality is not SensorQuality.GOOD or value is None:
        return TriggerDecision(
            trigger_id=f"trigger-{event.event_id}",
            tenant_id=event.tenant_id,
            incident_id=incident.incident_id,
            status=TriggerStatus.SUPPRESSED,
            severity=severity,
            proposed_action=ProactiveActionType.SUPPRESS,
            reason_codes=("SENSOR_QUALITY_INVALID",),
            decided_at=now,
        )
    if (now - event.event_time).total_seconds() > policy.maximum_sensor_age_seconds:
        return TriggerDecision(
            trigger_id=f"trigger-{event.event_id}",
            tenant_id=event.tenant_id,
            incident_id=incident.incident_id,
            status=TriggerStatus.SUPPRESSED,
            severity=severity,
            proposed_action=ProactiveActionType.SUPPRESS,
            reason_codes=("SENSOR_STALE",),
            decided_at=now,
        )

    numeric_value = float(value)
    escalation = (
        incident.last_notified_severity is not None
        and is_more_severe(severity, incident.last_notified_severity)
    )
    if escalation:
        status = TriggerStatus.ACTIVATED
        reasons = ("SEVERITY_ESCALATION_BYPASS",)
    elif incident.status in {
        IncidentStatus.ACTIVE,
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.RECOVERING,
    }:
        if (
            policy.recovery_threshold is not None
            and numeric_value <= policy.recovery_threshold
        ):
            if sustained_recovery_seconds >= policy.recovery_duration_seconds:
                status = TriggerStatus.RESOLVED
                reasons = ("SUSTAINED_RECOVERY",)
            else:
                status = TriggerStatus.RECOVERY_PENDING
                reasons = ("RECOVERY_DEBOUNCE_NOT_MET",)
        elif incident.status is IncidentStatus.ACTIVE:
            status = TriggerStatus.ACTIVATED
            reasons = ("BREACH_CONTINUES",)
        else:
            status = TriggerStatus.NOT_TRIGGERED
            reasons = ("INCIDENT_ACKNOWLEDGED",)
    elif (
        policy.activation_threshold is not None
        and numeric_value >= policy.activation_threshold
    ):
        if sustained_breach_seconds >= policy.sustain_duration_seconds:
            status = TriggerStatus.ACTIVATED
            reasons = ("SUSTAINED_BREACH",)
        else:
            status = TriggerStatus.PENDING
            reasons = ("DEBOUNCE_NOT_MET",)
    else:
        status = TriggerStatus.NOT_TRIGGERED
        reasons = ("HYSTERESIS_NOT_MET",)

    return TriggerDecision(
        trigger_id=f"trigger-{event.event_id}",
        tenant_id=event.tenant_id,
        incident_id=incident.incident_id,
        status=status,
        severity=severity,
        proposed_action=(
            policy.allowed_proactive_action
            if status is TriggerStatus.ACTIVATED
            else ProactiveActionType.SUPPRESS
        ),
        reason_codes=reasons,
        decided_at=now,
    )


def next_workday_delivery(preference: RecipientPreference, now: datetime) -> datetime:
    zone = ZoneInfo(preference.timezone)
    local = now.astimezone(zone)
    candidate = datetime.combine(local.date(), preference.workday_start, tzinfo=zone)
    if local >= candidate:
        candidate += timedelta(days=1)
    while candidate.weekday() not in preference.working_weekdays:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def route_notification(
    proposal: NotificationProposal,
    *,
    preference: RecipientPreference,
    on_call: OnCallAssignment,
    now: datetime,
) -> RoutingDecision:
    """Apply mandatory policy, current schedule, timezone, and preference."""

    if proposal.tenant_id != preference.tenant_id or proposal.tenant_id != on_call.tenant_id:
        raise ProactivePolicyError("ROUTING_TENANT_MISMATCH")
    if preference.recipient_id != on_call.recipient_id:
        raise ProactivePolicyError("RECIPIENT_PREFERENCE_MISMATCH")
    if on_call.role != proposal.recipient_scope:
        raise ProactivePolicyError("RECIPIENT_SCOPE_DENIED")
    if not on_call.valid_from <= now < on_call.valid_until:
        raise ProactivePolicyError("ON_CALL_ASSIGNMENT_STALE")

    mandatory = proposal.severity is Severity.P1
    local = now.astimezone(ZoneInfo(preference.timezone))
    in_workday = (
        local.weekday() in preference.working_weekdays
        and preference.workday_start <= local.time().replace(tzinfo=None)
        < preference.workday_end
    )
    if mandatory:
        action = RoutingAction.SEND_NOW
        channel = on_call.channel
        deliver_at = now
        reasons = ("MANDATORY_P1_POLICY", "CURRENT_ON_CALL_RESOLVED")
    elif proposal.category in preference.opted_out_categories:
        action = RoutingAction.SUPPRESS
        channel = preference.digest_channel
        deliver_at = now
        reasons = ("OPTIONAL_USER_PREFERENCE",)
    elif not in_workday:
        action = RoutingAction.DIGEST
        channel = preference.digest_channel
        deliver_at = next_workday_delivery(preference, now)
        reasons = ("QUIET_HOURS", "DURABLE_DIGEST_REQUIRED")
    else:
        action = RoutingAction.SEND_NOW
        channel = preference.preferred_channel
        deliver_at = now
        reasons = ("WITHIN_WORKING_HOURS",)

    return RoutingDecision(
        routing_id=f"route-{proposal.proposal_id}",
        proposal_id=proposal.proposal_id,
        tenant_id=proposal.tenant_id,
        action=action,
        recipient_id=on_call.recipient_id,
        channel=channel,
        deliver_at=deliver_at,
        reason_codes=reasons,
        mandatory_policy_applied=mandatory,
    )


ACTION_CAPABILITIES = {
    ProactiveActionType.NOTIFY: "notify.oncall",
    ProactiveActionType.CREATE_TASK: "task.create",
    ProactiveActionType.REQUEST_APPROVAL: "approval.request",
    ProactiveActionType.START_READ_ONLY_INVESTIGATION: "incident.read",
    ProactiveActionType.RUN_PREAUTHORIZED_WORKFLOW: "workflow.execute.preapproved",
    ProactiveActionType.DEFER: "schedule.write",
    ProactiveActionType.SUPPRESS: "notification.suppress",
}


def authorize_proactive_action(
    action: ProactiveActionType,
    *,
    actor_capabilities: Sequence[str],
) -> str:
    required = ACTION_CAPABILITIES[action]
    if required not in actor_capabilities:
        raise ProactivePolicyError("PROACTIVE_ACTION_CAPABILITY_DENIED")
    return required
