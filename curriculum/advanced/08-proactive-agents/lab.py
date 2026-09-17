"""Deterministic, credential-free proactive-agent lab for Advanced 08.

SQLite stands in for a durable transactional state store. The fixture sends no
real notification and performs no production mutation.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from policy import (
    ACTION_CAPABILITIES,
    AuditEventType,
    BackpressureAction,
    BackpressureDecision,
    BackpressurePolicy,
    DeliveryAttempt,
    DeliveryReceipt,
    DeliveryStatus,
    DigestItem,
    DigestStatus,
    EscalationPolicy,
    EventEnvelope,
    EventStatus,
    EventType,
    IncidentAggregate,
    IncidentStatus,
    NotificationProposal,
    NotificationStatus,
    OnCallAssignment,
    ProactiveActionType,
    ProactiveMetrics,
    ProactivePolicyError,
    ProactiveRunState,
    RecipientPreference,
    RoutingAction,
    RoutingDecision,
    SensorQuality,
    Severity,
    SuppressionReason,
    TriggerDecision,
    TriggerPolicy,
    TriggerStatus,
    admit_event,
    authorize_proactive_action,
    build_event,
    canonical_digest,
    derive_severity,
    evaluate_backpressure,
    evaluate_metric_trigger,
    fingerprint_event,
    is_at_least,
    is_more_severe,
    route_notification,
)

FIXED_TIME = datetime(2026, 3, 9, 10, 0, tzinfo=UTC)
TENANT = "northstar-commerce"
OTHER_TENANT = "globex-commerce"
TRUSTED_SOURCES = {
    "northstar-otel": ("otel-v7",),
    "northstar-scheduler": ("scheduler-v3",),
    "northstar-certificate-inventory": ("inventory-v2",),
}

DEFAULT_ACTOR_CAPABILITIES = (
    "notify.oncall",
    "task.create",
    "approval.request",
    "incident.read",
)


class DurableProactiveStore:
    """Small SQLite repository with uniqueness, transactions, and CAS checks."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(
            self.path,
            isolation_level=None,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 3000")
        if self.path != ":memory:":
            self.connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                tenant_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                incident_id TEXT,
                delivery_count INTEGER NOT NULL DEFAULT 1,
                event_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, event_id)
            );
            CREATE TABLE IF NOT EXISTS dedupe_claims (
                tenant_id TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, dedupe_key)
            );
            CREATE TABLE IF NOT EXISTS incidents (
                tenant_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                correlation_key TEXT NOT NULL,
                incident_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, incident_id),
                UNIQUE (tenant_id, correlation_key)
            );
            CREATE TABLE IF NOT EXISTS metric_samples (
                tenant_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_time TEXT NOT NULL,
                value REAL,
                quality TEXT NOT NULL,
                PRIMARY KEY (tenant_id, event_id)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                tenant_id TEXT NOT NULL,
                logical_notification_id TEXT NOT NULL,
                proposal_json TEXT NOT NULL,
                routing_json TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_receipt_json TEXT,
                state_version INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (tenant_id, logical_notification_id)
            );
            CREATE TABLE IF NOT EXISTS delivery_attempts (
                tenant_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                logical_notification_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                attempt_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, attempt_id),
                UNIQUE (tenant_id, logical_notification_id, attempt_number)
            );
            CREATE TABLE IF NOT EXISTS digest_items (
                tenant_id TEXT NOT NULL,
                digest_item_id TEXT NOT NULL,
                item_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, digest_item_id)
            );
            CREATE TABLE IF NOT EXISTS escalations (
                tenant_id TEXT NOT NULL,
                escalation_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                logical_notification_id TEXT NOT NULL,
                due_at TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (tenant_id, escalation_id)
            );
            CREATE TABLE IF NOT EXISTS delivery_rate (
                tenant_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                delivered_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS incident_usage (
                tenant_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                model_calls INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tenant_id, incident_id)
            );
            CREATE TABLE IF NOT EXISTS dead_letters (
                tenant_id TEXT NOT NULL,
                logical_notification_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, logical_notification_id)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                metadata_digest TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )

    def audit(
        self,
        event_type: AuditEventType,
        *,
        tenant_id: str,
        subject_id: str,
        reason_code: str,
        safe_metadata: Mapping[str, Any],
        now: datetime,
    ) -> None:
        self.connection.execute(
            """INSERT INTO audit_log
               (tenant_id, event_type, subject_id, reason_code, metadata_digest, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                event_type.value,
                subject_id,
                reason_code,
                canonical_digest(safe_metadata),
                now.isoformat(),
            ),
        )

    def audit_events(self, tenant_id: str) -> tuple[sqlite3.Row, ...]:
        rows = self.connection.execute(
            "SELECT * FROM audit_log WHERE tenant_id = ? ORDER BY audit_id",
            (tenant_id,),
        ).fetchall()
        return tuple(rows)

    def claim_dedupe(
        self,
        *,
        tenant_id: str,
        dedupe_key: str,
        owner_id: str,
        expires_at: datetime,
        now: datetime,
    ) -> bool:
        """Atomic conditional insert: SQLite analogue of SET key value NX EX."""

        with self.connection:
            self.connection.execute(
                "DELETE FROM dedupe_claims WHERE tenant_id = ? AND expires_at <= ?",
                (tenant_id, now.isoformat()),
            )
            cursor = self.connection.execute(
                """INSERT OR IGNORE INTO dedupe_claims
                   (tenant_id, dedupe_key, owner_id, expires_at)
                   VALUES (?, ?, ?, ?)""",
                (tenant_id, dedupe_key, owner_id, expires_at.isoformat()),
            )
        return cursor.rowcount == 1

    def record_event(self, event: EventEnvelope) -> tuple[bool, str | None]:
        """Atomically claim a source event; redelivery increments delivery_count."""

        with self.connection:
            cursor = self.connection.execute(
                """INSERT OR IGNORE INTO processed_events
                   (tenant_id, event_id, incident_id, event_json)
                   VALUES (?, ?, NULL, ?)""",
                (event.tenant_id, event.event_id, event.model_dump_json()),
            )
            if cursor.rowcount == 1:
                return True, None
            self.connection.execute(
                """UPDATE processed_events
                   SET delivery_count = delivery_count + 1
                   WHERE tenant_id = ? AND event_id = ?""",
                (event.tenant_id, event.event_id),
            )
            row = self.connection.execute(
                """SELECT incident_id FROM processed_events
                   WHERE tenant_id = ? AND event_id = ?""",
                (event.tenant_id, event.event_id),
            ).fetchone()
        return False, row["incident_id"] if row else None

    def bind_event_to_incident(
        self, event: EventEnvelope, incident_id: str
    ) -> None:
        self.connection.execute(
            """UPDATE processed_events SET incident_id = ?
               WHERE tenant_id = ? AND event_id = ?""",
            (incident_id, event.tenant_id, event.event_id),
        )

    def get_incident(
        self, tenant_id: str, incident_id: str
    ) -> IncidentAggregate | None:
        row = self.connection.execute(
            """SELECT incident_json FROM incidents
               WHERE tenant_id = ? AND incident_id = ?""",
            (tenant_id, incident_id),
        ).fetchone()
        return IncidentAggregate.model_validate_json(row[0]) if row else None

    def get_incident_by_correlation(
        self, tenant_id: str, correlation_key: str
    ) -> IncidentAggregate | None:
        row = self.connection.execute(
            """SELECT incident_json FROM incidents
               WHERE tenant_id = ?
                 AND (correlation_key = ? OR correlation_key LIKE ?)
               ORDER BY json_extract(incident_json, '$.last_seen') DESC
               LIMIT 1""",
            (tenant_id, correlation_key, f"{correlation_key}#%"),
        ).fetchone()
        return IncidentAggregate.model_validate_json(row[0]) if row else None

    def create_incident(self, incident: IncidentAggregate) -> bool:
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO incidents
               (tenant_id, incident_id, correlation_key, incident_json)
               VALUES (?, ?, ?, ?)""",
            (
                incident.tenant_id,
                incident.incident_id,
                incident.correlation_key,
                incident.model_dump_json(),
            ),
        )
        return cursor.rowcount == 1

    def update_incident(
        self, incident: IncidentAggregate, *, expected_version: int
    ) -> IncidentAggregate:
        updated = incident.model_copy(update={"state_version": expected_version + 1})
        cursor = self.connection.execute(
            """UPDATE incidents SET incident_json = ?
               WHERE tenant_id = ? AND incident_id = ?
               AND json_extract(incident_json, '$.state_version') = ?""",
            (
                updated.model_dump_json(),
                updated.tenant_id,
                updated.incident_id,
                expected_version,
            ),
        )
        if cursor.rowcount != 1:
            raise ProactivePolicyError("STATE_VERSION_CONFLICT")
        return updated

    def record_metric_sample(self, event: EventEnvelope, incident_id: str) -> None:
        self.connection.execute(
            """INSERT OR IGNORE INTO metric_samples
               (tenant_id, incident_id, event_id, event_time, value, quality)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event.tenant_id,
                incident_id,
                event.event_id,
                event.event_time.isoformat(),
                event.safe_facts.get("value"),
                str(event.safe_facts.get("quality", SensorQuality.GOOD.value)),
            ),
        )

    def sustained_duration(
        self,
        *,
        tenant_id: str,
        incident_id: str,
        threshold: float,
        direction: str,
    ) -> float:
        rows = self.connection.execute(
            """SELECT event_time, value, quality FROM metric_samples
               WHERE tenant_id = ? AND incident_id = ? ORDER BY event_time DESC""",
            (tenant_id, incident_id),
        ).fetchall()
        matching: list[datetime] = []
        for row in rows:
            if row["quality"] != SensorQuality.GOOD.value or row["value"] is None:
                break
            value = float(row["value"])
            passes = value >= threshold if direction == "above" else value <= threshold
            if not passes:
                break
            matching.append(datetime.fromisoformat(row["event_time"]))
        if len(matching) < 2:
            return 0.0
        return (max(matching) - min(matching)).total_seconds()

    def save_notification(
        self, proposal: NotificationProposal, routing: RoutingDecision
    ) -> bool:
        status = (
            NotificationStatus.DEFERRED
            if routing.action in {RoutingAction.DEFER, RoutingAction.DIGEST}
            else NotificationStatus.ROUTED
        )
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO notifications
               (tenant_id, logical_notification_id, proposal_json, routing_json, status)
               VALUES (?, ?, ?, ?, ?)""",
            (
                proposal.tenant_id,
                proposal.logical_notification_id,
                proposal.model_dump_json(),
                routing.model_dump_json(),
                status.value,
            ),
        )
        return cursor.rowcount == 1

    def load_notification(
        self, tenant_id: str, logical_notification_id: str
    ) -> tuple[NotificationProposal, RoutingDecision, sqlite3.Row]:
        row = self.connection.execute(
            """SELECT * FROM notifications
               WHERE tenant_id = ? AND logical_notification_id = ?""",
            (tenant_id, logical_notification_id),
        ).fetchone()
        if row is None:
            raise ProactivePolicyError("NOTIFICATION_NOT_FOUND")
        return (
            NotificationProposal.model_validate_json(row["proposal_json"]),
            RoutingDecision.model_validate_json(row["routing_json"]),
            row,
        )

    def update_notification(
        self,
        *,
        tenant_id: str,
        logical_notification_id: str,
        status: NotificationStatus,
        attempt_count: int,
        receipt: DeliveryReceipt | None,
    ) -> None:
        self.connection.execute(
            """UPDATE notifications SET status = ?, attempt_count = ?,
               last_receipt_json = ?, state_version = state_version + 1
               WHERE tenant_id = ? AND logical_notification_id = ?""",
            (
                status.value,
                attempt_count,
                receipt.model_dump_json() if receipt else None,
                tenant_id,
                logical_notification_id,
            ),
        )

    def cancel_pending_notifications(self, tenant_id: str, incident_id: str) -> None:
        rows = self.connection.execute(
            "SELECT logical_notification_id, proposal_json, status FROM notifications WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchall()
        terminal = {
            NotificationStatus.DELIVERED.value,
            NotificationStatus.ACKNOWLEDGED.value,
            NotificationStatus.CANCELLED.value,
            NotificationStatus.SUPERSEDED.value,
        }
        for row in rows:
            proposal = NotificationProposal.model_validate_json(row["proposal_json"])
            if proposal.incident_id == incident_id and row["status"] not in terminal:
                self.connection.execute(
                    """UPDATE notifications SET status = ?, state_version = state_version + 1
                       WHERE tenant_id = ? AND logical_notification_id = ?""",
                    (
                        NotificationStatus.CANCELLED.value,
                        tenant_id,
                        row["logical_notification_id"],
                    ),
                )

    def save_delivery_attempt(self, attempt: DeliveryAttempt) -> None:
        self.connection.execute(
            """INSERT INTO delivery_attempts
               (tenant_id, attempt_id, logical_notification_id,
                attempt_number, attempt_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                attempt.tenant_id,
                attempt.attempt_id,
                attempt.logical_notification_id,
                attempt.attempt_number,
                attempt.model_dump_json(),
            ),
        )

    def delivery_attempts(
        self, tenant_id: str, logical_notification_id: str
    ) -> tuple[DeliveryAttempt, ...]:
        rows = self.connection.execute(
            """SELECT attempt_json FROM delivery_attempts
               WHERE tenant_id = ? AND logical_notification_id = ?
               ORDER BY attempt_number""",
            (tenant_id, logical_notification_id),
        ).fetchall()
        return tuple(DeliveryAttempt.model_validate_json(row[0]) for row in rows)

    def save_digest_item(self, item: DigestItem) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO digest_items
               (tenant_id, digest_item_id, item_json) VALUES (?, ?, ?)""",
            (item.tenant_id, item.digest_item_id, item.model_dump_json()),
        )

    def digest_items(
        self, tenant_id: str, recipient_id: str
    ) -> tuple[DigestItem, ...]:
        rows = self.connection.execute(
            "SELECT item_json FROM digest_items WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchall()
        items = tuple(DigestItem.model_validate_json(row[0]) for row in rows)
        return tuple(item for item in items if item.recipient_id == recipient_id)

    def update_digest_for_incident(
        self, tenant_id: str, incident_id: str, status: DigestStatus
    ) -> None:
        rows = self.connection.execute(
            "SELECT item_json FROM digest_items WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchall()
        for row in rows:
            item = DigestItem.model_validate_json(row[0])
            if item.incident_id == incident_id:
                self.save_digest_item(
                    item.model_copy(
                        update={"status": status, "state_version": item.state_version + 1}
                    )
                )

    def schedule_escalations(
        self,
        *,
        proposal: NotificationProposal,
        policy: EscalationPolicy,
        now: datetime,
    ) -> None:
        for index, role in enumerate(policy.escalation_roles, start=1):
            due_at = now + timedelta(
                seconds=policy.acknowledgment_timeout_seconds * index
            )
            self.connection.execute(
                """INSERT OR IGNORE INTO escalations
                   (tenant_id, escalation_id, incident_id,
                    logical_notification_id, due_at, role, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'SCHEDULED')""",
                (
                    proposal.tenant_id,
                    f"escalation-{proposal.incident_id}-{index}",
                    proposal.incident_id,
                    proposal.logical_notification_id,
                    due_at.isoformat(),
                    role,
                ),
            )

    def cancel_escalations(self, tenant_id: str, incident_id: str) -> None:
        self.connection.execute(
            """UPDATE escalations SET status = 'CANCELLED'
               WHERE tenant_id = ? AND incident_id = ? AND status = 'SCHEDULED'""",
            (tenant_id, incident_id),
        )

    def due_escalations(self, tenant_id: str, now: datetime) -> tuple[sqlite3.Row, ...]:
        rows = self.connection.execute(
            """SELECT * FROM escalations
               WHERE tenant_id = ? AND status = 'SCHEDULED' AND due_at <= ?
               ORDER BY due_at""",
            (tenant_id, now.isoformat()),
        ).fetchall()
        return tuple(rows)

    def mark_escalation_sent(self, tenant_id: str, escalation_id: str) -> None:
        self.connection.execute(
            """UPDATE escalations SET status = 'SENT'
               WHERE tenant_id = ? AND escalation_id = ?""",
            (tenant_id, escalation_id),
        )

    def recent_delivery_count(
        self,
        tenant_id: str,
        recipient_id: str,
        channel: str,
        since: datetime,
    ) -> int:
        row = self.connection.execute(
            """SELECT COUNT(*) AS count FROM delivery_rate
               WHERE tenant_id = ? AND recipient_id = ? AND channel = ?
               AND delivered_at >= ?""",
            (tenant_id, recipient_id, channel, since.isoformat()),
        ).fetchone()
        return int(row["count"])

    def record_delivery_rate(
        self, tenant_id: str, recipient_id: str, channel: str, now: datetime
    ) -> None:
        self.connection.execute(
            """INSERT INTO delivery_rate
               (tenant_id, recipient_id, channel, delivered_at)
               VALUES (?, ?, ?, ?)""",
            (tenant_id, recipient_id, channel, now.isoformat()),
        )

    def model_call_count(self, tenant_id: str, incident_id: str) -> int:
        row = self.connection.execute(
            """SELECT model_calls FROM incident_usage
               WHERE tenant_id = ? AND incident_id = ?""",
            (tenant_id, incident_id),
        ).fetchone()
        return int(row["model_calls"]) if row else 0

    def consume_model_call(
        self, *, tenant_id: str, incident_id: str, maximum_calls: int
    ) -> int:
        """Atomically consume a durable per-incident model-call budget."""

        with self.connection:
            self.connection.execute(
                """INSERT OR IGNORE INTO incident_usage
                   (tenant_id, incident_id, model_calls) VALUES (?, ?, 0)""",
                (tenant_id, incident_id),
            )
            cursor = self.connection.execute(
                """UPDATE incident_usage SET model_calls = model_calls + 1
                   WHERE tenant_id = ? AND incident_id = ? AND model_calls < ?""",
                (tenant_id, incident_id, maximum_calls),
            )
            row = self.connection.execute(
                """SELECT model_calls FROM incident_usage
                   WHERE tenant_id = ? AND incident_id = ?""",
                (tenant_id, incident_id),
            ).fetchone()
        if cursor.rowcount != 1:
            raise ProactivePolicyError("MODEL_CALL_BUDGET_EXHAUSTED")
        return int(row["model_calls"])


def metric_event(
    event_id: str,
    *,
    value: float | None,
    event_time: datetime,
    sequence: int,
    tenant_id: str = TENANT,
    quality: SensorQuality = SensorQuality.GOOD,
    affected_customer_pct: float = 25,
    correlation_key: str = "eu-checkout-error-rate",
    free_text: str | None = None,
) -> EventEnvelope:
    facts: dict[str, Any] = {
        "service": "checkout",
        "metric": "error_rate",
        "region": "eu-west-1",
        "environment": "production",
        "value": value,
        "quality": quality.value,
        "affected_customer_pct": affected_customer_pct,
    }
    if free_text is not None:
        facts["message"] = free_text
    return build_event(
        event_id=event_id,
        source="northstar-otel",
        source_version="otel-v7",
        tenant_id=tenant_id,
        event_type=EventType.METRIC_OBSERVATION,
        event_time=event_time,
        received_at=max(event_time, FIXED_TIME),
        correlation_key=correlation_key,
        sequence=sequence,
        safe_facts=facts,
    )


def recovery_event(
    event_id: str,
    *,
    event_time: datetime,
    sequence: int,
    correlation_key: str = "eu-checkout-error-rate",
) -> EventEnvelope:
    return build_event(
        event_id=event_id,
        source="northstar-otel",
        source_version="otel-v7",
        tenant_id=TENANT,
        event_type=EventType.INCIDENT_RECOVERED,
        event_time=event_time,
        received_at=event_time,
        correlation_key=correlation_key,
        sequence=sequence,
        safe_facts={"service": "checkout", "region": "eu-west-1"},
    )


def default_trigger_policy() -> TriggerPolicy:
    return TriggerPolicy(
        policy_id="checkout-error-policy",
        tenant_id=TENANT,
        event_type=EventType.METRIC_OBSERVATION,
        metric_name="error_rate",
        activation_threshold=0.30,
        recovery_threshold=0.10,
        sustain_duration_seconds=120,
        recovery_duration_seconds=120,
        minimum_severity=Severity.P2,
        allowed_proactive_action=ProactiveActionType.NOTIFY,
        required_capabilities=("notify.oncall",),
        cooldown_seconds=900,
    )


def default_preference(
    *,
    tenant_id: str = TENANT,
    recipient_id: str = "northstar-primary-1",
    timezone: str = "America/Vancouver",
    opted_out_categories: tuple[str, ...] = (),
) -> RecipientPreference:
    return RecipientPreference(
        tenant_id=tenant_id,
        recipient_id=recipient_id,
        timezone=timezone,
        preferred_channel="slack",
        digest_channel="email",
        opted_out_categories=opted_out_categories,
    )


def on_call_assignment(
    *,
    recipient_id: str = "northstar-primary-1",
    tenant_id: str = TENANT,
    role: str = "on_call_primary",
    channel: str = "pagerduty",
    valid_from: datetime = FIXED_TIME - timedelta(hours=8),
    valid_until: datetime = FIXED_TIME + timedelta(hours=8),
) -> OnCallAssignment:
    return OnCallAssignment(
        tenant_id=tenant_id,
        schedule_id="northstar-checkout-primary",
        role=role,
        recipient_id=recipient_id,
        valid_from=valid_from,
        valid_until=valid_until,
        channel=channel,
    )


class ProactiveEngine:
    def __init__(
        self,
        store: DurableProactiveStore,
        *,
        authenticated_tenant: str = TENANT,
        trusted_sources: Mapping[str, Sequence[str]] = TRUSTED_SOURCES,
        actor_capabilities: Sequence[str] = DEFAULT_ACTOR_CAPABILITIES,
        model_call_budget_per_incident: int = 2,
    ) -> None:
        self.store = store
        self.authenticated_tenant = authenticated_tenant
        self.trusted_sources = trusted_sources
        self.actor_capabilities = tuple(actor_capabilities)
        self.model_call_budget_per_incident = model_call_budget_per_incident

    def apply_backpressure(
        self,
        event: EventEnvelope,
        *,
        queue_depth: int,
        consumer_lag_seconds: int,
        policy: BackpressurePolicy,
        now: datetime,
    ) -> BackpressureDecision:
        decision = evaluate_backpressure(
            event,
            queue_depth=queue_depth,
            consumer_lag_seconds=consumer_lag_seconds,
            policy=policy,
        )
        if decision.action is BackpressureAction.SHED:
            self.store.audit(
                AuditEventType.EVENT_SHED,
                tenant_id=event.tenant_id,
                subject_id=event.event_id,
                reason_code=decision.reason_codes[0],
                safe_metadata={
                    "severity": derive_severity(event).value,
                    "queue_depth": queue_depth,
                    "consumer_lag_seconds": consumer_lag_seconds,
                    "policy_version": policy.policy_version,
                    "event_count": 1,
                },
                now=now,
            )
        return decision

    def _new_incident(
        self,
        event: EventEnvelope,
        severity: Severity,
        *,
        correlation_key: str | None = None,
    ) -> IncidentAggregate:
        service = str(event.safe_facts.get("service", "unknown"))
        instance_key = correlation_key or event.correlation_key
        return IncidentAggregate(
            incident_id=f"incident-{canonical_digest((event.tenant_id, instance_key))[:16]}",
            tenant_id=event.tenant_id,
            correlation_key=instance_key,
            first_seen=event.event_time,
            last_seen=event.event_time,
            occurrence_count=1,
            duplicate_delivery_count=0,
            severity=severity,
            affected_services=(service,),
            status=IncidentStatus.NORMAL,
            state_version=1,
            last_sequence=event.sequence,
            last_event_time=event.event_time,
        )

    def _update_occurrence(
        self,
        incident: IncidentAggregate,
        event: EventEnvelope,
        severity: Severity,
        *,
        transport_duplicate: bool,
    ) -> IncidentAggregate:
        service = str(event.safe_facts.get("service", "unknown"))
        updated = incident.model_copy(
            update={
                "last_seen": max(incident.last_seen, event.event_time),
                "last_event_time": max(incident.last_event_time, event.event_time),
                "last_sequence": max(incident.last_sequence, event.sequence),
                "occurrence_count": incident.occurrence_count
                + int(not transport_duplicate),
                "duplicate_delivery_count": incident.duplicate_delivery_count
                + int(transport_duplicate),
                "severity": (
                    severity if is_more_severe(severity, incident.severity) else incident.severity
                ),
                "affected_services": tuple(
                    sorted(set(incident.affected_services) | {service})
                ),
            }
        )
        return self.store.update_incident(
            updated, expected_version=incident.state_version
        )

    def process_event(
        self,
        event: EventEnvelope,
        *,
        policy: TriggerPolicy,
        preference: RecipientPreference,
        on_call: OnCallAssignment,
        now: datetime,
    ) -> ProactiveRunState:
        try:
            admit_event(
                event,
                authenticated_tenant=self.authenticated_tenant,
                trusted_sources=self.trusted_sources,
                now=now,
            )
            if policy.tenant_id != event.tenant_id:
                raise ProactivePolicyError("TRIGGER_POLICY_TENANT_MISMATCH")
            if event.event_type not in {
                policy.event_type,
                EventType.INCIDENT_RECOVERED,
            }:
                raise ProactivePolicyError("TRIGGER_POLICY_EVENT_TYPE_MISMATCH")
        except ProactivePolicyError as error:
            code = str(error)
            self.store.audit(
                AuditEventType.EVENT_REJECTED,
                tenant_id=event.tenant_id,
                subject_id=event.event_id,
                reason_code=code,
                safe_metadata={"payload_digest": event.payload_digest},
                now=now,
            )
            return ProactiveRunState(
                run_id=f"run-{event.event_id}",
                event_status=(EventStatus.STALE if code == "STALE_EVENT" else EventStatus.REJECTED),
                incident_id=None,
                trigger_status=None,
                notification_id=None,
                suppression_reason=(
                    SuppressionReason.STALE_EVENT if code == "STALE_EVENT" else None
                ),
                model_calls=0,
                terminal_reason=code,
            )

        self.store.audit(
            AuditEventType.EVENT_ADMITTED,
            tenant_id=event.tenant_id,
            subject_id=event.event_id,
            reason_code="EVENT_POLICY_VALID",
            safe_metadata={"payload_digest": event.payload_digest},
            now=now,
        )
        is_new, existing_incident_id = self.store.record_event(event)
        if not is_new:
            incident = (
                self.store.get_incident(event.tenant_id, existing_incident_id)
                if existing_incident_id
                else None
            )
            if incident is not None:
                incident = self._update_occurrence(
                    incident,
                    event,
                    derive_severity(event),
                    transport_duplicate=True,
                )
            self.store.audit(
                AuditEventType.EVENT_DUPLICATED,
                tenant_id=event.tenant_id,
                subject_id=event.event_id,
                reason_code="SOURCE_EVENT_ALREADY_PROCESSED",
                safe_metadata={"incident_id": existing_incident_id},
                now=now,
            )
            return ProactiveRunState(
                run_id=f"run-{event.event_id}-duplicate",
                event_status=EventStatus.DUPLICATE,
                incident_id=existing_incident_id,
                trigger_status=TriggerStatus.SUPPRESSED,
                notification_id=None,
                suppression_reason=SuppressionReason.DUPLICATE,
                model_calls=0,
                terminal_reason="SOURCE_EVENT_ALREADY_PROCESSED",
            )

        fingerprint = fingerprint_event(event)
        severity = derive_severity(event)
        incident = self.store.get_incident_by_correlation(
            event.tenant_id, event.correlation_key
        )
        if incident is None:
            candidate = self._new_incident(event, severity)
            if self.store.create_incident(candidate):
                incident = candidate
            else:
                incident = self.store.get_incident_by_correlation(
                    event.tenant_id, event.correlation_key
                )
                if incident is None:
                    raise ProactivePolicyError("INCIDENT_CORRELATION_RACE")
                incident = self._update_occurrence(
                    incident, event, severity, transport_duplicate=False
                )
        else:
            if event.sequence <= incident.last_sequence:
                self.store.bind_event_to_incident(event, incident.incident_id)
                return ProactiveRunState(
                    run_id=f"run-{event.event_id}-out-of-order",
                    event_status=EventStatus.OUT_OF_ORDER,
                    incident_id=incident.incident_id,
                    trigger_status=TriggerStatus.SUPPRESSED,
                    notification_id=None,
                    suppression_reason=SuppressionReason.OUT_OF_ORDER,
                    model_calls=0,
                    terminal_reason="OUT_OF_ORDER_EVENT",
                )
            if (
                incident.status is IncidentStatus.RESOLVED
                and incident.resolved_at is not None
                and event.event_time <= incident.resolved_at
            ):
                self.store.bind_event_to_incident(event, incident.incident_id)
                return ProactiveRunState(
                    run_id=f"run-{event.event_id}-stale",
                    event_status=EventStatus.STALE,
                    incident_id=incident.incident_id,
                    trigger_status=TriggerStatus.SUPPRESSED,
                    notification_id=None,
                    suppression_reason=SuppressionReason.STALE_EVENT,
                    model_calls=0,
                    terminal_reason="STALE_EVENT_CANNOT_REOPEN_INCIDENT",
                )
            outside_window = event.event_time > incident.last_seen + timedelta(
                seconds=policy.correlation_window_seconds
            )
            after_resolution = (
                incident.status is IncidentStatus.RESOLVED
                and incident.resolved_at is not None
                and event.event_time > incident.resolved_at
            )
            if outside_window or after_resolution:
                incident = self._new_incident(
                    event,
                    severity,
                    correlation_key=f"{event.correlation_key}#{event.event_id}",
                )
                if not self.store.create_incident(incident):
                    canonical = self.store.get_incident_by_correlation(
                        event.tenant_id, event.correlation_key
                    )
                    if canonical is None:
                        raise ProactivePolicyError("INCIDENT_CORRELATION_RACE")
                    incident = self._update_occurrence(
                        canonical, event, severity, transport_duplicate=False
                    )
            else:
                incident = self._update_occurrence(
                    incident, event, severity, transport_duplicate=False
                )
        self.store.bind_event_to_incident(event, incident.incident_id)
        self.store.audit(
            AuditEventType.INCIDENT_CORRELATED,
            tenant_id=event.tenant_id,
            subject_id=incident.incident_id,
            reason_code="CORRELATION_KEY_MATCHED",
            safe_metadata={
                "event_id": event.event_id,
                "fingerprint_version": fingerprint.fingerprint_version,
            },
            now=now,
        )

        if event.event_type is EventType.INCIDENT_RECOVERED:
            return self.resolve_incident(
                event.tenant_id, incident.incident_id, now=now, event_id=event.event_id
            )

        if event.event_type is not EventType.METRIC_OBSERVATION:
            decision = self._non_metric_decision(event, incident, policy, now)
        else:
            self.store.record_metric_sample(event, incident.incident_id)
            breach_duration = self.store.sustained_duration(
                tenant_id=event.tenant_id,
                incident_id=incident.incident_id,
                threshold=float(policy.activation_threshold or 0),
                direction="above",
            )
            recovery_duration = self.store.sustained_duration(
                tenant_id=event.tenant_id,
                incident_id=incident.incident_id,
                threshold=float(policy.recovery_threshold or 0),
                direction="below",
            )
            decision = evaluate_metric_trigger(
                incident=incident,
                event=event,
                policy=policy,
                sustained_breach_seconds=breach_duration,
                sustained_recovery_seconds=recovery_duration,
                now=now,
            )

        if decision.status is TriggerStatus.RESOLVED:
            return self.resolve_incident(
                event.tenant_id, incident.incident_id, now=now, event_id=event.event_id
            )
        if (
            decision.status is TriggerStatus.ACTIVATED
            and not is_at_least(decision.severity, policy.minimum_severity)
        ):
            return ProactiveRunState(
                run_id=f"run-{event.event_id}-low-severity",
                event_status=EventStatus.ADMITTED,
                incident_id=incident.incident_id,
                trigger_status=TriggerStatus.SUPPRESSED,
                notification_id=None,
                suppression_reason=SuppressionReason.LOW_SEVERITY,
                model_calls=0,
                terminal_reason="BELOW_MINIMUM_SEVERITY",
            )
        if decision.status is not TriggerStatus.ACTIVATED:
            status = (
                IncidentStatus.PENDING
                if decision.status is TriggerStatus.PENDING
                else incident.status
            )
            if status is not incident.status:
                incident = self.store.update_incident(
                    incident.model_copy(update={"status": status}),
                    expected_version=incident.state_version,
                )
            return ProactiveRunState(
                run_id=f"run-{event.event_id}",
                event_status=EventStatus.ADMITTED,
                incident_id=incident.incident_id,
                trigger_status=decision.status,
                notification_id=None,
                suppression_reason=self._suppression_reason(decision),
                model_calls=0,
                terminal_reason=decision.reason_codes[0],
            )

        escalation = (
            incident.last_notified_severity is not None
            and is_more_severe(decision.severity, incident.last_notified_severity)
        )
        in_cooldown = (
            incident.last_notification_at is not None
            and now
            < incident.last_notification_at + timedelta(seconds=policy.cooldown_seconds)
        )
        required_action_capability = ACTION_CAPABILITIES[decision.proposed_action]
        if required_action_capability not in policy.required_capabilities:
            self.store.audit(
                AuditEventType.ACTION_DENIED,
                tenant_id=event.tenant_id,
                subject_id=event.event_id,
                reason_code="TRIGGER_POLICY_ACTION_REQUIREMENT_MISSING",
                safe_metadata={
                    "incident_id": incident.incident_id,
                    "proposed_action": decision.proposed_action.value,
                },
                now=now,
            )
            raise ProactivePolicyError("TRIGGER_POLICY_ACTION_REQUIREMENT_MISSING")
        missing_grants = tuple(
            capability
            for capability in policy.required_capabilities
            if capability not in self.actor_capabilities
        )
        if missing_grants:
            self.store.audit(
                AuditEventType.ACTION_DENIED,
                tenant_id=event.tenant_id,
                subject_id=event.event_id,
                reason_code="PROACTIVE_ACTION_CAPABILITY_DENIED",
                safe_metadata={
                    "incident_id": incident.incident_id,
                    "proposed_action": decision.proposed_action.value,
                    "missing_capabilities": missing_grants,
                },
                now=now,
            )
            raise ProactivePolicyError("PROACTIVE_ACTION_CAPABILITY_DENIED")
        authorize_proactive_action(
            decision.proposed_action,
            actor_capabilities=self.actor_capabilities,
        )
        fingerprint_claimed = self.store.claim_dedupe(
            tenant_id=event.tenant_id,
            dedupe_key=fingerprint.dedupe_key,
            owner_id=event.event_id,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )
        if not fingerprint_claimed:
            reason = (
                "SEVERITY_ESCALATION_BYPASS"
                if escalation
                else "FINGERPRINT_ALREADY_CLAIMED"
            )
            self.store.audit(
                (
                    AuditEventType.TRIGGER_ACTIVATED
                    if escalation
                    else AuditEventType.EVENT_DUPLICATED
                ),
                tenant_id=event.tenant_id,
                subject_id=event.event_id,
                reason_code=reason,
                safe_metadata={
                    "incident_id": incident.incident_id,
                    "fingerprint_version": fingerprint.fingerprint_version,
                },
                now=now,
            )
            if not escalation:
                return ProactiveRunState(
                    run_id=f"run-{event.event_id}-fingerprint-duplicate",
                    event_status=EventStatus.DUPLICATE,
                    incident_id=incident.incident_id,
                    trigger_status=TriggerStatus.SUPPRESSED,
                    notification_id=None,
                    suppression_reason=SuppressionReason.DUPLICATE,
                    model_calls=0,
                    terminal_reason="FINGERPRINT_ALREADY_CLAIMED",
                )
        if in_cooldown and not escalation and decision.severity is not Severity.P1:
            return ProactiveRunState(
                run_id=f"run-{event.event_id}-cooldown",
                event_status=EventStatus.ADMITTED,
                incident_id=incident.incident_id,
                trigger_status=TriggerStatus.SUPPRESSED,
                notification_id=None,
                suppression_reason=SuppressionReason.COOLDOWN,
                model_calls=0,
                terminal_reason="COOLDOWN",
            )
        incident = self.store.update_incident(
            incident.model_copy(
                update={
                    "status": IncidentStatus.ACTIVE,
                    "severity": decision.severity,
                    "last_notified_severity": decision.severity,
                    "last_notification_at": now,
                }
            ),
            expected_version=incident.state_version,
        )
        if decision.proposed_action is not ProactiveActionType.NOTIFY:
            self.store.audit(
                AuditEventType.TRIGGER_ACTIVATED,
                tenant_id=event.tenant_id,
                subject_id=decision.trigger_id,
                reason_code=decision.reason_codes[0],
                safe_metadata={"proposed_action": decision.proposed_action.value},
                now=now,
            )
            return ProactiveRunState(
                run_id=f"run-{event.event_id}",
                event_status=EventStatus.ADMITTED,
                incident_id=incident.incident_id,
                trigger_status=TriggerStatus.ACTIVATED,
                notification_id=None,
                suppression_reason=None,
                model_calls=0,
                terminal_reason=f"{decision.proposed_action.value}_PROPOSED",
            )
        proposal = self._notification_proposal(event, incident, decision, now)
        routing = route_notification(
            proposal, preference=preference, on_call=on_call, now=now
        )
        created = self.store.save_notification(proposal, routing)
        if created and proposal.severity is Severity.P1:
            self.store.schedule_escalations(
                proposal=proposal,
                policy=EscalationPolicy(
                    policy_id="northstar-p1-escalation-v1",
                    tenant_id=proposal.tenant_id,
                    severity=Severity.P1,
                    acknowledgment_timeout_seconds=60,
                    escalation_roles=("incident_commander", "vp_engineering"),
                ),
                now=now,
            )
        if routing.action is RoutingAction.DIGEST:
            self.store.save_digest_item(
                DigestItem(
                    digest_item_id=f"digest-{proposal.logical_notification_id}",
                    tenant_id=proposal.tenant_id,
                    recipient_id=routing.recipient_id,
                    incident_id=proposal.incident_id,
                    logical_notification_id=proposal.logical_notification_id,
                    status=DigestStatus.OPEN,
                    title=proposal.title,
                    occurrence_count=incident.occurrence_count,
                    deliver_at=routing.deliver_at,
                    state_version=1,
                )
            )
        self.store.audit(
            AuditEventType.TRIGGER_ACTIVATED,
            tenant_id=event.tenant_id,
            subject_id=decision.trigger_id,
            reason_code=decision.reason_codes[0],
            safe_metadata={"incident_id": incident.incident_id},
            now=now,
        )
        self.store.audit(
            (
                AuditEventType.NOTIFICATION_DEFERRED
                if routing.action is RoutingAction.DIGEST
                else AuditEventType.NOTIFICATION_PROPOSED
            ),
            tenant_id=event.tenant_id,
            subject_id=proposal.logical_notification_id,
            reason_code=routing.reason_codes[0],
            safe_metadata={"proposal_id": proposal.proposal_id},
            now=now,
        )
        return ProactiveRunState(
            run_id=f"run-{event.event_id}",
            event_status=EventStatus.ADMITTED,
            incident_id=incident.incident_id,
            trigger_status=TriggerStatus.ACTIVATED,
            notification_id=(proposal.logical_notification_id if created else None),
            suppression_reason=None,
            model_calls=0,
            terminal_reason="NOTIFICATION_PROPOSED",
        )

    @staticmethod
    def _suppression_reason(decision: TriggerDecision) -> SuppressionReason | None:
        mapping = {
            "HYSTERESIS_NOT_MET": SuppressionReason.HYSTERESIS_NOT_MET,
            "DEBOUNCE_NOT_MET": SuppressionReason.DEBOUNCE_NOT_MET,
            "SENSOR_QUALITY_INVALID": SuppressionReason.SENSOR_QUALITY_INVALID,
        }
        return mapping.get(decision.reason_codes[0])

    @staticmethod
    def _non_metric_decision(
        event: EventEnvelope,
        incident: IncidentAggregate,
        policy: TriggerPolicy,
        now: datetime,
    ) -> TriggerDecision:
        action = {
            EventType.CERTIFICATE_EXPIRY: ProactiveActionType.CREATE_TASK,
            EventType.EXPECTED_EVENT_MISSING: ProactiveActionType.START_READ_ONLY_INVESTIGATION,
            EventType.TREND_SIGNAL: ProactiveActionType.START_READ_ONLY_INVESTIGATION,
            EventType.PREDICTIVE_SIGNAL: ProactiveActionType.REQUEST_APPROVAL,
        }.get(event.event_type, policy.allowed_proactive_action)
        return TriggerDecision(
            trigger_id=f"trigger-{event.event_id}",
            tenant_id=event.tenant_id,
            incident_id=incident.incident_id,
            status=TriggerStatus.ACTIVATED,
            severity=derive_severity(event),
            proposed_action=action,
            reason_codes=(f"{event.event_type.value}_TRIGGER",),
            decided_at=now,
        )

    @staticmethod
    def _notification_proposal(
        event: EventEnvelope,
        incident: IncidentAggregate,
        decision: TriggerDecision,
        now: datetime,
    ) -> NotificationProposal:
        service = str(event.safe_facts.get("service", "service"))
        title = f"{decision.severity.value} {service} proactive incident"
        logical_id = f"notification-{incident.incident_id}-{decision.severity.value}"
        return NotificationProposal(
            proposal_id=f"proposal-{event.event_id}",
            logical_notification_id=logical_id,
            tenant_id=event.tenant_id,
            incident_id=incident.incident_id,
            recipient_scope="on_call_primary",
            severity=decision.severity,
            category="production_incident",
            title=title,
            evidence_ids=(event.event_id,),
            interruptible=decision.severity is not Severity.P1,
            delivery_deadline=now
            + timedelta(minutes=1 if decision.severity is Severity.P1 else 60),
            created_at=now,
        )

    def enrich_incident(
        self,
        incident: IncidentAggregate,
        *,
        model_available: bool,
    ) -> dict[str, Any]:
        calls = self.store.model_call_count(
            incident.tenant_id, incident.incident_id
        )
        if not model_available:
            return {
                "summary": "Deterministic incident template; enrichment unavailable.",
                "model_calls": calls,
                "proactive_action": "NONE",
            }
        calls = self.store.consume_model_call(
            tenant_id=incident.tenant_id,
            incident_id=incident.incident_id,
            maximum_calls=self.model_call_budget_per_incident,
        )
        return {
            "summary": (
                f"{incident.severity.value} incident affecting "
                f"{', '.join(incident.affected_services)}."
            ),
            "model_calls": calls,
            "proactive_action": "READ_ONLY_ENRICHMENT",
        }

    def resolve_incident(
        self,
        tenant_id: str,
        incident_id: str,
        *,
        now: datetime,
        event_id: str = "manual-resolution",
    ) -> ProactiveRunState:
        incident = self.store.get_incident(tenant_id, incident_id)
        if incident is None:
            raise ProactivePolicyError("INCIDENT_NOT_FOUND")
        incident = self.store.update_incident(
            incident.model_copy(
                update={"status": IncidentStatus.RESOLVED, "resolved_at": now}
            ),
            expected_version=incident.state_version,
        )
        self.store.cancel_escalations(tenant_id, incident_id)
        self.store.cancel_pending_notifications(tenant_id, incident_id)
        self.store.update_digest_for_incident(
            tenant_id, incident_id, DigestStatus.RESOLVED
        )
        self.store.audit(
            AuditEventType.INCIDENT_RESOLVED,
            tenant_id=tenant_id,
            subject_id=incident_id,
            reason_code="TRUSTED_RECOVERY_EVENT",
            safe_metadata={"event_id": event_id},
            now=now,
        )
        return ProactiveRunState(
            run_id=f"run-{event_id}",
            event_status=EventStatus.ADMITTED,
            incident_id=incident_id,
            trigger_status=TriggerStatus.RESOLVED,
            notification_id=None,
            suppression_reason=None,
            model_calls=0,
            terminal_reason="INCIDENT_RESOLVED",
        )


PROVIDER_ATTEMPT_COST_USD = {
    "pagerduty": 0.002,
    "sms": 0.01,
    "slack": 0.001,
    "email": 0.0005,
}


def _record_provider_attempt(
    store: DurableProactiveStore,
    *,
    tenant_id: str,
    logical_notification_id: str,
    recipient_id: str,
    channel: str,
    attempt_number: int,
    outcome: DeliveryStatus,
    now: datetime,
) -> DeliveryAttempt:
    provider_message_id = (
        f"provider-{canonical_digest((logical_notification_id, channel, attempt_number))[:16]}"
        if outcome is DeliveryStatus.DELIVERED
        else None
    )
    attempt = DeliveryAttempt(
        attempt_id=f"attempt-{logical_notification_id}-{attempt_number}",
        logical_notification_id=logical_notification_id,
        tenant_id=tenant_id,
        recipient_id=recipient_id,
        channel=channel,
        attempt_number=attempt_number,
        created_at=now,
        status=outcome,
        provider_message_id=provider_message_id,
        estimated_cost_usd=PROVIDER_ATTEMPT_COST_USD.get(channel, 0.001),
    )
    store.save_delivery_attempt(attempt)
    store.audit(
        AuditEventType.DELIVERY_ATTEMPTED,
        tenant_id=tenant_id,
        subject_id=attempt.attempt_id,
        reason_code=outcome.value,
        safe_metadata={
            "logical_notification_id": logical_notification_id,
            "channel": channel,
            "estimated_cost_usd": attempt.estimated_cost_usd,
        },
        now=now,
    )
    return attempt


def deliver_notification(
    store: DurableProactiveStore,
    *,
    tenant_id: str,
    logical_notification_id: str,
    preference: RecipientPreference,
    current_on_call: OnCallAssignment,
    provider_outcomes: Mapping[str, DeliveryStatus],
    now: datetime,
    max_attempts: int = 3,
    low_priority_hourly_limit: int = 3,
) -> DeliveryReceipt:
    """Idempotent delivery with typed policy deferral and provider attempts."""

    proposal, _, row = store.load_notification(tenant_id, logical_notification_id)
    if row["status"] in {
        NotificationStatus.CANCELLED.value,
        NotificationStatus.SUPERSEDED.value,
    }:
        raise ProactivePolicyError("DELIVERY_CANCELLED")
    if row["last_receipt_json"]:
        previous = DeliveryReceipt.model_validate_json(row["last_receipt_json"])
        if previous.status in {DeliveryStatus.DELIVERED, DeliveryStatus.RECONCILED}:
            return previous
        if previous.status is DeliveryStatus.UNKNOWN:
            raise ProactivePolicyError("DELIVERY_OUTCOME_UNKNOWN")

    routing = route_notification(
        proposal,
        preference=preference,
        on_call=current_on_call,
        now=now,
    )
    if routing.action in {RoutingAction.DIGEST, RoutingAction.DEFER} and now < routing.deliver_at:
        raise ProactivePolicyError("DELIVERY_NOT_DUE")
    if proposal.severity is not Severity.P1:
        recent = store.recent_delivery_count(
            tenant_id,
            routing.recipient_id,
            routing.channel,
            now - timedelta(hours=1),
        )
        if recent >= low_priority_hourly_limit:
            receipt = DeliveryReceipt(
                logical_notification_id=logical_notification_id,
                tenant_id=tenant_id,
                recipient_id=routing.recipient_id,
                channel=routing.channel,
                status=DeliveryStatus.DEFERRED,
                reason_codes=(SuppressionReason.RATE_LIMIT.value,),
            )
            store.update_notification(
                tenant_id=tenant_id,
                logical_notification_id=logical_notification_id,
                status=NotificationStatus.DEFERRED,
                attempt_count=int(row["attempt_count"]),
                receipt=receipt,
            )
            store.audit(
                AuditEventType.NOTIFICATION_DEFERRED,
                tenant_id=tenant_id,
                subject_id=logical_notification_id,
                reason_code=SuppressionReason.RATE_LIMIT.value,
                safe_metadata={"recipient_id": routing.recipient_id},
                now=now,
            )
            return receipt

    previous_attempts = int(row["attempt_count"])
    if previous_attempts >= max_attempts:
        raise ProactivePolicyError("DELIVERY_RETRIES_EXHAUSTED")
    primary_number = previous_attempts + 1
    primary_outcome = provider_outcomes.get(
        routing.channel, DeliveryStatus.TRANSIENT_FAILURE
    )
    final_attempt = _record_provider_attempt(
        store,
        tenant_id=tenant_id,
        logical_notification_id=logical_notification_id,
        recipient_id=routing.recipient_id,
        channel=routing.channel,
        attempt_number=primary_number,
        outcome=primary_outcome,
        now=now,
    )
    reason_codes: tuple[str, ...] = ()
    if (
        primary_outcome is DeliveryStatus.TRANSIENT_FAILURE
        and proposal.severity is Severity.P1
        and primary_number < max_attempts
    ):
        fallback = "pagerduty" if routing.channel != "pagerduty" else "sms"
        fallback_outcome = provider_outcomes.get(
            fallback, DeliveryStatus.TRANSIENT_FAILURE
        )
        final_attempt = _record_provider_attempt(
            store,
            tenant_id=tenant_id,
            logical_notification_id=logical_notification_id,
            recipient_id=routing.recipient_id,
            channel=fallback,
            attempt_number=primary_number + 1,
            outcome=fallback_outcome,
            now=now,
        )
        reason_codes = ("P1_FALLBACK_CHANNEL",)

    outcome = final_attempt.status
    receipt = DeliveryReceipt(
        logical_notification_id=logical_notification_id,
        tenant_id=tenant_id,
        recipient_id=routing.recipient_id,
        channel=final_attempt.channel,
        attempt_id=final_attempt.attempt_id,
        provider_message_id=final_attempt.provider_message_id,
        status=outcome,
        sent_at=now if outcome is DeliveryStatus.DELIVERED else None,
        reason_codes=reason_codes,
    )
    if outcome is DeliveryStatus.DELIVERED:
        notification_status = NotificationStatus.DELIVERED
        store.record_delivery_rate(
            tenant_id, routing.recipient_id, final_attempt.channel, now
        )
        store.audit(
            AuditEventType.NOTIFICATION_DELIVERED,
            tenant_id=tenant_id,
            subject_id=logical_notification_id,
            reason_code=reason_codes[0] if reason_codes else "PROVIDER_CONFIRMED",
            safe_metadata={"attempt_id": final_attempt.attempt_id},
            now=now,
        )
    elif outcome is DeliveryStatus.UNKNOWN:
        notification_status = NotificationStatus.DELIVERING
    elif outcome is DeliveryStatus.PERMANENT_FAILURE:
        notification_status = NotificationStatus.FAILED
        store.connection.execute(
            """INSERT OR IGNORE INTO dead_letters
               (tenant_id, logical_notification_id, reason, created_at)
               VALUES (?, ?, ?, ?)""",
            (tenant_id, logical_notification_id, "PERMANENT_FAILURE", now.isoformat()),
        )
    elif final_attempt.attempt_number >= max_attempts:
        receipt = receipt.model_copy(update={"status": DeliveryStatus.DEAD_LETTERED})
        notification_status = NotificationStatus.FAILED
        store.connection.execute(
            """INSERT OR IGNORE INTO dead_letters
               (tenant_id, logical_notification_id, reason, created_at)
               VALUES (?, ?, ?, ?)""",
            (tenant_id, logical_notification_id, "RETRIES_EXHAUSTED", now.isoformat()),
        )
    else:
        notification_status = NotificationStatus.SCHEDULED

    store.update_notification(
        tenant_id=tenant_id,
        logical_notification_id=logical_notification_id,
        status=notification_status,
        attempt_count=final_attempt.attempt_number,
        receipt=receipt,
    )
    if receipt.status in {
        DeliveryStatus.PERMANENT_FAILURE,
        DeliveryStatus.DEAD_LETTERED,
    }:
        store.audit(
            AuditEventType.DELIVERY_FAILED,
            tenant_id=tenant_id,
            subject_id=logical_notification_id,
            reason_code=receipt.status.value,
            safe_metadata={"attempt_id": receipt.attempt_id},
            now=now,
        )
    return receipt


def reconcile_unknown_delivery(
    store: DurableProactiveStore,
    *,
    tenant_id: str,
    logical_notification_id: str,
    provider_message_id: str,
    now: datetime,
) -> DeliveryReceipt:
    proposal, _, row = store.load_notification(tenant_id, logical_notification_id)
    if not row["last_receipt_json"]:
        raise ProactivePolicyError("DELIVERY_RECEIPT_MISSING")
    previous = DeliveryReceipt.model_validate_json(row["last_receipt_json"])
    if previous.status is not DeliveryStatus.UNKNOWN:
        raise ProactivePolicyError("DELIVERY_NOT_UNKNOWN")
    receipt = previous.model_copy(
        update={
            "status": DeliveryStatus.RECONCILED,
            "provider_message_id": provider_message_id,
            "sent_at": now,
            "reason_codes": ("PROVIDER_RECONCILED",),
        }
    )
    store.update_notification(
        tenant_id=tenant_id,
        logical_notification_id=logical_notification_id,
        status=NotificationStatus.DELIVERED,
        attempt_count=int(row["attempt_count"]),
        receipt=receipt,
    )
    store.record_delivery_rate(
        tenant_id, previous.recipient_id, previous.channel, now
    )
    return receipt


def acknowledge_incident(
    store: DurableProactiveStore,
    *,
    tenant_id: str,
    incident_id: str,
    now: datetime,
) -> IncidentAggregate:
    incident = store.get_incident(tenant_id, incident_id)
    if incident is None:
        raise ProactivePolicyError("INCIDENT_NOT_FOUND")
    updated = store.update_incident(
        incident.model_copy(update={"status": IncidentStatus.ACKNOWLEDGED}),
        expected_version=incident.state_version,
    )
    store.cancel_escalations(tenant_id, incident_id)
    store.audit(
        AuditEventType.ACKNOWLEDGED,
        tenant_id=tenant_id,
        subject_id=incident_id,
        reason_code="AUTHORIZED_ACKNOWLEDGMENT",
        safe_metadata={},
        now=now,
    )
    return updated


def execute_due_escalations(
    store: DurableProactiveStore,
    *,
    tenant_id: str,
    now: datetime,
    role_routes: Mapping[
        str, tuple[RecipientPreference, OnCallAssignment]
    ],
    provider_outcomes: Mapping[str, DeliveryStatus],
    actor_capabilities: Sequence[str] = DEFAULT_ACTOR_CAPABILITIES,
) -> tuple[DeliveryReceipt, ...]:
    """Turn due escalation state into the same typed delivery lifecycle."""

    receipts: list[DeliveryReceipt] = []
    for row in store.due_escalations(tenant_id, now):
        incident = store.get_incident(tenant_id, row["incident_id"])
        if incident is None or incident.status in {
            IncidentStatus.ACKNOWLEDGED,
            IncidentStatus.RESOLVED,
        }:
            store.cancel_escalations(tenant_id, row["incident_id"])
            continue
        if row["role"] not in role_routes:
            raise ProactivePolicyError("ESCALATION_ROUTE_MISSING")
        authorize_proactive_action(
            ProactiveActionType.NOTIFY,
            actor_capabilities=actor_capabilities,
        )
        preference, on_call = role_routes[row["role"]]
        logical_id = f"notification-{row['escalation_id']}"
        proposal = NotificationProposal(
            proposal_id=f"proposal-{row['escalation_id']}",
            logical_notification_id=logical_id,
            tenant_id=tenant_id,
            incident_id=incident.incident_id,
            recipient_scope=row["role"],
            severity=Severity.P1,
            category="production_incident_escalation",
            title=f"P1 escalation for {incident.incident_id}",
            evidence_ids=(row["logical_notification_id"],),
            interruptible=False,
            delivery_deadline=now + timedelta(minutes=1),
            created_at=now,
        )
        routing = route_notification(
            proposal, preference=preference, on_call=on_call, now=now
        )
        store.save_notification(proposal, routing)
        receipt = deliver_notification(
            store,
            tenant_id=tenant_id,
            logical_notification_id=logical_id,
            preference=preference,
            current_on_call=on_call,
            provider_outcomes=provider_outcomes,
            now=now,
        )
        receipts.append(receipt)
        if receipt.status in {DeliveryStatus.DELIVERED, DeliveryStatus.RECONCILED}:
            store.mark_escalation_sent(tenant_id, row["escalation_id"])
            store.audit(
                AuditEventType.ESCALATED,
                tenant_id=tenant_id,
                subject_id=row["escalation_id"],
                reason_code="ACKNOWLEDGMENT_TIMEOUT_DELIVERED",
                safe_metadata={
                    "role": row["role"],
                    "attempt_id": receipt.attempt_id,
                },
                now=now,
            )
    return tuple(receipts)


def dispatch_digest(
    store: DurableProactiveStore,
    *,
    tenant_id: str,
    recipient_id: str,
    now: datetime,
) -> tuple[str, ...]:
    """Aggregate due digest text only; this fixture does not call a provider."""
    summaries: list[str] = []
    for item in store.digest_items(tenant_id, recipient_id):
        if item.deliver_at > now or item.status in {
            DigestStatus.CANCELLED,
            DigestStatus.SUPERSEDED,
            DigestStatus.ESCALATED,
        }:
            continue
        suffix = (
            "occurred and resolved"
            if item.status is DigestStatus.RESOLVED
            else "remains open"
        )
        summaries.append(
            f"{item.title}: {suffix}; {item.occurrence_count} occurrence(s)."
        )
    return tuple(summaries)


def evaluation_fixture() -> dict[str, ProactiveMetrics]:
    """Labelled deterministic comparison—not a live-model quality benchmark."""

    cases = (
        # useful, critical, duplicate, detection seconds, delivery seconds
        (True, True, False, 5.0, 12.0),
        (True, False, False, 120.0, 180.0),
        (True, False, False, 60.0, 0.0),
        (False, False, False, 0.0, 3.0),
        (False, False, True, 0.0, 3.0),
        (False, False, True, 0.0, 3.0),
        (False, False, True, 0.0, 3.0),
        (False, False, False, 0.0, 3.0),
        (False, False, False, 0.0, 3.0),
        (False, False, False, 0.0, 3.0),
    )
    useful = sum(case[0] for case in cases)
    critical = sum(case[1] for case in cases)
    governed_delivered = useful
    governed = ProactiveMetrics(
        labelled_events=len(cases),
        trigger_true_positives=useful,
        trigger_false_positives=0,
        trigger_false_negatives=0,
        p1_events=critical,
        p1_misses=0,
        delivered_notifications=governed_delivered,
        useful_notifications=useful,
        duplicate_deliveries=0,
        model_calls=1,
        mean_detection_latency_seconds=sum(case[3] for case in cases if case[0])
        / useful,
        mean_notification_latency_seconds=sum(case[4] for case in cases if case[0])
        / useful,
        estimated_model_cost_usd=0.012,
        events_observed=len(cases),
        events_shed=0,
    )
    naive = ProactiveMetrics(
        labelled_events=len(cases),
        trigger_true_positives=useful,
        trigger_false_positives=len(cases) - useful,
        trigger_false_negatives=0,
        p1_events=critical,
        p1_misses=0,
        delivered_notifications=len(cases),
        useful_notifications=useful,
        duplicate_deliveries=sum(case[2] for case in cases),
        model_calls=len(cases),
        mean_detection_latency_seconds=0,
        mean_notification_latency_seconds=sum(case[4] for case in cases)
        / len(cases),
        estimated_model_cost_usd=0.12,
        events_observed=len(cases),
        events_shed=0,
    )
    return {"naive": naive, "governed": governed}


def demo_summary(database_path: str | Path = ":memory:") -> dict[str, Any]:
    store = DurableProactiveStore(database_path)
    engine = ProactiveEngine(store)
    policy = default_trigger_policy()
    preference = default_preference(timezone="UTC")
    on_call = on_call_assignment()
    runs = []
    for index, offset in enumerate((0, 60, 120), start=1):
        event_time = FIXED_TIME + timedelta(seconds=offset)
        runs.append(
            engine.process_event(
                metric_event(
                    f"checkout-{index}",
                    value=0.42,
                    event_time=event_time,
                    sequence=index,
                ),
                policy=policy,
                preference=preference,
                on_call=on_call.model_copy(
                    update={"valid_until": FIXED_TIME + timedelta(hours=12)}
                ),
                now=event_time,
            )
        )
    incident = store.get_incident_by_correlation(TENANT, "eu-checkout-error-rate")
    metrics = evaluation_fixture()
    summary = {
        "terminal_states": [run.terminal_reason for run in runs],
        "incident_status": incident.status.value if incident else None,
        "occurrence_count": incident.occurrence_count if incident else 0,
        "notification_id": runs[-1].notification_id,
        "model_calls_on_critical_path": runs[-1].model_calls,
        "governed_notification_precision": metrics["governed"].notification_precision,
        "naive_notifications": metrics["naive"].delivered_notifications,
        "governed_notifications": metrics["governed"].delivered_notifications,
        "production_side_effects": 0,
    }
    store.close()
    return summary


if __name__ == "__main__":
    print(json.dumps(demo_summary(), indent=2))
