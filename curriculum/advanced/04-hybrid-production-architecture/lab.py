"""Deterministic Northstar lab for application-owned architecture selection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from policy import (
    ArchitectureDecision,
    ArchitectureEscalationRequest,
    ArchitectureTransitionState,
    ArchitectureType,
    Capability,
    DataClassification,
    DecisionAudit,
    ExecutionContract,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    FailureCode,
    Intent,
    PIIAction,
    POLICY_VERSION,
    PasswordResetState,
    PasswordResetStatus,
    ReasonCode,
    RequestClassification,
    RequestContext,
    RiskTier,
    SideEffectLevel,
    ClassificationConfidence,
    LatencyClass,
    admit_architecture_transition,
    build_execution_contract,
    decide_architecture,
    propose_classification,
    record_decision,
    require_capabilities,
    validate_classification,
    validate_execution_result,
)


NORTHSTAR_TENANT = "northstar-commerce"
FIXED_TIME = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
FIXTURE_OTP = "731904"

REQUESTS = {
    "status": "Is checkout healthy?",
    "password": "Reset my password.",
    "diagnosis": "Why did EU checkout conversion fall after deploy-1842?",
    "pipeline": "Generate a remediation proposal and independently security-review it.",
    "team": "Investigate checkout across observability, deployment, and customer impact.",
    "rollback": "Rollback deploy-1842.",
    "unknown_destructive": "Please destroy every stale record immediately.",
}

ALL_CAPABILITIES = tuple(Capability)


def build_context(
    request_id: str,
    *,
    tenant_id: str = NORTHSTAR_TENANT,
    allowed_capabilities: tuple[Capability, ...] = ALL_CAPABILITIES,
    data_classification: DataClassification = DataClassification.INTERNAL,
    deadline_ms: int = 2_000,
) -> RequestContext:
    return RequestContext(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id="user-1042",
        roles=("support-user", "incident-responder"),
        allowed_capabilities=allowed_capabilities,
        data_classification=data_classification,
        policy_version=POLICY_VERSION,
        deadline_ms=deadline_ms,
    )


_EVIDENCE = {
    "checkout-health": {
        "tenant_id": NORTHSTAR_TENANT,
        "status": "degraded",
        "conversion_drop": "38%",
    },
    "checkout-logs": {
        "tenant_id": NORTHSTAR_TENANT,
        "failure_mode": "3DS callback signature mismatch",
    },
    "deploy-1842": {
        "tenant_id": NORTHSTAR_TENANT,
        "component": "checkout-api",
        "version": "deploy-1842",
    },
    "rollback-runbook": {
        "tenant_id": NORTHSTAR_TENANT,
        "next_step": "review proposal, obtain approval, execute idempotently",
    },
    "customer-impact": {
        "tenant_id": NORTHSTAR_TENANT,
        "affected_segment": "EU enterprise",
        "reported_failures": 126,
    },
}


def _tenant_evidence(contract: ExecutionContract, evidence_id: str) -> dict[str, object]:
    record = _EVIDENCE[evidence_id]
    if record["tenant_id"] != contract.tenant_id:
        raise ValueError("AUTH_DENIED")
    return record


def _result(
    contract: ExecutionContract,
    *,
    status: ExecutionStatus,
    output: dict[str, object],
    evidence_ids: tuple[str, ...] = (),
    model_calls: int = 0,
    tool_calls: int = 0,
    cost_usd: float = 0,
    total_work_ms: int = 0,
    wall_clock_ms: int = 0,
    events: tuple[str, ...] = (),
    failure: FailureCode | None = None,
    privileged_exposure: int = 0,
) -> ExecutionResult:
    return ExecutionResult(
        request_id=contract.request_id,
        tenant_id=contract.tenant_id,
        architecture=contract.architecture,
        status=status,
        output=output,
        evidence_ids=evidence_ids,
        model_calls=model_calls,
        tool_calls=tool_calls,
        cost_usd=cost_usd,
        total_work_ms=total_work_ms,
        wall_clock_ms=wall_clock_ms,
        policy_events=events,
        approval_required=contract.approval_required,
        failure_code=failure,
        privileged_capability_exposure=privileged_exposure,
    )


class ArchitectureRunner(Protocol):
    def run(
        self, contract: ExecutionContract, request: ExecutionRequest
    ) -> ExecutionResult: ...


class DirectFunctionRunner:
    def run(self, contract: ExecutionContract, request: ExecutionRequest) -> ExecutionResult:
        require_capabilities(contract, (Capability.CHECKOUT_HEALTH_READ,))
        if not request.dependencies_available:
            return _result(
                contract,
                status=ExecutionStatus.DEGRADED,
                output={"message": "Health source unavailable; status not guessed."},
                tool_calls=1,
                total_work_ms=20,
                wall_clock_ms=20,
                events=("DEPENDENCY_FALLBACK_REQUIRED",),
                failure=FailureCode.DEPENDENCY_UNAVAILABLE,
            )
        health = _tenant_evidence(contract, "checkout-health")
        return _result(
            contract,
            status=ExecutionStatus.SUCCEEDED,
            output={"checkout_status": health["status"]},
            evidence_ids=("checkout-health",),
            tool_calls=1,
            total_work_ms=25,
            wall_clock_ms=25,
            events=("DIRECT_HANDLER_ADMITTED", "OUTPUT_VALIDATED"),
        )


def _otp_digest(request_id: str, otp: str) -> str:
    return sha256(f"{request_id}:{otp}".encode()).hexdigest()


def begin_password_reset(
    context: RequestContext,
    *,
    now: datetime = FIXED_TIME,
    otp: str = FIXTURE_OTP,
    ttl_seconds: int = 300,
    max_attempts: int = 3,
) -> PasswordResetState:
    if not {Capability.OTP_SEND, Capability.PASSWORD_UPDATE}.issubset(
        set(context.allowed_capabilities)
    ):
        raise ValueError("AUTH_DENIED")
    state = PasswordResetState(
        request_id=context.request_id,
        tenant_id=context.tenant_id,
        logical_operation_id=f"password-reset:{context.tenant_id}:{context.user_id}",
        status=PasswordResetStatus.REQUESTED,
        otp_digest=_otp_digest(context.request_id, otp),
        otp_expires_at=now + timedelta(seconds=ttl_seconds),
        max_attempts=max_attempts,
    )
    state.status = PasswordResetStatus.OTP_SENT
    state.status = PasswordResetStatus.WAITING_FOR_OTP
    return state


def submit_otp(
    state: PasswordResetState,
    otp: str,
    *,
    attempt_id: str,
    now: datetime = FIXED_TIME,
) -> PasswordResetStatus:
    if state.status is PasswordResetStatus.CANCELLED:
        raise ValueError("CANCELLED")
    if state.status not in {
        PasswordResetStatus.WAITING_FOR_OTP,
        PasswordResetStatus.INVALID_OTP,
    }:
        raise ValueError("OTP_NOT_EXPECTED")
    if attempt_id in state.attempt_ids:
        raise ValueError("DUPLICATE_ATTEMPT")
    state.attempt_ids = (*state.attempt_ids, attempt_id)
    if now >= state.otp_expires_at:
        state.status = PasswordResetStatus.EXPIRED_OTP
        return state.status
    state.attempt_count += 1
    if _otp_digest(state.request_id, otp) != state.otp_digest:
        state.status = (
            PasswordResetStatus.MAX_ATTEMPTS
            if state.attempt_count >= state.max_attempts
            else PasswordResetStatus.INVALID_OTP
        )
        return state.status
    state.verified_identity = True
    state.status = PasswordResetStatus.VERIFIED
    return state.status


def authorize_password_update(state: PasswordResetState) -> None:
    if state.status is not PasswordResetStatus.VERIFIED or not state.verified_identity:
        raise ValueError("IDENTITY_NOT_VERIFIED")
    state.update_authorized = True
    state.status = PasswordResetStatus.PASSWORD_UPDATE_AUTHORIZED


def execute_password_update(state: PasswordResetState) -> bool:
    if state.logical_operation_id in state.completed_operation_ids:
        state.status = PasswordResetStatus.COMPLETED
        return False
    if (
        state.status is not PasswordResetStatus.PASSWORD_UPDATE_AUTHORIZED
        or not state.verified_identity
        or not state.update_authorized
    ):
        raise ValueError("PASSWORD_UPDATE_NOT_AUTHORIZED")
    state.password_update_count += 1
    state.completed_operation_ids = (
        *state.completed_operation_ids,
        state.logical_operation_id,
    )
    state.status = PasswordResetStatus.COMPLETED
    return True


def cancel_password_reset(state: PasswordResetState) -> None:
    if state.status is not PasswordResetStatus.COMPLETED:
        state.status = PasswordResetStatus.CANCELLED


def save_password_state(state: PasswordResetState, path: Path) -> None:
    path.write_text(state.model_dump_json(indent=2))


def load_password_state(path: Path) -> PasswordResetState:
    return PasswordResetState.model_validate_json(path.read_text())


class WorkflowRunner:
    def run(self, contract: ExecutionContract, request: ExecutionRequest) -> ExecutionResult:
        if not request.dependencies_available:
            return _result(
                contract,
                status=ExecutionStatus.DEGRADED,
                output={"message": "Workflow dependency unavailable; no write attempted."},
                events=("DEPENDENCY_UNAVAILABLE", "WRITE_NOT_ATTEMPTED"),
                failure=FailureCode.DEPENDENCY_UNAVAILABLE,
            )
        if "rollback" in request.text.casefold():
            try:
                require_capabilities(contract, (Capability.PRODUCTION_ROLLBACK,))
            except ValueError:
                return _result(
                    contract,
                    status=ExecutionStatus.BLOCKED,
                    output={"message": "Rollback capability denied."},
                    events=("AUTHORIZATION_DENIED",),
                    failure=FailureCode.AUTH_DENIED,
                )
            if not request.validated_approval:
                return _result(
                    contract,
                    status=ExecutionStatus.BLOCKED,
                    output={"message": "Validated approval required before rollback."},
                    evidence_ids=("review-pass",),
                    events=("APPROVAL_REQUIRED",),
                    failure=FailureCode.POLICY_BLOCKED,
                )
            return _result(
                contract,
                status=ExecutionStatus.SUCCEEDED,
                output={"operation": "rollback deploy-1842", "idempotent": True},
                evidence_ids=("review-pass", "validated-approval"),
                tool_calls=1,
                total_work_ms=80,
                wall_clock_ms=80,
                events=("REVIEW_PASS_VALIDATED", "APPROVAL_VALIDATED", "WRITE_EXECUTED"),
                privileged_exposure=1,
            )

        try:
            require_capabilities(
                contract, (Capability.OTP_SEND, Capability.PASSWORD_UPDATE)
            )
        except ValueError:
            return _result(
                contract,
                status=ExecutionStatus.BLOCKED,
                output={"message": "Password workflow capability denied."},
                events=("AUTHORIZATION_DENIED",),
                failure=FailureCode.AUTH_DENIED,
            )
        context = build_context(
            contract.request_id,
            tenant_id=contract.tenant_id,
            allowed_capabilities=contract.allowed_capabilities,
        )
        state = begin_password_reset(context)
        if request.supplied_otp is None:
            return _result(
                contract,
                status=ExecutionStatus.WAITING,
                output={"workflow_state": state.status.value},
                tool_calls=1,
                total_work_ms=30,
                wall_clock_ms=30,
                events=("OTP_SENT", "WAITING_FOR_OTP"),
            )
        status = submit_otp(
            state,
            request.supplied_otp,
            attempt_id=f"{contract.request_id}:otp-attempt-1",
        )
        if status is not PasswordResetStatus.VERIFIED:
            return _result(
                contract,
                status=ExecutionStatus.BLOCKED,
                output={"workflow_state": status.value},
                tool_calls=2,
                total_work_ms=45,
                wall_clock_ms=45,
                events=("OTP_REJECTED",),
                failure=FailureCode.POLICY_BLOCKED,
            )
        authorize_password_update(state)
        execute_password_update(state)
        return _result(
            contract,
            status=ExecutionStatus.SUCCEEDED,
            output={"workflow_state": state.status.value},
            evidence_ids=("identity-verification",),
            tool_calls=3,
            total_work_ms=70,
            wall_clock_ms=70,
            events=("OTP_VERIFIED", "PASSWORD_UPDATE_AUTHORIZED", "UPDATE_COMMITTED"),
        )


class BoundedAgentRunner:
    def run(self, contract: ExecutionContract, request: ExecutionRequest) -> ExecutionResult:
        required = (
            Capability.CHECKOUT_HEALTH_READ,
            Capability.LOGS_READ,
            Capability.DEPLOYMENT_READ,
            Capability.RUNBOOK_READ,
        )
        require_capabilities(contract, required)
        if not request.model_available:
            return _result(
                contract,
                status=ExecutionStatus.ESCALATED,
                output={"message": "Model unavailable; evidence was not interpreted."},
                events=("MODEL_UNAVAILABLE", "HUMAN_ESCALATION_REQUESTED"),
                failure=FailureCode.MODEL_UNAVAILABLE,
            )
        if not request.dependencies_available:
            return _result(
                contract,
                status=ExecutionStatus.DEGRADED,
                output={"message": "Required evidence source unavailable."},
                model_calls=1,
                tool_calls=1,
                cost_usd=0.004,
                total_work_ms=90,
                wall_clock_ms=90,
                events=("DEPENDENCY_UNAVAILABLE", "SAFE_DEGRADED_RESPONSE"),
                failure=FailureCode.DEPENDENCY_UNAVAILABLE,
            )
        for evidence_id in (
            "checkout-health",
            "checkout-logs",
            "deploy-1842",
            "rollback-runbook",
        ):
            _tenant_evidence(contract, evidence_id)
        if "need a team" in request.text.casefold():
            return _result(
                contract,
                status=ExecutionStatus.ESCALATED,
                output={
                    "event": "ARCHITECTURE_ESCALATION_REQUEST",
                    "target": ArchitectureType.SELECTOR_TEAM.value,
                },
                evidence_ids=("checkout-health",),
                model_calls=1,
                tool_calls=1,
                cost_usd=0.006,
                total_work_ms=100,
                wall_clock_ms=100,
                events=("ARCHITECTURE_ESCALATION_REQUEST",),
            )
        return _result(
            contract,
            status=ExecutionStatus.SUCCEEDED,
            output={
                "hypothesis": "deploy-1842 introduced a 3DS callback signature mismatch",
                "next_step": "prepare a rollback proposal; do not execute",
            },
            evidence_ids=(
                "checkout-health",
                "checkout-logs",
                "deploy-1842",
                "rollback-runbook",
            ),
            model_calls=2,
            tool_calls=4,
            cost_usd=0.018,
            total_work_ms=260,
            wall_clock_ms=260,
            events=("READ_TOOLS_ONLY", "EVIDENCE_COMPLETE", "OUTPUT_VALIDATED"),
        )


class PipelineRunner:
    def run(self, contract: ExecutionContract, request: ExecutionRequest) -> ExecutionResult:
        require_capabilities(
            contract, (Capability.PROPOSAL_GENERATE, Capability.SECURITY_REVIEW)
        )
        if not request.model_available:
            return _result(
                contract,
                status=ExecutionStatus.ESCALATED,
                output={"message": "Proposal pipeline unavailable; human review required."},
                events=("MODEL_UNAVAILABLE", "HUMAN_ESCALATION_REQUESTED"),
                failure=FailureCode.MODEL_UNAVAILABLE,
            )
        return _result(
            contract,
            status=ExecutionStatus.SUCCEEDED,
            output={
                "proposal": "Validate rollback candidate under the controlled workflow.",
                "security_review": "PASS_WITH_APPROVAL_REQUIRED",
                "deterministic_gate_state": "PROPOSAL_REVIEWED",
            },
            evidence_ids=("remediation-proposal", "security-review"),
            model_calls=2,
            cost_usd=0.026,
            total_work_ms=240,
            wall_clock_ms=240,
            events=(
                "PROPOSAL_ACCEPTED",
                "INDEPENDENT_REVIEW_ACCEPTED",
                "DETERMINISTIC_GATE_PASSED",
            ),
        )


class TeamRunner:
    def run(self, contract: ExecutionContract, request: ExecutionRequest) -> ExecutionResult:
        required = (
            Capability.CHECKOUT_HEALTH_READ,
            Capability.DEPLOYMENT_READ,
            Capability.CUSTOMER_IMPACT_READ,
        )
        require_capabilities(contract, required)
        if not request.model_available:
            return _result(
                contract,
                status=ExecutionStatus.ESCALATED,
                output={"message": "Team models unavailable; route to incident command."},
                events=("MODEL_UNAVAILABLE", "HUMAN_ESCALATION_REQUESTED"),
                failure=FailureCode.MODEL_UNAVAILABLE,
            )
        if not request.dependencies_available:
            return _result(
                contract,
                status=ExecutionStatus.DEGRADED,
                output={"message": "One or more specialist sources unavailable."},
                model_calls=3,
                tool_calls=3,
                cost_usd=0.025,
                total_work_ms=180,
                wall_clock_ms=70,
                events=("PARTIAL_EVIDENCE", "HUMAN_ESCALATION_REQUESTED"),
                failure=FailureCode.DEPENDENCY_UNAVAILABLE,
            )
        for evidence_id in ("checkout-health", "deploy-1842", "customer-impact"):
            _tenant_evidence(contract, evidence_id)
        return _result(
            contract,
            status=ExecutionStatus.SUCCEEDED,
            output={
                "synthesis": "EU enterprise conversion fell after deploy-1842.",
                "specialists": ["observability", "deployment", "customer-impact"],
            },
            evidence_ids=("checkout-health", "deploy-1842", "customer-impact"),
            model_calls=4,
            tool_calls=3,
            cost_usd=0.044,
            total_work_ms=290,
            wall_clock_ms=150,
            events=("PARALLEL_SPECIALISTS", "TYPED_ARTIFACTS", "SYNTHESIS_VALIDATED"),
        )


class HumanEscalationRunner:
    def run(self, contract: ExecutionContract, request: ExecutionRequest) -> ExecutionResult:
        return _result(
            contract,
            status=ExecutionStatus.ESCALATED,
            output={"message": "Request requires deterministic clarification or human review."},
            events=("HUMAN_ESCALATION",),
            failure=FailureCode.POLICY_BLOCKED,
        )


class ArchitectureRegistry:
    """Framework-neutral adapters behind one application-owned interface."""

    def __init__(self) -> None:
        direct = DirectFunctionRunner()
        workflow = WorkflowRunner()
        agent = BoundedAgentRunner()
        pipeline = PipelineRunner()
        team = TeamRunner()
        human = HumanEscalationRunner()
        self._runners: dict[ArchitectureType, ArchitectureRunner] = {
            ArchitectureType.DIRECT_FUNCTION: direct,
            ArchitectureType.DETERMINISTIC_WORKFLOW: workflow,
            ArchitectureType.BOUNDED_SINGLE_AGENT: agent,
            ArchitectureType.PIPELINE: pipeline,
            ArchitectureType.MANAGER_SPECIALISTS: team,
            ArchitectureType.SELECTOR_TEAM: team,
            ArchitectureType.CREW: team,
            ArchitectureType.HUMAN_ESCALATION: human,
        }

    def run(
        self,
        contract: ExecutionContract,
        request: ExecutionRequest,
        *,
        pii_action: PIIAction = PIIAction.BLOCK,
    ) -> ExecutionResult:
        if request.cancelled:
            return _result(
                contract,
                status=ExecutionStatus.CANCELLED,
                output={"message": "Cancelled before runner invocation."},
                events=("CANCELLED_BEFORE_NEXT_WORK",),
                failure=FailureCode.CANCELLED,
            )
        runner = self._runners[contract.architecture]
        try:
            candidate = runner.run(contract, request)
        except ValueError as error:
            if str(error) != "AUTH_DENIED":
                raise
            candidate = _result(
                contract,
                status=ExecutionStatus.BLOCKED,
                output={"message": "Required capability denied."},
                events=("AUTHORIZATION_DENIED",),
                failure=FailureCode.AUTH_DENIED,
            )
        return validate_execution_result(candidate, contract, pii_action=pii_action)


class ControlPlaneRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    classification: RequestClassification
    decision: ArchitectureDecision
    contract: ExecutionContract
    result: ExecutionResult
    audit: DecisionAudit


def run_control_plane(
    request_text: str,
    context: RequestContext,
    *,
    supplied_otp: str | None = None,
    validated_approval: bool = False,
    classifier_available: bool = True,
    router_available: bool = True,
    model_available: bool = True,
    dependencies_available: bool = True,
    cancelled: bool = False,
) -> ControlPlaneRun:
    if classifier_available:
        proposed = propose_classification(request_text, context)
        classification = validate_classification(request_text, context, proposed)
    else:
        classification = propose_classification("unclassified request", context)
    if router_available:
        decision = decide_architecture(context, classification)
    else:
        fallback_classification = propose_classification("unclassified request", context)
        decision = decide_architecture(context, fallback_classification)
        classification = fallback_classification
    contract = build_execution_contract(context, classification, decision)
    result = ArchitectureRegistry().run(
        contract,
        ExecutionRequest(
            text=request_text,
            supplied_otp=supplied_otp,
            validated_approval=validated_approval,
            model_available=model_available,
            dependencies_available=dependencies_available,
            cancelled=cancelled,
        ),
    )
    fallback = None
    if not classifier_available:
        fallback = "CLASSIFIER_UNAVAILABLE_TO_HUMAN"
    elif not router_available:
        fallback = "ROUTER_UNAVAILABLE_TO_HUMAN"
    elif result.status in {ExecutionStatus.DEGRADED, ExecutionStatus.ESCALATED}:
        fallback = result.failure_code.value if result.failure_code else result.status.value
    audit = record_decision(
        request_text,
        context,
        classification,
        decision,
        occurred_at=FIXED_TIME,
        fallback_or_escalation=fallback,
    )
    return ControlPlaneRun(
        classification=classification,
        decision=decision,
        contract=contract,
        result=result,
        audit=audit,
    )


class ArchitectureProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    architecture: ArchitectureType
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    total_work_ms: int = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)
    complexity: int = Field(ge=0)


ARCHITECTURE_PROFILES = {
    ArchitectureType.DIRECT_FUNCTION: ArchitectureProfile(
        architecture=ArchitectureType.DIRECT_FUNCTION,
        model_calls=0,
        tool_calls=1,
        cost_usd=0,
        total_work_ms=25,
        wall_clock_ms=25,
        complexity=2,
    ),
    ArchitectureType.DETERMINISTIC_WORKFLOW: ArchitectureProfile(
        architecture=ArchitectureType.DETERMINISTIC_WORKFLOW,
        model_calls=0,
        tool_calls=1,
        cost_usd=0,
        total_work_ms=45,
        wall_clock_ms=45,
        complexity=4,
    ),
    ArchitectureType.BOUNDED_SINGLE_AGENT: ArchitectureProfile(
        architecture=ArchitectureType.BOUNDED_SINGLE_AGENT,
        model_calls=1,
        tool_calls=1,
        cost_usd=0.008,
        total_work_ms=110,
        wall_clock_ms=110,
        complexity=5,
    ),
    ArchitectureType.SELECTOR_TEAM: ArchitectureProfile(
        architecture=ArchitectureType.SELECTOR_TEAM,
        model_calls=4,
        tool_calls=3,
        cost_usd=0.044,
        total_work_ms=290,
        wall_clock_ms=150,
        complexity=11,
    ),
}


class BenchmarkRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    architecture: ArchitectureType
    task_success: float = Field(ge=0, le=1)
    grounding: float = Field(ge=0, le=1)
    policy_compliance: float = Field(ge=0, le=1)
    cost_usd: float = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)
    total_work_ms: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    privileged_exposure: int = Field(ge=0)
    recovery: float = Field(ge=0, le=1)
    complexity: int = Field(ge=0)
    cost_per_successful_compliant_request: float | None = Field(default=None, ge=0)


def same_workload_benchmark() -> tuple[BenchmarkRow, ...]:
    """Deterministic fixture comparison, not a live-model quality benchmark."""
    rows = []
    for profile in ARCHITECTURE_PROFILES.values():
        rows.append(
            BenchmarkRow(
                architecture=profile.architecture,
                task_success=1,
                grounding=1,
                policy_compliance=1,
                cost_usd=profile.cost_usd,
                wall_clock_ms=profile.wall_clock_ms,
                total_work_ms=profile.total_work_ms,
                model_calls=profile.model_calls,
                tool_calls=profile.tool_calls,
                privileged_exposure=0,
                recovery=1,
                complexity=profile.complexity,
                cost_per_successful_compliant_request=profile.cost_usd,
            )
        )
    return tuple(rows)


class LabelledRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    text: str
    expected_intent: Intent
    expected_risk: RiskTier
    valid_architectures: frozenset[ArchitectureType]
    best_compliant_architecture: ArchitectureType
    routing_loss_weight: float = Field(gt=0)


def labelled_requests() -> tuple[LabelledRequest, ...]:
    return (
        LabelledRequest(name="status", text=REQUESTS["status"], expected_intent=Intent.CHECKOUT_STATUS, expected_risk=RiskTier.LOW, valid_architectures=frozenset({ArchitectureType.DIRECT_FUNCTION, ArchitectureType.DETERMINISTIC_WORKFLOW, ArchitectureType.BOUNDED_SINGLE_AGENT}), best_compliant_architecture=ArchitectureType.DIRECT_FUNCTION, routing_loss_weight=1),
        LabelledRequest(name="password", text=REQUESTS["password"], expected_intent=Intent.PASSWORD_RESET, expected_risk=RiskTier.HIGH, valid_architectures=frozenset({ArchitectureType.DETERMINISTIC_WORKFLOW}), best_compliant_architecture=ArchitectureType.DETERMINISTIC_WORKFLOW, routing_loss_weight=8),
        LabelledRequest(name="diagnosis", text=REQUESTS["diagnosis"], expected_intent=Intent.INCIDENT_DIAGNOSIS, expected_risk=RiskTier.MEDIUM, valid_architectures=frozenset({ArchitectureType.BOUNDED_SINGLE_AGENT, ArchitectureType.SELECTOR_TEAM}), best_compliant_architecture=ArchitectureType.BOUNDED_SINGLE_AGENT, routing_loss_weight=2),
        LabelledRequest(name="pipeline", text=REQUESTS["pipeline"], expected_intent=Intent.REMEDIATION_REVIEW, expected_risk=RiskTier.MEDIUM, valid_architectures=frozenset({ArchitectureType.PIPELINE}), best_compliant_architecture=ArchitectureType.PIPELINE, routing_loss_weight=3),
        LabelledRequest(name="team", text=REQUESTS["team"], expected_intent=Intent.MULTI_DOMAIN_INCIDENT, expected_risk=RiskTier.MEDIUM, valid_architectures=frozenset({ArchitectureType.SELECTOR_TEAM, ArchitectureType.MANAGER_SPECIALISTS, ArchitectureType.CREW}), best_compliant_architecture=ArchitectureType.SELECTOR_TEAM, routing_loss_weight=3),
        LabelledRequest(name="rollback", text=REQUESTS["rollback"], expected_intent=Intent.PRODUCTION_ROLLBACK, expected_risk=RiskTier.HIGH, valid_architectures=frozenset({ArchitectureType.DETERMINISTIC_WORKFLOW, ArchitectureType.HUMAN_ESCALATION}), best_compliant_architecture=ArchitectureType.DETERMINISTIC_WORKFLOW, routing_loss_weight=10),
        LabelledRequest(name="unknown-destructive", text=REQUESTS["unknown_destructive"], expected_intent=Intent.UNKNOWN, expected_risk=RiskTier.HIGH_RISK_UNKNOWN, valid_architectures=frozenset({ArchitectureType.HUMAN_ESCALATION}), best_compliant_architecture=ArchitectureType.HUMAN_ESCALATION, routing_loss_weight=10),
    )


def architecture_regret(
    selected: ArchitectureType, best: ArchitectureType
) -> dict[str, float]:
    if selected is best:
        return {"extra_cost_usd": 0, "extra_latency_ms": 0, "extra_complexity": 0}
    selected_profile = ARCHITECTURE_PROFILES.get(selected)
    best_profile = ARCHITECTURE_PROFILES.get(best)
    if selected_profile is None or best_profile is None:
        return {"extra_cost_usd": 0, "extra_latency_ms": 0, "extra_complexity": 0}
    return {
        "extra_cost_usd": max(0, selected_profile.cost_usd - best_profile.cost_usd),
        "extra_latency_ms": float(max(0, selected_profile.wall_clock_ms - best_profile.wall_clock_ms)),
        "extra_complexity": float(max(0, selected_profile.complexity - best_profile.complexity)),
    }


class RoutingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    intent_accuracy: float = Field(ge=0, le=1)
    risk_accuracy: float = Field(ge=0, le=1)
    high_risk_false_negative_rate: float = Field(ge=0, le=1)
    architecture_validity_rate: float = Field(ge=0, le=1)
    weighted_routing_loss: float = Field(ge=0)
    mean_extra_cost_usd: float = Field(ge=0)
    mean_extra_latency_ms: float = Field(ge=0)
    mean_extra_complexity: float = Field(ge=0)


def evaluate_routing(
    *,
    forced_architectures: dict[str, ArchitectureType] | None = None,
    forced_risks: dict[str, RiskTier] | None = None,
) -> RoutingMetrics:
    dataset = labelled_requests()
    forced_architectures = forced_architectures or {}
    forced_risks = forced_risks or {}
    intent_correct = risk_correct = valid = 0
    high_risk_total = high_risk_false_negatives = 0
    weighted_loss = total_weight = 0.0
    regrets: list[dict[str, float]] = []
    for index, item in enumerate(dataset):
        context = build_context(f"eval-{index}")
        classification = propose_classification(item.text, context)
        predicted_risk = forced_risks.get(item.name, classification.risk_tier)
        selected = forced_architectures.get(
            item.name, decide_architecture(context, classification).architecture
        )
        intent_correct += int(classification.intent is item.expected_intent)
        risk_correct += int(predicted_risk is item.expected_risk)
        is_high_risk = item.expected_risk in {RiskTier.HIGH, RiskTier.HIGH_RISK_UNKNOWN}
        if is_high_risk:
            high_risk_total += 1
            if predicted_risk not in {RiskTier.HIGH, RiskTier.HIGH_RISK_UNKNOWN}:
                high_risk_false_negatives += 1
        is_valid = selected in item.valid_architectures
        valid += int(is_valid)
        total_weight += item.routing_loss_weight
        if not is_valid:
            weighted_loss += item.routing_loss_weight
        regrets.append(architecture_regret(selected, item.best_compliant_architecture))
    count = len(dataset)
    return RoutingMetrics(
        intent_accuracy=intent_correct / count,
        risk_accuracy=risk_correct / count,
        high_risk_false_negative_rate=high_risk_false_negatives / high_risk_total,
        architecture_validity_rate=valid / count,
        weighted_routing_loss=weighted_loss / total_weight,
        mean_extra_cost_usd=sum(item["extra_cost_usd"] for item in regrets) / count,
        mean_extra_latency_ms=sum(item["extra_latency_ms"] for item in regrets) / count,
        mean_extra_complexity=sum(item["extra_complexity"] for item in regrets) / count,
    )


class RouterCandidateMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    success_rate: float = Field(ge=0, le=1)
    high_risk_violation_rate: float = Field(ge=0, le=1)
    mean_cost_usd: float = Field(ge=0)
    mean_latency_ms: float = Field(ge=0)
    complexity_score: float = Field(ge=0)


def architecture_regression_gate(
    baseline: RouterCandidateMetrics,
    candidate: RouterCandidateMetrics,
) -> str:
    if candidate.high_risk_violation_rate > baseline.high_risk_violation_rate:
        return "REJECT_CANDIDATE"
    if candidate.success_rate < baseline.success_rate:
        return "REJECT_CANDIDATE"
    efficiency_gain = (
        candidate.mean_cost_usd < baseline.mean_cost_usd
        or candidate.mean_latency_ms < baseline.mean_latency_ms
    )
    if candidate.complexity_score > baseline.complexity_score and not efficiency_gain:
        return "REJECT_CANDIDATE"
    return "ACCEPT_CANDIDATE"


def shadow_route(request_text: str, context: RequestContext) -> ArchitectureDecision:
    """Evaluate routing without invoking a worker or side effect."""
    classification = validate_classification(
        request_text, context, propose_classification(request_text, context)
    )
    return decide_architecture(context, classification)


def low_risk_canary_eligible(classification: RequestClassification) -> bool:
    return (
        classification.risk_tier is RiskTier.LOW
        and classification.side_effect_level is SideEffectLevel.NONE
    )


def build_agent_to_team_escalation(
    context: RequestContext,
) -> tuple[ArchitectureTransitionState, ArchitectureDecision]:
    transition = ArchitectureTransitionState(
        request_id=context.request_id,
        current=ArchitectureType.BOUNDED_SINGLE_AGENT,
    )
    escalation = ArchitectureEscalationRequest(
        request_id=context.request_id,
        proposed_architecture=ArchitectureType.SELECTOR_TEAM,
        reason_code=ReasonCode.DYNAMIC_RECOVERY_REQUIRED,
        evidence_gap="customer-impact",
    )
    revised = propose_classification(REQUESTS["team"], context)
    decision = admit_architecture_transition(
        transition,
        escalation,
        context=context,
        revised_classification=revised,
    )
    return transition, decision


def audit_table(runs: tuple[ControlPlaneRun, ...]) -> list[dict[str, object]]:
    return [
        {
            "request_id": run.audit.request_id,
            "intent": run.classification.intent.value,
            "risk": run.classification.risk_tier.value,
            "architecture": run.decision.architecture.value,
            "reason": run.decision.reason_codes[0].value,
            "capabilities": len(run.decision.allowed_capabilities),
            "model_calls": run.result.model_calls,
            "tool_calls": run.result.tool_calls,
            "status": run.result.status.value,
            "fallback": run.audit.fallback_or_escalation,
        }
        for run in runs
    ]
