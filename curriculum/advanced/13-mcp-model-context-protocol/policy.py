"""Typed contracts for the governed MCP gateway course.

MCP messages and server metadata are observations. The host application owns
identity, trust, authorization, approvals, execution, evidence, and audit.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProtocolEra(StrEnum):
    MODERN = "MODERN"
    LEGACY = "LEGACY"


class CapabilityKind(StrEnum):
    TOOL = "TOOL"
    RESOURCE = "RESOURCE"
    PROMPT = "PROMPT"


class EffectClass(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    FINANCIAL = "FINANCIAL"
    PRODUCTION_MUTATION = "PRODUCTION_MUTATION"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"


class RiskTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TrustTier(StrEnum):
    INTERNAL_APPROVED = "INTERNAL_APPROVED"
    EXTERNAL_APPROVED = "EXTERNAL_APPROVED"
    UNTRUSTED = "UNTRUSTED"


class ServerLifecycle(StrEnum):
    DISCOVERED = "DISCOVERED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


class ServerHealth(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    DISABLED = "DISABLED"


class DataClass(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    DENIED = "DENIED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RECONCILED = "RECONCILED"


class OperationAttemptStatus(StrEnum):
    RESERVED = "RESERVED"
    CANCELLED = "CANCELLED"
    DISPATCHED = "DISPATCHED"
    RESPONSE_INVALID = "RESPONSE_INVALID"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    SUCCEEDED = "SUCCEEDED"
    RECONCILED = "RECONCILED"


class ReconciliationOutcome(StrEnum):
    CONFIRMED_EFFECT = "CONFIRMED_EFFECT"
    CONFIRMED_NO_EFFECT = "CONFIRMED_NO_EFFECT"
    STILL_UNKNOWN = "STILL_UNKNOWN"


class ApprovalClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    IN_FLIGHT = "IN_FLIGHT"
    SUCCEEDED = "SUCCEEDED"
    UNKNOWN = "UNKNOWN"
    CONFIRMED_NO_EFFECT = "CONFIRMED_NO_EFFECT"


class FailureCategory(StrEnum):
    TRANSPORT = "TRANSPORT"
    PROTOCOL = "PROTOCOL"
    SERVER = "SERVER"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    AUTHORIZATION = "AUTHORIZATION"
    VALIDATION = "VALIDATION"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class ChangeType(StrEnum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"


class MCPPolicyError(RuntimeError):
    """Stable policy failure used by the deterministic fixture."""


class PrincipalContext(FrozenModel):
    principal_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    purposes: tuple[str, ...] = ()


class ApproverContext(FrozenModel):
    approver_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    permitted_risk_tiers: tuple[RiskTier, ...] = ()
    max_amount_usd: float | None = Field(default=None, gt=0)
    authenticated_at: datetime
    expires_at: datetime
    revoked: bool = False

    @model_validator(mode="after")
    def valid_authentication_window(self) -> "ApproverContext":
        if self.expires_at <= self.authenticated_at:
            raise ValueError("APPROVER_EXPIRY_INVALID")
        return self


class DelegatedCredential(FrozenModel):
    credential_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    scopes: tuple[str, ...] = ()
    parent_scopes: tuple[str, ...] = ()
    issued_at: datetime
    expires_at: datetime
    revoked: bool = False

    @model_validator(mode="after")
    def valid_delegation(self) -> "DelegatedCredential":
        if self.expires_at <= self.issued_at:
            raise ValueError("CREDENTIAL_EXPIRY_INVALID")
        if not set(self.scopes) <= set(self.parent_scopes):
            raise ValueError("DELEGATION_SCOPE_EXPANSION")
        return self


class ServerIdentity(FrozenModel):
    server_id: str = Field(min_length=1)
    publisher_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    artifact_version: str = Field(min_length=1)
    artifact_digest: str = Field(min_length=64, max_length=64)


class ServerTrustRecord(FrozenModel):
    identity: ServerIdentity
    trust_tier: TrustTier
    lifecycle: ServerLifecycle
    health: ServerHealth
    registry_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    allowed_namespaces: tuple[str, ...] = Field(min_length=1)
    permitted_data_classes: tuple[DataClass, ...] = Field(min_length=1)
    approved_at: datetime | None = None
    approved_by: str | None = None
    allowed_egress: tuple[str, ...] = ()

    @model_validator(mode="after")
    def active_server_is_approved(self) -> "ServerTrustRecord":
        if self.lifecycle is ServerLifecycle.ACTIVE and (not self.approved_at or not self.approved_by):
            raise ValueError("ACTIVE_SERVER_REQUIRES_APPROVAL")
        return self


class ToolDescriptor(FrozenModel):
    capability_id: str = Field(min_length=3)
    server_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    descriptor_version: str = Field(min_length=1)
    descriptor_digest: str = Field(min_length=64, max_length=64)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    effect: EffectClass
    risk: RiskTier
    required_scope: str = Field(min_length=1)
    approval_required: bool = False
    max_result_bytes: int = Field(default=16_384, gt=0)
    estimated_latency_ms: int = Field(default=40, gt=0)
    estimated_cost_usd: float = Field(default=0.002, gt=0)
    estimated_response_bytes: int = Field(default=128, gt=0)

    @model_validator(mode="after")
    def namespaced_identity(self) -> "ToolDescriptor":
        if not self.capability_id.startswith(f"{self.server_id}/"):
            raise ValueError("CAPABILITY_NAMESPACE_MISMATCH")
        return self


class ResourceDescriptor(FrozenModel):
    capability_id: str = Field(min_length=3)
    server_id: str = Field(min_length=1)
    uri_template: str = Field(min_length=1)
    descriptor_version: str = Field(min_length=1)
    descriptor_digest: str = Field(min_length=64, max_length=64)
    mime_types: tuple[str, ...] = Field(min_length=1)
    data_class: DataClass
    trust_class: str = Field(min_length=1)
    required_scope: str = Field(min_length=1)
    max_bytes: int = Field(gt=0)
    freshness_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def namespaced_identity(self) -> "ResourceDescriptor":
        if not self.capability_id.startswith(f"{self.server_id}/"):
            raise ValueError("CAPABILITY_NAMESPACE_MISMATCH")
        return self


class PromptDescriptor(FrozenModel):
    capability_id: str = Field(min_length=3)
    server_id: str = Field(min_length=1)
    publisher_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    descriptor_digest: str = Field(min_length=64, max_length=64)
    argument_schema: dict[str, Any]
    template: str = Field(min_length=1)
    required_scope: str = Field(min_length=1)
    approval_status: str = Field(pattern="^(APPROVED|PENDING|QUARANTINED)$")
    approved_at: datetime | None = None
    trust_level: str = Field(pattern="^(WORKFLOW_CONFIGURATION|UNTRUSTED_DATA)$")

    @model_validator(mode="after")
    def namespaced_identity(self) -> "PromptDescriptor":
        if not self.capability_id.startswith(f"{self.server_id}/"):
            raise ValueError("CAPABILITY_NAMESPACE_MISMATCH")
        if self.approval_status == "APPROVED" and self.approved_at is None:
            raise ValueError("APPROVED_PROMPT_REQUIRES_REVIEW_TIME")
        return self


class CapabilitySnapshot(FrozenModel):
    snapshot_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    server_artifact_digest: str = Field(min_length=64, max_length=64)
    registry_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    credential_id: str = Field(min_length=1)
    credential_expires_at: datetime
    credential_scope_digest: str = Field(min_length=64, max_length=64)
    capability_digests: dict[str, str]
    hidden_reason_codes: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_lifetime(self) -> "CapabilitySnapshot":
        if self.expires_at <= self.created_at:
            raise ValueError("SNAPSHOT_EXPIRY_INVALID")
        return self


class ProtocolConnection(FrozenModel):
    protocol_version: str = Field(min_length=1)
    era: ProtocolEra
    server_id: str = Field(min_length=1)
    advertised_capabilities: tuple[str, ...]


class ToolInvocationProposal(FrozenModel):
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    logical_operation_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    arguments: dict[str, Any]
    target_tenant_id: str = Field(min_length=1)
    target_subject_id: str | None = None
    purpose: str = Field(min_length=1)
    timeout_ms: int = Field(gt=0)
    approval_id: str | None = None


class ApprovalReceipt(FrozenModel):
    approval_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    logical_operation_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    target_subject_id: str | None = None
    purpose: str = Field(min_length=1)
    arguments_digest: str = Field(min_length=64, max_length=64)
    policy_version: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    approver_role: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_lifetime(self) -> "ApprovalReceipt":
        if self.expires_at <= self.issued_at:
            raise ValueError("APPROVAL_EXPIRY_INVALID")
        return self


class RateLimitPolicy(FrozenModel):
    limit: int = Field(gt=0)
    window_seconds: int = Field(gt=0)


class ExecutionBudget(FrozenModel):
    max_tool_calls: int = Field(gt=0)
    max_server_calls: int = Field(gt=0)
    max_response_bytes: int = Field(gt=0)
    deadline_ms: int = Field(gt=0)
    max_cost_usd: float = Field(gt=0)


class BudgetState(FrozenModel):
    tool_calls: int = Field(default=0, ge=0)
    server_calls: int = Field(default=0, ge=0)
    response_bytes: int = Field(default=0, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)
    reserved_tool_calls: int = Field(default=0, ge=0)
    reserved_server_calls: int = Field(default=0, ge=0)
    reserved_response_bytes: int = Field(default=0, ge=0)
    reserved_elapsed_ms: int = Field(default=0, ge=0)
    reserved_cost_usd: float = Field(default=0, ge=0)
    cancelled: bool = False


class GatewayDecision(FrozenModel):
    allowed: bool
    reason_code: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)


class ToolExecutionReceipt(FrozenModel):
    receipt_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    logical_operation_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    descriptor_digest: str = Field(min_length=64, max_length=64)
    arguments_digest: str = Field(min_length=64, max_length=64)
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime
    status: ExecutionStatus
    result_id: str | None = None
    result_digest: str | None = Field(default=None, min_length=64, max_length=64)
    result: dict[str, Any] | None = None
    retryable: bool = False
    failure_category: FailureCategory | None = None
    reconciliation_outcome: ReconciliationOutcome | None = None


class OperationAttempt(FrozenModel):
    attempt_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    logical_operation_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    descriptor_digest: str = Field(min_length=64, max_length=64)
    arguments_digest: str = Field(min_length=64, max_length=64)
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    approval_id: str | None = None
    policy_version: str = Field(min_length=1)
    status: OperationAttemptStatus
    reserved_latency_ms: int = Field(ge=0)
    reserved_cost_usd: float = Field(ge=0)
    created_at: datetime
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None
    failure_category: FailureCategory | None = None


class ApprovalClaim(FrozenModel):
    approval_id: str = Field(min_length=1)
    logical_operation_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    status: ApprovalClaimStatus
    claimed_at: datetime
    updated_at: datetime


class PreparedToolCall(FrozenModel):
    prepared_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    proposal: ToolInvocationProposal
    descriptor: ToolDescriptor
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    credential_id: str = Field(min_length=1)
    reserved_latency_ms: int = Field(ge=0)
    reserved_cost_usd: float = Field(ge=0)
    reserved_response_bytes: int = Field(ge=0)
    prepared_at: datetime


class ResourceRequest(FrozenModel):
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    target_tenant_id: str = Field(min_length=1)
    target_subject_id: str | None = None
    purpose: str = Field(min_length=1)


class ResourceEvidence(FrozenModel):
    evidence_id: str = Field(min_length=1)
    resource_uri: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str | None = None
    source_observed_at: datetime
    retrieved_at: datetime
    mime_type: str = Field(min_length=1)
    digest: str = Field(min_length=64, max_length=64)
    data_class: DataClass
    trust_class: str = Field(min_length=1)
    content: str
    instruction_authority: bool = False


class RenderedPrompt(FrozenModel):
    capability_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    publisher_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    descriptor_digest: str = Field(min_length=64, max_length=64)
    approved_at: datetime
    trust_level: str = Field(pattern="^(WORKFLOW_CONFIGURATION|UNTRUSTED_DATA)$")
    template_text: str
    arguments: dict[str, Any]
    argument_trust_level: str = Field(default="UNTRUSTED_DATA", pattern="^UNTRUSTED_DATA$")
    rendered_text: str
    instruction_authority: bool = False


class AuditEvent(FrozenModel):
    event_id: str = Field(min_length=1)
    timestamp: datetime
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    decision: str = Field(pattern="^(ALLOW|DENY|INFO)$")
    reason_code: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    request_digest: str = Field(min_length=64, max_length=64)
    previous_event_digest: str | None = Field(default=None, min_length=64, max_length=64)
    event_digest: str = Field(min_length=64, max_length=64)


class CapabilityChange(FrozenModel):
    capability_id: str = Field(min_length=1)
    change_type: ChangeType
    old_digest: str | None = Field(default=None, min_length=64, max_length=64)
    new_digest: str | None = Field(default=None, min_length=64, max_length=64)
    disposition: str = Field(pattern="^(PENDING_REVIEW|REMOVED|UNCHANGED)$")


class AdapterReport(FrozenModel):
    sdk_version: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    listed_tools: tuple[str, ...]
    result: dict[str, Any]
    policy_reused: bool
    adapter_calls: int = Field(ge=0)
