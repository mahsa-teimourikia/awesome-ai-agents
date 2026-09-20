"""Typed contracts for governed, reproducible enterprise agent benchmarks.

Agent output and traces are observations, not authority. The application-owned
evaluation harness owns dataset governance, environment state, deterministic
hard gates, metric denominators, comparison, and release decisions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BenchmarkPolicyError(ValueError):
    """Fail-closed benchmark error whose message is a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BenchmarkType(StrEnum):
    CAPABILITY = "CAPABILITY"
    SYSTEM = "SYSTEM"
    SAFETY = "SAFETY"
    REGRESSION = "REGRESSION"
    LOAD_PERFORMANCE = "LOAD_PERFORMANCE"
    PRODUCTION_SHADOW = "PRODUCTION_SHADOW"


class ContaminationExposure(StrEnum):
    PUBLIC_SOURCE = "PUBLIC_SOURCE"
    CONTROLLED_ENVIRONMENT = "CONTROLLED_ENVIRONMENT"
    PRIVATE_HELD_OUT = "PRIVATE_HELD_OUT"


class CaseProvenance(StrEnum):
    PRODUCTION_DERIVED = "PRODUCTION_DERIVED"
    EXPERT_AUTHORED = "EXPERT_AUTHORED"
    SYNTHETIC_VALIDATED = "SYNTHETIC_VALIDATED"
    REGRESSION = "REGRESSION"
    ADVERSARIAL = "ADVERSARIAL"


class CaseStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    REVIEWED = "REVIEWED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class DatasetSplit(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    CHALLENGE = "CHALLENGE"


class EventType(StrEnum):
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    PROPOSAL = "PROPOSAL"
    APPROVAL = "APPROVAL"
    EXECUTION_RECEIPT = "EXECUTION_RECEIPT"
    STATE_TRANSITION = "STATE_TRANSITION"
    FINAL_ARTIFACT = "FINAL_ARTIFACT"


class CaseOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ABSTAIN = "ABSTAIN"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_RUN = "INVALID_RUN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FailureOrigin(StrEnum):
    NONE = "NONE"
    AGENT = "AGENT"
    HARNESS = "HARNESS"


class ReleaseMode(StrEnum):
    SHADOW = "SHADOW"
    ADVISORY = "ADVISORY"
    BLOCKING = "BLOCKING"


class ReleaseStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"
    INVALID = "INVALID"


class BenchmarkIdentity(FrozenModel):
    benchmark_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    environment_version: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    created_at: datetime
    retired_at: datetime | None = None


class ToolConstraint(FrozenModel):
    required: tuple[str, ...] = ()
    allowed: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()
    max_tool_calls: int = Field(default=8, ge=0)

    @model_validator(mode="after")
    def sets_do_not_conflict(self) -> "ToolConstraint":
        required, allowed, forbidden = map(set, (self.required, self.allowed, self.forbidden))
        if required & forbidden or allowed & forbidden:
            raise ValueError("CONFLICTING_TOOL_CONSTRAINT")
        if len(required) != len(self.required) or len(forbidden) != len(self.forbidden):
            raise ValueError("DUPLICATE_TOOL_CONSTRAINT")
        return self


class PartialOrderConstraint(FrozenModel):
    before: str = Field(min_length=1)
    after: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_events(self) -> "PartialOrderConstraint":
        if self.before == self.after:
            raise ValueError("SELF_ORDER_CONSTRAINT")
        return self


class ExpectedOutcome(FrozenModel):
    authoritative_state: str = Field(min_length=1)
    required_artifact_fields: tuple[str, ...] = ()
    required_evidence_ids: tuple[str, ...] = ()
    allow_abstention: bool = False


class BenchmarkCase(FrozenModel):
    case_id: str = Field(min_length=1)
    case_version: str = Field(min_length=1)
    case_digest: str = Field(min_length=64, max_length=64)
    title: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    split: DatasetSplit
    provenance: CaseProvenance
    status: CaseStatus
    source_reference: str = Field(min_length=1)
    created_at: datetime
    approved_by: str | None = None
    risk_tags: tuple[str, ...] = Field(min_length=1)
    scenario_tags: tuple[str, ...] = Field(min_length=1)
    expected: ExpectedOutcome
    tools: ToolConstraint
    ordering: tuple[PartialOrderConstraint, ...] = ()
    policy_version: str = Field(min_length=1)
    environment_version: str = Field(min_length=1)
    fixture_version: str = Field(min_length=1)
    development_exposures: tuple[str, ...] = ()
    max_cost_usd: float = Field(gt=0)
    max_wall_clock_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def active_cases_are_governed(self) -> "BenchmarkCase":
        if self.status is CaseStatus.ACTIVE and not self.approved_by:
            raise ValueError("ACTIVE_CASE_REQUIRES_APPROVAL")
        if self.split in {DatasetSplit.VALIDATION, DatasetSplit.CHALLENGE} and self.development_exposures:
            raise ValueError("HELD_OUT_CASE_EXPOSED_TO_DEVELOPMENT")
        return self


class BenchmarkSuite(FrozenModel):
    identity: BenchmarkIdentity
    benchmark_type: BenchmarkType
    contamination_exposure: ContaminationExposure
    cases: tuple[BenchmarkCase, ...] = Field(min_length=1)
    owner_groups: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_active_cases(self) -> "BenchmarkSuite":
        identities = [(case.case_id, case.case_version) for case in self.cases]
        if len(identities) != len(set(identities)):
            raise ValueError("DUPLICATE_CASE_ID_VERSION")
        for case in self.cases:
            if case.policy_version != self.identity.policy_version:
                raise ValueError("CASE_POLICY_VERSION_MISMATCH")
            if case.environment_version != self.identity.environment_version:
                raise ValueError("CASE_ENVIRONMENT_VERSION_MISMATCH")
        return self


class EnvironmentManifest(FrozenModel):
    environment_version: str = Field(min_length=1)
    fixture_version: str = Field(min_length=1)
    tool_versions: dict[str, str] = Field(min_length=1)
    knowledge_snapshot: str = Field(min_length=1)
    cache_policy: str = Field(min_length=1)
    reset_between_cases: bool
    seed: int


class AgentConfigManifest(FrozenModel):
    agent_id: str = Field(min_length=1)
    config_digest: str = Field(min_length=64, max_length=64)
    model: str = Field(min_length=1)
    deployment_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    temperature: float = Field(ge=0)
    policy_version: str = Field(min_length=1)
    router_version: str = Field(min_length=1)
    memory_config_version: str = Field(min_length=1)


class BenchmarkRunManifest(FrozenModel):
    run_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    split: tuple[DatasetSplit, ...] = Field(min_length=1)
    environment: EnvironmentManifest
    agent: AgentConfigManifest
    seed: int
    started_at: datetime


class EvidenceRecord(FrozenModel):
    evidence_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    observed_at: datetime
    digest: str = Field(min_length=64, max_length=64)
    supported_claims: tuple[str, ...] = Field(min_length=1)


class TraceEvent(FrozenModel):
    event_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: EventType
    tenant_id: str = Field(min_length=1)
    tool_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    operation_id: str | None = None
    artifact: dict[str, Any] = Field(default_factory=dict)


class OperationalMetrics(FrozenModel):
    wall_clock_ms: int = Field(ge=0)
    model_latency_ms: int = Field(ge=0)
    tool_latency_ms: int = Field(ge=0)
    queue_wait_ms: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    model_cost_usd: float = Field(ge=0)
    tool_cost_usd: float = Field(ge=0)
    evaluator_cost_usd: float = Field(ge=0)
    retry_count: int = Field(ge=0)
    handoff_count: int = Field(ge=0)
    duplicate_work_count: int = Field(ge=0)

    @property
    def total_cost_usd(self) -> float:
        return self.model_cost_usd + self.tool_cost_usd + self.evaluator_cost_usd


class CaseObservation(FrozenModel):
    case_id: str = Field(min_length=1)
    case_version: str = Field(min_length=1)
    environment_version: str = Field(min_length=1)
    fixture_version: str = Field(min_length=1)
    reported_outcome: str = Field(min_length=1)
    authoritative_state: str | None
    events: tuple[TraceEvent, ...]
    evidence: tuple[EvidenceRecord, ...]
    final_artifact: dict[str, Any]
    operational: OperationalMetrics
    failure_origin: FailureOrigin = FailureOrigin.NONE
    platform_blocked_actions: tuple[str, ...] = ()


class GateResult(FrozenModel):
    gate_id: str = Field(min_length=1)
    passed: bool
    reason_code: str = Field(min_length=1)


class TrajectoryResult(FrozenModel):
    missing_required_actions: tuple[str, ...] = ()
    forbidden_tool_attempts: tuple[str, ...] = ()
    unnecessary_tool_calls: int = Field(default=0, ge=0)
    duplicate_calls: int = Field(default=0, ge=0)
    order_violations: tuple[str, ...] = ()
    evidence_coverage: float = Field(ge=0, le=1)


class CaseResult(FrozenModel):
    run_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    case_version: str = Field(min_length=1)
    outcome: CaseOutcome
    task_success: bool
    compliant_success: bool
    platform_containment_succeeded: bool
    hard_gates: tuple[GateResult, ...]
    trajectory: TrajectoryResult
    operational: OperationalMetrics
    failure_reasons: tuple[str, ...]
    artifacts: tuple[str, ...] = ()


class ConfidenceInterval(FrozenModel):
    estimate: float = Field(ge=0, le=1)
    lower: float = Field(ge=0, le=1)
    upper: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)


class RepeatedTrialSummary(FrozenModel):
    case_id: str = Field(min_length=1)
    trials: int = Field(ge=1)
    successes: int = Field(ge=0)
    success_probability: float = Field(ge=0, le=1)
    variance: float = Field(ge=0)
    flaky: bool


class SliceMetrics(FrozenModel):
    slice_id: str = Field(min_length=1)
    support: int = Field(ge=0)
    task_success_rate: float = Field(ge=0, le=1)
    compliant_success_rate: float = Field(ge=0, le=1)
    critical_failures: int = Field(ge=0)


class BenchmarkMetrics(FrozenModel):
    total_runs: int = Field(ge=0)
    valid_agent_runs: int = Field(ge=0)
    invalid_runs: int = Field(ge=0)
    harness_failures: int = Field(ge=0)
    task_success: ConfidenceInterval
    compliant_success: ConfidenceInterval
    critical_failure: ConfidenceInterval
    invalid_run_rate: float = Field(ge=0, le=1)
    cost_per_successful_compliant_task_usd: float | None = Field(default=None, ge=0)
    p50_wall_clock_ms: float = Field(ge=0)
    p95_wall_clock_ms: float = Field(ge=0)
    average_model_calls: float = Field(ge=0)
    average_tool_calls: float = Field(ge=0)
    per_slice: tuple[SliceMetrics, ...]


class RegressionResult(FrozenModel):
    case_id: str = Field(min_length=1)
    baseline_outcome: CaseOutcome
    candidate_outcome: CaseOutcome
    baseline_compliant: bool
    candidate_compliant: bool
    classification: str = Field(pattern="^(IMPROVEMENT|REGRESSION|UNCHANGED|INVALID_COMPARISON)$")
    risk_tags: tuple[str, ...]


class PairedComparison(FrozenModel):
    baseline_run_id: str = Field(min_length=1)
    candidate_run_id: str = Field(min_length=1)
    improvements: int = Field(ge=0)
    regressions: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    invalid_comparisons: int = Field(ge=0)
    critical_regressions: int = Field(ge=0)
    rows: tuple[RegressionResult, ...]


class ReleasePolicy(FrozenModel):
    policy_id: str = Field(min_length=1)
    mode: ReleaseMode
    min_valid_cases: int = Field(ge=1)
    min_compliant_success_rate: float = Field(ge=0, le=1)
    max_critical_failures: int = Field(ge=0)
    max_critical_regressions: int = Field(ge=0)
    max_p95_wall_clock_ms: float = Field(gt=0)
    max_cost_per_successful_compliant_task_usd: float = Field(gt=0)
    minimum_slice_support: dict[str, int]


class ReleaseDecision(FrozenModel):
    status: ReleaseStatus
    permits_release: bool
    mode: ReleaseMode
    reason_codes: tuple[str, ...]


class BenchmarkException(FrozenModel):
    exception_id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    scoped_reason_codes: tuple[str, ...] = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def expires_after_issue(self) -> "BenchmarkException":
        if self.expires_at <= self.issued_at:
            raise ValueError("EXCEPTION_ALREADY_EXPIRED")
        return self
