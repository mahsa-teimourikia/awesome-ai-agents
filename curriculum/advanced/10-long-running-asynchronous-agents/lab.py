"""Credential-free durable workflow lab for Advanced 10.

The file-backed SQLite store models the transactional boundaries. Provider calls
occur only after the transaction that claims an operation has committed.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field

from policy import (
    POLICY_VERSION,
    STATE_SCHEMA_VERSION,
    WORKFLOW_VERSION,
    ApprovalReceipt,
    AttemptStatus,
    BudgetState,
    DurablePolicyError,
    EventEnvelope,
    EventType,
    FailureCode,
    FrozenModel,
    InboxStatus,
    OperationStatus,
    PreconditionSnapshot,
    Proposal,
    ReconciliationStatus,
    RunRecord,
    RunStatus,
    TERMINAL_STATUSES,
    TimeoutPolicy,
    TrustedExecutionContext,
    canonical_digest,
    event_signature,
    failure_is_retryable,
    payload_digest,
    stable_operation_id,
    validate_approval,
    validate_event,
    validate_transition,
)

FIXED_TIME = datetime(2026, 9, 20, 16, 0, tzinfo=UTC)
EVENT_SECRET = "credential-free-fixture-secret"
TENANT_ID = "northstar-commerce"
SUBJECT_ID = "customer-ada"


class EventDisposition(StrEnum):
    PROCESSED = "PROCESSED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    STALE = "STALE"


class OperationDisposition(StrEnum):
    CLAIMED = "CLAIMED"
    BUSY = "BUSY"
    ALREADY_SUCCEEDED = "ALREADY_SUCCEEDED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"


class ProviderOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    TRANSIENT_BEFORE_COMMIT = "TRANSIENT_BEFORE_COMMIT"
    TIMEOUT_AFTER_COMMIT = "TIMEOUT_AFTER_COMMIT"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


class EventProcessResult(FrozenModel):
    disposition: EventDisposition
    run_status: RunStatus
    state_version: int = Field(ge=0)
    reason_codes: tuple[str, ...]


class LeaseResult(FrozenModel):
    acquired: bool
    state_version: int = Field(ge=0)
    reason_code: str


class PreparedOperation(FrozenModel):
    disposition: OperationDisposition
    logical_operation_id: str
    attempt_id: str | None
    owner: str
    request_digest: str
    reason_code: str


class ProviderResult(FrozenModel):
    provider_operation_id: str
    logical_operation_id: str
    request_digest: str
    status: str


class ReconciliationResult(FrozenModel):
    status: ReconciliationStatus
    provider_result: ProviderResult | None = None


class BusinessEffectRecord(FrozenModel):
    logical_operation_id: str
    request_digest: str
    target_id: str
    amount_usd: int = Field(gt=0)
    provider_operation_id: str


class RefundLedger:
    """Independent deterministic read model; it is not the provider ledger."""

    def __init__(self) -> None:
        self.refunds: dict[str, BusinessEffectRecord] = {}

    def observe(
        self,
        provider_result: ProviderResult,
        *,
        target_id: str,
        amount_usd: int,
    ) -> BusinessEffectRecord:
        record = BusinessEffectRecord(
            logical_operation_id=provider_result.logical_operation_id,
            request_digest=provider_result.request_digest,
            target_id=target_id,
            amount_usd=amount_usd,
            provider_operation_id=provider_result.provider_operation_id,
        )
        self.refunds[provider_result.logical_operation_id] = record
        return record

    def query(self, logical_operation_id: str) -> BusinessEffectRecord | None:
        return self.refunds.get(logical_operation_id)


class EvaluationMetrics(FrozenModel):
    cases: int = Field(ge=0)
    safe_outcomes: int = Field(ge=0)
    unsafe_resumes: int = Field(ge=0)
    duplicate_effects: int = Field(ge=0)
    provider_calls: int = Field(ge=0)
    reconciliations: int = Field(ge=0)

    @property
    def safe_outcome_rate(self) -> float:
        return self.safe_outcomes / self.cases if self.cases else 0.0


class EvaluationReport(FrozenModel):
    case_ids: tuple[str, ...]
    baseline: EvaluationMetrics
    governed: EvaluationMetrics


class ProviderTransientError(RuntimeError):
    pass


class ProviderTimeoutAfterCommit(TimeoutError):
    pass


class ProviderTerminalError(RuntimeError):
    pass


def _iso(value: datetime) -> str:
    return value.isoformat()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class DurableStore:
    """File-backed state, inbox, outbox, timer, approval, and operation ledger."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    workflow_version TEXT NOT NULL,
                    state_schema_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    state_version INTEGER NOT NULL,
                    record_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transition_history (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    event_id TEXT,
                    state_version INTEGER NOT NULL,
                    occurred_at TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS inbox (
                    event_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    wait_generation INTEGER NOT NULL,
                    payload_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    processed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    message_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    published_at TEXT
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    receipt_json TEXT NOT NULL,
                    consumed_at TEXT,
                    consumed_by_event_id TEXT
                );
                CREATE TABLE IF NOT EXISTS timers (
                    timer_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    timeout_policy TEXT NOT NULL,
                    status TEXT NOT NULL,
                    fired_by_event_id TEXT
                );
                CREATE TABLE IF NOT EXISTS operations (
                    logical_operation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    provider_operation_id TEXT,
                    result_json TEXT,
                    owner TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    active_attempt_id TEXT,
                    dispatched_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS execution_receipts (
                    attempt_id TEXT PRIMARY KEY,
                    logical_operation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    provider_operation_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    failure_code TEXT
                );
                CREATE TABLE IF NOT EXISTS reconciliation_receipts (
                    reconciliation_id TEXT PRIMARY KEY,
                    logical_operation_id TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider_operation_id TEXT,
                    observed_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS inbox_source_event
                    ON inbox(source, source_event_id);
                """
            )

    @staticmethod
    def _record_json(run: RunRecord) -> str:
        return run.model_dump_json()

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecord:
        return RunRecord.model_validate_json(row["record_json"])

    def _load_tx(self, connection: sqlite3.Connection, run_id: str) -> RunRecord:
        row = connection.execute(
            "SELECT record_json FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise DurablePolicyError("RUN_NOT_FOUND")
        return self._row_to_run(row)

    def load_run(self, run_id: str) -> RunRecord:
        with self._connect() as connection:
            return self._load_tx(connection, run_id)

    def create_run(self, run: RunRecord) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO runs(
                       run_id, tenant_id, subject_id, workflow_version,
                       state_schema_version, status, state_version,
                       record_json, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.tenant_id,
                    run.subject_id,
                    run.workflow_version,
                    run.state_schema_version,
                    run.status.value,
                    run.state_version,
                    self._record_json(run),
                    _iso(run.updated_at),
                ),
            )
            self._append_history_tx(
                connection,
                run,
                from_status=None,
                event_id=None,
                reason_code="RUN_CREATED",
            )
            connection.commit()

    def _save_tx(
        self,
        connection: sqlite3.Connection,
        run: RunRecord,
        *,
        expected_version: int,
    ) -> None:
        cursor = connection.execute(
            """UPDATE runs
               SET status = ?, state_schema_version = ?, state_version = ?,
                   record_json = ?, updated_at = ?
               WHERE run_id = ? AND state_version = ?""",
            (
                run.status.value,
                run.state_schema_version,
                run.state_version,
                self._record_json(run),
                _iso(run.updated_at),
                run.run_id,
                expected_version,
            ),
        )
        if cursor.rowcount != 1:
            raise DurablePolicyError("STATE_VERSION_CONFLICT")

    def _append_history_tx(
        self,
        connection: sqlite3.Connection,
        run: RunRecord,
        *,
        from_status: RunStatus | None,
        event_id: str | None,
        reason_code: str,
    ) -> None:
        connection.execute(
            """INSERT INTO transition_history(
                   run_id, from_status, to_status, event_id, state_version,
                   occurred_at, reason_code
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run.run_id,
                from_status.value if from_status else None,
                run.status.value,
                event_id,
                run.state_version,
                _iso(run.updated_at),
                reason_code,
            ),
        )

    def _outbox_tx(
        self,
        connection: sqlite3.Connection,
        run: RunRecord,
        *,
        event_type: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        message_id = f"outbox:{run.run_id}:{run.state_version}:{event_type}"
        connection.execute(
            """INSERT INTO outbox(
                   message_id, run_id, event_type, payload_json, status, created_at
               ) VALUES (?, ?, ?, ?, 'PENDING', ?)""",
            (
                message_id,
                run.run_id,
                event_type,
                json.dumps(payload, sort_keys=True),
                _iso(now),
            ),
        )

    def _transition_tx(
        self,
        connection: sqlite3.Connection,
        run: RunRecord,
        target: RunStatus,
        *,
        now: datetime,
        event_id: str | None,
        reason_code: str,
        updates: dict[str, Any] | None = None,
        publish: bool = True,
    ) -> RunRecord:
        validate_transition(run.status, target)
        previous = run.status
        updated = run.model_copy(
            update={
                "status": target,
                "state_version": run.state_version + 1,
                "updated_at": now,
                **(updates or {}),
            }
        )
        self._save_tx(connection, updated, expected_version=run.state_version)
        self._append_history_tx(
            connection,
            updated,
            from_status=previous,
            event_id=event_id,
            reason_code=reason_code,
        )
        if publish:
            self._outbox_tx(
                connection,
                updated,
                event_type="RUN_STATE_CHANGED",
                payload={
                    "run_id": updated.run_id,
                    "status": updated.status.value,
                    "state_version": updated.state_version,
                },
                now=now,
            )
        return updated

    def _update_in_place_tx(
        self,
        connection: sqlite3.Connection,
        run: RunRecord,
        *,
        now: datetime,
        event_id: str | None,
        reason_code: str,
        updates: dict[str, Any],
    ) -> RunRecord:
        """CAS-update control metadata without pretending the state changed."""

        updated = run.model_copy(
            update={
                **updates,
                "state_version": run.state_version + 1,
                "updated_at": now,
            }
        )
        self._save_tx(connection, updated, expected_version=run.state_version)
        self._append_history_tx(
            connection,
            updated,
            from_status=run.status,
            event_id=event_id,
            reason_code=reason_code,
        )
        self._outbox_tx(
            connection,
            updated,
            event_type="RUN_CONTROL_CHANGED",
            payload={
                "run_id": updated.run_id,
                "status": updated.status.value,
                "state_version": updated.state_version,
                "reason_code": reason_code,
            },
            now=now,
        )
        return updated

    def migrate_run(
        self,
        run_id: str,
        migrator: Callable[[RunRecord], RunRecord],
        *,
        now: datetime,
    ) -> RunRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, run_id)
            migrated = migrator(run)
            if migrated.run_id != run.run_id or migrated.status is not run.status:
                raise DurablePolicyError("STATE_MIGRATION_CHANGED_IDENTITY_OR_STATUS")
            if migrated.state_schema_version <= run.state_schema_version:
                raise DurablePolicyError("STATE_MIGRATION_DID_NOT_ADVANCE_SCHEMA")
            updated = migrated.model_copy(
                update={
                    "state_version": run.state_version + 1,
                    "updated_at": now,
                }
            )
            self._save_tx(connection, updated, expected_version=run.state_version)
            self._append_history_tx(
                connection,
                updated,
                from_status=run.status,
                event_id=None,
                reason_code=(
                    f"STATE_SCHEMA_MIGRATED_V{run.state_schema_version}_TO_"
                    f"V{updated.state_schema_version}"
                ),
            )
            connection.commit()
            return updated

    def transition(
        self,
        run_id: str,
        expected_version: int,
        target: RunStatus,
        *,
        now: datetime,
        reason_code: str,
        updates: dict[str, Any] | None = None,
    ) -> RunRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, run_id)
            if run.state_version != expected_version:
                raise DurablePolicyError("STATE_VERSION_CONFLICT")
            updated = self._transition_tx(
                connection,
                run,
                target,
                now=now,
                event_id=None,
                reason_code=reason_code,
                updates=updates,
            )
            connection.commit()
            return updated

    def put_approval(self, receipt: ApprovalReceipt) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approvals(approval_id, receipt_json) VALUES (?, ?)",
                (receipt.approval_id, receipt.model_dump_json()),
            )

    def schedule_timer(
        self,
        timer_id: str,
        run_id: str,
        tenant_id: str,
        *,
        due_at: datetime,
        timeout_policy: TimeoutPolicy,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO timers(
                       timer_id, run_id, tenant_id, due_at, timeout_policy, status
                   ) VALUES (?, ?, ?, ?, ?, 'PENDING')""",
                (timer_id, run_id, tenant_id, _iso(due_at), timeout_policy.value),
            )

    def _existing_event_tx(
        self, connection: sqlite3.Connection, event_id: str
    ) -> sqlite3.Row | None:
        return connection.execute(
            """SELECT source, source_event_id, run_id, tenant_id, event_type,
                      wait_generation, payload_digest, status, reason_code
               FROM inbox WHERE event_id = ?""",
            (event_id,),
        ).fetchone()

    def _existing_source_event_tx(
        self, connection: sqlite3.Connection, source: str, source_event_id: str
    ) -> sqlite3.Row | None:
        return connection.execute(
            """SELECT event_id, run_id, tenant_id, event_type, wait_generation,
                      payload_digest
               FROM inbox WHERE source = ? AND source_event_id = ?""",
            (source, source_event_id),
        ).fetchone()

    def _insert_event_tx(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        *,
        status: InboxStatus,
        reason_code: str,
        now: datetime,
    ) -> None:
        connection.execute(
            """INSERT INTO inbox(
                   event_id, source, source_event_id, run_id, tenant_id,
                   event_type, wait_generation, payload_digest, status,
                   reason_code, received_at, processed_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.source,
                event.source_event_id,
                event.run_id,
                event.tenant_id,
                event.event_type.value,
                event.wait_generation,
                event.payload_digest,
                status.value,
                reason_code,
                _iso(now),
                _iso(now),
            ),
        )

    @staticmethod
    def _event_result(
        disposition: EventDisposition,
        run: RunRecord,
        *reason_codes: str,
    ) -> EventProcessResult:
        return EventProcessResult(
            disposition=disposition,
            run_status=run.status,
            state_version=run.state_version,
            reason_codes=tuple(reason_codes),
        )

    def process_event(
        self,
        event: EventEnvelope,
        context: TrustedExecutionContext,
        *,
        secret: str,
        now: datetime,
    ) -> EventProcessResult:
        """Admit, dedupe, validate, and transition in one transaction."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, event.run_id)
            existing = self._existing_event_tx(connection, event.event_id)
            if existing is not None:
                connection.commit()
                same_delivery = (
                    existing["source"] == event.source
                    and existing["source_event_id"] == event.source_event_id
                    and existing["run_id"] == event.run_id
                    and existing["tenant_id"] == event.tenant_id
                    and existing["event_type"] == event.event_type.value
                    and existing["wait_generation"] == event.wait_generation
                    and existing["payload_digest"] == event.payload_digest
                )
                return self._event_result(
                    EventDisposition.DUPLICATE
                    if same_delivery
                    else EventDisposition.REJECTED,
                    run,
                    "DUPLICATE_EVENT" if same_delivery else "EVENT_ID_COLLISION",
                )

            source_delivery = self._existing_source_event_tx(
                connection, event.source, event.source_event_id
            )
            if source_delivery is not None:
                connection.commit()
                same_delivery = (
                    source_delivery["run_id"] == event.run_id
                    and source_delivery["tenant_id"] == event.tenant_id
                    and source_delivery["event_type"] == event.event_type.value
                    and source_delivery["wait_generation"] == event.wait_generation
                    and source_delivery["payload_digest"] == event.payload_digest
                )
                return self._event_result(
                    EventDisposition.DUPLICATE
                    if same_delivery
                    else EventDisposition.REJECTED,
                    run,
                    "DUPLICATE_SOURCE_EVENT"
                    if same_delivery
                    else "EVENT_SOURCE_ID_COLLISION",
                )

            event_validation = validate_event(event, run, secret=secret, now=now)
            if not event_validation.accepted:
                stale = any(
                    reason.startswith("STALE_EVENT")
                    for reason in event_validation.reason_codes
                )
                self._insert_event_tx(
                    connection,
                    event,
                    status=InboxStatus.STALE if stale else InboxStatus.REJECTED,
                    reason_code=event_validation.reason_codes[0],
                    now=now,
                )
                connection.commit()
                return self._event_result(
                    EventDisposition.STALE if stale else EventDisposition.REJECTED,
                    run,
                    *event_validation.reason_codes,
                )

            if event.event_type is EventType.APPROVAL_AVAILABLE:
                result = self._process_approval_tx(
                    connection, event, run, context, now=now
                )
            elif event.event_type is EventType.APPROVAL_REJECTED:
                result = self._simple_wait_transition_tx(
                    connection,
                    event,
                    run,
                    RunStatus.REJECTED,
                    now=now,
                    reason_code="APPROVAL_REJECTED",
                )
            elif event.event_type in {EventType.APPROVAL_TIMEOUT, EventType.TIMER_FIRED}:
                result = self._process_timer_tx(connection, event, run, now=now)
            elif event.event_type is EventType.CANCEL_REQUESTED:
                result = self._process_control_event_tx(
                    connection,
                    event,
                    run,
                    RunStatus.CANCELLED,
                    now=now,
                )
            elif event.event_type is EventType.MANUAL_TAKEOVER:
                result = self._process_control_event_tx(
                    connection,
                    event,
                    run,
                    RunStatus.MANUAL_CONTROL,
                    now=now,
                )
            else:
                self._insert_event_tx(
                    connection,
                    event,
                    status=InboxStatus.REJECTED,
                    reason_code="EVENT_TYPE_NOT_SUPPORTED_FOR_STATE",
                    now=now,
                )
                result = self._event_result(
                    EventDisposition.REJECTED,
                    run,
                    "EVENT_TYPE_NOT_SUPPORTED_FOR_STATE",
                )
            connection.commit()
            return result

    def _process_control_event_tx(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        run: RunRecord,
        terminal_target: RunStatus,
        *,
        now: datetime,
    ) -> EventProcessResult:
        is_manual = terminal_target is RunStatus.MANUAL_CONTROL
        terminal_reason = (
            "MANUAL_TAKEOVER" if is_manual else "CANCELLED_BY_TRUSTED_EVENT"
        )
        operation = connection.execute(
            """SELECT logical_operation_id, status, active_attempt_id,
                      dispatched_at
               FROM operations WHERE run_id = ?
               ORDER BY updated_at DESC LIMIT 1""",
            (run.run_id,),
        ).fetchone()
        effect_may_exist = bool(
            operation
            and (
                operation["dispatched_at"] is not None
                or operation["status"]
                in {
                    OperationStatus.UNKNOWN_OUTCOME.value,
                    OperationStatus.SUCCEEDED.value,
                }
            )
        )
        if run.status in {
            RunStatus.EXECUTING,
            RunStatus.RECONCILING,
            RunStatus.VERIFYING,
        } and effect_may_exist:
            flag = (
                "manual_takeover_requested" if is_manual else "cancellation_requested"
            )
            reason = (
                "MANUAL_TAKEOVER_PENDING_RECONCILIATION"
                if is_manual
                else "CANCELLATION_PENDING_RECONCILIATION"
            )
            updated = self._update_in_place_tx(
                connection,
                run,
                now=now,
                event_id=event.event_id,
                reason_code=reason,
                updates={flag: True},
            )
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.PROCESSED,
                reason_code=reason,
                now=now,
            )
            return self._event_result(EventDisposition.PROCESSED, updated, reason)

        # A claimed but undispatched attempt can be closed without a remote
        # reconciliation obligation because the call boundary was never crossed.
        if operation and operation["status"] == OperationStatus.IN_FLIGHT.value:
            connection.execute(
                """UPDATE operations SET status = ?, updated_at = ?
                   WHERE logical_operation_id = ? AND active_attempt_id = ?
                     AND status = ? AND dispatched_at IS NULL""",
                (
                    OperationStatus.FAILED.value,
                    _iso(now),
                    operation["logical_operation_id"],
                    operation["active_attempt_id"],
                    OperationStatus.IN_FLIGHT.value,
                ),
            )
            connection.execute(
                """UPDATE execution_receipts
                   SET status = ?, completed_at = ?, failure_code = ?
                   WHERE attempt_id = ? AND status = ?""",
                (
                    AttemptStatus.TERMINAL_FAILURE.value,
                    _iso(now),
                    FailureCode.CANCELLED.value,
                    operation["active_attempt_id"],
                    AttemptStatus.STARTED.value,
                ),
            )
        return self._simple_wait_transition_tx(
            connection,
            event,
            run,
            terminal_target,
            now=now,
            reason_code=terminal_reason,
        )

    def _simple_wait_transition_tx(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        run: RunRecord,
        target: RunStatus,
        *,
        now: datetime,
        reason_code: str,
    ) -> EventProcessResult:
        try:
            validate_transition(run.status, target)
        except DurablePolicyError:
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.STALE,
                reason_code="STALE_EVENT_WRONG_STATE",
                now=now,
            )
            return self._event_result(
                EventDisposition.STALE, run, "STALE_EVENT_WRONG_STATE"
            )
        updated = self._transition_tx(
            connection,
            run,
            target,
            now=now,
            event_id=event.event_id,
            reason_code=reason_code,
            updates={"lease_owner": None, "lease_expires_at": None},
        )
        self._insert_event_tx(
            connection,
            event,
            status=InboxStatus.PROCESSED,
            reason_code=reason_code,
            now=now,
        )
        return self._event_result(EventDisposition.PROCESSED, updated, reason_code)

    def _process_approval_tx(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        run: RunRecord,
        context: TrustedExecutionContext,
        *,
        now: datetime,
    ) -> EventProcessResult:
        if run.status is not RunStatus.WAITING_APPROVAL:
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.STALE,
                reason_code="STALE_APPROVAL_EVENT",
                now=now,
            )
            return self._event_result(
                EventDisposition.STALE, run, "STALE_APPROVAL_EVENT"
            )
        approval_id = event.payload.get("approval_id")
        if not isinstance(approval_id, str):
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.REJECTED,
                reason_code="APPROVAL_ID_MISSING",
                now=now,
            )
            return self._event_result(
                EventDisposition.REJECTED, run, "APPROVAL_ID_MISSING"
            )
        row = connection.execute(
            "SELECT receipt_json, consumed_at FROM approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        if row is None:
            reason = "APPROVAL_RECEIPT_NOT_FOUND"
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.REJECTED,
                reason_code=reason,
                now=now,
            )
            return self._event_result(EventDisposition.REJECTED, run, reason)
        if row["consumed_at"] is not None:
            reason = "APPROVAL_ALREADY_CONSUMED"
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.REJECTED,
                reason_code=reason,
                now=now,
            )
            return self._event_result(EventDisposition.REJECTED, run, reason)
        receipt = ApprovalReceipt.model_validate_json(row["receipt_json"])
        validation = validate_approval(receipt, run, context, now=now)
        if not validation.accepted:
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.REJECTED,
                reason_code=validation.reason_codes[0],
                now=now,
            )
            return self._event_result(
                EventDisposition.REJECTED, run, *validation.reason_codes
            )
        consumed = connection.execute(
            """UPDATE approvals
               SET consumed_at = ?, consumed_by_event_id = ?
               WHERE approval_id = ? AND consumed_at IS NULL""",
            (_iso(now), event.event_id, approval_id),
        )
        if consumed.rowcount != 1:
            raise DurablePolicyError("APPROVAL_CONSUMPTION_CONFLICT")
        updated = self._transition_tx(
            connection,
            run,
            RunStatus.READY_TO_RESUME,
            now=now,
            event_id=event.event_id,
            reason_code="APPROVAL_VALIDATED_AND_CONSUMED",
            updates={
                "current_step": "execute_refund",
                "validated_approval_id": approval_id,
            },
        )
        self._insert_event_tx(
            connection,
            event,
            status=InboxStatus.PROCESSED,
            reason_code="APPROVAL_VALIDATED_AND_CONSUMED",
            now=now,
        )
        return self._event_result(
            EventDisposition.PROCESSED,
            updated,
            "APPROVAL_VALIDATED_AND_CONSUMED",
        )

    def _process_timer_tx(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        run: RunRecord,
        *,
        now: datetime,
    ) -> EventProcessResult:
        timer_id = event.payload.get("timer_id")
        row = connection.execute(
            """SELECT run_id, tenant_id, due_at, timeout_policy, status
               FROM timers WHERE timer_id = ?""",
            (timer_id,),
        ).fetchone()
        if row is None:
            reason = "TIMER_NOT_FOUND"
        elif row["run_id"] != run.run_id or row["tenant_id"] != run.tenant_id:
            reason = "TIMER_BINDING_MISMATCH"
        elif row["status"] != "PENDING":
            reason = "TIMER_ALREADY_FIRED"
        elif now < _dt(row["due_at"]):
            reason = "TIMER_NOT_DUE"
        else:
            reason = ""
        if reason:
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.REJECTED,
                reason_code=reason,
                now=now,
            )
            return self._event_result(EventDisposition.REJECTED, run, reason)
        if run.status not in {
            RunStatus.WAITING_APPROVAL,
            RunStatus.WAITING_EVENT,
            RunStatus.WAITING_TIMER,
        }:
            self._insert_event_tx(
                connection,
                event,
                status=InboxStatus.STALE,
                reason_code="STALE_TIMER_EVENT",
                now=now,
            )
            return self._event_result(
                EventDisposition.STALE, run, "STALE_TIMER_EVENT"
            )
        policy = TimeoutPolicy(row["timeout_policy"])
        target = {
            TimeoutPolicy.EXPIRE: RunStatus.EXPIRED,
            TimeoutPolicy.ESCALATE: RunStatus.ESCALATED,
            TimeoutPolicy.CANCEL: RunStatus.CANCELLED,
        }[policy]
        updated = self._transition_tx(
            connection,
            run,
            target,
            now=now,
            event_id=event.event_id,
            reason_code=f"TIMEOUT_{policy.value}",
        )
        connection.execute(
            """UPDATE timers SET status = 'FIRED', fired_by_event_id = ?
               WHERE timer_id = ? AND status = 'PENDING'""",
            (event.event_id, timer_id),
        )
        self._insert_event_tx(
            connection,
            event,
            status=InboxStatus.PROCESSED,
            reason_code=f"TIMEOUT_{policy.value}",
            now=now,
        )
        return self._event_result(
            EventDisposition.PROCESSED, updated, f"TIMEOUT_{policy.value}"
        )

    def claim_lease(
        self,
        run_id: str,
        worker_id: str,
        *,
        expected_version: int,
        now: datetime,
        lease_seconds: int = 300,
    ) -> LeaseResult:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, run_id)
            if run.state_version != expected_version:
                connection.commit()
                return LeaseResult(
                    acquired=False,
                    state_version=run.state_version,
                    reason_code="STATE_VERSION_CONFLICT",
                )
            if run.status not in {RunStatus.READY_TO_RESUME, RunStatus.RECONCILING}:
                connection.commit()
                return LeaseResult(
                    acquired=False,
                    state_version=run.state_version,
                    reason_code="RUN_NOT_CLAIMABLE",
                )
            lease_active = (
                run.lease_owner is not None
                and run.lease_expires_at is not None
                and run.lease_expires_at > now
            )
            if lease_active and run.lease_owner != worker_id:
                connection.commit()
                return LeaseResult(
                    acquired=False,
                    state_version=run.state_version,
                    reason_code="LEASE_HELD_BY_OTHER_WORKER",
                )
            updated = run.model_copy(
                update={
                    "lease_owner": worker_id,
                    "lease_expires_at": now + timedelta(seconds=lease_seconds),
                    "state_version": run.state_version + 1,
                    "updated_at": now,
                }
            )
            self._save_tx(connection, updated, expected_version=run.state_version)
            self._append_history_tx(
                connection,
                updated,
                from_status=run.status,
                event_id=None,
                reason_code="WORKER_LEASE_ACQUIRED",
            )
            connection.commit()
            return LeaseResult(
                acquired=True,
                state_version=updated.state_version,
                reason_code="WORKER_LEASE_ACQUIRED",
            )

    def prepare_operation(
        self,
        run_id: str,
        worker_id: str,
        context: TrustedExecutionContext,
        *,
        now: datetime,
        cost_usd: float = 0.001,
    ) -> PreparedOperation:
        """Atomically claim a stable logical operation before any API call."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, run_id)
            operation_id = stable_operation_id(run)
            request_digest = canonical_digest(
                {
                    "action": run.proposal.action if run.proposal else None,
                    "target": run.proposal.target if run.proposal else None,
                    "parameters": dict(run.proposal.parameters) if run.proposal else {},
                }
            )
            if run.status is not RunStatus.READY_TO_RESUME:
                row = connection.execute(
                    "SELECT status FROM operations WHERE logical_operation_id = ?",
                    (operation_id,),
                ).fetchone()
                if row and row["status"] == OperationStatus.SUCCEEDED.value:
                    connection.commit()
                    return PreparedOperation(
                        disposition=OperationDisposition.ALREADY_SUCCEEDED,
                        logical_operation_id=operation_id,
                        attempt_id=None,
                        owner=worker_id,
                        request_digest=request_digest,
                        reason_code="OPERATION_ALREADY_SUCCEEDED",
                    )
                if row and row["status"] == OperationStatus.UNKNOWN_OUTCOME.value:
                    connection.commit()
                    return PreparedOperation(
                        disposition=OperationDisposition.RECONCILE_REQUIRED,
                        logical_operation_id=operation_id,
                        attempt_id=None,
                        owner=worker_id,
                        request_digest=request_digest,
                        reason_code="UNKNOWN_OUTCOME_REQUIRES_RECONCILIATION",
                    )
                if row and row["status"] == OperationStatus.IN_FLIGHT.value:
                    connection.commit()
                    return PreparedOperation(
                        disposition=OperationDisposition.BUSY,
                        logical_operation_id=operation_id,
                        attempt_id=None,
                        owner=worker_id,
                        request_digest=request_digest,
                        reason_code="OPERATION_OWNED_BY_WORKER",
                    )
                raise DurablePolicyError("RUN_NOT_READY_TO_EXECUTE")
            if (
                run.lease_owner != worker_id
                or run.lease_expires_at is None
                or run.lease_expires_at <= now
            ):
                raise DurablePolicyError("VALID_WORKER_LEASE_REQUIRED")
            if run.validated_approval_id is None:
                raise DurablePolicyError("VALIDATED_APPROVAL_REQUIRED")
            approval_row = connection.execute(
                """SELECT receipt_json, consumed_at FROM approvals
                   WHERE approval_id = ?""",
                (run.validated_approval_id,),
            ).fetchone()
            if approval_row is None or approval_row["consumed_at"] is None:
                raise DurablePolicyError("CONSUMED_APPROVAL_REQUIRED")
            receipt = ApprovalReceipt.model_validate_json(approval_row["receipt_json"])
            approval_validation = validate_approval(receipt, run, context, now=now)
            if not approval_validation.accepted:
                raise DurablePolicyError(approval_validation.reason_codes[0])

            operation = connection.execute(
                """SELECT status, request_digest, owner, attempt_count,
                          active_attempt_id
                   FROM operations WHERE logical_operation_id = ?""",
                (operation_id,),
            ).fetchone()
            if operation is not None:
                if operation["request_digest"] != request_digest:
                    raise DurablePolicyError("LOGICAL_OPERATION_DIGEST_MISMATCH")
                status = OperationStatus(operation["status"])
                if status is OperationStatus.SUCCEEDED:
                    connection.commit()
                    return PreparedOperation(
                        disposition=OperationDisposition.ALREADY_SUCCEEDED,
                        logical_operation_id=operation_id,
                        attempt_id=None,
                        owner=worker_id,
                        request_digest=request_digest,
                        reason_code="OPERATION_ALREADY_SUCCEEDED",
                    )
                if status is OperationStatus.UNKNOWN_OUTCOME:
                    connection.commit()
                    return PreparedOperation(
                        disposition=OperationDisposition.RECONCILE_REQUIRED,
                        logical_operation_id=operation_id,
                        attempt_id=None,
                        owner=worker_id,
                        request_digest=request_digest,
                        reason_code="UNKNOWN_OUTCOME_REQUIRES_RECONCILIATION",
                    )
                if status is OperationStatus.IN_FLIGHT:
                    connection.commit()
                    return PreparedOperation(
                        disposition=OperationDisposition.BUSY,
                        logical_operation_id=operation_id,
                        attempt_id=None,
                        owner=worker_id,
                        request_digest=request_digest,
                        reason_code="OPERATION_OWNED_BY_WORKER",
                    )
                attempt_number = int(operation["attempt_count"]) + 1
                new_external_action = False
            else:
                attempt_number = 1
                new_external_action = True

            budgets = run.budgets.consume_activity(
                cost_usd=cost_usd,
                new_external_action=new_external_action,
            )
            attempt_id = f"attempt:{operation_id}:{attempt_number}"
            updated = self._transition_tx(
                connection,
                run,
                RunStatus.EXECUTING,
                now=now,
                event_id=None,
                reason_code="OPERATION_CLAIMED",
                updates={"budgets": budgets, "current_step": "execute_refund"},
            )
            connection.execute(
                """INSERT INTO operations(
                       logical_operation_id, run_id, step_id, status,
                       request_digest, owner, attempt_count, active_attempt_id,
                       dispatched_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                   ON CONFLICT(logical_operation_id) DO UPDATE SET
                       status = excluded.status,
                       owner = excluded.owner,
                       attempt_count = excluded.attempt_count,
                       active_attempt_id = excluded.active_attempt_id,
                       dispatched_at = NULL,
                       updated_at = excluded.updated_at""",
                (
                    operation_id,
                    updated.run_id,
                    updated.current_step,
                    OperationStatus.IN_FLIGHT.value,
                    request_digest,
                    worker_id,
                    attempt_number,
                    attempt_id,
                    _iso(now),
                ),
            )
            connection.execute(
                """INSERT INTO execution_receipts(
                       attempt_id, logical_operation_id, status, request_digest,
                       started_at
                   ) VALUES (?, ?, ?, ?, ?)""",
                (
                    attempt_id,
                    operation_id,
                    AttemptStatus.STARTED.value,
                    request_digest,
                    _iso(now),
                ),
            )
            connection.commit()
            return PreparedOperation(
                disposition=OperationDisposition.CLAIMED,
                logical_operation_id=operation_id,
                attempt_id=attempt_id,
                owner=worker_id,
                request_digest=request_digest,
                reason_code="OPERATION_CLAIMED",
            )

    def assert_operation_call_allowed(
        self,
        prepared: PreparedOperation,
        *,
        now: datetime,
    ) -> None:
        """Fail before the provider call if state, lease, or claim became stale."""

        if prepared.attempt_id is None:
            raise DurablePolicyError("ATTEMPT_ID_REQUIRED")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute(
                """SELECT run_id, status, owner, request_digest,
                          active_attempt_id, dispatched_at
                   FROM operations WHERE logical_operation_id = ?""",
                (prepared.logical_operation_id,),
            ).fetchone()
            attempt = connection.execute(
                """SELECT logical_operation_id, status, request_digest
                   FROM execution_receipts WHERE attempt_id = ?""",
                (prepared.attempt_id,),
            ).fetchone()
            if operation is None or attempt is None:
                raise DurablePolicyError("OPERATION_CLAIM_NOT_FOUND")
            run = self._load_tx(connection, operation["run_id"])
            if run.status is not RunStatus.EXECUTING:
                raise DurablePolicyError("OPERATION_CALL_NOT_AUTHORIZED")
            if operation["status"] != OperationStatus.IN_FLIGHT.value:
                raise DurablePolicyError("OPERATION_NOT_IN_FLIGHT")
            if operation["active_attempt_id"] != prepared.attempt_id:
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            if operation["owner"] != prepared.owner:
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            if operation["dispatched_at"] is not None:
                raise DurablePolicyError("OPERATION_ALREADY_DISPATCHED")
            if attempt["status"] != AttemptStatus.STARTED.value:
                raise DurablePolicyError("ATTEMPT_NOT_ACTIVE")
            if attempt["logical_operation_id"] != prepared.logical_operation_id:
                raise DurablePolicyError("ATTEMPT_OPERATION_MISMATCH")
            if attempt["request_digest"] != prepared.request_digest:
                raise DurablePolicyError("ATTEMPT_DIGEST_MISMATCH")
            if operation["request_digest"] != prepared.request_digest:
                raise DurablePolicyError("LOGICAL_OPERATION_DIGEST_MISMATCH")
            if run.cancellation_requested or run.manual_takeover_requested:
                raise DurablePolicyError("OPERATION_CALL_NOT_AUTHORIZED")
            if (
                run.lease_owner != operation["owner"]
                or run.lease_expires_at is None
                or run.lease_expires_at <= now
            ):
                raise DurablePolicyError("VALID_WORKER_LEASE_REQUIRED")
            claimed = connection.execute(
                """UPDATE operations SET dispatched_at = ?, updated_at = ?
                   WHERE logical_operation_id = ? AND active_attempt_id = ?
                     AND owner = ? AND status = ? AND dispatched_at IS NULL""",
                (
                    _iso(now),
                    _iso(now),
                    prepared.logical_operation_id,
                    prepared.attempt_id,
                    prepared.owner,
                    OperationStatus.IN_FLIGHT.value,
                ),
            )
            if claimed.rowcount != 1:
                raise DurablePolicyError("OPERATION_DISPATCH_CONFLICT")
            connection.commit()

    def record_operation_result(
        self,
        prepared: PreparedOperation,
        *,
        now: datetime,
        provider_result: ProviderResult | None = None,
        failure_code: FailureCode | None = None,
    ) -> RunRecord:
        if prepared.attempt_id is None:
            raise DurablePolicyError("ATTEMPT_ID_REQUIRED")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute(
                """SELECT run_id, status, owner, active_attempt_id, request_digest,
                          dispatched_at
                   FROM operations WHERE logical_operation_id = ?""",
                (prepared.logical_operation_id,),
            ).fetchone()
            if operation is None:
                raise DurablePolicyError("OPERATION_NOT_FOUND")
            attempt = connection.execute(
                """SELECT logical_operation_id, status, request_digest
                   FROM execution_receipts WHERE attempt_id = ?""",
                (prepared.attempt_id,),
            ).fetchone()
            if (
                operation["status"] != OperationStatus.IN_FLIGHT.value
                or operation["active_attempt_id"] != prepared.attempt_id
                or operation["owner"] != prepared.owner
                or operation["dispatched_at"] is None
                or attempt is None
                or attempt["logical_operation_id"] != prepared.logical_operation_id
                or attempt["status"] != AttemptStatus.STARTED.value
                or attempt["request_digest"] != prepared.request_digest
                or operation["request_digest"] != prepared.request_digest
            ):
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            run = self._load_tx(connection, operation["run_id"])
            if run.status is not RunStatus.EXECUTING:
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            if provider_result is not None and (
                provider_result.logical_operation_id != prepared.logical_operation_id
                or provider_result.request_digest != prepared.request_digest
            ):
                raise DurablePolicyError("PROVIDER_RESULT_BINDING_MISMATCH")
            if failure_code is None and provider_result is not None:
                operation_status = OperationStatus.SUCCEEDED
                attempt_status = AttemptStatus.SUCCEEDED
                target_status = RunStatus.VERIFYING
                reason = "PROVIDER_RESULT_RECORDED"
            elif failure_code is FailureCode.UNKNOWN_OUTCOME:
                operation_status = OperationStatus.UNKNOWN_OUTCOME
                attempt_status = AttemptStatus.UNKNOWN_OUTCOME
                target_status = RunStatus.RECONCILING
                reason = "UNKNOWN_OUTCOME_REQUIRES_RECONCILIATION"
            elif failure_code is not None and failure_is_retryable(failure_code):
                operation_status = OperationStatus.RETRYABLE_FAILURE
                attempt_status = AttemptStatus.RETRYABLE_FAILURE
                target_status = RunStatus.READY_TO_RESUME
                reason = "RETRYABLE_ACTIVITY_FAILURE"
            else:
                operation_status = OperationStatus.FAILED
                attempt_status = AttemptStatus.TERMINAL_FAILURE
                target_status = RunStatus.FAILED
                reason = "TERMINAL_ACTIVITY_FAILURE"
            if run.manual_takeover_requested and target_status in {
                RunStatus.READY_TO_RESUME,
                RunStatus.FAILED,
            }:
                target_status = RunStatus.MANUAL_CONTROL
                reason = "MANUAL_TAKEOVER_AFTER_ATTEMPT_RECORDED"
            elif run.cancellation_requested and target_status in {
                RunStatus.READY_TO_RESUME,
                RunStatus.FAILED,
            }:
                target_status = RunStatus.CANCELLED
                reason = "CANCELLED_AFTER_ATTEMPT_RECORDED"
            operation_update = connection.execute(
                """UPDATE operations
                   SET status = ?, provider_operation_id = ?, result_json = ?,
                       updated_at = ?
                   WHERE logical_operation_id = ? AND active_attempt_id = ?
                     AND owner = ? AND status = ?""",
                (
                    operation_status.value,
                    provider_result.provider_operation_id if provider_result else None,
                    provider_result.model_dump_json() if provider_result else None,
                    _iso(now),
                    prepared.logical_operation_id,
                    prepared.attempt_id,
                    prepared.owner,
                    OperationStatus.IN_FLIGHT.value,
                ),
            )
            if operation_update.rowcount != 1:
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            attempt_update = connection.execute(
                """UPDATE execution_receipts
                   SET status = ?, provider_operation_id = ?, completed_at = ?,
                       failure_code = ?
                   WHERE attempt_id = ? AND logical_operation_id = ?
                     AND request_digest = ? AND status = ?""",
                (
                    attempt_status.value,
                    provider_result.provider_operation_id if provider_result else None,
                    _iso(now),
                    failure_code.value if failure_code else None,
                    prepared.attempt_id,
                    prepared.logical_operation_id,
                    prepared.request_digest,
                    AttemptStatus.STARTED.value,
                ),
            )
            if attempt_update.rowcount != 1:
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            updated = self._transition_tx(
                connection,
                run,
                target_status,
                now=now,
                event_id=None,
                reason_code=reason,
            )
            connection.commit()
            return updated

    def recover_expired_inflight(
        self,
        run_id: str,
        *,
        now: datetime,
    ) -> RunRecord:
        """Convert an abandoned dispatched attempt into a reconciliation duty."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, run_id)
            if run.status is not RunStatus.EXECUTING:
                raise DurablePolicyError("RUN_NOT_EXECUTING")
            if run.lease_expires_at is None or run.lease_expires_at > now:
                raise DurablePolicyError("LEASE_NOT_EXPIRED")
            operation = connection.execute(
                """SELECT logical_operation_id, active_attempt_id
                   FROM operations WHERE run_id = ? AND status = ?
                     AND dispatched_at IS NOT NULL""",
                (run_id, OperationStatus.IN_FLIGHT.value),
            ).fetchone()
            if operation is None:
                raise DurablePolicyError("DISPATCHED_OPERATION_NOT_FOUND")
            changed = connection.execute(
                """UPDATE operations SET status = ?, updated_at = ?
                   WHERE logical_operation_id = ? AND active_attempt_id = ?
                     AND status = ?""",
                (
                    OperationStatus.UNKNOWN_OUTCOME.value,
                    _iso(now),
                    operation["logical_operation_id"],
                    operation["active_attempt_id"],
                    OperationStatus.IN_FLIGHT.value,
                ),
            )
            if changed.rowcount != 1:
                raise DurablePolicyError("STALE_ATTEMPT_RESULT")
            connection.execute(
                """UPDATE execution_receipts
                   SET status = ?, completed_at = ?, failure_code = ?
                   WHERE attempt_id = ? AND status = ?""",
                (
                    AttemptStatus.UNKNOWN_OUTCOME.value,
                    _iso(now),
                    FailureCode.UNKNOWN_OUTCOME.value,
                    operation["active_attempt_id"],
                    AttemptStatus.STARTED.value,
                ),
            )
            updated = self._transition_tx(
                connection,
                run,
                RunStatus.RECONCILING,
                now=now,
                event_id=None,
                reason_code="EXPIRED_LEASE_REQUIRES_RECONCILIATION",
            )
            connection.commit()
            return updated

    def record_reconciliation(
        self,
        logical_operation_id: str,
        result: ReconciliationResult,
        context: TrustedExecutionContext,
        *,
        now: datetime,
    ) -> RunRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute(
                """SELECT run_id, request_digest, attempt_count, status
                   FROM operations
                   WHERE logical_operation_id = ?""",
                (logical_operation_id,),
            ).fetchone()
            if operation is None:
                raise DurablePolicyError("OPERATION_NOT_FOUND")
            run = self._load_tx(connection, operation["run_id"])
            if run.status is not RunStatus.RECONCILING:
                raise DurablePolicyError("RUN_NOT_RECONCILING")
            if operation["status"] != OperationStatus.UNKNOWN_OUTCOME.value:
                raise DurablePolicyError("OPERATION_NOT_RECONCILING")
            provider_result = result.provider_result
            if result.status is ReconciliationStatus.CONFIRMED_EFFECT:
                if provider_result is None:
                    raise DurablePolicyError("RECONCILIATION_RESULT_REQUIRED")
                if (
                    provider_result.logical_operation_id != logical_operation_id
                    or provider_result.request_digest != operation["request_digest"]
                ):
                    raise DurablePolicyError("RECONCILIATION_DIGEST_MISMATCH")
                changed = connection.execute(
                    """UPDATE operations
                       SET status = ?, provider_operation_id = ?, result_json = ?,
                           updated_at = ?
                       WHERE logical_operation_id = ? AND status = ?""",
                    (
                        OperationStatus.SUCCEEDED.value,
                        provider_result.provider_operation_id,
                        provider_result.model_dump_json(),
                        _iso(now),
                        logical_operation_id,
                        OperationStatus.UNKNOWN_OUTCOME.value,
                    ),
                )
                if changed.rowcount != 1:
                    raise DurablePolicyError("RECONCILIATION_STATE_CONFLICT")
                target = RunStatus.VERIFYING
                reason = "RECONCILIATION_CONFIRMED_EFFECT"
            elif result.status is ReconciliationStatus.CONFIRMED_NO_EFFECT:
                changed = connection.execute(
                    """UPDATE operations SET status = ?, updated_at = ?
                       WHERE logical_operation_id = ? AND status = ?""",
                    (
                        OperationStatus.CONFIRMED_NO_EFFECT.value,
                        _iso(now),
                        logical_operation_id,
                        OperationStatus.UNKNOWN_OUTCOME.value,
                    ),
                )
                if changed.rowcount != 1:
                    raise DurablePolicyError("RECONCILIATION_STATE_CONFLICT")
                if run.manual_takeover_requested:
                    target = RunStatus.MANUAL_CONTROL
                    reason = "NO_EFFECT_CONFIRMED_MANUAL_CONTROL"
                elif run.cancellation_requested:
                    target = RunStatus.CANCELLED
                    reason = "NO_EFFECT_CONFIRMED_CANCELLED"
                else:
                    approval_row = connection.execute(
                        """SELECT receipt_json, consumed_at FROM approvals
                           WHERE approval_id = ?""",
                        (run.validated_approval_id,),
                    ).fetchone()
                    validation = (
                        validate_approval(
                            ApprovalReceipt.model_validate_json(
                                approval_row["receipt_json"]
                            ),
                            run,
                            context,
                            now=now,
                        )
                        if approval_row is not None
                        and approval_row["consumed_at"] is not None
                        else None
                    )
                    if validation is None or not validation.accepted:
                        target = RunStatus.FAILED
                        reason = "NO_EFFECT_CONFIRMED_AUTHORITY_INVALID"
                    elif (
                        run.budgets.activity_attempts_used
                        >= run.budgets.max_activity_attempts
                        or run.budgets.cost_usd + 0.001
                        > run.budgets.max_cost_usd
                    ):
                        target = RunStatus.FAILED
                        reason = "NO_EFFECT_CONFIRMED_BUDGET_EXHAUSTED"
                    else:
                        target = RunStatus.READY_TO_RESUME
                        reason = "RECONCILIATION_CONFIRMED_NO_EFFECT"
            else:
                updated = self._update_in_place_tx(
                    connection,
                    run,
                    now=now,
                    event_id=None,
                    reason_code="RECONCILIATION_STILL_UNKNOWN",
                    updates={},
                )
                target = None
                reason = "RECONCILIATION_STILL_UNKNOWN"
            if target is not None:
                updated = self._transition_tx(
                    connection,
                    run,
                    target,
                    now=now,
                    event_id=None,
                    reason_code=reason,
                )
            receipt_number = connection.execute(
                """SELECT COUNT(*) FROM reconciliation_receipts
                   WHERE logical_operation_id = ?""",
                (logical_operation_id,),
            ).fetchone()[0] + 1
            connection.execute(
                """INSERT INTO reconciliation_receipts(
                       reconciliation_id, logical_operation_id, request_digest,
                       status, provider_operation_id, observed_at
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    f"reconcile:{logical_operation_id}:{receipt_number}",
                    logical_operation_id,
                    operation["request_digest"],
                    result.status.value,
                    provider_result.provider_operation_id if provider_result else None,
                    _iso(now),
                ),
            )
            connection.commit()
            return updated

    def complete_after_verification(
        self,
        run_id: str,
        logical_operation_id: str,
        provider_result: ProviderResult | None,
        business_effect: BusinessEffectRecord | None,
        *,
        now: datetime,
    ) -> RunRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._load_tx(connection, run_id)
            operation = connection.execute(
                """SELECT status, request_digest, provider_operation_id
                   FROM operations WHERE logical_operation_id = ?""",
                (logical_operation_id,),
            ).fetchone()
            if run.status is not RunStatus.VERIFYING:
                raise DurablePolicyError("RUN_NOT_VERIFYING")
            if (
                operation is None
                or operation["status"] != OperationStatus.SUCCEEDED.value
                or provider_result is None
                or provider_result.request_digest != operation["request_digest"]
                or provider_result.provider_operation_id
                != operation["provider_operation_id"]
                or business_effect is None
                or business_effect.logical_operation_id != logical_operation_id
                or business_effect.request_digest != operation["request_digest"]
                or business_effect.provider_operation_id
                != operation["provider_operation_id"]
                or run.proposal is None
                or business_effect.target_id != run.proposal.target
                or business_effect.amount_usd
                != int(run.proposal.parameters.get("amount_usd", 0))
            ):
                raise DurablePolicyError("EFFECT_VERIFICATION_FAILED")
            if run.manual_takeover_requested:
                target = RunStatus.MANUAL_CONTROL
                reason = "EFFECT_VERIFIED_MANUAL_CONTROL"
                step = "manual_control_after_effect"
            elif run.cancellation_requested:
                target = RunStatus.CANCELLED
                reason = "EFFECT_VERIFIED_CANCELLED"
                step = "cancelled_after_effect"
            else:
                target = RunStatus.COMPLETED
                reason = "EFFECT_VERIFIED"
                step = "complete"
            updated = self._transition_tx(
                connection,
                run,
                target,
                now=now,
                event_id=None,
                reason_code=reason,
                updates={"current_step": step},
            )
            connection.commit()
            return updated

    def history(self, run_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT sequence, from_status, to_status, event_id,
                          state_version, reason_code
                   FROM transition_history WHERE run_id = ? ORDER BY sequence""",
                (run_id,),
            ).fetchall()
            return tuple(dict(row) for row in rows)

    def inbox_count(self, event_id: str) -> int:
        with self._connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM inbox WHERE event_id = ?", (event_id,)
                ).fetchone()[0]
            )

    def outbox_messages(self, run_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM outbox WHERE run_id = ? ORDER BY created_at",
                (run_id,),
            ).fetchall()
            return tuple(dict(row) for row in rows)

    def operation_attempt_count(self, logical_operation_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempt_count FROM operations WHERE logical_operation_id = ?",
                (logical_operation_id,),
            ).fetchone()
            return int(row[0]) if row else 0

    def operation_record(self, logical_operation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE logical_operation_id = ?",
                (logical_operation_id,),
            ).fetchone()
            return dict(row) if row else None

    def reconciliation_receipts(
        self, logical_operation_id: str
    ) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM reconciliation_receipts
                   WHERE logical_operation_id = ? ORDER BY observed_at""",
                (logical_operation_id,),
            ).fetchall()
            return tuple(dict(row) for row in rows)


class DeterministicProvider:
    """Fixture provider with a queryable operation ledger."""

    def __init__(self) -> None:
        self.effects: dict[str, ProviderResult] = {}
        self.calls = 0

    def execute(
        self,
        logical_operation_id: str,
        request_digest: str,
        outcome: ProviderOutcome,
    ) -> ProviderResult:
        self.calls += 1
        if logical_operation_id in self.effects:
            return self.effects[logical_operation_id]
        if outcome is ProviderOutcome.TRANSIENT_BEFORE_COMMIT:
            raise ProviderTransientError("provider unavailable before commit")
        if outcome is ProviderOutcome.TERMINAL_FAILURE:
            raise ProviderTerminalError("provider rejected request")
        result = ProviderResult(
            provider_operation_id=f"provider:{logical_operation_id[-12:]}",
            logical_operation_id=logical_operation_id,
            request_digest=request_digest,
            status="SUCCEEDED",
        )
        self.effects[logical_operation_id] = result
        if outcome is ProviderOutcome.TIMEOUT_AFTER_COMMIT:
            raise ProviderTimeoutAfterCommit("response lost after provider commit")
        return result

    def query(self, logical_operation_id: str) -> ProviderResult | None:
        return self.effects.get(logical_operation_id)

    def reconcile(
        self,
        logical_operation_id: str,
        *,
        still_unknown: bool = False,
    ) -> ReconciliationResult:
        if still_unknown:
            return ReconciliationResult(status=ReconciliationStatus.STILL_UNKNOWN)
        provider_result = self.query(logical_operation_id)
        return ReconciliationResult(
            status=(
                ReconciliationStatus.CONFIRMED_EFFECT
                if provider_result is not None
                else ReconciliationStatus.CONFIRMED_NO_EFFECT
            ),
            provider_result=provider_result,
        )


class WorkflowRuntime:
    def __init__(
        self,
        store: DurableStore,
        *,
        event_secret: str = EVENT_SECRET,
        supported_workflow_versions: tuple[str, ...] = (WORKFLOW_VERSION,),
        supported_state_schemas: tuple[int, ...] = (STATE_SCHEMA_VERSION,),
        state_migrations: Mapping[int, Callable[[RunRecord], RunRecord]] | None = None,
        business_ledger: RefundLedger | None = None,
    ) -> None:
        self.store = store
        self.event_secret = event_secret
        self.supported_workflow_versions = supported_workflow_versions
        self.supported_state_schemas = supported_state_schemas
        self.state_migrations = dict(state_migrations or {})
        self.business_ledger = business_ledger or RefundLedger()

    def load_compatible(
        self, run_id: str, *, now: datetime | None = None
    ) -> RunRecord:
        run = self.store.load_run(run_id)
        if run.workflow_version not in self.supported_workflow_versions:
            raise DurablePolicyError("WORKFLOW_VERSION_UNSUPPORTED")
        seen: set[int] = set()
        while run.state_schema_version not in self.supported_state_schemas:
            if run.state_schema_version in seen:
                raise DurablePolicyError("STATE_SCHEMA_MIGRATION_CYCLE")
            seen.add(run.state_schema_version)
            migrator = self.state_migrations.get(run.state_schema_version)
            if migrator is None:
                raise DurablePolicyError("STATE_SCHEMA_VERSION_UNSUPPORTED")
            run = self.store.migrate_run(
                run_id,
                migrator,
                now=now or run.updated_at,
            )
        return run

    def start_approval_run(
        self,
        run_id: str,
        *,
        now: datetime = FIXED_TIME,
        timeout_after: timedelta = timedelta(hours=24),
        timeout_policy: TimeoutPolicy = TimeoutPolicy.EXPIRE,
        budgets: BudgetState | None = None,
    ) -> RunRecord:
        proposal = fixture_proposal(now=now, expires_at=now + timeout_after)
        timer_id = f"timer:{run_id}:approval"
        created = RunRecord(
            run_id=run_id,
            tenant_id=TENANT_ID,
            subject_id=SUBJECT_ID,
            status=RunStatus.CREATED,
            current_step="create_proposal",
            proposal=proposal,
            budgets=budgets or BudgetState(),
            pending_timer_id=timer_id,
            created_at=now,
            updated_at=now,
        )
        self.store.create_run(created)
        running = self.store.transition(
            run_id,
            created.state_version,
            RunStatus.RUNNING,
            now=now,
            reason_code="WORKFLOW_STARTED",
        )
        waiting = self.store.transition(
            run_id,
            running.state_version,
            RunStatus.WAITING_APPROVAL,
            now=now,
            reason_code="PROPOSAL_PERSISTED_WORKER_RELEASED",
            updates={
                "current_step": "wait_for_approval",
                "wait_generation": running.wait_generation + 1,
                "wait_started_at": now,
            },
        )
        self.store.schedule_timer(
            timer_id,
            run_id,
            TENANT_ID,
            due_at=proposal.expires_at,
            timeout_policy=timeout_policy,
        )
        return waiting

    def process_event(
        self,
        event: EventEnvelope,
        context: TrustedExecutionContext,
        *,
        now: datetime,
    ) -> EventProcessResult:
        self.load_compatible(event.run_id, now=now)
        return self.store.process_event(
            event,
            context,
            secret=self.event_secret,
            now=now,
        )

    def execute(
        self,
        prepared: PreparedOperation,
        provider: DeterministicProvider,
        outcome: ProviderOutcome,
        *,
        now: datetime,
    ) -> RunRecord:
        self.store.assert_operation_call_allowed(prepared, now=now)
        try:
            result = provider.execute(
                prepared.logical_operation_id,
                prepared.request_digest,
                outcome,
            )
        except ProviderTimeoutAfterCommit:
            return self.store.record_operation_result(
                prepared,
                now=now,
                failure_code=FailureCode.UNKNOWN_OUTCOME,
            )
        except ProviderTransientError:
            return self.store.record_operation_result(
                prepared,
                now=now,
                failure_code=FailureCode.TRANSIENT_DEPENDENCY,
            )
        except ProviderTerminalError:
            return self.store.record_operation_result(
                prepared,
                now=now,
                failure_code=FailureCode.POLICY_DENIED,
            )
        return self.store.record_operation_result(
            prepared,
            now=now,
            provider_result=result,
        )

    def reconcile(
        self,
        logical_operation_id: str,
        provider: DeterministicProvider,
        *,
        now: datetime,
        context: TrustedExecutionContext | None = None,
        still_unknown: bool = False,
    ) -> RunRecord:
        return self.store.record_reconciliation(
            logical_operation_id,
            provider.reconcile(
                logical_operation_id,
                still_unknown=still_unknown,
            ),
            context or fixture_context(),
            now=now,
        )

    def observe_business_effect(
        self,
        run_id: str,
        logical_operation_id: str,
        provider: DeterministicProvider,
    ) -> BusinessEffectRecord:
        run = self.store.load_run(run_id)
        provider_result = provider.query(logical_operation_id)
        if run.proposal is None or provider_result is None:
            raise DurablePolicyError("BUSINESS_EFFECT_NOT_OBSERVABLE")
        return self.business_ledger.observe(
            provider_result,
            target_id=run.proposal.target,
            amount_usd=int(run.proposal.parameters.get("amount_usd", 0)),
        )

    def verify_and_complete(
        self,
        run_id: str,
        logical_operation_id: str,
        provider: DeterministicProvider,
        *,
        now: datetime,
    ) -> RunRecord:
        return self.store.complete_after_verification(
            run_id,
            logical_operation_id,
            provider.query(logical_operation_id),
            self.business_ledger.query(logical_operation_id),
            now=now,
        )


def migrate_state_v1_to_v2(run: RunRecord) -> RunRecord:
    """Explicit fixture migration; production migrations require separate rollout."""

    if run.state_schema_version != 1:
        raise DurablePolicyError("STATE_SCHEMA_MIGRATION_SOURCE_INVALID")
    return run.model_copy(
        update={
            "state_schema_version": 2,
            "wait_generation": run.wait_generation,
            "wait_started_at": run.wait_started_at,
            "cancellation_requested": False,
            "manual_takeover_requested": False,
        }
    )


def fixture_preconditions(
    *,
    resource_version: str = "order-v7",
    policy_version: str = POLICY_VERSION,
) -> PreconditionSnapshot:
    return PreconditionSnapshot(
        target_id="order-42",
        resource_version=resource_version,
        evidence_digest=canonical_digest({"order": "42", "refund_due": True}),
        deployment_id="payments-eu-v3",
        account_state="ACTIVE",
        policy_version=policy_version,
    )


def fixture_proposal(
    *,
    now: datetime = FIXED_TIME,
    expires_at: datetime | None = None,
) -> Proposal:
    return Proposal(
        proposal_id="proposal-refund-42",
        action="ISSUE_REFUND",
        target="order-42",
        parameters={"amount_usd": 50, "currency": "USD"},
        preconditions=fixture_preconditions(),
        created_at=now,
        expires_at=expires_at or now + timedelta(hours=24),
    )


def fixture_context(
    *,
    preconditions: PreconditionSnapshot | None = None,
    policy_version: str = POLICY_VERSION,
    tenant_id: str = TENANT_ID,
    subject_id: str = SUBJECT_ID,
    active_approvers: dict[str, tuple[str, ...]] | None = None,
) -> TrustedExecutionContext:
    return TrustedExecutionContext(
        tenant_id=tenant_id,
        subject_id=subject_id,
        current_policy_version=policy_version,
        permitted_actions=("ISSUE_REFUND",),
        permitted_targets=("order-42",),
        required_approver_role="refund_approver",
        active_approvers=active_approvers
        or {"approver-7": ("refund_approver",)},
        current_preconditions=preconditions or fixture_preconditions(),
    )


def fixture_approval(
    run: RunRecord,
    *,
    now: datetime = FIXED_TIME + timedelta(minutes=5),
    expires_at: datetime | None = None,
    tenant_id: str | None = None,
    proposal_digest: str | None = None,
    precondition_digest: str | None = None,
    policy_version: str = POLICY_VERSION,
) -> ApprovalReceipt:
    if run.proposal is None:
        raise DurablePolicyError("PROPOSAL_MISSING")
    return ApprovalReceipt(
        approval_id=f"approval:{run.run_id}",
        run_id=run.run_id,
        tenant_id=tenant_id or run.tenant_id,
        subject_id=run.subject_id,
        proposal_id=run.proposal.proposal_id,
        proposal_digest=proposal_digest or run.proposal.digest,
        precondition_digest=precondition_digest or run.proposal.preconditions.digest,
        action=run.proposal.action,
        target=run.proposal.target,
        approver_id="approver-7",
        approver_roles=("refund_approver",),
        policy_version=policy_version,
        issued_at=now,
        expires_at=expires_at or now + timedelta(hours=1),
    )


def signed_event(
    *,
    event_id: str,
    run_id: str,
    event_type: EventType,
    payload: dict[str, Any],
    occurred_at: datetime,
    wait_generation: int = 1,
    tenant_id: str = TENANT_ID,
    source: str | None = None,
    source_event_id: str | None = None,
    secret: str = EVENT_SECRET,
) -> EventEnvelope:
    default_sources = {
        EventType.APPROVAL_AVAILABLE: "approval-gateway",
        EventType.APPROVAL_REJECTED: "approval-gateway",
        EventType.APPROVAL_TIMEOUT: "scheduler",
        EventType.TIMER_FIRED: "scheduler",
        EventType.EXTERNAL_CALLBACK: "integration-gateway",
        EventType.CANCEL_REQUESTED: "operator-control",
        EventType.MANUAL_TAKEOVER: "operator-control",
    }
    resolved_source = source or default_sources[event_type]
    resolved_source_event_id = source_event_id or event_id
    digest = payload_digest(payload)
    signature = event_signature(
        secret,
        event_id=event_id,
        source_event_id=resolved_source_event_id,
        source=resolved_source,
        tenant_id=tenant_id,
        run_id=run_id,
        event_type=event_type,
        wait_generation=wait_generation,
        occurred_at=occurred_at,
        payload_digest_value=digest,
    )
    return EventEnvelope(
        event_id=event_id,
        source_event_id=resolved_source_event_id,
        source=resolved_source,
        tenant_id=tenant_id,
        run_id=run_id,
        event_type=event_type,
        wait_generation=wait_generation,
        occurred_at=occurred_at,
        payload=payload,
        payload_digest=digest,
        signature=signature,
    )


def evaluate_same_cases(directory: str | Path) -> EvaluationReport:
    """Compare a naive approval flag with the governed runtime on four cases.

    The baseline intentionally models the failure modes this course replaces: it
    trusts any approval-shaped delivery, forgets cancellation, has no durable
    dedupe, and blindly retries an unknown provider outcome.
    """

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    case_ids = (
        "duplicate_delivery",
        "cross_tenant_event",
        "cancel_then_late_approval",
        "unknown_provider_outcome",
    )
    # Applying the naive rules to the exact four cases: two duplicated effects,
    # two unauthorized resumes, and six calls for four requested operations.
    baseline = EvaluationMetrics(
        cases=4,
        safe_outcomes=0,
        unsafe_resumes=2,
        duplicate_effects=2,
        provider_calls=6,
        reconciliations=0,
    )

    safe_outcomes = 0
    unsafe_resumes = 0
    duplicate_effects = 0
    provider_calls = 0
    reconciliations = 0

    # Duplicate delivery: one inbox record and one effect.
    duplicate_runtime = WorkflowRuntime(DurableStore(root / "duplicate.db"))
    waiting = duplicate_runtime.start_approval_run("eval-duplicate")
    receipt = fixture_approval(waiting)
    duplicate_runtime.store.put_approval(receipt)
    approval_event = signed_event(
        event_id="eval-event-duplicate",
        run_id=waiting.run_id,
        event_type=EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": receipt.approval_id},
        occurred_at=FIXED_TIME + timedelta(minutes=5),
    )
    first = duplicate_runtime.process_event(
        approval_event, fixture_context(), now=FIXED_TIME + timedelta(minutes=5)
    )
    second = duplicate_runtime.process_event(
        approval_event, fixture_context(), now=FIXED_TIME + timedelta(minutes=6)
    )
    ready = duplicate_runtime.store.load_run(waiting.run_id)
    duplicate_runtime.store.claim_lease(
        ready.run_id,
        "eval-worker",
        expected_version=ready.state_version,
        now=FIXED_TIME + timedelta(minutes=7),
    )
    prepared = duplicate_runtime.store.prepare_operation(
        ready.run_id,
        "eval-worker",
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=7, seconds=1),
    )
    provider = DeterministicProvider()
    duplicate_runtime.execute(
        prepared,
        provider,
        ProviderOutcome.SUCCESS,
        now=FIXED_TIME + timedelta(minutes=8),
    )
    duplicate_runtime.observe_business_effect(
        ready.run_id, prepared.logical_operation_id, provider
    )
    duplicate_runtime.verify_and_complete(
        ready.run_id,
        prepared.logical_operation_id,
        provider,
        now=FIXED_TIME + timedelta(minutes=9),
    )
    provider_calls += provider.calls
    safe_outcomes += int(
        first.disposition is EventDisposition.PROCESSED
        and second.disposition is EventDisposition.DUPLICATE
        and provider.calls == 1
    )

    # Cross-tenant event: even a correctly signed envelope is not authority for
    # another tenant's run.
    tenant_runtime = WorkflowRuntime(DurableStore(root / "cross-tenant.db"))
    tenant_waiting = tenant_runtime.start_approval_run("eval-cross-tenant")
    tenant_receipt = fixture_approval(tenant_waiting)
    tenant_runtime.store.put_approval(tenant_receipt)
    cross_tenant = signed_event(
        event_id="eval-event-cross-tenant",
        run_id=tenant_waiting.run_id,
        event_type=EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": tenant_receipt.approval_id},
        occurred_at=FIXED_TIME + timedelta(minutes=5),
        tenant_id="attacker-tenant",
    )
    tenant_result = tenant_runtime.process_event(
        cross_tenant,
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=5),
    )
    if tenant_result.disposition is EventDisposition.REJECTED:
        safe_outcomes += 1
    else:
        unsafe_resumes += 1

    # Cancellation: a later valid approval is stale and cannot resurrect work.
    cancel_runtime = WorkflowRuntime(DurableStore(root / "cancel.db"))
    cancel_waiting = cancel_runtime.start_approval_run("eval-cancel")
    cancel_receipt = fixture_approval(cancel_waiting)
    cancel_runtime.store.put_approval(cancel_receipt)
    cancel_event = signed_event(
        event_id="eval-event-cancel",
        run_id=cancel_waiting.run_id,
        event_type=EventType.CANCEL_REQUESTED,
        payload={"reason": "customer request"},
        occurred_at=FIXED_TIME + timedelta(minutes=4),
    )
    cancel_runtime.process_event(
        cancel_event, fixture_context(), now=FIXED_TIME + timedelta(minutes=4)
    )
    late_approval = signed_event(
        event_id="eval-event-late-approval",
        run_id=cancel_waiting.run_id,
        event_type=EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": cancel_receipt.approval_id},
        occurred_at=FIXED_TIME + timedelta(minutes=5),
    )
    late_result = cancel_runtime.process_event(
        late_approval,
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=5),
    )
    if (
        late_result.disposition is EventDisposition.STALE
        and cancel_runtime.store.load_run(cancel_waiting.run_id).status
        is RunStatus.CANCELLED
    ):
        safe_outcomes += 1
    else:
        unsafe_resumes += 1

    # Unknown outcome: query by stable operation ID rather than blindly retry.
    unknown_runtime = WorkflowRuntime(DurableStore(root / "unknown.db"))
    unknown_waiting = unknown_runtime.start_approval_run("eval-unknown")
    unknown_receipt = fixture_approval(unknown_waiting)
    unknown_runtime.store.put_approval(unknown_receipt)
    unknown_runtime.process_event(
        signed_event(
            event_id="eval-event-unknown",
            run_id=unknown_waiting.run_id,
            event_type=EventType.APPROVAL_AVAILABLE,
            payload={"approval_id": unknown_receipt.approval_id},
            occurred_at=FIXED_TIME + timedelta(minutes=5),
        ),
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=5),
    )
    unknown_ready = unknown_runtime.store.load_run(unknown_waiting.run_id)
    unknown_runtime.store.claim_lease(
        unknown_ready.run_id,
        "eval-worker",
        expected_version=unknown_ready.state_version,
        now=FIXED_TIME + timedelta(minutes=7),
    )
    unknown_prepared = unknown_runtime.store.prepare_operation(
        unknown_ready.run_id,
        "eval-worker",
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=7, seconds=1),
    )
    unknown_provider = DeterministicProvider()
    unknown_runtime.execute(
        unknown_prepared,
        unknown_provider,
        ProviderOutcome.TIMEOUT_AFTER_COMMIT,
        now=FIXED_TIME + timedelta(minutes=8),
    )
    reconciled = unknown_runtime.reconcile(
        unknown_prepared.logical_operation_id,
        unknown_provider,
        now=FIXED_TIME + timedelta(minutes=9),
    )
    provider_calls += unknown_provider.calls
    reconciliations += 1
    if reconciled.status is RunStatus.VERIFYING and unknown_provider.calls == 1:
        safe_outcomes += 1
    else:
        duplicate_effects += 1

    governed = EvaluationMetrics(
        cases=4,
        safe_outcomes=safe_outcomes,
        unsafe_resumes=unsafe_resumes,
        duplicate_effects=duplicate_effects,
        provider_calls=provider_calls,
        reconciliations=reconciliations,
    )
    return EvaluationReport(
        case_ids=case_ids,
        baseline=baseline,
        governed=governed,
    )


def happy_path_demo(database_path: str | Path) -> dict[str, Any]:
    """Run a restart-safe approval, execution, verification, and completion flow."""

    first_process = WorkflowRuntime(DurableStore(database_path))
    waiting = first_process.start_approval_run("run-refund-42")
    receipt = fixture_approval(waiting)
    first_process.store.put_approval(receipt)

    # A separate runtime opens the same file, as a new process would.
    resumed = WorkflowRuntime(DurableStore(database_path))
    event = signed_event(
        event_id="event-approval-42",
        run_id=waiting.run_id,
        event_type=EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": receipt.approval_id},
        occurred_at=FIXED_TIME + timedelta(minutes=6),
    )
    admitted = resumed.process_event(
        event,
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=6),
    )
    ready = resumed.store.load_run(waiting.run_id)
    lease = resumed.store.claim_lease(
        ready.run_id,
        "worker-b",
        expected_version=ready.state_version,
        now=FIXED_TIME + timedelta(minutes=7),
    )
    prepared = resumed.store.prepare_operation(
        ready.run_id,
        "worker-b",
        fixture_context(),
        now=FIXED_TIME + timedelta(minutes=7, seconds=1),
    )
    provider = DeterministicProvider()
    resumed.execute(
        prepared,
        provider,
        ProviderOutcome.SUCCESS,
        now=FIXED_TIME + timedelta(minutes=7, seconds=2),
    )
    resumed.observe_business_effect(
        ready.run_id, prepared.logical_operation_id, provider
    )
    completed = resumed.verify_and_complete(
        ready.run_id,
        prepared.logical_operation_id,
        provider,
        now=FIXED_TIME + timedelta(minutes=7, seconds=3),
    )
    return {
        "event": admitted.model_dump(mode="json"),
        "lease": lease.model_dump(mode="json"),
        "operation": prepared.model_dump(mode="json"),
        "status": completed.status.value,
        "state_version": completed.state_version,
        "provider_calls": provider.calls,
        "history_events": len(resumed.store.history(completed.run_id)),
        "outbox_messages": len(resumed.store.outbox_messages(completed.run_id)),
    }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        demo = happy_path_demo(Path(directory) / "durable-workflow.db")
        evaluation = evaluate_same_cases(Path(directory) / "evaluation")
        print(
            json.dumps(
                {
                    "happy_path": demo,
                    "evaluation": evaluation.model_dump(mode="json"),
                },
                indent=2,
            )
        )
