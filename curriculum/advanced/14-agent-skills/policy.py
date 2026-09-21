"""Typed contracts for the governed Agent Skills course.

Skill packages are procedural inputs. The application owns trust, routing
eligibility, authority, execution, evidence validation, budgets, and lifecycle.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SkillLifecycle(StrEnum):
    DISCOVERED = "DISCOVERED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


class RiskClass(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EffectClass(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    FINANCIAL = "FINANCIAL"
    PRODUCTION_MUTATION = "PRODUCTION_MUTATION"


class ActivationMode(StrEnum):
    FULL = "FULL"
    DEGRADED = "DEGRADED"


class ExecutionMode(StrEnum):
    EPHEMERAL = "EPHEMERAL"
    DURABLE = "DURABLE"
    READ_ONLY = "READ_ONLY"
    APPROVAL_GATED = "APPROVAL_GATED"


class RouteOutcome(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABSTAINED = "ABSTAINED"
    BLOCKED = "BLOCKED"
    UNSATISFIED_REQUIREMENTS = "UNSATISFIED_REQUIREMENTS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    INVALID_OUTPUT = "INVALID_OUTPUT"


class ArtifactKind(StrEnum):
    INSTRUCTIONS = "INSTRUCTIONS"
    SCRIPT = "SCRIPT"
    REFERENCE = "REFERENCE"
    ASSET = "ASSET"


class SkillPolicyError(RuntimeError):
    """Stable fixture error with a machine-readable reason code."""


class PrincipalContext(FrozenModel):
    principal_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    permissions: tuple[str, ...] = ()
    allowed_risk_classes: tuple[RiskClass, ...] = (RiskClass.LOW,)
    allowed_data_classes: tuple[str, ...] = ("INTERNAL",)


class Capability(FrozenModel):
    capability_id: str = Field(min_length=1)
    effect: EffectClass
    healthy: bool = True


class SkillDependency(FrozenModel):
    skill_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    package_digest: str = Field(min_length=64, max_length=64)

    @property
    def ref(self) -> str:
        return f"{self.skill_id}@{self.version}"


class PackageArtifact(FrozenModel):
    artifact_id: str = Field(min_length=1)
    kind: ArtifactKind
    digest: str = Field(min_length=64, max_length=64)


class SandboxPolicy(FrozenModel):
    filesystem_roots: tuple[str, ...] = ()
    network_destinations: tuple[str, ...] = ()
    environment_allowlist: tuple[str, ...] = ()
    allow_subprocess: bool = False
    cpu_ms: int = Field(default=500, gt=0)
    memory_mb: int = Field(default=64, gt=0)
    timeout_ms: int = Field(default=1_000, gt=0)


class SkillManifest(FrozenModel):
    skill_id: str = Field(min_length=3)
    name: str = Field(min_length=1)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    publisher_id: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    package_digest: str = Field(min_length=64, max_length=64)
    description: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    intents: tuple[str, ...] = Field(min_length=1)
    requested_outcomes: tuple[str, ...] = Field(min_length=1)
    routing_terms: tuple[str, ...] = Field(min_length=1)
    required_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    dependencies: tuple[SkillDependency, ...] = ()
    risk_class: RiskClass
    execution_modes: tuple[ExecutionMode, ...] = (ExecutionMode.EPHEMERAL,)
    data_classes: tuple[str, ...] = ("INTERNAL",)
    sandbox_policy: SandboxPolicy
    artifacts: tuple[PackageArtifact, ...] = ()
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def stable_identity(self) -> "SkillManifest":
        expected_prefix = f"{self.publisher_id}/"
        if not self.skill_id.startswith(expected_prefix):
            raise ValueError("SKILL_PUBLISHER_NAMESPACE_MISMATCH")
        if set(self.required_capabilities) & set(self.optional_capabilities):
            raise ValueError("CAPABILITY_CANNOT_BE_REQUIRED_AND_OPTIONAL")
        return self

    @property
    def ref(self) -> str:
        return f"{self.skill_id}@{self.version}"


class SkillRegistryRecord(FrozenModel):
    manifest: SkillManifest
    lifecycle: SkillLifecycle
    approved_digest: str = Field(min_length=64, max_length=64)
    approved_by: str = Field(min_length=1)
    approved_at: datetime
    allowed_tenants: tuple[str, ...] = Field(min_length=1)
    policy_version: str = Field(min_length=1)


class SkillRoutingRequest(FrozenModel):
    request_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    requested_outcome: str = Field(min_length=1)
    data_class: str = Field(min_length=1)
    risk_class: RiskClass
    query: str = Field(min_length=1)
    available_capabilities: tuple[str, ...] = ()
    explicit_user_intent: bool = False


class RoutingCandidate(FrozenModel):
    skill_ref: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    reasons: tuple[str, ...]


class SkillRoutingDecision(FrozenModel):
    request_id: str = Field(min_length=1)
    outcome: RouteOutcome
    selected_skill_ref: str | None = None
    candidates: tuple[RoutingCandidate, ...] = ()
    filtered_reasons: dict[str, str] = Field(default_factory=dict)
    reason_code: str = Field(min_length=1)
    requires_clarification: bool = False
    router_version: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)


class ExecutionBudget(FrozenModel):
    max_skill_activations: int = Field(gt=0)
    max_tool_calls: int = Field(gt=0)
    max_model_calls: int = Field(gt=0)
    max_tokens: int = Field(gt=0)
    max_cost_usd: float = Field(gt=0)
    deadline_ms: int = Field(gt=0)
    max_composition_depth: int = Field(gt=0)
    max_instruction_bytes: int = Field(gt=0)
    max_reference_bytes: int = Field(gt=0)


class BudgetState(FrozenModel):
    skill_activations: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)


class SkillActivation(FrozenModel):
    activation_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    package_digest: str = Field(min_length=64, max_length=64)
    routing_reason: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    effective_capabilities: tuple[str, ...]
    missing_optional_capabilities: tuple[str, ...]
    dependency_refs: tuple[str, ...]
    dependency_activation_ids: tuple[str, ...] = ()
    mode: ActivationMode
    budget: ExecutionBudget
    policy_version: str = Field(min_length=1)
    router_version: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)
    activated_at: datetime


class SkillActivationProposal(FrozenModel):
    parent_activation_id: str = Field(min_length=1)
    child_skill_ref: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class SkillExecutionNode(FrozenModel):
    activation_id: str = Field(min_length=1)
    skill_ref: str = Field(min_length=1)


class SkillExecutionEdge(FrozenModel):
    parent_activation_id: str = Field(min_length=1)
    child_activation_id: str = Field(min_length=1)


class SkillExecutionGraph(FrozenModel):
    request_id: str = Field(min_length=1)
    nodes: tuple[SkillExecutionNode, ...]
    edges: tuple[SkillExecutionEdge, ...]


class IncidentSkillInput(FrozenModel):
    service: str = Field(min_length=1, max_length=64)
    time_window_minutes: int = Field(ge=5, le=240)


class EvidenceRecord(FrozenModel):
    evidence_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    observed_at: datetime
    digest: str = Field(min_length=64, max_length=64)
    supports_claims: tuple[str, ...]
    content: str
    instruction_authority: bool = False


class EvidenceBoundClaim(FrozenModel):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ActionProposal(FrozenModel):
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    arguments: dict[str, Any]
    requires_approval: bool = True
    executed: bool = False


class ModelSkillOutput(FrozenModel):
    claims: tuple[EvidenceBoundClaim, ...] = Field(min_length=1)
    action_proposal: ActionProposal | None = None
    self_reported_confidence: str | None = None


class SkillExecutionResult(FrozenModel):
    activation_id: str = Field(min_length=1)
    status: ExecutionStatus
    claims: tuple[EvidenceBoundClaim, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    action_proposal: ActionProposal | None = None
    reason_code: str = Field(min_length=1)
    verified_postconditions: tuple[str, ...] = ()


class SkillArtifact(FrozenModel):
    artifact_id: str = Field(min_length=1)
    activation_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    skill_version: str = Field(min_length=1)
    skill_digest: str = Field(min_length=64, max_length=64)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    created_at: datetime
    evidence_ids: tuple[str, ...] = ()
    input_artifact_ids: tuple[str, ...] = ()
    content_digest: str = Field(min_length=64, max_length=64)


class ExternalOperationReceipt(FrozenModel):
    logical_operation_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    status: str = Field(min_length=1)


class SkillCheckpoint(FrozenModel):
    checkpoint_id: str = Field(min_length=1)
    activation_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    step: str = Field(min_length=1)
    completed_artifact_ids: tuple[str, ...] = ()
    pending_approval_id: str | None = None
    external_operation_receipts: tuple[ExternalOperationReceipt, ...] = ()
    version: int = Field(ge=1)
    created_at: datetime


class SkillTraceEvent(FrozenModel):
    event_id: str = Field(min_length=1)
    timestamp: datetime
    request_id: str = Field(min_length=1)
    activation_id: str | None = None
    principal_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    skill_ref: str | None = None
    action: str = Field(min_length=1)
    decision: str = Field(pattern="^(ALLOW|DENY|INFO)$")
    reason_code: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    router_version: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)
    cost_usd: float = Field(default=0, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)


class SandboxRequest(FrozenModel):
    script_id: str = Field(min_length=1)
    script_digest: str = Field(min_length=64, max_length=64)
    filesystem_paths: tuple[str, ...] = ()
    network_destinations: tuple[str, ...] = ()
    environment_variables: tuple[str, ...] = ()
    subprocess: bool = False
    timeout_ms: int = Field(gt=0)


class SandboxDecision(FrozenModel):
    allowed: bool
    reason_code: str = Field(min_length=1)
    script_id: str = Field(min_length=1)
    executed_in_host_process: bool = False


class SkillChange(FrozenModel):
    field: str = Field(min_length=1)
    before_digest: str | None = Field(default=None, min_length=64, max_length=64)
    after_digest: str | None = Field(default=None, min_length=64, max_length=64)
    review_reason: str = Field(min_length=1)
    high_risk: bool = False


class RoutingEvaluationCase(FrozenModel):
    case_id: str = Field(min_length=1)
    request: SkillRoutingRequest
    expected_outcome: RouteOutcome
    expected_skill_ref: str | None = None
    forbidden_skill_refs: tuple[str, ...] = ()
    high_risk: bool = False


class RoutingEvaluationReport(FrozenModel):
    total_cases: int = Field(gt=0)
    matched_cases: int = Field(ge=0)
    top1_correct: int = Field(ge=0)
    no_match_cases: int = Field(ge=0)
    no_match_correct: int = Field(ge=0)
    false_activations: int = Field(ge=0)
    high_risk_cases: int = Field(ge=0)
    high_risk_misroutes: int = Field(ge=0)
    top1_accuracy: float = Field(ge=0, le=1)
    no_match_accuracy: float = Field(ge=0, le=1)
    false_activation_rate: float = Field(ge=0, le=1)
    high_risk_misrouting_rate: float = Field(ge=0, le=1)
