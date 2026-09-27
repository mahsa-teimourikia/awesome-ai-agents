"""Application-owned contracts for calibrated LLM and evaluator-agent judgments.

Candidate text and model output are untrusted proposals. The application owns the
rubric, evidence, tool authority, aggregation, release mode, and final decision.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationPolicyError(ValueError):
    """Fail-closed policy error whose message is a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CriterionType(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    SEMANTIC = "SEMANTIC"


class CriterionStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    ABSTAIN = "ABSTAIN"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class JudgeDecision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ABSTAIN = "ABSTAIN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_EVALUATION = "INVALID_EVALUATION"


class PairwiseChoice(StrEnum):
    CANDIDATE_A = "CANDIDATE_A"
    CANDIDATE_B = "CANDIDATE_B"
    TIE = "TIE"
    ABSTAIN = "ABSTAIN"


class PairwiseConsistency(StrEnum):
    CONSISTENT_A = "CONSISTENT_A"
    CONSISTENT_B = "CONSISTENT_B"
    CONSISTENT_TIE = "CONSISTENT_TIE"
    POSITION_UNSTABLE = "POSITION_UNSTABLE"
    ABSTAIN = "ABSTAIN"


class ToolCapability(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"


class ReleaseMode(StrEnum):
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    BLOCKING = "BLOCKING"


class EvidenceAuthority(StrEnum):
    AUTHORITATIVE = "AUTHORITATIVE"
    CORROBORATING = "CORROBORATING"
    UNTRUSTED = "UNTRUSTED"


class Anchor(FrozenModel):
    score: int = Field(ge=1, le=5)
    observable: str = Field(min_length=1)


class RubricCriterion(FrozenModel):
    criterion_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    criterion_type: CriterionType
    anchors: tuple[Anchor, ...] = ()
    hard_gate: bool = False
    required: bool = True
    required_evidence_types: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_anchors(self) -> "RubricCriterion":
        scores = [anchor.score for anchor in self.anchors]
        if len(scores) != len(set(scores)):
            raise ValueError("DUPLICATE_ANCHOR_SCORE")
        if self.criterion_type is CriterionType.SEMANTIC and not self.anchors:
            raise ValueError("SEMANTIC_CRITERION_REQUIRES_ANCHORS")
        return self


class Rubric(FrozenModel):
    rubric_id: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    criteria: tuple[RubricCriterion, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_criteria(self) -> "Rubric":
        ids = [criterion.criterion_id for criterion in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_CRITERION_ID")
        return self

    def criterion(self, criterion_id: str) -> RubricCriterion:
        for criterion in self.criteria:
            if criterion.criterion_id == criterion_id:
                return criterion
        raise EvaluationPolicyError("UNKNOWN_CRITERION")


class HumanRating(FrozenModel):
    rater_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    criterion_id: str = Field(min_length=1)
    score: int | None = Field(default=None, ge=1, le=5)
    status: CriterionStatus


class AdjudicatedLabel(FrozenModel):
    case_id: str = Field(min_length=1)
    criterion_id: str = Field(min_length=1)
    score: int | None = Field(default=None, ge=1, le=5)
    status: CriterionStatus
    disagreement_recorded: bool


class ReferenceLabel(FrozenModel):
    criterion_id: str = Field(min_length=1)
    score: int | None = Field(default=None, ge=1, le=5)
    status: CriterionStatus


class EvaluationCase(FrozenModel):
    case_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    split: str = Field(pattern="^(development|validation)$")
    tenant_id: str = Field(min_length=1)
    primary_agent_id: str = Field(min_length=1)
    candidate_artifact: str
    trace_digest: str = Field(min_length=1)
    reference_labels: tuple[ReferenceLabel, ...]
    reference_decision: JudgeDecision
    slices: tuple[str, ...] = ()
    expected_operation_id: str | None = None
    action_event_time: datetime | None = None


class EvidenceRecord(FrozenModel):
    evidence_id: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    observed_at: datetime
    retrieved_at: datetime
    source_version: str = Field(min_length=1)
    digest: str = Field(min_length=1)
    authority: EvidenceAuthority
    supported_criteria: tuple[str, ...]
    operation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def temporal_order(self) -> "EvidenceRecord":
        if self.retrieved_at < self.observed_at:
            raise ValueError("EVIDENCE_RETRIEVED_BEFORE_OBSERVED")
        return self


class EvidenceRequirement(FrozenModel):
    evidence_type: str = Field(min_length=1)
    criterion_id: str = Field(min_length=1)
    max_age_seconds: int = Field(gt=0)
    require_authoritative: bool = True
    require_post_action: bool = False
    require_operation_binding: bool = False


class JudgeIdentity(FrozenModel):
    judge_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    deployment: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    temperature: float = Field(ge=0)

    @property
    def version(self) -> str:
        return f"{self.provider}/{self.model}/{self.model_version}/{self.deployment}"


class JudgeRequest(FrozenModel):
    evaluation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    rubric_id: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    candidate_artifact: str
    trusted_evidence_ids: tuple[str, ...]
    evidence_snapshot_digest: str = Field(min_length=1)

    @model_validator(mode="after")
    def unique_evidence_ids(self) -> "JudgeRequest":
        if len(self.trusted_evidence_ids) != len(set(self.trusted_evidence_ids)):
            raise ValueError("DUPLICATE_TRUSTED_EVIDENCE_ID")
        return self


class CriterionResult(FrozenModel):
    criterion_id: str = Field(min_length=1)
    status: CriterionStatus
    score: int | None = Field(default=None, ge=1, le=5)
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Estimated probability that this criterion judgment is correct.",
    )
    evidence_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class HardGateResult(FrozenModel):
    gate_id: str = Field(min_length=1)
    passed: bool
    evidence_ids: tuple[str, ...] = ()
    reason_code: str = Field(min_length=1)


class JudgeVerdict(FrozenModel):
    evaluation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    rubric_id: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    judge_id: str = Field(min_length=1)
    judge_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    settings: dict[str, Any]
    evidence_snapshot_digest: str = Field(min_length=1)
    criterion_results: tuple[CriterionResult, ...]
    hard_gate_results: tuple[HardGateResult, ...]
    verdict: JudgeDecision
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason_codes: tuple[str, ...] = ()


class PairwiseVerdict(FrozenModel):
    candidate_a_id: str = Field(min_length=1)
    candidate_b_id: str = Field(min_length=1)
    first_order: tuple[str, str]
    first_choice: PairwiseChoice
    swapped_order: tuple[str, str]
    swapped_choice: PairwiseChoice
    consistency: PairwiseConsistency


class BiasProbe(FrozenModel):
    probe_id: str = Field(min_length=1)
    bias_type: str = Field(min_length=1)
    sample_size: int = Field(ge=1)
    failure_rate: float = Field(ge=0, le=1)


class ToolSpec(FrozenModel):
    tool_id: str = Field(min_length=1)
    capability: ToolCapability
    effect_class: str = Field(min_length=1)
    allowed_for_evaluator: bool
    tenant_scoped: bool = True


class EvaluatorBudget(FrozenModel):
    max_tool_calls: int = Field(default=4, ge=0)
    max_model_calls: int = Field(default=1, ge=0)
    max_cost_usd: float = Field(default=0.05, ge=0)
    deadline: datetime


class EvaluatorUsage(FrozenModel):
    tool_calls: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)


class EvaluatorContext(FrozenModel):
    evaluator_id: str = Field(min_length=1)
    primary_agent_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    allowed_tool_ids: tuple[str, ...]
    budget: EvaluatorBudget

    @model_validator(mode="after")
    def separate_identity(self) -> "EvaluatorContext":
        if self.evaluator_id == self.primary_agent_id:
            raise ValueError("EVALUATOR_IDENTITY_NOT_SEPARATE")
        return self


class AgreementReport(FrozenModel):
    exact_agreement: float = Field(ge=0, le=1)
    within_one_agreement: float = Field(ge=0, le=1)
    mean_absolute_error: float = Field(ge=0)
    weighted_kappa: float = Field(ge=-1, le=1)
    sample_size: int = Field(ge=1)


class CalibrationReport(FrozenModel):
    brier_score: float = Field(ge=0, le=1)
    expected_calibration_error: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=1)


class BiasReport(FrozenModel):
    candidate_consistent_rate: float = Field(ge=0, le=1)
    tie_consistent_rate: float = Field(ge=0, le=1)
    abstain_rate: float = Field(ge=0, le=1)
    position_unstable_rate: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=1)
    probes: tuple[BiasProbe, ...]


class SliceMetrics(FrozenModel):
    agreement: AgreementReport
    case_count: int = Field(ge=1)
    negative_case_count: int = Field(ge=0)
    false_pass_rate: float | None = Field(default=None, ge=0, le=1)


class EvaluationMetrics(FrozenModel):
    validation_case_count: int = Field(ge=0)
    dataset_splits: tuple[str, ...] = Field(min_length=1)
    agreement: AgreementReport
    calibration: CalibrationReport
    false_pass_rate: float = Field(ge=0, le=1)
    false_fail_rate: float = Field(ge=0, le=1)
    pass_rate: float = Field(ge=0, le=1)
    confusion_matrix: dict[str, int]
    per_criterion: dict[str, AgreementReport]
    per_slice: dict[str, SliceMetrics]


class AcceptancePolicy(FrozenModel):
    policy_id: str = Field(min_length=1)
    release_mode: ReleaseMode
    min_weighted_kappa: float = Field(ge=-1, le=1)
    max_false_pass_rate: float = Field(ge=0, le=1)
    max_false_fail_rate: float = Field(ge=0, le=1)
    max_ece: float = Field(ge=0, le=1)
    required_validation_cases: int = Field(ge=1)
    minimum_slice_support: dict[str, int] = Field(default_factory=dict)
    maximum_slice_false_pass_rate: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_slice_limits(self) -> "AcceptancePolicy":
        if any(value < 1 for value in self.minimum_slice_support.values()):
            raise ValueError("SLICE_SUPPORT_MUST_BE_POSITIVE")
        if any(value < 0 or value > 1 for value in self.maximum_slice_false_pass_rate.values()):
            raise ValueError("SLICE_FALSE_PASS_RATE_OUT_OF_RANGE")
        return self


class GateDecision(FrozenModel):
    admitted: bool
    release_mode: ReleaseMode
    reason_codes: tuple[str, ...]
    requires_human_review: bool


class DriftReport(FrozenModel):
    agreement_delta: float
    pass_rate_delta: float
    criterion_deltas: dict[str, float]
    drift_detected: bool
    reason_codes: tuple[str, ...]
