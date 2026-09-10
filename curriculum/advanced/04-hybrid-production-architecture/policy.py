"""Application-owned architecture control plane for Advanced Course 04.

Models may propose request classifications and workers may return candidates.
Only this credential-free policy layer can admit an architecture, attenuate its
capabilities, authorize transitions, validate results, and record decisions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


POLICY_VERSION = "northstar-architecture-policy-v1"
CLASSIFIER_VERSION = "northstar-rules-v1"
ROUTER_VERSION = "northstar-router-v1"
OUTPUT_SIZE_LIMIT = 4_000

_DATA_CLASSIFICATION_RANK = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "SENSITIVE": 2,
    "RESTRICTED": 3,
}


class PolicyError(ValueError):
    """A fail-closed policy decision with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MutableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ArchitectureType(StrEnum):
    DIRECT_FUNCTION = "DIRECT_FUNCTION"
    DETERMINISTIC_WORKFLOW = "DETERMINISTIC_WORKFLOW"
    BOUNDED_SINGLE_AGENT = "BOUNDED_SINGLE_AGENT"
    PIPELINE = "PIPELINE"
    MANAGER_SPECIALISTS = "MANAGER_SPECIALISTS"
    SELECTOR_TEAM = "SELECTOR_TEAM"
    CREW = "CREW"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class Capability(StrEnum):
    CHECKOUT_HEALTH_READ = "checkout.health.read"
    LOGS_READ = "logs.read"
    DEPLOYMENT_READ = "deployment.read"
    CUSTOMER_IMPACT_READ = "customer-impact.read"
    RUNBOOK_READ = "runbook.read"
    OTP_SEND = "identity.otp.send"
    PASSWORD_UPDATE = "identity.password.update"
    PROPOSAL_GENERATE = "remediation.proposal.generate"
    SECURITY_REVIEW = "security.review"
    PRODUCTION_ROLLBACK = "production.rollback"
    WEB_ACCESS = "web.access"


class Intent(StrEnum):
    CHECKOUT_STATUS = "CHECKOUT_STATUS"
    PASSWORD_RESET = "PASSWORD_RESET"
    INCIDENT_DIAGNOSIS = "INCIDENT_DIAGNOSIS"
    REMEDIATION_REVIEW = "REMEDIATION_REVIEW"
    MULTI_DOMAIN_INCIDENT = "MULTI_DOMAIN_INCIDENT"
    PRODUCTION_ROLLBACK = "PRODUCTION_ROLLBACK"
    UNKNOWN = "UNKNOWN"


class ClassificationConfidence(StrEnum):
    CONFIDENT = "CONFIDENT"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class RiskTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    HIGH_RISK_UNKNOWN = "HIGH_RISK_UNKNOWN"


class SideEffectLevel(StrEnum):
    NONE = "NONE"
    REVERSIBLE = "REVERSIBLE"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    DESTRUCTIVE = "DESTRUCTIVE"


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class LatencyClass(StrEnum):
    INTERACTIVE = "INTERACTIVE"
    BATCH = "BATCH"


class ExecutionMode(StrEnum):
    SYNC = "SYNC"
    ASYNC = "ASYNC"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class FailureCode(StrEnum):
    AUTH_DENIED = "AUTH_DENIED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    TIMEOUT = "TIMEOUT"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CANCELLED = "CANCELLED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"


class ReasonCode(StrEnum):
    SIMPLE_DETERMINISTIC_LOOKUP = "SIMPLE_DETERMINISTIC_LOOKUP"
    KNOWN_CONTROLLED_PROCESS = "KNOWN_CONTROLLED_PROCESS"
    AMBIGUOUS_DIAGNOSIS = "AMBIGUOUS_DIAGNOSIS"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    MULTI_DOMAIN_PARALLEL_WORK = "MULTI_DOMAIN_PARALLEL_WORK"
    DYNAMIC_RECOVERY_REQUIRED = "DYNAMIC_RECOVERY_REQUIRED"
    HIGH_RISK_ACTION = "HIGH_RISK_ACTION"
    UNKNOWN_REQUEST = "UNKNOWN_REQUEST"


class PIIAction(StrEnum):
    ALLOW = "ALLOW"
    MASK = "MASK"
    REDACT = "REDACT"
    BLOCK = "BLOCK"


class PasswordResetStatus(StrEnum):
    REQUESTED = "REQUESTED"
    OTP_SENT = "OTP_SENT"
    WAITING_FOR_OTP = "WAITING_FOR_OTP"
    VERIFIED = "VERIFIED"
    PASSWORD_UPDATE_AUTHORIZED = "PASSWORD_UPDATE_AUTHORIZED"
    COMPLETED = "COMPLETED"
    INVALID_OTP = "INVALID_OTP"
    EXPIRED_OTP = "EXPIRED_OTP"
    MAX_ATTEMPTS = "MAX_ATTEMPTS"
    CANCELLED = "CANCELLED"


class RequestContext(FrozenModel):
    request_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    roles: tuple[str, ...]
    allowed_capabilities: tuple[Capability, ...]
    data_classification: DataClassification
    policy_version: str = Field(min_length=1)
    deadline_ms: int = Field(gt=0)

    @field_validator("roles", "allowed_capabilities")
    @classmethod
    def unique_values(cls, value: tuple[Any, ...]) -> tuple[Any, ...]:
        if len(value) != len(set(value)):
            raise ValueError("values must be unique")
        return value


class RequestClassification(FrozenModel):
    intent: Intent
    ambiguity: ClassificationConfidence
    risk_tier: RiskTier
    side_effect_level: SideEffectLevel
    requires_current_evidence: bool
    requires_multi_domain_evidence: bool
    requires_human_approval: bool
    data_sensitivity: DataClassification
    latency_class: LatencyClass
    classifier_version: str


class ExecutionBudget(FrozenModel):
    max_model_calls: int = Field(ge=0)
    max_tool_calls: int = Field(ge=0)
    max_cost_usd: float = Field(ge=0)
    deadline_ms: int = Field(gt=0)
    max_replans: int = Field(default=0, ge=0)
    max_architecture_transitions: int = Field(default=1, ge=0)
    max_depth: int = Field(default=1, ge=0)


class ArchitectureDecision(FrozenModel):
    architecture: ArchitectureType
    reason_codes: tuple[ReasonCode, ...]
    allowed_capabilities: tuple[Capability, ...]
    budget: ExecutionBudget
    approval_required: bool
    execution_mode: ExecutionMode
    policy_version: str
    classifier_version: str
    router_version: str


class ExecutionContract(FrozenModel):
    request_id: str
    tenant_id: str
    user_id: str
    roles: tuple[str, ...]
    architecture: ArchitectureType
    allowed_capabilities: tuple[Capability, ...]
    required_evidence: tuple[str, ...]
    max_model_calls: int = Field(ge=0)
    max_tool_calls: int = Field(ge=0)
    max_cost_usd: float = Field(ge=0)
    deadline_ms: int = Field(gt=0)
    approval_required: bool
    policy_version: str
    classifier_version: str
    router_version: str
    execution_mode: ExecutionMode
    max_replans: int = Field(ge=0)


class ApprovalReceipt(FrozenModel):
    """Application-issued approval bound to one exact consequential proposal."""

    approval_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    action: Capability
    target: str = Field(min_length=1)
    proposal_digest: str = Field(min_length=64, max_length=64)
    approver_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime


class EvidenceReceipt(FrozenModel):
    """Application-owned proof that evidence was accepted during this run."""

    evidence_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    digest: str = Field(min_length=64, max_length=64)


class AcceptedEvidenceRegistry(MutableModel):
    request_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    receipts: dict[str, EvidenceReceipt] = Field(default_factory=dict)

    def register(self, receipt: EvidenceReceipt) -> None:
        if receipt.request_id != self.request_id:
            raise PolicyError("EVIDENCE_REQUEST_MISMATCH")
        if receipt.tenant_id != self.tenant_id:
            raise PolicyError("EVIDENCE_TENANT_MISMATCH")
        existing = self.receipts.get(receipt.evidence_id)
        if existing is not None and existing != receipt:
            raise PolicyError("EVIDENCE_RECEIPT_CONFLICT")
        self.receipts[receipt.evidence_id] = receipt


class ExecutionResult(FrozenModel):
    request_id: str
    tenant_id: str
    architecture: ArchitectureType
    status: ExecutionStatus
    output: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    total_work_ms: int = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)
    policy_events: tuple[str, ...]
    approval_required: bool
    failure_code: FailureCode | None = None
    privileged_capability_exposure: int = Field(default=0, ge=0)


class ExecutionRequest(FrozenModel):
    text: str = Field(min_length=1)
    supplied_otp: str | None = None
    subject_user_id: str | None = None
    approval_receipt: ApprovalReceipt | None = None
    model_available: bool = True
    dependencies_available: bool = True
    cancelled: bool = False


class DecisionAudit(FrozenModel):
    request_id: str
    tenant_id: str
    request_reference: str
    request_digest: str = Field(min_length=64, max_length=64)
    retention_class: str
    classification: RequestClassification
    decision: ArchitectureDecision
    occurred_at: datetime
    fallback_or_escalation: str | None = None


class ArchitectureTransitionState(MutableModel):
    request_id: str
    original_request_text: str
    original_classification: RequestClassification
    accepted_evidence_ids: tuple[str, ...] = ()
    current: ArchitectureType
    transitions: int = 0
    depth: int = 0
    history: tuple[ArchitectureType, ...] = ()
    cancelled: bool = False


class ArchitectureEscalationRequest(FrozenModel):
    request_id: str
    proposed_architecture: ArchitectureType
    reason_code: ReasonCode
    evidence_gap: str


class PasswordResetState(MutableModel):
    request_id: str
    tenant_id: str
    user_id: str
    logical_operation_id: str
    attempt_ids: tuple[str, ...] = ()
    status: PasswordResetStatus = PasswordResetStatus.REQUESTED
    otp_digest: str
    otp_expires_at: datetime
    attempt_count: int = 0
    max_attempts: int = Field(default=3, ge=1)
    verified_identity: bool = False
    update_authorized: bool = False
    completed_operation_ids: tuple[str, ...] = ()
    password_update_count: int = 0


_ARCHITECTURE_BUDGETS: Mapping[ArchitectureType, ExecutionBudget] = {
    ArchitectureType.DIRECT_FUNCTION: ExecutionBudget(
        max_model_calls=0, max_tool_calls=1, max_cost_usd=0, deadline_ms=150
    ),
    ArchitectureType.DETERMINISTIC_WORKFLOW: ExecutionBudget(
        max_model_calls=0,
        max_tool_calls=4,
        max_cost_usd=0,
        deadline_ms=500,
        max_architecture_transitions=1,
        max_depth=1,
    ),
    ArchitectureType.BOUNDED_SINGLE_AGENT: ExecutionBudget(
        max_model_calls=3,
        max_tool_calls=4,
        max_cost_usd=0.03,
        deadline_ms=900,
        max_replans=1,
        max_architecture_transitions=1,
        max_depth=1,
    ),
    ArchitectureType.PIPELINE: ExecutionBudget(
        max_model_calls=2,
        max_tool_calls=1,
        max_cost_usd=0.04,
        deadline_ms=1_200,
        max_architecture_transitions=1,
        max_depth=1,
    ),
    ArchitectureType.MANAGER_SPECIALISTS: ExecutionBudget(
        max_model_calls=5,
        max_tool_calls=3,
        max_cost_usd=0.08,
        deadline_ms=1_500,
        max_replans=1,
        max_architecture_transitions=1,
        max_depth=2,
    ),
    ArchitectureType.SELECTOR_TEAM: ExecutionBudget(
        max_model_calls=4,
        max_tool_calls=3,
        max_cost_usd=0.06,
        deadline_ms=1_200,
        max_architecture_transitions=1,
        max_depth=2,
    ),
    ArchitectureType.CREW: ExecutionBudget(
        max_model_calls=4,
        max_tool_calls=3,
        max_cost_usd=0.06,
        deadline_ms=1_200,
        max_architecture_transitions=1,
        max_depth=2,
    ),
    ArchitectureType.HUMAN_ESCALATION: ExecutionBudget(
        max_model_calls=0,
        max_tool_calls=0,
        max_cost_usd=0,
        deadline_ms=100,
        max_architecture_transitions=0,
        max_depth=0,
    ),
}


_REQUIRED_CAPABILITIES: Mapping[Intent, tuple[Capability, ...]] = {
    Intent.CHECKOUT_STATUS: (Capability.CHECKOUT_HEALTH_READ,),
    Intent.PASSWORD_RESET: (Capability.OTP_SEND, Capability.PASSWORD_UPDATE),
    Intent.INCIDENT_DIAGNOSIS: (
        Capability.CHECKOUT_HEALTH_READ,
        Capability.LOGS_READ,
        Capability.DEPLOYMENT_READ,
        Capability.RUNBOOK_READ,
    ),
    Intent.REMEDIATION_REVIEW: (
        Capability.PROPOSAL_GENERATE,
        Capability.SECURITY_REVIEW,
    ),
    Intent.MULTI_DOMAIN_INCIDENT: (
        Capability.CHECKOUT_HEALTH_READ,
        Capability.DEPLOYMENT_READ,
        Capability.CUSTOMER_IMPACT_READ,
    ),
    Intent.PRODUCTION_ROLLBACK: (Capability.PRODUCTION_ROLLBACK,),
    Intent.UNKNOWN: (),
}


_REQUIRED_EVIDENCE: Mapping[Intent, tuple[str, ...]] = {
    Intent.CHECKOUT_STATUS: ("checkout-health",),
    Intent.PASSWORD_RESET: ("identity-verification",),
    Intent.INCIDENT_DIAGNOSIS: (
        "checkout-health",
        "checkout-logs",
        "deploy-1842",
        "rollback-runbook",
    ),
    Intent.REMEDIATION_REVIEW: ("remediation-proposal", "security-review"),
    Intent.MULTI_DOMAIN_INCIDENT: (
        "checkout-health",
        "deploy-1842",
        "customer-impact",
    ),
    Intent.PRODUCTION_ROLLBACK: ("review-pass", "validated-approval"),
    Intent.UNKNOWN: (),
}


def _classification(
    intent: Intent,
    *,
    ambiguity: ClassificationConfidence,
    risk: RiskTier,
    side_effect: SideEffectLevel,
    current_evidence: bool,
    multi_domain: bool,
    human_approval: bool,
    sensitivity: DataClassification,
    latency: LatencyClass,
) -> RequestClassification:
    return RequestClassification(
        intent=intent,
        ambiguity=ambiguity,
        risk_tier=risk,
        side_effect_level=side_effect,
        requires_current_evidence=current_evidence,
        requires_multi_domain_evidence=multi_domain,
        requires_human_approval=human_approval,
        data_sensitivity=sensitivity,
        latency_class=latency,
        classifier_version=CLASSIFIER_VERSION,
    )


def propose_classification(
    request_text: str, context: RequestContext
) -> RequestClassification:
    """Return a deterministic offline proposal; production may swap the proposer."""
    text = request_text.casefold()
    sensitivity = context.data_classification
    if "rollback" in text and "deploy-1842" in text:
        return _classification(
            Intent.PRODUCTION_ROLLBACK,
            ambiguity=ClassificationConfidence.CONFIDENT,
            risk=RiskTier.HIGH,
            side_effect=SideEffectLevel.CONSEQUENTIAL,
            current_evidence=True,
            multi_domain=False,
            human_approval=True,
            sensitivity=sensitivity,
            latency=LatencyClass.INTERACTIVE,
        )
    if "reset" in text and "password" in text:
        password_sensitivity = (
            DataClassification.RESTRICTED
            if sensitivity is DataClassification.RESTRICTED
            else DataClassification.SENSITIVE
        )
        return _classification(
            Intent.PASSWORD_RESET,
            ambiguity=ClassificationConfidence.CONFIDENT,
            risk=RiskTier.HIGH,
            side_effect=SideEffectLevel.CONSEQUENTIAL,
            current_evidence=False,
            multi_domain=False,
            human_approval=False,
            sensitivity=password_sensitivity,
            latency=LatencyClass.INTERACTIVE,
        )
    if "remediation proposal" in text and "security-review" in text:
        return _classification(
            Intent.REMEDIATION_REVIEW,
            ambiguity=ClassificationConfidence.CONFIDENT,
            risk=RiskTier.MEDIUM,
            side_effect=SideEffectLevel.NONE,
            current_evidence=True,
            multi_domain=False,
            human_approval=False,
            sensitivity=sensitivity,
            latency=LatencyClass.BATCH,
        )
    if "across observability" in text and "customer impact" in text:
        return _classification(
            Intent.MULTI_DOMAIN_INCIDENT,
            ambiguity=ClassificationConfidence.AMBIGUOUS,
            risk=RiskTier.MEDIUM,
            side_effect=SideEffectLevel.NONE,
            current_evidence=True,
            multi_domain=True,
            human_approval=False,
            sensitivity=sensitivity,
            latency=LatencyClass.BATCH,
        )
    if "why did eu checkout conversion fall" in text:
        return _classification(
            Intent.INCIDENT_DIAGNOSIS,
            ambiguity=ClassificationConfidence.AMBIGUOUS,
            risk=RiskTier.MEDIUM,
            side_effect=SideEffectLevel.NONE,
            current_evidence=True,
            multi_domain=False,
            human_approval=False,
            sensitivity=sensitivity,
            latency=LatencyClass.INTERACTIVE,
        )
    if "checkout healthy" in text:
        return _classification(
            Intent.CHECKOUT_STATUS,
            ambiguity=ClassificationConfidence.CONFIDENT,
            risk=RiskTier.LOW,
            side_effect=SideEffectLevel.NONE,
            current_evidence=True,
            multi_domain=False,
            human_approval=False,
            sensitivity=sensitivity,
            latency=LatencyClass.INTERACTIVE,
        )
    destructive = any(
        token in text
        for token in ("delete", "destroy", "drop database", "transfer money", "rollback")
    )
    return _classification(
        Intent.UNKNOWN,
        ambiguity=ClassificationConfidence.UNKNOWN,
        risk=RiskTier.HIGH_RISK_UNKNOWN,
        side_effect=(SideEffectLevel.DESTRUCTIVE if destructive else SideEffectLevel.NONE),
        current_evidence=False,
        multi_domain=False,
        human_approval=destructive,
        sensitivity=sensitivity,
        latency=LatencyClass.INTERACTIVE,
    )


def validate_classification(
    request_text: str,
    context: RequestContext,
    proposal: RequestClassification,
) -> RequestClassification:
    """Validate a classifier proposal against trusted context and hard overrides."""
    if context.policy_version != POLICY_VERSION:
        raise PolicyError("POLICY_VERSION_MISMATCH")
    if proposal.classifier_version != CLASSIFIER_VERSION:
        raise PolicyError("CLASSIFIER_VERSION_MISMATCH")
    if _DATA_CLASSIFICATION_RANK[proposal.data_sensitivity.value] < (
        _DATA_CLASSIFICATION_RANK[context.data_classification.value]
    ):
        raise PolicyError("CLASSIFIER_DATA_DOWNGRADE")

    authoritative = propose_classification(request_text, context)
    high_risk_intents = {Intent.PASSWORD_RESET, Intent.PRODUCTION_ROLLBACK}
    if authoritative.intent in high_risk_intents:
        return authoritative
    if authoritative.intent is Intent.UNKNOWN:
        return authoritative
    if proposal.intent != authoritative.intent:
        raise PolicyError("CLASSIFIER_INTENT_CONFLICT")
    if proposal.risk_tier is RiskTier.LOW and authoritative.risk_tier is not RiskTier.LOW:
        raise PolicyError("CLASSIFIER_RISK_DOWNGRADE")
    return proposal


def _attenuate(
    requested: tuple[Capability, ...], context: RequestContext
) -> tuple[Capability, ...]:
    grants = set(context.allowed_capabilities)
    return tuple(capability for capability in requested if capability in grants)


def minimum_required_capabilities(
    intent: Intent, architecture: ArchitectureType
) -> tuple[Capability, ...]:
    """Return the least authority with which this fixture route can succeed."""
    if architecture is ArchitectureType.HUMAN_ESCALATION:
        return ()
    return _REQUIRED_CAPABILITIES[intent]


def decide_architecture(
    context: RequestContext,
    classification: RequestClassification,
) -> ArchitectureDecision:
    """Select the least-complex permissible architecture for a validated class."""
    if context.policy_version != POLICY_VERSION:
        raise PolicyError("POLICY_VERSION_MISMATCH")

    route: tuple[ArchitectureType, ReasonCode, ExecutionMode]
    if classification.intent is Intent.CHECKOUT_STATUS:
        route = (
            ArchitectureType.DIRECT_FUNCTION,
            ReasonCode.SIMPLE_DETERMINISTIC_LOOKUP,
            ExecutionMode.SYNC,
        )
    elif classification.intent is Intent.PASSWORD_RESET:
        route = (
            ArchitectureType.DETERMINISTIC_WORKFLOW,
            ReasonCode.KNOWN_CONTROLLED_PROCESS,
            ExecutionMode.SYNC,
        )
    elif classification.intent is Intent.INCIDENT_DIAGNOSIS:
        route = (
            ArchitectureType.BOUNDED_SINGLE_AGENT,
            ReasonCode.AMBIGUOUS_DIAGNOSIS,
            ExecutionMode.SYNC,
        )
    elif classification.intent is Intent.REMEDIATION_REVIEW:
        route = (
            ArchitectureType.PIPELINE,
            ReasonCode.INDEPENDENT_REVIEW,
            ExecutionMode.ASYNC,
        )
    elif classification.intent is Intent.MULTI_DOMAIN_INCIDENT:
        route = (
            ArchitectureType.SELECTOR_TEAM,
            ReasonCode.MULTI_DOMAIN_PARALLEL_WORK,
            ExecutionMode.ASYNC,
        )
    elif classification.intent is Intent.PRODUCTION_ROLLBACK:
        route = (
            ArchitectureType.DETERMINISTIC_WORKFLOW,
            ReasonCode.HIGH_RISK_ACTION,
            ExecutionMode.SYNC,
        )
    else:
        route = (
            ArchitectureType.HUMAN_ESCALATION,
            ReasonCode.UNKNOWN_REQUEST,
            ExecutionMode.SYNC,
        )

    architecture, reason, mode = route
    if (
        context.data_classification is DataClassification.RESTRICTED
        and architecture
        in {
            ArchitectureType.MANAGER_SPECIALISTS,
            ArchitectureType.SELECTOR_TEAM,
            ArchitectureType.CREW,
        }
    ):
        architecture = ArchitectureType.HUMAN_ESCALATION
        reason = ReasonCode.HIGH_RISK_ACTION
        mode = ExecutionMode.SYNC

    requested = _REQUIRED_CAPABILITIES[classification.intent]
    allowed = _attenuate(requested, context)
    if architecture is ArchitectureType.HUMAN_ESCALATION:
        allowed = ()
    required = minimum_required_capabilities(classification.intent, architecture)
    if not set(required).issubset(set(allowed)):
        raise PolicyError("AUTH_DENIED")
    budget = _ARCHITECTURE_BUDGETS[architecture].model_copy(
        update={"deadline_ms": min(_ARCHITECTURE_BUDGETS[architecture].deadline_ms, context.deadline_ms)}
    )
    return ArchitectureDecision(
        architecture=architecture,
        reason_codes=(reason,),
        allowed_capabilities=allowed,
        budget=budget,
        approval_required=classification.requires_human_approval,
        execution_mode=mode,
        policy_version=POLICY_VERSION,
        classifier_version=classification.classifier_version,
        router_version=ROUTER_VERSION,
    )


def build_execution_contract(
    context: RequestContext,
    classification: RequestClassification,
    decision: ArchitectureDecision,
) -> ExecutionContract:
    if decision.policy_version != context.policy_version:
        raise PolicyError("DECISION_POLICY_VERSION_MISMATCH")
    if decision.classifier_version != classification.classifier_version:
        raise PolicyError("DECISION_CLASSIFIER_VERSION_MISMATCH")
    if not set(decision.allowed_capabilities).issubset(
        set(context.allowed_capabilities)
    ):
        raise PolicyError("ARCHITECTURE_CAPABILITY_WIDENING")
    return ExecutionContract(
        request_id=context.request_id,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        roles=context.roles,
        architecture=decision.architecture,
        allowed_capabilities=decision.allowed_capabilities,
        required_evidence=_REQUIRED_EVIDENCE[classification.intent],
        max_model_calls=decision.budget.max_model_calls,
        max_tool_calls=decision.budget.max_tool_calls,
        max_cost_usd=decision.budget.max_cost_usd,
        deadline_ms=decision.budget.deadline_ms,
        approval_required=decision.approval_required,
        policy_version=decision.policy_version,
        classifier_version=decision.classifier_version,
        router_version=decision.router_version,
        execution_mode=decision.execution_mode,
        max_replans=decision.budget.max_replans,
    )


def require_capabilities(
    contract: ExecutionContract, required: tuple[Capability, ...]
) -> None:
    if not set(required).issubset(set(contract.allowed_capabilities)):
        raise PolicyError("AUTH_DENIED")


def proposal_digest(
    *, request_id: str, tenant_id: str, action: Capability, target: str
) -> str:
    normalized = json.dumps(
        {
            "action": action.value,
            "request_id": request_id,
            "target": target,
            "tenant_id": tenant_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode()).hexdigest()


def evidence_digest(payload: Mapping[str, Any]) -> str:
    normalized = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode()).hexdigest()


def validate_approval_receipt(
    receipt: ApprovalReceipt,
    contract: ExecutionContract,
    *,
    action: Capability,
    target: str,
    now: datetime,
    authorized_approvers: frozenset[str],
) -> None:
    """Validate the exact approval immediately before consequential execution."""
    if receipt.request_id != contract.request_id:
        raise PolicyError("APPROVAL_REQUEST_MISMATCH")
    if receipt.tenant_id != contract.tenant_id:
        raise PolicyError("APPROVAL_TENANT_MISMATCH")
    if receipt.action is not action:
        raise PolicyError("APPROVAL_ACTION_MISMATCH")
    if receipt.target != target:
        raise PolicyError("APPROVAL_TARGET_MISMATCH")
    expected_digest = proposal_digest(
        request_id=contract.request_id,
        tenant_id=contract.tenant_id,
        action=action,
        target=target,
    )
    if receipt.proposal_digest != expected_digest:
        raise PolicyError("APPROVAL_PROPOSAL_MISMATCH")
    if receipt.policy_version != contract.policy_version:
        raise PolicyError("APPROVAL_POLICY_STALE")
    if receipt.issued_at > now or receipt.expires_at <= now:
        raise PolicyError("APPROVAL_EXPIRED")
    if receipt.expires_at <= receipt.issued_at:
        raise PolicyError("APPROVAL_WINDOW_INVALID")
    if receipt.approver_id not in authorized_approvers:
        raise PolicyError("APPROVER_NOT_AUTHORIZED")


def validate_execution_result(
    result: ExecutionResult,
    contract: ExecutionContract,
    *,
    accepted_evidence: AcceptedEvidenceRegistry,
    pii_action: PIIAction = PIIAction.BLOCK,
    max_output_chars: int = OUTPUT_SIZE_LIMIT,
) -> ExecutionResult:
    """Apply the common post-run schema, scope, budget, evidence, and DLP gate."""
    if result.request_id != contract.request_id:
        raise PolicyError("RESULT_REQUEST_MISMATCH")
    if result.tenant_id != contract.tenant_id:
        raise PolicyError("RESULT_TENANT_MISMATCH")
    if result.architecture is not contract.architecture:
        raise PolicyError("RESULT_ARCHITECTURE_MISMATCH")
    if result.model_calls > contract.max_model_calls:
        raise PolicyError("MODEL_CALL_BUDGET_EXCEEDED")
    if result.tool_calls > contract.max_tool_calls:
        raise PolicyError("TOOL_CALL_BUDGET_EXCEEDED")
    if result.cost_usd > contract.max_cost_usd:
        raise PolicyError("COST_BUDGET_EXCEEDED")
    if result.wall_clock_ms > contract.deadline_ms:
        raise PolicyError("DEADLINE_EXCEEDED")
    if result.status is ExecutionStatus.SUCCEEDED:
        if not set(contract.required_evidence).issubset(set(result.evidence_ids)):
            raise PolicyError("INSUFFICIENT_EVIDENCE")
        for evidence_id in result.evidence_ids:
            receipt = accepted_evidence.receipts.get(evidence_id)
            if receipt is None:
                raise PolicyError("INVALID_EVIDENCE")
            if receipt.request_id != contract.request_id:
                raise PolicyError("EVIDENCE_REQUEST_MISMATCH")
            if receipt.tenant_id != contract.tenant_id:
                raise PolicyError("EVIDENCE_TENANT_MISMATCH")
            if not receipt.source_id or not receipt.source_version or len(receipt.digest) != 64:
                raise PolicyError("EVIDENCE_PROVENANCE_INVALID")

    encoded = json.dumps(dict(result.output), sort_keys=True, default=str)
    if len(encoded) > max_output_chars:
        raise PolicyError("OUTPUT_SIZE_LIMIT")
    transformed = apply_structured_pii_policy(dict(result.output), pii_action)
    if transformed != dict(result.output):
        return result.model_copy(update={"output": transformed})
    return result


_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def apply_pii_policy(text: str, action: PIIAction) -> str:
    """Illustrative PII layer; production DLP needs structured detectors too."""
    has_pii = bool(_EMAIL.search(text) or _CARD.search(text))
    if not has_pii or action is PIIAction.ALLOW:
        return text
    if action is PIIAction.BLOCK:
        raise PolicyError("PII_BLOCKED")
    replacement = "[MASKED]" if action is PIIAction.MASK else "[REDACTED]"
    return _CARD.sub(replacement, _EMAIL.sub(replacement, text))


def apply_structured_pii_policy(value: Any, action: PIIAction) -> Any:
    """Recursively protect string values without collapsing output structure."""
    if isinstance(value, Mapping):
        return {key: apply_structured_pii_policy(item, action) for key, item in value.items()}
    if isinstance(value, list):
        return [apply_structured_pii_policy(item, action) for item in value]
    if isinstance(value, tuple):
        return tuple(apply_structured_pii_policy(item, action) for item in value)
    if isinstance(value, str):
        return apply_pii_policy(value, action)
    return value


_ALLOWED_TRANSITIONS: Mapping[ArchitectureType, set[ArchitectureType]] = {
    ArchitectureType.DIRECT_FUNCTION: set(),
    ArchitectureType.DETERMINISTIC_WORKFLOW: {ArchitectureType.HUMAN_ESCALATION},
    ArchitectureType.BOUNDED_SINGLE_AGENT: {
        ArchitectureType.SELECTOR_TEAM,
        ArchitectureType.HUMAN_ESCALATION,
    },
    ArchitectureType.PIPELINE: {ArchitectureType.HUMAN_ESCALATION},
    ArchitectureType.MANAGER_SPECIALISTS: {ArchitectureType.HUMAN_ESCALATION},
    ArchitectureType.SELECTOR_TEAM: {ArchitectureType.HUMAN_ESCALATION},
    ArchitectureType.CREW: {ArchitectureType.HUMAN_ESCALATION},
    ArchitectureType.HUMAN_ESCALATION: set(),
}

_TRANSITION_REMEDIES: Mapping[
    tuple[ArchitectureType, Intent, str], tuple[ArchitectureType, Intent]
] = {
    (
        ArchitectureType.BOUNDED_SINGLE_AGENT,
        Intent.INCIDENT_DIAGNOSIS,
        "customer-impact",
    ): (ArchitectureType.SELECTOR_TEAM, Intent.MULTI_DOMAIN_INCIDENT),
}


def admit_architecture_transition(
    transition: ArchitectureTransitionState,
    escalation: ArchitectureEscalationRequest,
    *,
    context: RequestContext,
) -> ArchitectureDecision:
    """Re-run admission before allowing a worker-proposed architecture change."""
    if transition.cancelled:
        raise PolicyError("CANCELLED")
    if escalation.request_id != context.request_id or transition.request_id != context.request_id:
        raise PolicyError("TRANSITION_REQUEST_MISMATCH")
    current_budget = _ARCHITECTURE_BUDGETS[transition.current]
    if transition.transitions >= current_budget.max_architecture_transitions:
        raise PolicyError("ARCHITECTURE_TRANSITION_BUDGET_EXCEEDED")
    if transition.depth >= current_budget.max_depth:
        raise PolicyError("ARCHITECTURE_DEPTH_EXCEEDED")
    if escalation.proposed_architecture not in _ALLOWED_TRANSITIONS[transition.current]:
        raise PolicyError("ARCHITECTURE_TRANSITION_DENIED")
    validated_original = validate_classification(
        transition.original_request_text,
        context,
        transition.original_classification,
    )
    if escalation.evidence_gap in transition.accepted_evidence_ids:
        raise PolicyError("EVIDENCE_GAP_ALREADY_RESOLVED")
    remedy = _TRANSITION_REMEDIES.get(
        (transition.current, validated_original.intent, escalation.evidence_gap)
    )
    if remedy is None:
        raise PolicyError("EVIDENCE_GAP_NOT_ADDRESSABLE")
    expected_architecture, revised_intent = remedy
    if escalation.reason_code is not ReasonCode.DYNAMIC_RECOVERY_REQUIRED:
        raise PolicyError("TRANSITION_REASON_MISMATCH")
    if escalation.proposed_architecture is not expected_architecture:
        raise PolicyError("EVIDENCE_GAP_ARCHITECTURE_MISMATCH")
    revised_classification = validated_original.model_copy(
        update={
            "intent": revised_intent,
            "requires_multi_domain_evidence": True,
            "ambiguity": ClassificationConfidence.AMBIGUOUS,
        }
    )
    decision = decide_architecture(context, revised_classification)
    if decision.architecture is not escalation.proposed_architecture:
        raise PolicyError("ARCHITECTURE_READMISSION_MISMATCH")
    transition.history = (*transition.history, transition.current)
    transition.current = decision.architecture
    transition.transitions += 1
    transition.depth += 1
    return decision


def record_decision(
    request_text: str,
    context: RequestContext,
    classification: RequestClassification,
    decision: ArchitectureDecision,
    *,
    occurred_at: datetime,
    fallback_or_escalation: str | None = None,
) -> DecisionAudit:
    return DecisionAudit(
        request_id=context.request_id,
        tenant_id=context.tenant_id,
        request_reference=f"request:{context.request_id}",
        request_digest=hashlib.sha256(request_text.encode()).hexdigest(),
        retention_class=(
            "REFERENCE_AND_DIGEST_ONLY"
            if context.data_classification
            in {DataClassification.SENSITIVE, DataClassification.RESTRICTED}
            else "MINIMUM_AUDIT_30_DAYS"
        ),
        classification=classification,
        decision=decision,
        occurred_at=occurred_at,
        fallback_or_escalation=fallback_or_escalation,
    )
