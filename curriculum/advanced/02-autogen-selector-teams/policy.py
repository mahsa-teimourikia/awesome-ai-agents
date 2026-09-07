"""Framework-neutral control plane for a bounded evidence-driven selector team.

The selector proposes a speaker. The application owns eligibility, evidence,
authority, budgets, and termination. Chat text is trace data, not control state.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PolicyError(ValueError):
    """Fail-closed policy result with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentRole(StrEnum):
    OBSERVABILITY = "OBSERVABILITY"
    DEPLOYMENT = "DEPLOYMENT"
    CUSTOMER_IMPACT = "CUSTOMER_IMPACT"
    ANALYST = "ANALYST"
    REVIEWER = "REVIEWER"


class EvidenceStatus(StrEnum):
    MISSING = "MISSING"
    COLLECTED = "COLLECTED"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICT = "CONFLICT"


class SelectorReason(StrEnum):
    MISSING_HEALTH_EVIDENCE = "MISSING_HEALTH_EVIDENCE"
    MISSING_LOG_EVIDENCE = "MISSING_LOG_EVIDENCE"
    MISSING_DEPLOYMENT_EVIDENCE = "MISSING_DEPLOYMENT_EVIDENCE"
    MISSING_CUSTOMER_IMPACT = "MISSING_CUSTOMER_IMPACT"
    MISSING_RUNBOOK_EVIDENCE = "MISSING_RUNBOOK_EVIDENCE"
    CONFLICT_RECONCILIATION = "CONFLICT_RECONCILIATION"
    DUPLICATE_SELECTION = "DUPLICATE_SELECTION"
    READY_FOR_ANALYSIS = "READY_FOR_ANALYSIS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NO_ELIGIBLE_SPEAKER = "NO_ELIGIBLE_SPEAKER"
    AMBIGUOUS_SELECTION = "AMBIGUOUS_SELECTION"


class TerminationReason(StrEnum):
    COMPLETE = "COMPLETE"
    ESCALATE = "ESCALATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LOOP_DETECTED = "LOOP_DETECTED"
    STALLED = "STALLED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    CANCELLED = "CANCELLED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    CONTINUE = "CONTINUE"


class TeamStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class FailureCode(StrEnum):
    TIMEOUT = "TIMEOUT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    AUTH_DENIED = "AUTH_DENIED"
    POLICY_DENIED = "POLICY_DENIED"
    INVALID_ARTIFACT = "INVALID_ARTIFACT"


class RecoveryAction(StrEnum):
    BOUNDED_RETRY = "BOUNDED_RETRY"
    ALTERNATE_SOURCE = "ALTERNATE_SOURCE"
    NO_RETRY = "NO_RETRY"
    BOUNDED_REPAIR = "BOUNDED_REPAIR"


class AgentDefinition(FrozenModel):
    agent_id: str = Field(min_length=1)
    role: AgentRole
    allowed_capabilities: tuple[str, ...]
    eligible_gap_types: tuple[str, ...]
    max_turns: int = Field(ge=1)
    context_policy: str = Field(min_length=1)

    @field_validator("allowed_capabilities", "eligible_gap_types")
    @classmethod
    def unique_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("values must be unique")
        return value


class TeamBudget(FrozenModel):
    max_messages: int = Field(ge=1)
    max_selector_calls: int = Field(ge=1)
    max_worker_calls: int = Field(ge=1)
    max_turns_per_agent: int = Field(ge=1)
    max_repeated_speaker: int = Field(ge=1)
    max_cost_usd: float = Field(ge=0)
    deadline_ms: int = Field(ge=1)


class TeamContext(FrozenModel):
    tenant_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    required_evidence: tuple[str, ...] = Field(min_length=1)
    capability_policy: Mapping[str, tuple[str, ...]]
    source_allowlist: Mapping[str, tuple[str, ...]]
    budget: TeamBudget
    policy_version: str = Field(min_length=1)


class TeamMessage(FrozenModel):
    message_id: str
    sender: str
    turn_id: str
    artifact_id: str | None = None
    content: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class EvidenceRecord(FrozenModel):
    evidence_id: str
    tenant_id: str
    evidence_type: str
    source_id: str
    capability: str
    findings: Mapping[str, str]
    status: EvidenceStatus = EvidenceStatus.COLLECTED
    provenance_verified: bool
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class EvidenceGap(FrozenModel):
    evidence_type: str
    status: EvidenceStatus
    detail: str


class SelectorDecision(FrozenModel):
    next_agent: str | None
    reason_code: SelectorReason
    target_gap: str | None
    eligible_agents: tuple[str, ...]

    @model_validator(mode="after")
    def abstention_shape(self) -> "SelectorDecision":
        abstains = {
            SelectorReason.NO_ELIGIBLE_SPEAKER,
            SelectorReason.AMBIGUOUS_SELECTION,
        }
        if self.reason_code in abstains and self.next_agent is not None:
            raise ValueError("abstention cannot name a speaker")
        if self.reason_code not in abstains and self.next_agent is None:
            raise ValueError("routing decision must name a speaker")
        return self


class WorkerArtifact(FrozenModel):
    artifact_id: str
    agent_id: str
    tenant_id: str
    evidence_ids: tuple[str, ...]
    findings: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    created_at: datetime
    evidence_records: tuple[EvidenceRecord, ...] = ()
    candidate_diagnosis: str | None = None
    review_result: str | None = None
    review_feedback: str | None = None

    @field_validator("created_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class SpeakerTurn(FrozenModel):
    turn_id: str
    agent_id: str
    target_gap: str | None
    evidence_digest_before: str
    evidence_digest_after: str
    candidate_digest: str
    review_feedback_digest: str
    material_digest_before: str
    material_digest_after: str
    worker_tokens: int = Field(ge=0)
    worker_cost_usd: float = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    created_at: datetime


class TerminationDecision(FrozenModel):
    reason: TerminationReason
    status: TeamStatus
    should_stop: bool
    detail: str


class TeamRun(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    context: TeamContext
    agents: Mapping[str, AgentDefinition]
    evidence: Mapping[str, EvidenceRecord] = Field(default_factory=dict)
    gaps: tuple[EvidenceGap, ...]
    candidate_diagnosis: str | None = None
    candidate_evidence_ids: tuple[str, ...] = ()
    review_passed: bool = False
    review_feedback: str | None = None
    messages: tuple[TeamMessage, ...] = ()
    turns: tuple[SpeakerTurn, ...] = ()
    selector_calls: int = 0
    worker_calls: int = 0
    selector_tokens: int = 0
    worker_tokens: int = 0
    selector_cost_usd: float = 0.0
    worker_cost_usd: float = 0.0
    selector_work_ms: int = 0
    worker_work_ms: int = 0
    wall_clock_ms: int = 0
    cancelled: bool = False
    policy_blocked: bool = False
    escalated: bool = False
    insufficient_evidence: bool = False


class TeamMetrics(FrozenModel):
    run_type: str
    task_success: bool
    grounded: bool
    required_evidence_recall: float = Field(ge=0, le=1)
    model_calls: int = Field(ge=0)
    selector_model_calls: int = Field(ge=0)
    worker_model_calls: int = Field(ge=0)
    selector_tokens: int = Field(ge=0)
    worker_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)
    total_work_ms: int = Field(ge=0)
    selector_work_ms: int = Field(ge=0)
    worker_work_ms: int = Field(ge=0)
    selector_cost_usd: float = Field(ge=0)
    worker_cost_usd: float = Field(ge=0)
    cost_usd: float = Field(ge=0)
    cost_per_successful_compliant_task: float | None
    duplicate_turns: int = Field(ge=0)


class SelectorSnapshot(FrozenModel):
    snapshot_id: str
    state_summary: str
    eligible_agents: tuple[str, ...]
    valid_next_agents: tuple[str, ...]
    expected_termination: TerminationReason


class SelectorEvaluation(FrozenModel):
    cases: int = Field(ge=1)
    valid_speaker_rate: float = Field(ge=0, le=1)
    speaker_set_accuracy: float = Field(ge=0, le=1)
    invalid_speaker_rate: float = Field(ge=0, le=1)
    premature_analysis_rate: float = Field(ge=0, le=1)
    premature_review_rate: float = Field(ge=0, le=1)
    premature_completion_rate: float = Field(ge=0, le=1)
    loop_selection_rate: float = Field(ge=0, le=1)
    no_speaker_handling_rate: float = Field(ge=0, le=1)


GAP_TO_AGENT = {
    "health": "ObservabilityAgent",
    "logs": "ObservabilityAgent",
    "deployment": "DeploymentAgent",
    "customer-impact": "CustomerImpactAgent",
    "current-runbook": "DeploymentAgent",
}

GAP_TO_REASON = {
    "health": SelectorReason.MISSING_HEALTH_EVIDENCE,
    "logs": SelectorReason.MISSING_LOG_EVIDENCE,
    "deployment": SelectorReason.MISSING_DEPLOYMENT_EVIDENCE,
    "customer-impact": SelectorReason.MISSING_CUSTOMER_IMPACT,
    "current-runbook": SelectorReason.MISSING_RUNBOOK_EVIDENCE,
}


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()[:16]


def evidence_digest(run: TeamRun) -> str:
    return stable_digest(
        {
            key: {
                "status": record.status,
                "source": record.source_id,
                "findings": dict(record.findings),
            }
            for key, record in sorted(run.evidence.items())
        }
    )


def candidate_digest(run: TeamRun) -> str:
    return stable_digest(run.candidate_diagnosis or "")


def review_digest(run: TeamRun) -> str:
    return stable_digest(
        {"passed": run.review_passed, "feedback": run.review_feedback or ""}
    )


def material_digest(run: TeamRun) -> str:
    return stable_digest(
        {
            "evidence": evidence_digest(run),
            "candidate": candidate_digest(run),
            "review": review_digest(run),
        }
    )


def compute_gaps(run: TeamRun) -> tuple[EvidenceGap, ...]:
    gaps: list[EvidenceGap] = []
    for evidence_type in run.context.required_evidence:
        record = run.evidence.get(evidence_type)
        status = record.status if record else EvidenceStatus.MISSING
        if status is not EvidenceStatus.COLLECTED:
            gaps.append(
                EvidenceGap(
                    evidence_type=evidence_type,
                    status=status,
                    detail=f"{evidence_type} evidence is {status.value.lower()}",
                )
            )
    return tuple(gaps)


def evidence_sufficient(run: TeamRun) -> bool:
    return not compute_gaps(run)


def _budget_exhausted(run: TeamRun) -> bool:
    budget = run.context.budget
    if len(run.messages) >= budget.max_messages:
        return True
    if run.selector_calls >= budget.max_selector_calls:
        return True
    if run.worker_calls >= budget.max_worker_calls:
        return True
    if run.selector_cost_usd + run.worker_cost_usd >= budget.max_cost_usd:
        return True
    counts = Counter(turn.agent_id for turn in run.turns)
    for agent_id, count in counts.items():
        agent_limit = min(budget.max_turns_per_agent, run.agents[agent_id].max_turns)
        if count >= agent_limit:
            return True
    if run.turns:
        last = run.turns[-1].agent_id
        repeated = 0
        for turn in reversed(run.turns):
            if turn.agent_id != last:
                break
            repeated += 1
        if repeated >= budget.max_repeated_speaker:
            return True
    return False


def detect_duplicate_selection(run: TeamRun, decision: SelectorDecision) -> bool:
    if not run.turns or decision.next_agent is None:
        return False
    previous = run.turns[-1]
    return (
        previous.agent_id == decision.next_agent
        and previous.target_gap == decision.target_gap
        and previous.evidence_digest_after == evidence_digest(run)
    )


def detect_ping_pong(run: TeamRun) -> bool:
    if len(run.turns) < 4:
        return False
    turns = run.turns[-4:]
    agents = tuple(turn.agent_id for turn in turns)
    if not (agents[0] == agents[2] and agents[1] == agents[3] and agents[0] != agents[1]):
        return False
    return len({turn.material_digest_after for turn in turns}) == 1


def detect_stagnation(run: TeamRun, *, window: int = 3) -> bool:
    if len(run.turns) < window:
        return False
    turns = run.turns[-window:]
    return all(turn.material_digest_before == turn.material_digest_after for turn in turns)


def detect_review_churn(run: TeamRun) -> bool:
    if len(run.turns) < 4:
        return False
    turns = run.turns[-4:]
    roles = tuple(run.agents[turn.agent_id].role for turn in turns)
    if roles != (
        AgentRole.ANALYST,
        AgentRole.REVIEWER,
        AgentRole.ANALYST,
        AgentRole.REVIEWER,
    ):
        return False
    return (
        len({turn.evidence_digest_after for turn in turns}) == 1
        and turns[0].candidate_digest == turns[2].candidate_digest
        and turns[1].review_feedback_digest == turns[3].review_feedback_digest
    )


def termination_decision(run: TeamRun) -> TerminationDecision:
    """Apply explicit precedence from strongest external control to completion."""
    if run.cancelled:
        return TerminationDecision(
            reason=TerminationReason.CANCELLED,
            status=TeamStatus.CANCELLED,
            should_stop=True,
            detail="application cancellation is authoritative",
        )
    if run.policy_blocked:
        return TerminationDecision(
            reason=TerminationReason.POLICY_BLOCKED,
            status=TeamStatus.BLOCKED,
            should_stop=True,
            detail="application policy blocked continuation",
        )
    if run.wall_clock_ms >= run.context.budget.deadline_ms:
        return TerminationDecision(
            reason=TerminationReason.DEADLINE_EXCEEDED,
            status=TeamStatus.ESCALATED,
            should_stop=True,
            detail="wall-clock deadline reached",
        )
    if _budget_exhausted(run):
        return TerminationDecision(
            reason=TerminationReason.BUDGET_EXHAUSTED,
            status=TeamStatus.ESCALATED,
            should_stop=True,
            detail="a hard team budget was reached",
        )
    if detect_ping_pong(run) or detect_review_churn(run):
        return TerminationDecision(
            reason=TerminationReason.LOOP_DETECTED,
            status=TeamStatus.ESCALATED,
            should_stop=True,
            detail="repeated coordination produced no material state change",
        )
    if detect_stagnation(run):
        return TerminationDecision(
            reason=TerminationReason.STALLED,
            status=TeamStatus.ESCALATED,
            should_stop=True,
            detail="three turns produced no material change",
        )
    if run.escalated:
        return TerminationDecision(
            reason=TerminationReason.ESCALATE,
            status=TeamStatus.ESCALATED,
            should_stop=True,
            detail="validated application escalation",
        )
    if run.insufficient_evidence:
        return TerminationDecision(
            reason=TerminationReason.INSUFFICIENT_EVIDENCE,
            status=TeamStatus.ESCALATED,
            should_stop=True,
            detail="required evidence cannot be obtained safely",
        )
    if run.review_passed:
        return TerminationDecision(
            reason=TerminationReason.COMPLETE,
            status=TeamStatus.COMPLETED,
            should_stop=True,
            detail="required evidence, candidate diagnosis, and REVIEW_PASS are present",
        )
    return TerminationDecision(
        reason=TerminationReason.CONTINUE,
        status=TeamStatus.RUNNING,
        should_stop=False,
        detail="another bounded turn may proceed",
    )


def ensure_can_continue(run: TeamRun) -> None:
    decision = termination_decision(run)
    if decision.should_stop:
        raise PolicyError(f"TEAM_STOPPED:{decision.reason.value}")


def eligible_agents(run: TeamRun) -> tuple[str, ...]:
    if termination_decision(run).should_stop:
        return ()
    gaps = compute_gaps(run)
    candidates: list[str] = []
    for gap in gaps:
        agent_id = GAP_TO_AGENT.get(gap.evidence_type)
        if agent_id and agent_id in run.agents and agent_id not in candidates:
            definition = run.agents[agent_id]
            if gap.evidence_type in definition.eligible_gap_types:
                candidates.append(agent_id)
    if candidates:
        return tuple(candidates)
    if evidence_sufficient(run) and not run.candidate_diagnosis:
        return ("AnalystAgent",)
    if run.candidate_diagnosis and not run.review_passed:
        return ("ReviewerAgent",)
    return ()


def deterministic_selector(run: TeamRun) -> SelectorDecision:
    eligible = eligible_agents(run)
    if not eligible:
        return SelectorDecision(
            next_agent=None,
            reason_code=SelectorReason.NO_ELIGIBLE_SPEAKER,
            target_gap=None,
            eligible_agents=(),
        )
    gaps = compute_gaps(run)
    if gaps:
        routable = [gap for gap in gaps if GAP_TO_AGENT.get(gap.evidence_type) in eligible]
        gap = next(
            (gap for gap in routable if gap.status is EvidenceStatus.CONFLICT),
            routable[0],
        )
        return SelectorDecision(
            next_agent=GAP_TO_AGENT[gap.evidence_type],
            reason_code=(
                SelectorReason.CONFLICT_RECONCILIATION
                if gap.status is EvidenceStatus.CONFLICT
                else GAP_TO_REASON[gap.evidence_type]
            ),
            target_gap=gap.evidence_type,
            eligible_agents=eligible,
        )
    if not run.candidate_diagnosis:
        return SelectorDecision(
            next_agent="AnalystAgent",
            reason_code=SelectorReason.READY_FOR_ANALYSIS,
            target_gap=None,
            eligible_agents=eligible,
        )
    return SelectorDecision(
        next_agent="ReviewerAgent",
        reason_code=SelectorReason.READY_FOR_REVIEW,
        target_gap=None,
        eligible_agents=eligible,
    )


def validate_selector_decision(run: TeamRun, decision: SelectorDecision) -> None:
    ensure_can_continue(run)
    computed = eligible_agents(run)
    if tuple(decision.eligible_agents) != computed:
        raise PolicyError("STALE_OR_FORGED_ELIGIBLE_SET")
    if decision.next_agent is None:
        if computed:
            raise PolicyError("UNJUSTIFIED_ABSTENTION")
        return
    if decision.next_agent not in run.agents:
        raise PolicyError("UNKNOWN_AGENT")
    if decision.next_agent not in computed:
        raise PolicyError("INELIGIBLE_AGENT")
    if detect_duplicate_selection(run, decision):
        raise PolicyError("DUPLICATE_SELECTION")
    if decision.target_gap is not None:
        definition = run.agents[decision.next_agent]
        if decision.target_gap not in definition.eligible_gap_types:
            raise PolicyError("AGENT_CANNOT_CLOSE_TARGET_GAP")


def record_selector_call(
    run: TeamRun, *, tokens: int, cost_usd: float, elapsed_ms: int
) -> None:
    ensure_can_continue(run)
    run.selector_calls += 1
    run.selector_tokens += tokens
    run.selector_cost_usd += cost_usd
    run.selector_work_ms += elapsed_ms
    run.wall_clock_ms += elapsed_ms


def validate_worker_artifact(
    run: TeamRun, decision: SelectorDecision, artifact: WorkerArtifact
) -> None:
    validate_selector_decision(run, decision)
    if artifact.agent_id != decision.next_agent:
        raise PolicyError("UNEXPECTED_AGENT_ARTIFACT")
    if artifact.tenant_id != run.context.tenant_id:
        raise PolicyError("WRONG_TENANT_ARTIFACT")
    referenced = set(artifact.evidence_ids)
    new_ids = {record.evidence_id for record in artifact.evidence_records}
    known_ids = set(run.evidence)
    if not new_ids.issubset(referenced) or not referenced.issubset(known_ids | new_ids):
        raise PolicyError("INVALID_EVIDENCE_REFERENCE")
    allowed_capabilities = set(run.context.capability_policy.get(artifact.agent_id, ()))
    definition_capabilities = set(run.agents[artifact.agent_id].allowed_capabilities)
    allowed_sources = run.context.source_allowlist
    for record in artifact.evidence_records:
        if record.tenant_id != run.context.tenant_id:
            raise PolicyError("WRONG_TENANT_EVIDENCE")
        if record.evidence_id not in run.context.required_evidence:
            raise PolicyError("UNKNOWN_EVIDENCE_ID")
        if not record.provenance_verified:
            raise PolicyError("UNVERIFIED_PROVENANCE")
        if record.source_id not in allowed_sources.get(record.evidence_id, ()):
            raise PolicyError("UNAPPROVED_SOURCE")
        if record.capability not in allowed_capabilities:
            raise PolicyError("CAPABILITY_POLICY_DENIED")
        if record.capability not in definition_capabilities:
            raise PolicyError("AGENT_CAPABILITY_DENIED")
    role = run.agents[artifact.agent_id].role
    if artifact.candidate_diagnosis and role is not AgentRole.ANALYST:
        raise PolicyError("DIAGNOSIS_FROM_UNEXPECTED_ROLE")
    if artifact.review_result and role is not AgentRole.REVIEWER:
        raise PolicyError("REVIEW_FROM_UNEXPECTED_ROLE")
    if artifact.review_result not in (None, "REVIEW_PASS", "REVIEW_FAIL"):
        raise PolicyError("INVALID_REVIEW_RESULT")


def apply_worker_turn(
    run: TeamRun,
    decision: SelectorDecision,
    artifact: WorkerArtifact,
    *,
    worker_tokens: int,
    worker_cost_usd: float,
    elapsed_ms: int,
) -> SpeakerTurn:
    """Validate one proposal and one artifact, then commit one bounded turn."""
    validate_worker_artifact(run, decision, artifact)
    before_evidence = evidence_digest(run)
    before_material = material_digest(run)
    updated_evidence = dict(run.evidence)
    for record in artifact.evidence_records:
        updated_evidence[record.evidence_id] = record
    run.evidence = updated_evidence
    run.gaps = compute_gaps(run)
    if artifact.candidate_diagnosis:
        run.candidate_diagnosis = artifact.candidate_diagnosis
        run.candidate_evidence_ids = artifact.evidence_ids
    if artifact.review_result == "REVIEW_PASS":
        if not run.candidate_diagnosis or not evidence_sufficient(run):
            raise PolicyError("PREMATURE_REVIEW_PASS")
        run.review_passed = True
        run.review_feedback = artifact.review_feedback
    elif artifact.review_result == "REVIEW_FAIL":
        run.review_passed = False
        run.review_feedback = artifact.review_feedback
    run.worker_calls += 1
    run.worker_tokens += worker_tokens
    run.worker_cost_usd += worker_cost_usd
    run.worker_work_ms += elapsed_ms
    run.wall_clock_ms += elapsed_ms
    turn = SpeakerTurn(
        turn_id=f"turn-{len(run.turns) + 1}",
        agent_id=artifact.agent_id,
        target_gap=decision.target_gap,
        evidence_digest_before=before_evidence,
        evidence_digest_after=evidence_digest(run),
        candidate_digest=candidate_digest(run),
        review_feedback_digest=review_digest(run),
        material_digest_before=before_material,
        material_digest_after=material_digest(run),
        worker_tokens=worker_tokens,
        worker_cost_usd=worker_cost_usd,
        elapsed_ms=elapsed_ms,
        created_at=artifact.created_at,
    )
    run.turns = (*run.turns, turn)
    run.messages = (
        *run.messages,
        TeamMessage(
            message_id=f"message-{len(run.messages) + 1}",
            sender=artifact.agent_id,
            turn_id=turn.turn_id,
            artifact_id=artifact.artifact_id,
            content="; ".join(artifact.findings),
            created_at=artifact.created_at,
        ),
    )
    return turn


def request_cancellation(run: TeamRun) -> None:
    run.cancelled = True


def apply_validated_control_signal(
    run: TeamRun,
    *,
    signal: str,
    sender: str,
    expected_sender: str,
    artifact_validated: bool,
) -> bool:
    """Only a trusted expected role plus validated output may affect control state."""
    if sender != expected_sender or not artifact_validated:
        return False
    if signal == "ESCALATE_TO_HUMAN":
        run.escalated = True
        return True
    return False


def failure_recovery(code: FailureCode) -> RecoveryAction:
    return {
        FailureCode.TIMEOUT: RecoveryAction.BOUNDED_RETRY,
        FailureCode.SOURCE_UNAVAILABLE: RecoveryAction.ALTERNATE_SOURCE,
        FailureCode.AUTH_DENIED: RecoveryAction.NO_RETRY,
        FailureCode.POLICY_DENIED: RecoveryAction.NO_RETRY,
        FailureCode.INVALID_ARTIFACT: RecoveryAction.BOUNDED_REPAIR,
    }[code]


def projected_selector_context(run: TeamRun) -> dict[str, Any]:
    """Minimum useful routing state; raw message text and tenant secrets are omitted."""
    return {
        "goal": run.context.goal,
        "gaps": [gap.model_dump(mode="json") for gap in compute_gaps(run)],
        "eligible_agents": list(eligible_agents(run)),
        "last_material_change": run.turns[-1].material_digest_after if run.turns else None,
        "budget_remaining": {
            "selector_calls": run.context.budget.max_selector_calls - run.selector_calls,
            "worker_calls": run.context.budget.max_worker_calls - run.worker_calls,
            "cost_usd": round(
                run.context.budget.max_cost_usd
                - run.selector_cost_usd
                - run.worker_cost_usd,
                6,
            ),
        },
    }


def estimate_context_tokens(value: Any) -> int:
    return max(1, len(json.dumps(value, default=str)) // 4)


def derive_metrics(run: TeamRun, *, run_type: str) -> TeamMetrics:
    required = set(run.context.required_evidence)
    collected = {
        key for key, record in run.evidence.items() if record.status is EvidenceStatus.COLLECTED
    }
    recall = len(required & collected) / len(required)
    compliant = (
        run.review_passed
        and recall == 1.0
        and not run.policy_blocked
        and not run.cancelled
    )
    total_cost = run.selector_cost_usd + run.worker_cost_usd
    duplicates = sum(
        1
        for left, right in zip(run.turns, run.turns[1:])
        if left.agent_id == right.agent_id
        and left.target_gap == right.target_gap
        and left.evidence_digest_after == right.evidence_digest_after
    )
    return TeamMetrics(
        run_type=run_type,
        task_success=compliant,
        grounded=recall == 1.0 and bool(run.candidate_evidence_ids),
        required_evidence_recall=recall,
        model_calls=run.selector_calls + run.worker_calls,
        selector_model_calls=run.selector_calls,
        worker_model_calls=run.worker_calls,
        selector_tokens=run.selector_tokens,
        worker_tokens=run.worker_tokens,
        total_tokens=run.selector_tokens + run.worker_tokens,
        wall_clock_ms=run.wall_clock_ms,
        total_work_ms=run.selector_work_ms + run.worker_work_ms,
        selector_work_ms=run.selector_work_ms,
        worker_work_ms=run.worker_work_ms,
        selector_cost_usd=round(run.selector_cost_usd, 6),
        worker_cost_usd=round(run.worker_cost_usd, 6),
        cost_usd=round(total_cost, 6),
        cost_per_successful_compliant_task=round(total_cost, 6) if compliant else None,
        duplicate_turns=duplicates,
    )


def evaluate_selector(
    snapshots: Sequence[SelectorSnapshot], predictions: Sequence[str | None]
) -> SelectorEvaluation:
    if len(snapshots) != len(predictions) or not snapshots:
        raise ValueError("snapshots and predictions must be non-empty and aligned")
    valid = invalid = early_analysis = early_review = early_complete = loops = no_speaker = 0
    exact_sets = 0
    for case, prediction in zip(snapshots, predictions):
        expected = set(case.valid_next_agents)
        if prediction in expected:
            valid += 1
        elif prediction is not None or expected:
            invalid += 1
        if prediction == "AnalystAgent" and prediction not in expected:
            early_analysis += 1
        if prediction == "ReviewerAgent" and prediction not in expected:
            early_review += 1
        if prediction == "COMPLETE" and case.expected_termination is not TerminationReason.COMPLETE:
            early_complete += 1
        if prediction == "LOOP":
            loops += 1
        if not expected and prediction is None:
            no_speaker += 1
        predicted_set = {prediction} if prediction is not None else set()
        if predicted_set == expected:
            exact_sets += 1
        elif prediction in expected:
            # Set-valued correctness: one of several valid speakers is acceptable.
            exact_sets += 1
    n = len(snapshots)
    return SelectorEvaluation(
        cases=n,
        valid_speaker_rate=valid / n,
        speaker_set_accuracy=exact_sets / n,
        invalid_speaker_rate=invalid / n,
        premature_analysis_rate=early_analysis / n,
        premature_review_rate=early_review / n,
        premature_completion_rate=early_complete / n,
        loop_selection_rate=loops / n,
        no_speaker_handling_rate=no_speaker / max(1, sum(not c.valid_next_agents for c in snapshots)),
    )
