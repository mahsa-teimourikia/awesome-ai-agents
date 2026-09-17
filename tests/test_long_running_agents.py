"""Advanced Course 10 durable workflow and authority-boundary invariants."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

COURSE_DIR = (
    Path(__file__).resolve().parents[1]
    / "curriculum"
    / "advanced"
    / "10-long-running-asynchronous-agents"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _load("course10_policy", COURSE_DIR / "policy.py")
previous_policy = sys.modules.get("policy")
sys.modules["policy"] = policy
lab = _load("course10_lab", COURSE_DIR / "lab.py")
if previous_policy is None:
    sys.modules.pop("policy", None)
else:
    sys.modules["policy"] = previous_policy


def _runtime(tmp_path: Path, name: str = "workflow.db"):
    return lab.WorkflowRuntime(lab.DurableStore(tmp_path / name))


def _approval_event(run, receipt, *, event_id="event-approval"):
    return lab.signed_event(
        event_id=event_id,
        run_id=run.run_id,
        event_type=policy.EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": receipt.approval_id},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=6),
    )


def _approve(runtime, run, *, context=None, receipt=None, event_id="event-approval"):
    receipt = receipt or lab.fixture_approval(run)
    runtime.store.put_approval(receipt)
    result = runtime.process_event(
        _approval_event(run, receipt, event_id=event_id),
        context or lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=6),
    )
    return result, receipt


def _claim_and_prepare(runtime, run_id, *, worker="worker-a", now=None, context=None):
    now = now or lab.FIXED_TIME + timedelta(minutes=7)
    ready = runtime.store.load_run(run_id)
    lease = runtime.store.claim_lease(
        run_id,
        worker,
        expected_version=ready.state_version,
        now=now,
    )
    assert lease.acquired
    return runtime.store.prepare_operation(
        run_id,
        worker,
        context or lab.fixture_context(),
        now=now + timedelta(seconds=1),
    )


def test_happy_path_survives_process_restart(tmp_path):
    database = tmp_path / "restart.db"
    process_a = lab.WorkflowRuntime(lab.DurableStore(database))
    waiting = process_a.start_approval_run("run-restart")
    receipt = lab.fixture_approval(waiting)
    process_a.store.put_approval(receipt)

    process_b = lab.WorkflowRuntime(lab.DurableStore(database))
    admitted = process_b.process_event(
        _approval_event(waiting, receipt),
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=6),
    )
    prepared = _claim_and_prepare(process_b, waiting.run_id)
    provider = lab.DeterministicProvider()
    process_b.execute(
        prepared,
        provider,
        lab.ProviderOutcome.SUCCESS,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    completed = process_b.verify_and_complete(
        waiting.run_id,
        prepared.logical_operation_id,
        provider,
        now=lab.FIXED_TIME + timedelta(minutes=9),
    )

    assert admitted.run_status is policy.RunStatus.READY_TO_RESUME
    assert completed.status is policy.RunStatus.COMPLETED
    assert provider.calls == 1
    assert len(process_b.store.history(waiting.run_id)) >= 8


def test_invalid_state_transition_fails_closed(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-transition")
    with pytest.raises(policy.DurablePolicyError, match="INVALID_TRANSITION"):
        runtime.store.transition(
            waiting.run_id,
            waiting.state_version,
            policy.RunStatus.COMPLETED,
            now=lab.FIXED_TIME + timedelta(minutes=1),
            reason_code="SKIP_CONTROLS",
        )


def test_compare_and_swap_rejects_stale_state_version(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-cas")
    with pytest.raises(policy.DurablePolicyError, match="STATE_VERSION_CONFLICT"):
        runtime.store.transition(
            waiting.run_id,
            waiting.state_version - 1,
            policy.RunStatus.CANCELLED,
            now=lab.FIXED_TIME + timedelta(minutes=1),
            reason_code="STALE_WRITER",
        )


def test_duplicate_event_is_deduplicated_durably(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-dedupe")
    receipt = lab.fixture_approval(waiting)
    runtime.store.put_approval(receipt)
    event = _approval_event(waiting, receipt)

    first = runtime.process_event(event, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=6))
    second = runtime.process_event(event, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=7))

    assert first.disposition is lab.EventDisposition.PROCESSED
    assert second.disposition is lab.EventDisposition.DUPLICATE
    assert second.state_version == first.state_version
    assert runtime.store.inbox_count(event.event_id) == 1


def test_reused_event_id_with_different_payload_is_rejected_as_collision(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-event-collision")
    receipt = lab.fixture_approval(waiting)
    runtime.store.put_approval(receipt)
    event = _approval_event(waiting, receipt)
    runtime.process_event(
        event,
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=6),
    )
    collision = lab.signed_event(
        event_id=event.event_id,
        run_id=waiting.run_id,
        event_type=policy.EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": "different-receipt"},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=7),
    )
    result = runtime.process_event(
        collision,
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=7),
    )
    assert result.disposition is lab.EventDisposition.REJECTED
    assert result.reason_codes == ("EVENT_ID_COLLISION",)
    assert runtime.store.inbox_count(event.event_id) == 1


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("tenant", "EVENT_TENANT_MISMATCH"),
        ("payload", "EVENT_PAYLOAD_DIGEST_INVALID"),
        ("signature", "EVENT_SIGNATURE_INVALID"),
    ],
)
def test_untrusted_or_tampered_events_cannot_resume(tmp_path, mutation, reason):
    runtime = _runtime(tmp_path, f"{mutation}.db")
    waiting = runtime.start_approval_run(f"run-{mutation}")
    receipt = lab.fixture_approval(waiting)
    runtime.store.put_approval(receipt)
    event = _approval_event(waiting, receipt)
    if mutation == "tenant":
        event = lab.signed_event(
            event_id=event.event_id,
            run_id=event.run_id,
            event_type=event.event_type,
            payload=dict(event.payload),
            occurred_at=event.occurred_at,
            tenant_id="other-tenant",
        )
    elif mutation == "payload":
        event = event.model_copy(update={"payload": {"approval_id": "attacker"}})
    else:
        event = event.model_copy(update={"signature": "not-a-valid-signature"})

    result = runtime.process_event(event, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=6))

    assert result.disposition is lab.EventDisposition.REJECTED
    assert reason in result.reason_codes
    assert runtime.store.load_run(waiting.run_id).status is policy.RunStatus.WAITING_APPROVAL


@pytest.mark.parametrize(
    ("receipt_update", "context_update", "reason"),
    [
        ({"tenant_id": "other"}, {}, "APPROVAL_TENANT_MISMATCH"),
        ({"subject_id": "other"}, {}, "APPROVAL_SUBJECT_MISMATCH"),
        ({"proposal_id": "other"}, {}, "APPROVAL_PROPOSAL_MISMATCH"),
        ({"proposal_digest": "other"}, {}, "APPROVAL_DIGEST_MISMATCH"),
        ({"precondition_digest": "other"}, {}, "APPROVAL_PRECONDITION_BINDING_MISMATCH"),
        ({"action": "DELETE_ORDER"}, {}, "APPROVAL_ACTION_MISMATCH"),
        ({"target": "order-99"}, {}, "APPROVAL_TARGET_MISMATCH"),
        ({"policy_version": "old-policy"}, {}, "CURRENT_POLICY_CHANGED"),
        ({}, {"current_policy_version": "new-policy"}, "CURRENT_POLICY_CHANGED"),
        ({}, {"permitted_actions": ()}, "CURRENT_POLICY_ACTION_DENIED"),
        ({}, {"permitted_targets": ()}, "CURRENT_POLICY_TARGET_DENIED"),
        ({}, {"active_approvers": {}}, "APPROVER_ROLE_NO_LONGER_ACTIVE"),
    ],
)
def test_approval_receipt_and_current_authority_are_fully_bound(
    tmp_path, receipt_update, context_update, reason
):
    runtime = _runtime(tmp_path, f"approval-{reason}.db")
    waiting = runtime.start_approval_run(f"run-{reason.lower()}")
    receipt = lab.fixture_approval(waiting).model_copy(update=receipt_update)
    context = lab.fixture_context().model_copy(update=context_update)
    runtime.store.put_approval(receipt)

    result = runtime.process_event(
        _approval_event(waiting, receipt),
        context,
        now=lab.FIXED_TIME + timedelta(minutes=6),
    )

    assert result.disposition is lab.EventDisposition.REJECTED
    assert reason in result.reason_codes


def test_changed_precondition_blocks_approval(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-precondition")
    context = lab.fixture_context(
        preconditions=lab.fixture_preconditions(resource_version="order-v8")
    )
    result, _ = _approve(runtime, waiting, context=context)
    assert result.disposition is lab.EventDisposition.REJECTED
    assert "PRECONDITION_CHANGED" in result.reason_codes


def test_expired_and_future_approvals_are_rejected(tmp_path):
    for suffix, receipt in (
        (
            "expired",
            lambda run: lab.fixture_approval(
                run,
                now=lab.FIXED_TIME,
                expires_at=lab.FIXED_TIME + timedelta(minutes=1),
            ),
        ),
        (
            "future",
            lambda run: lab.fixture_approval(
                run,
                now=lab.FIXED_TIME + timedelta(hours=2),
            ),
        ),
    ):
        runtime = _runtime(tmp_path, f"{suffix}.db")
        waiting = runtime.start_approval_run(f"run-{suffix}")
        result, _ = _approve(runtime, waiting, receipt=receipt(waiting))
        assert result.disposition is lab.EventDisposition.REJECTED


def test_resume_event_without_receipt_has_no_authority(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-no-receipt")
    event = lab.signed_event(
        event_id="event-no-receipt",
        run_id=waiting.run_id,
        event_type=policy.EventType.APPROVAL_AVAILABLE,
        payload={"approval_id": "missing"},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=6),
    )
    result = runtime.process_event(event, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=6))
    assert result.disposition is lab.EventDisposition.REJECTED
    assert result.reason_codes == ("APPROVAL_RECEIPT_NOT_FOUND",)


def test_approval_receipt_is_single_use(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-single-use")
    first, receipt = _approve(runtime, waiting)
    second = runtime.process_event(
        _approval_event(waiting, receipt, event_id="second-delivery"),
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=7),
    )
    assert first.disposition is lab.EventDisposition.PROCESSED
    assert second.disposition is lab.EventDisposition.STALE
    assert second.run_status is policy.RunStatus.READY_TO_RESUME


def test_cancellation_wins_and_stale_approval_cannot_resurrect_run(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-cancel")
    receipt = lab.fixture_approval(waiting)
    runtime.store.put_approval(receipt)
    cancel = lab.signed_event(
        event_id="event-cancel",
        run_id=waiting.run_id,
        event_type=policy.EventType.CANCEL_REQUESTED,
        payload={"reason": "customer request"},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=5),
    )
    cancelled = runtime.process_event(cancel, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=5))
    late = runtime.process_event(
        _approval_event(waiting, receipt),
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=6),
    )
    assert cancelled.run_status is policy.RunStatus.CANCELLED
    assert late.disposition is lab.EventDisposition.STALE
    assert runtime.store.load_run(waiting.run_id).status is policy.RunStatus.CANCELLED


def test_manual_takeover_wins_and_stale_callbacks_cannot_resume(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-manual")
    takeover = lab.signed_event(
        event_id="event-takeover",
        run_id=waiting.run_id,
        event_type=policy.EventType.MANUAL_TAKEOVER,
        payload={"operator": "incident-commander"},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=3),
    )
    result = runtime.process_event(takeover, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=3))
    callback = lab.signed_event(
        event_id="late-callback",
        run_id=waiting.run_id,
        event_type=policy.EventType.EXTERNAL_CALLBACK,
        payload={"status": "ok"},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=4),
    )
    stale = runtime.process_event(callback, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=4))
    assert result.run_status is policy.RunStatus.MANUAL_CONTROL
    assert stale.disposition is lab.EventDisposition.STALE


@pytest.mark.parametrize(
    ("timeout_policy", "expected"),
    [
        (policy.TimeoutPolicy.EXPIRE, policy.RunStatus.EXPIRED),
        (policy.TimeoutPolicy.ESCALATE, policy.RunStatus.ESCALATED),
        (policy.TimeoutPolicy.CANCEL, policy.RunStatus.CANCELLED),
    ],
)
def test_durable_timer_applies_explicit_timeout_policy(tmp_path, timeout_policy, expected):
    runtime = _runtime(tmp_path, f"timer-{timeout_policy}.db")
    waiting = runtime.start_approval_run(
        f"run-{timeout_policy}",
        timeout_after=timedelta(minutes=10),
        timeout_policy=timeout_policy,
    )
    event = lab.signed_event(
        event_id=f"event-{timeout_policy}",
        run_id=waiting.run_id,
        event_type=policy.EventType.TIMER_FIRED,
        payload={"timer_id": waiting.pending_timer_id},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=10),
    )
    result = runtime.process_event(event, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=10))
    assert result.run_status is expected


def test_early_timer_is_rejected_without_state_change(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-early-timer")
    event = lab.signed_event(
        event_id="event-early-timer",
        run_id=waiting.run_id,
        event_type=policy.EventType.TIMER_FIRED,
        payload={"timer_id": waiting.pending_timer_id},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=1),
    )
    result = runtime.process_event(event, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=1))
    assert result.disposition is lab.EventDisposition.REJECTED
    assert result.run_status is policy.RunStatus.WAITING_APPROVAL


def test_approval_wins_race_and_late_timer_is_stale(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-race", timeout_after=timedelta(minutes=10))
    approved, _ = _approve(runtime, waiting)
    timer = lab.signed_event(
        event_id="event-late-timer",
        run_id=waiting.run_id,
        event_type=policy.EventType.TIMER_FIRED,
        payload={"timer_id": waiting.pending_timer_id},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=10),
    )
    late = runtime.process_event(timer, lab.fixture_context(), now=lab.FIXED_TIME + timedelta(minutes=10))
    assert approved.run_status is policy.RunStatus.READY_TO_RESUME
    assert late.disposition is lab.EventDisposition.STALE


def test_only_one_worker_claims_same_state_version(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-workers")
    _approve(runtime, waiting)
    ready = runtime.store.load_run(waiting.run_id)
    first = runtime.store.claim_lease(
        waiting.run_id, "worker-a", expected_version=ready.state_version, now=lab.FIXED_TIME + timedelta(minutes=7)
    )
    second = runtime.store.claim_lease(
        waiting.run_id, "worker-b", expected_version=ready.state_version, now=lab.FIXED_TIME + timedelta(minutes=7)
    )
    assert first.acquired
    assert not second.acquired
    assert second.reason_code == "STATE_VERSION_CONFLICT"


def test_expired_lease_can_be_reclaimed(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-lease-expiry")
    _approve(runtime, waiting)
    ready = runtime.store.load_run(waiting.run_id)
    first = runtime.store.claim_lease(
        waiting.run_id,
        "worker-a",
        expected_version=ready.state_version,
        now=lab.FIXED_TIME + timedelta(minutes=7),
        lease_seconds=1,
    )
    latest = runtime.store.load_run(waiting.run_id)
    second = runtime.store.claim_lease(
        waiting.run_id,
        "worker-b",
        expected_version=latest.state_version,
        now=lab.FIXED_TIME + timedelta(minutes=7, seconds=2),
    )
    assert first.acquired and second.acquired
    assert runtime.store.load_run(waiting.run_id).lease_owner == "worker-b"


def test_execution_requires_a_valid_lease_and_consumed_approval(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-execution-authority")
    _approve(runtime, waiting)
    with pytest.raises(policy.DurablePolicyError, match="VALID_WORKER_LEASE_REQUIRED"):
        runtime.store.prepare_operation(
            waiting.run_id,
            "unleased-worker",
            lab.fixture_context(),
            now=lab.FIXED_TIME + timedelta(minutes=7),
        )


def test_cancellation_after_claim_stops_the_next_provider_call(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-cancel-before-call")
    _approve(runtime, waiting)
    prepared = _claim_and_prepare(runtime, waiting.run_id)
    cancel = lab.signed_event(
        event_id="cancel-after-claim",
        run_id=waiting.run_id,
        event_type=policy.EventType.CANCEL_REQUESTED,
        payload={"reason": "operator stop"},
        occurred_at=lab.FIXED_TIME + timedelta(minutes=7, seconds=2),
    )
    cancelled = runtime.process_event(
        cancel,
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=7, seconds=2),
    )
    provider = lab.DeterministicProvider()
    with pytest.raises(policy.DurablePolicyError, match="OPERATION_CALL_NOT_AUTHORIZED"):
        runtime.execute(
            prepared,
            provider,
            lab.ProviderOutcome.SUCCESS,
            now=lab.FIXED_TIME + timedelta(minutes=7, seconds=3),
        )
    assert cancelled.run_status is policy.RunStatus.CANCELLED
    assert provider.calls == 0


def test_stable_logical_operation_id_and_unique_attempt_ids_across_retry(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-retry")
    _approve(runtime, waiting)
    first = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    runtime.execute(
        first,
        provider,
        lab.ProviderOutcome.TRANSIENT_BEFORE_COMMIT,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    ready = runtime.store.load_run(waiting.run_id)
    lease = runtime.store.claim_lease(
        waiting.run_id,
        "worker-a",
        expected_version=ready.state_version,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    assert lease.acquired
    retry = runtime.store.prepare_operation(
        waiting.run_id,
        "worker-a",
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=8, seconds=1),
    )
    assert retry.logical_operation_id == first.logical_operation_id
    assert retry.attempt_id != first.attempt_id
    assert runtime.store.operation_attempt_count(first.logical_operation_id) == 2


def test_unknown_outcome_requires_reconciliation_before_retry(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-unknown")
    _approve(runtime, waiting)
    prepared = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    uncertain = runtime.execute(
        prepared,
        provider,
        lab.ProviderOutcome.TIMEOUT_AFTER_COMMIT,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    blocked = runtime.store.prepare_operation(
        waiting.run_id,
        "worker-a",
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=8, seconds=1),
    )
    reconciled = runtime.reconcile(
        prepared.logical_operation_id,
        provider,
        now=lab.FIXED_TIME + timedelta(minutes=9),
    )
    assert uncertain.status is policy.RunStatus.RECONCILING
    assert blocked.disposition is lab.OperationDisposition.RECONCILE_REQUIRED
    assert reconciled.status is policy.RunStatus.VERIFYING
    assert provider.calls == 1


def test_reconciliation_can_prove_no_effect_then_allow_stable_retry(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-reconcile-none")
    _approve(runtime, waiting)
    first = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    runtime.execute(
        first,
        provider,
        lab.ProviderOutcome.TIMEOUT_AFTER_COMMIT,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    provider.effects.clear()
    ready = runtime.reconcile(first.logical_operation_id, provider, now=lab.FIXED_TIME + timedelta(minutes=9))
    lease = runtime.store.claim_lease(
        waiting.run_id,
        "worker-a",
        expected_version=ready.state_version,
        now=lab.FIXED_TIME + timedelta(minutes=9),
    )
    assert lease.acquired
    retry = runtime.store.prepare_operation(
        waiting.run_id,
        "worker-a",
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=9, seconds=1),
    )
    assert ready.status is policy.RunStatus.READY_TO_RESUME
    assert retry.logical_operation_id == first.logical_operation_id
    assert retry.attempt_id != first.attempt_id


def test_duplicate_execution_delivery_does_not_repeat_confirmed_effect(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-effect-dedupe")
    _approve(runtime, waiting)
    prepared = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    runtime.execute(prepared, provider, lab.ProviderOutcome.SUCCESS, now=lab.FIXED_TIME + timedelta(minutes=8))
    duplicate = runtime.store.prepare_operation(
        waiting.run_id,
        "worker-a",
        lab.fixture_context(),
        now=lab.FIXED_TIME + timedelta(minutes=9),
    )
    assert duplicate.disposition is lab.OperationDisposition.ALREADY_SUCCEEDED
    assert provider.calls == 1


def test_terminal_failure_is_not_retried(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-terminal")
    _approve(runtime, waiting)
    prepared = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    failed = runtime.execute(
        prepared,
        provider,
        lab.ProviderOutcome.TERMINAL_FAILURE,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    assert failed.status is policy.RunStatus.FAILED
    assert policy.failure_is_retryable(policy.FailureCode.POLICY_DENIED) is False
    assert policy.failure_is_retryable(policy.FailureCode.TRANSIENT_DEPENDENCY) is True


def test_activity_budget_is_persistent_and_bounded_across_restart(tmp_path):
    database = tmp_path / "budget.db"
    runtime = lab.WorkflowRuntime(lab.DurableStore(database))
    waiting = runtime.start_approval_run(
        "run-budget",
        budgets=policy.BudgetState(max_activity_attempts=1),
    )
    _approve(runtime, waiting)
    prepared = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    runtime.execute(
        prepared,
        provider,
        lab.ProviderOutcome.TRANSIENT_BEFORE_COMMIT,
        now=lab.FIXED_TIME + timedelta(minutes=8),
    )
    restarted = lab.WorkflowRuntime(lab.DurableStore(database))
    ready = restarted.store.load_run(waiting.run_id)
    lease = restarted.store.claim_lease(
        waiting.run_id,
        "worker-a",
        expected_version=ready.state_version,
        now=lab.FIXED_TIME + timedelta(minutes=9),
    )
    assert lease.acquired
    with pytest.raises(policy.DurablePolicyError, match="ACTIVITY_ATTEMPT_BUDGET_EXHAUSTED"):
        restarted.store.prepare_operation(
            waiting.run_id,
            "worker-a",
            lab.fixture_context(),
            now=lab.FIXED_TIME + timedelta(minutes=8, seconds=1),
        )


def test_completion_requires_effect_verification(tmp_path):
    runtime = _runtime(tmp_path)
    waiting = runtime.start_approval_run("run-verify")
    _approve(runtime, waiting)
    prepared = _claim_and_prepare(runtime, waiting.run_id)
    provider = lab.DeterministicProvider()
    runtime.execute(prepared, provider, lab.ProviderOutcome.SUCCESS, now=lab.FIXED_TIME + timedelta(minutes=8))
    provider.effects.clear()
    with pytest.raises(policy.DurablePolicyError, match="EFFECT_VERIFICATION_FAILED"):
        runtime.verify_and_complete(
            waiting.run_id,
            prepared.logical_operation_id,
            provider,
            now=lab.FIXED_TIME + timedelta(minutes=9),
        )


@pytest.mark.parametrize(
    ("workflow_version", "schema_version", "reason"),
    [
        ("future-workflow", policy.STATE_SCHEMA_VERSION, "WORKFLOW_VERSION_UNSUPPORTED"),
        (policy.WORKFLOW_VERSION, 999, "STATE_SCHEMA_VERSION_UNSUPPORTED"),
    ],
)
def test_unsupported_versions_are_not_silently_replayed(
    tmp_path, workflow_version, schema_version, reason
):
    store = lab.DurableStore(tmp_path / f"{reason}.db")
    run = policy.RunRecord(
        run_id=f"run-{reason}",
        tenant_id=lab.TENANT_ID,
        subject_id=lab.SUBJECT_ID,
        workflow_version=workflow_version,
        state_schema_version=schema_version,
        status=policy.RunStatus.CREATED,
        current_step="created",
        created_at=lab.FIXED_TIME,
        updated_at=lab.FIXED_TIME,
    )
    store.create_run(run)
    runtime = lab.WorkflowRuntime(store)
    with pytest.raises(policy.DurablePolicyError, match=reason):
        runtime.load_compatible(run.run_id)


def test_history_and_outbox_are_durable_audit_records(tmp_path):
    database = tmp_path / "audit.db"
    runtime = lab.WorkflowRuntime(lab.DurableStore(database))
    waiting = runtime.start_approval_run("run-audit")
    _approve(runtime, waiting)
    restarted = lab.DurableStore(database)
    history = restarted.history(waiting.run_id)
    outbox = restarted.outbox_messages(waiting.run_id)
    assert [row["to_status"] for row in history] == [
        "CREATED",
        "RUNNING",
        "WAITING_APPROVAL",
        "READY_TO_RESUME",
    ]
    assert all(message["status"] == "PENDING" for message in outbox)
    assert len(outbox) == 3


def test_schema_rejects_invalid_expiry_windows():
    with pytest.raises(ValidationError, match="PROPOSAL_EXPIRY_INVALID"):
        policy.Proposal(
            proposal_id="p",
            action="a",
            target="t",
            parameters={},
            preconditions=lab.fixture_preconditions(),
            created_at=lab.FIXED_TIME,
            expires_at=lab.FIXED_TIME,
        )


def test_course_source_avoids_unsafe_replace_and_exactly_once_claims():
    source = (COURSE_DIR / "lab.py").read_text()
    assert "INSERT OR REPLACE" not in source
    assert "exactly once" not in source.lower()


def test_same_case_evaluation_exposes_naive_baseline_failures(tmp_path):
    report = lab.evaluate_same_cases(tmp_path / "evaluation")
    assert report.case_ids == (
        "duplicate_delivery",
        "cross_tenant_event",
        "cancel_then_late_approval",
        "unknown_provider_outcome",
    )
    assert report.baseline.safe_outcome_rate == 0
    assert report.baseline.unsafe_resumes == 2
    assert report.baseline.duplicate_effects == 2
    assert report.governed.safe_outcome_rate == 1
    assert report.governed.unsafe_resumes == 0
    assert report.governed.duplicate_effects == 0
    assert report.governed.provider_calls == 2
    assert report.governed.reconciliations == 1
