"""Application-owned policy for durable long-running workflow execution.

Model output may propose work. Only trusted application state admits events,
validates approval, owns transitions, authorizes side effects, and completes a run.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

WORKFLOW_VERSION = "refund-workflow-v1"
STATE_SCHEMA_VERSION = 2
POLICY_VERSION = "northstar-refund-policy-v1"
EVENT_MAX_FUTURE_SKEW = timedelta(minutes=1)


class DurablePolicyError(ValueError):
    """Fail-closed policy error with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_EVENT = "WAITING_EVENT"
    WAITING_TIMER = "WAITING_TIMER"
    READY_TO_RESUME = "READY_TO_RESUME"
    EXECUTING = "EXECUTING"
    RECONCILING = "RECONCILING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    MANUAL_CONTROL = "MANUAL_CONTROL"


TERMINAL_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.REJECTED,
    RunStatus.EXPIRED,
    RunStatus.CANCELLED,
    RunStatus.FAILED,
    RunStatus.ESCALATED,
    RunStatus.MANUAL_CONTROL,
}


ALLOWED_TRANSITIONS: Mapping[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.WAITING_APPROVAL,
            RunStatus.WAITING_EVENT,
            RunStatus.WAITING_TIMER,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.WAITING_APPROVAL: frozenset(
        {
            RunStatus.READY_TO_RESUME,
            RunStatus.REJECTED,
            RunStatus.EXPIRED,
            RunStatus.ESCALATED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.WAITING_EVENT: frozenset(
        {
            RunStatus.READY_TO_RESUME,
            RunStatus.EXPIRED,
            RunStatus.ESCALATED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.WAITING_TIMER: frozenset(
        {
            RunStatus.READY_TO_RESUME,
            RunStatus.EXPIRED,
            RunStatus.ESCALATED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.READY_TO_RESUME: frozenset(
        {
            RunStatus.EXECUTING,
            RunStatus.CANCELLED,
            RunStatus.FAILED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.EXECUTING: frozenset(
        {
            RunStatus.READY_TO_RESUME,
            RunStatus.RECONCILING,
            RunStatus.VERIFYING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.RECONCILING: frozenset(
        {
            RunStatus.READY_TO_RESUME,
            RunStatus.EXECUTING,
            RunStatus.VERIFYING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
    RunStatus.VERIFYING: frozenset(
        {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.MANUAL_CONTROL,
        }
    ),
}


class EventType(StrEnum):
    APPROVAL_AVAILABLE = "APPROVAL_AVAILABLE"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    APPROVAL_TIMEOUT = "APPROVAL_TIMEOUT"
    EXTERNAL_CALLBACK = "EXTERNAL_CALLBACK"
    TIMER_FIRED = "TIMER_FIRED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    MANUAL_TAKEOVER = "MANUAL_TAKEOVER"


class InboxStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    STALE = "STALE"


class TimeoutPolicy(StrEnum):
    EXPIRE = "EXPIRE"
    ESCALATE = "ESCALATE"
    CANCEL = "CANCEL"


class OperationStatus(StrEnum):
    IN_FLIGHT = "IN_FLIGHT"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    CONFIRMED_NO_EFFECT = "CONFIRMED_NO_EFFECT"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class AttemptStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


class ReconciliationStatus(StrEnum):
    CONFIRMED_EFFECT = "CONFIRMED_EFFECT"
    CONFIRMED_NO_EFFECT = "CONFIRMED_NO_EFFECT"
    STILL_UNKNOWN = "STILL_UNKNOWN"


class FailureCode(StrEnum):
    TRANSIENT_DEPENDENCY = "TRANSIENT_DEPENDENCY"
    TIMEOUT = "TIMEOUT"
    AUTH_DENIED = "AUTH_DENIED"
    POLICY_DENIED = "POLICY_DENIED"
    INVALID_EVENT = "INVALID_EVENT"
    STALE_EVENT = "STALE_EVENT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    PRECONDITION_CHANGED = "PRECONDITION_CHANGED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    CANCELLED = "CANCELLED"


RETRYABLE_FAILURES = {FailureCode.TRANSIENT_DEPENDENCY}


class BudgetState(FrozenModel):
    activity_attempts_used: int = Field(default=0, ge=0)
    max_activity_attempts: int = Field(default=3, ge=1)
    external_actions_used: int = Field(default=0, ge=0)
    max_external_actions: int = Field(default=1, ge=0)
    model_calls_used: int = Field(default=0, ge=0)
    max_model_calls: int = Field(default=3, ge=0)
    cost_usd: float = Field(default=0, ge=0)
    max_cost_usd: float = Field(default=0.05, ge=0)

    def consume_activity(self, *, cost_usd: float, new_external_action: bool) -> "BudgetState":
        attempts = self.activity_attempts_used + 1
        actions = self.external_actions_used + int(new_external_action)
        cost = self.cost_usd + cost_usd
        if attempts > self.max_activity_attempts:
            raise DurablePolicyError("ACTIVITY_ATTEMPT_BUDGET_EXHAUSTED")
        if actions > self.max_external_actions:
            raise DurablePolicyError("EXTERNAL_ACTION_BUDGET_EXHAUSTED")
        if cost > self.max_cost_usd:
            raise DurablePolicyError("COST_BUDGET_EXHAUSTED")
        return self.model_copy(
            update={
                "activity_attempts_used": attempts,
                "external_actions_used": actions,
                "cost_usd": cost,
            }
        )


class PreconditionSnapshot(FrozenModel):
    target_id: str = Field(min_length=1)
    resource_version: str = Field(min_length=1)
    evidence_digest: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    account_state: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)

    @property
    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class Proposal(FrozenModel):
    proposal_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    parameters: Mapping[str, Any]
    preconditions: PreconditionSnapshot
    created_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_window(self) -> "Proposal":
        if self.expires_at <= self.created_at:
            raise ValueError("PROPOSAL_EXPIRY_INVALID")
        return self

    @property
    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class ApprovalReceipt(FrozenModel):
    approval_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    proposal_digest: str = Field(min_length=1)
    precondition_digest: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    approver_roles: tuple[str, ...]
    policy_version: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_window(self) -> "ApprovalReceipt":
        if self.expires_at <= self.issued_at:
            raise ValueError("APPROVAL_EXPIRY_INVALID")
        return self


class EventEnvelope(FrozenModel):
    event_id: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    event_type: EventType
    wait_generation: int = Field(ge=0)
    occurred_at: datetime
    payload: Mapping[str, Any]
    payload_digest: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class TrustedExecutionContext(FrozenModel):
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    current_policy_version: str = Field(min_length=1)
    permitted_actions: tuple[str, ...]
    permitted_targets: tuple[str, ...]
    required_approver_role: str = Field(min_length=1)
    active_approvers: Mapping[str, tuple[str, ...]]
    current_preconditions: PreconditionSnapshot


class RunRecord(FrozenModel):
    run_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    workflow_version: str = WORKFLOW_VERSION
    state_schema_version: int = STATE_SCHEMA_VERSION
    status: RunStatus
    current_step: str = Field(min_length=1)
    proposal: Proposal | None = None
    budgets: BudgetState = Field(default_factory=BudgetState)
    workflow_attempt: int = Field(default=1, ge=1)
    state_version: int = Field(default=0, ge=0)
    wait_generation: int = Field(default=0, ge=0)
    wait_started_at: datetime | None = None
    pending_timer_id: str | None = None
    validated_approval_id: str | None = None
    cancellation_requested: bool = False
    manual_takeover_requested: bool = False
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ValidationResult(FrozenModel):
    accepted: bool
    reason_codes: tuple[str, ...]


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def payload_digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest(dict(payload))


def event_signature(
    secret: str,
    *,
    event_id: str,
    source_event_id: str,
    source: str,
    tenant_id: str,
    run_id: str,
    event_type: EventType,
    wait_generation: int,
    occurred_at: datetime,
    payload_digest_value: str,
) -> str:
    body = canonical_digest(
        {
            "event_id": event_id,
            "source_event_id": source_event_id,
            "source": source,
            "tenant_id": tenant_id,
            "run_id": run_id,
            "event_type": event_type.value,
            "wait_generation": wait_generation,
            "occurred_at": occurred_at.isoformat(),
            "payload_digest": payload_digest_value,
        }
    )
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def validate_transition(current: RunStatus, target: RunStatus) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise DurablePolicyError(f"INVALID_TRANSITION:{current.value}->{target.value}")


def validate_event(
    event: EventEnvelope,
    run: RunRecord,
    *,
    secret: str,
    now: datetime,
) -> ValidationResult:
    reasons: list[str] = []
    if event.run_id != run.run_id:
        reasons.append("EVENT_RUN_MISMATCH")
    if event.tenant_id != run.tenant_id:
        reasons.append("EVENT_TENANT_MISMATCH")
    allowed_sources: Mapping[EventType, frozenset[str]] = {
        EventType.APPROVAL_AVAILABLE: frozenset({"approval-gateway"}),
        EventType.APPROVAL_REJECTED: frozenset({"approval-gateway"}),
        EventType.APPROVAL_TIMEOUT: frozenset({"scheduler"}),
        EventType.TIMER_FIRED: frozenset({"scheduler"}),
        EventType.EXTERNAL_CALLBACK: frozenset({"integration-gateway"}),
        EventType.CANCEL_REQUESTED: frozenset({"operator-control"}),
        EventType.MANUAL_TAKEOVER: frozenset({"operator-control"}),
    }
    if event.source not in allowed_sources[event.event_type]:
        reasons.append("EVENT_SOURCE_NOT_AUTHORIZED")
    if event.wait_generation != run.wait_generation:
        reasons.append("STALE_EVENT_WAIT_GENERATION")
    if run.wait_started_at is not None and event.occurred_at < run.wait_started_at:
        reasons.append("STALE_EVENT_BEFORE_WAIT")
    if event.occurred_at > now + EVENT_MAX_FUTURE_SKEW:
        reasons.append("EVENT_OCCURRED_IN_FUTURE")
    if event.payload_digest != payload_digest(event.payload):
        reasons.append("EVENT_PAYLOAD_DIGEST_INVALID")
    expected = event_signature(
        secret,
        event_id=event.event_id,
        source_event_id=event.source_event_id,
        source=event.source,
        tenant_id=event.tenant_id,
        run_id=event.run_id,
        event_type=event.event_type,
        wait_generation=event.wait_generation,
        occurred_at=event.occurred_at,
        payload_digest_value=event.payload_digest,
    )
    if not hmac.compare_digest(expected, event.signature):
        reasons.append("EVENT_SIGNATURE_INVALID")
    if run.status in TERMINAL_STATUSES:
        reasons.append("STALE_EVENT_TERMINAL_RUN")
    return ValidationResult(
        accepted=not reasons,
        reason_codes=tuple(reasons) if reasons else ("EVENT_ADMITTED",),
    )


def validate_approval(
    receipt: ApprovalReceipt,
    run: RunRecord,
    context: TrustedExecutionContext,
    *,
    now: datetime,
) -> ValidationResult:
    reasons: list[str] = []
    proposal = run.proposal
    if proposal is None:
        reasons.append("PROPOSAL_MISSING")
    else:
        bindings = (
            (receipt.run_id == run.run_id, "APPROVAL_RUN_MISMATCH"),
            (receipt.tenant_id == run.tenant_id, "APPROVAL_TENANT_MISMATCH"),
            (receipt.subject_id == run.subject_id, "APPROVAL_SUBJECT_MISMATCH"),
            (receipt.proposal_id == proposal.proposal_id, "APPROVAL_PROPOSAL_MISMATCH"),
            (receipt.proposal_digest == proposal.digest, "APPROVAL_DIGEST_MISMATCH"),
            (
                receipt.precondition_digest == proposal.preconditions.digest,
                "APPROVAL_PRECONDITION_BINDING_MISMATCH",
            ),
            (receipt.action == proposal.action, "APPROVAL_ACTION_MISMATCH"),
            (receipt.target == proposal.target, "APPROVAL_TARGET_MISMATCH"),
        )
        reasons.extend(reason for passed, reason in bindings if not passed)
        if now > proposal.expires_at:
            reasons.append("PROPOSAL_EXPIRED")
        if receipt.issued_at < proposal.created_at:
            reasons.append("APPROVAL_PREDATES_PROPOSAL")
    if now > receipt.expires_at:
        reasons.append("APPROVAL_EXPIRED")
    if receipt.issued_at > now:
        reasons.append("APPROVAL_ISSUED_IN_FUTURE")
    if receipt.policy_version != context.current_policy_version:
        reasons.append("CURRENT_POLICY_CHANGED")
    if context.tenant_id != run.tenant_id:
        reasons.append("CONTEXT_TENANT_MISMATCH")
    if context.subject_id != run.subject_id:
        reasons.append("CONTEXT_SUBJECT_MISMATCH")
    if proposal is not None:
        if proposal.action not in context.permitted_actions:
            reasons.append("CURRENT_POLICY_ACTION_DENIED")
        if proposal.target not in context.permitted_targets:
            reasons.append("CURRENT_POLICY_TARGET_DENIED")
        if proposal.preconditions.digest != context.current_preconditions.digest:
            reasons.append("PRECONDITION_CHANGED")
    current_roles = context.active_approvers.get(receipt.approver_id, ())
    if context.required_approver_role not in receipt.approver_roles:
        reasons.append("APPROVER_ROLE_MISSING_AT_ISSUANCE")
    if context.required_approver_role not in current_roles:
        reasons.append("APPROVER_ROLE_NO_LONGER_ACTIVE")
    return ValidationResult(
        accepted=not reasons,
        reason_codes=tuple(reasons) if reasons else ("APPROVAL_VALIDATED",),
    )


def stable_operation_id(run: RunRecord) -> str:
    if run.proposal is None:
        raise DurablePolicyError("PROPOSAL_MISSING")
    identity = {
        "tenant_id": run.tenant_id,
        "run_id": run.run_id,
        "proposal_id": run.proposal.proposal_id,
        "action": run.proposal.action,
        "target": run.proposal.target,
    }
    return f"operation:{canonical_digest(identity)[:24]}"


def failure_is_retryable(code: FailureCode) -> bool:
    return code in RETRYABLE_FAILURES
