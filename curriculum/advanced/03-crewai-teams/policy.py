"""Application-owned contracts and policy for Advanced Course 03.

CrewAI can orchestrate bounded work, but role text and model output are not
authority.  This module remains credential-free so the notebook and tests use
exactly the same enforcement logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PolicyError(ValueError):
    """A fail-closed policy result with a stable reason code."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MutableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FrozenDict(dict):
    """A small JSON-serializable immutable mapping for accepted records."""

    def _immutable(self, *_: Any, **__: Any) -> None:
        raise TypeError("immutable mapping")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return FrozenDict({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


class AgentRole(StrEnum):
    MANAGER = "MANAGER"
    OBSERVABILITY = "OBSERVABILITY"
    DEPLOYMENT = "DEPLOYMENT"
    CUSTOMER_IMPACT = "CUSTOMER_IMPACT"
    INCIDENT_ANALYST = "INCIDENT_ANALYST"
    REVIEWER = "REVIEWER"


class Capability(StrEnum):
    HEALTH_READ = "health.read"
    LOGS_READ = "logs.read"
    DEPLOYMENT_READ = "deployment.read"
    CUSTOMER_IMPACT_READ = "customer-impact.read"
    RUNBOOK_READ = "runbook.read"
    PRODUCTION_ROLLBACK = "production.rollback"
    DATABASE_DELETE = "database.delete"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    RETRYABLE = "RETRYABLE"
    CANCELLED = "CANCELLED"


class ArtifactType(StrEnum):
    HEALTH_FINDING = "HEALTH_FINDING"
    LOG_FINDING = "LOG_FINDING"
    DEPLOYMENT_FINDING = "DEPLOYMENT_FINDING"
    CUSTOMER_IMPACT = "CUSTOMER_IMPACT"
    RUNBOOK_GUIDANCE = "RUNBOOK_GUIDANCE"
    INCIDENT_BRIEF = "INCIDENT_BRIEF"
    REVIEW_DECISION = "REVIEW_DECISION"


class FailureCode(StrEnum):
    TIMEOUT = "TIMEOUT"
    INVALID_ARTIFACT = "INVALID_ARTIFACT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    AUTH_DENIED = "AUTH_DENIED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    DUPLICATE_EXECUTION = "DUPLICATE_EXECUTION"
    DELEGATION_STALLED = "DELEGATION_STALLED"


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class DelegationDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


ROOT_DELEGATION_CONTEXT = "ROOT_DELEGATION_CONTEXT"


class FlowEventType(StrEnum):
    FLOW_STARTED = "FLOW_STARTED"
    TASK_READY = "TASK_READY"
    CREW_STARTED = "CREW_STARTED"
    TASK_SUCCEEDED = "TASK_SUCCEEDED"
    TASK_FAILED = "TASK_FAILED"
    ARTIFACT_ACCEPTED = "ARTIFACT_ACCEPTED"
    ARTIFACT_REJECTED = "ARTIFACT_REJECTED"
    MANAGER_DELEGATED = "MANAGER_DELEGATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class AgentDefinition(FrozenModel):
    agent_id: str = Field(min_length=1)
    role: AgentRole
    goal: str = Field(min_length=1)
    backstory: str = Field(min_length=1)
    advertised_tools: tuple[Capability, ...] = ()


class CapabilityPolicy(FrozenModel):
    tenant_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    grants: Mapping[str, tuple[Capability, ...]]
    manager_workers: Mapping[str, tuple[str, ...]]
    manager_artifact_types: Mapping[str, tuple[ArtifactType, ...]]
    manager_capabilities: Mapping[str, tuple[Capability, ...]]

    @field_validator(
        "grants", "manager_workers", "manager_artifact_types", "manager_capabilities"
    )
    @classmethod
    def immutable_policy_maps(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _deep_freeze(value)


class TaskDefinition(FrozenModel):
    task_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    assigned_agent_id: str = Field(min_length=1)
    expected_artifact_type: ArtifactType
    required_inputs: tuple[ArtifactType, ...] = ()
    dependencies: tuple[str, ...] = ()
    allowed_capabilities: tuple[Capability, ...] = ()
    max_attempts: int = Field(ge=1)
    timeout_ms: int = Field(ge=1)
    risk_tier: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    estimated_cost: float = Field(default=0, ge=0)
    deadline: datetime | None = None

    @field_validator("dependencies", "required_inputs", "allowed_capabilities")
    @classmethod
    def unique_values(cls, value: tuple[Any, ...]) -> tuple[Any, ...]:
        if len(value) != len(set(value)):
            raise ValueError("values must be unique")
        return value


class EvidenceRecord(FrozenModel):
    evidence_id: str
    source_id: str
    source_version: str
    tenant_id: str
    observed_at: datetime
    evidence_hash: str
    capability: Capability
    facts: Mapping[str, str]
    provenance_verified: bool = True

    @field_validator("facts")
    @classmethod
    def immutable_facts(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        return _deep_freeze(value)


class ArtifactEnvelope(FrozenModel):
    artifact_id: str
    task_id: str
    producer_agent_id: str
    tenant_id: str
    artifact_type: ArtifactType
    evidence_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    payload: Mapping[str, Any]
    artifact_hash: str
    created_at: datetime
    policy_version: str

    @field_validator("payload")
    @classmethod
    def immutable_payload(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _deep_freeze(value)


class TaskExecutionRecord(FrozenModel):
    logical_task_execution_id: str
    attempt_id: str
    task_id: str
    attempt_number: int = Field(ge=1)
    status: TaskStatus
    failure_code: FailureCode | None = None
    elapsed_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class CrewDefinition(FrozenModel):
    crew_id: str
    process: str = Field(pattern="^(sequential|hierarchical)$")
    task_ids: tuple[str, ...]
    worker_agent_ids: tuple[str, ...]
    manager_agent_id: str | None = None


class CrewBudget(FrozenModel):
    max_tasks: int = Field(ge=1)
    max_worker_calls: int = Field(ge=1)
    max_manager_calls: int = Field(ge=0)
    max_delegations: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    max_cost_usd: float = Field(ge=0)
    deadline_ms: int = Field(ge=1)
    max_depth: int = Field(default=2, ge=0)
    max_replans: int = Field(default=1, ge=0)


class ManagerDecision(FrozenModel):
    manager_id: str
    parent_task_id: str
    worker_agent_id: str
    proposed_task: TaskDefinition
    reason_code: str
    evidence_gap: str
    depth: int = Field(ge=1)
    estimated_cost: float = Field(ge=0)


class FlowEvent(FrozenModel):
    event_type: FlowEventType
    occurred_at: datetime
    task_id: str | None = None
    artifact_id: str | None = None
    detail: str = ""


class FlowState(MutableModel):
    tenant_id: str
    incident_id: str
    required_evidence_ids: tuple[str, ...]
    task_states: dict[str, TaskStatus]
    accepted_artifacts: dict[str, ArtifactEnvelope]
    evidence: dict[str, EvidenceRecord]
    budget: CrewBudget
    pending_review: bool
    terminal_status: RunStatus
    flow_version: str
    events: tuple[FlowEvent, ...] = ()
    worker_calls: int = 0
    manager_calls: int = 0
    delegations: int = 0
    total_cost_usd: float = 0
    elapsed_wall_clock_ms: int = 0
    executed_logical_ids: tuple[str, ...] = ()
    attempted_ids: tuple[str, ...] = ()
    delegation_signatures: tuple[str, ...] = ()
    replans: int = 0


class CrewMetrics(FrozenModel):
    architecture: str
    task_success: float = Field(ge=0, le=1)
    artifact_validity: float = Field(ge=0, le=1)
    required_evidence_recall: float = Field(ge=0, le=1)
    unsupported_claim_rate: float = Field(ge=0, le=1)
    manager_delegation_accuracy: float = Field(ge=0, le=1)
    duplicate_task_rate: float = Field(ge=0, le=1)
    recovery_rate: float = Field(ge=0, le=1)
    worker_calls: int = Field(ge=0)
    manager_calls: int = Field(ge=0)
    total_model_work_ms: int = Field(ge=0)
    wall_clock_latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    cost_per_successful_compliant_run: float | None = Field(default=None, ge=0)
    privileged_capability_exposure: int = Field(ge=0)
    completed: bool = False


def artifact_digest(artifact: ArtifactEnvelope | Mapping[str, Any]) -> str:
    """Hash the immutable artifact content, excluding the hash field itself."""
    data = artifact.model_dump(mode="json") if isinstance(artifact, ArtifactEnvelope) else dict(artifact)
    data.pop("artifact_hash", None)
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode()).hexdigest()


def evidence_digest(source_id: str, source_version: str, facts: Mapping[str, str]) -> str:
    encoded = json.dumps(
        {"source_id": source_id, "source_version": source_version, "facts": dict(facts)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode()).hexdigest()


def validate_task_graph(
    tasks: tuple[TaskDefinition, ...],
    *,
    available_inputs: tuple[ArtifactType, ...] = (),
) -> tuple[str, ...]:
    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise PolicyError("DUPLICATE_TASK_ID")
    for task in tasks:
        if task.task_id in task.dependencies:
            raise PolicyError("SELF_DEPENDENCY")
        missing = set(task.dependencies) - set(by_id)
        if missing:
            raise PolicyError(f"MISSING_DEPENDENCY:{','.join(sorted(missing))}")
        supplied = set(available_inputs)
        supplied.update(by_id[item].expected_artifact_type for item in task.dependencies)
        if not set(task.required_inputs).issubset(supplied):
            raise PolicyError(f"INVALID_INPUT_ARTIFACT_TYPE:{task.task_id}")

    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise PolicyError("TASK_CYCLE_DETECTED")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].dependencies:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)
        ordered.append(task_id)

    for task in tasks:
        visit(task.task_id)
    return tuple(ordered)


def ready_task_ids(
    tasks: tuple[TaskDefinition, ...], task_states: Mapping[str, TaskStatus]
) -> tuple[str, ...]:
    return tuple(
        task.task_id
        for task in tasks
        if task_states.get(task.task_id, TaskStatus.PENDING)
        in {TaskStatus.PENDING, TaskStatus.READY}
        and all(task_states.get(dep) is TaskStatus.SUCCEEDED for dep in task.dependencies)
    )


def authorize_task(
    agent: AgentDefinition,
    task: TaskDefinition,
    capability_policy: CapabilityPolicy,
    *,
    tenant_id: str,
) -> None:
    if tenant_id != capability_policy.tenant_id:
        raise PolicyError("TENANT_DENIED")
    grants = set(capability_policy.grants.get(agent.agent_id, ()))
    if not set(task.allowed_capabilities).issubset(grants):
        raise PolicyError("UNAUTHORIZED_TOOL")


def validate_artifact(
    artifact: ArtifactEnvelope,
    *,
    task: TaskDefinition,
    producer: AgentDefinition,
    state: FlowState,
    capability_policy: CapabilityPolicy,
) -> ArtifactEnvelope:
    if artifact.task_id != task.task_id:
        raise PolicyError("ARTIFACT_TASK_MISMATCH")
    if artifact.producer_agent_id != producer.agent_id or producer.agent_id != task.assigned_agent_id:
        raise PolicyError("ARTIFACT_PRODUCER_VIOLATION")
    if artifact.tenant_id != state.tenant_id:
        raise PolicyError("ARTIFACT_TENANT_VIOLATION")
    if artifact.artifact_type is not task.expected_artifact_type:
        raise PolicyError("ARTIFACT_TYPE_MISMATCH")
    if artifact.policy_version != capability_policy.policy_version:
        raise PolicyError("POLICY_VERSION_MISMATCH")
    if artifact.artifact_hash != artifact_digest(artifact):
        raise PolicyError("ARTIFACT_HASH_MISMATCH")
    if len(artifact.evidence_ids) != len(set(artifact.evidence_ids)):
        raise PolicyError("DUPLICATE_EVIDENCE_ID")

    records: list[EvidenceRecord] = []
    for evidence_id in artifact.evidence_ids:
        record = state.evidence.get(evidence_id)
        if record is None:
            raise PolicyError("UNKNOWN_EVIDENCE")
        if record.tenant_id != state.tenant_id:
            raise PolicyError("EVIDENCE_TENANT_VIOLATION")
        if not record.provenance_verified:
            raise PolicyError("UNVERIFIED_PROVENANCE")
        if record.evidence_hash != evidence_digest(record.source_id, record.source_version, record.facts):
            raise PolicyError("EVIDENCE_HASH_MISMATCH")
        records.append(record)
    if set(artifact.source_refs) != {record.source_id for record in records}:
        raise PolicyError("SOURCE_PROVENANCE_MISMATCH")

    authorize_task(producer, task, capability_policy, tenant_id=state.tenant_id)
    permitted = set(task.allowed_capabilities)
    if any(record.capability not in permitted for record in records):
        raise PolicyError("EVIDENCE_CAPABILITY_VIOLATION")

    artifact_evidence_ids = set(artifact.evidence_ids)
    records_by_id = {record.evidence_id: record for record in records}
    claims = artifact.payload.get("claims", ())
    if not isinstance(claims, (list, tuple)):
        raise PolicyError("INVALID_CLAIM_SCHEMA")
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise PolicyError("INVALID_CLAIM_SCHEMA")
        cited = set(claim.get("evidence_ids", ()))
        fact_keys = set(claim.get("fact_keys", ()))
        if not cited:
            raise PolicyError("CLAIM_EVIDENCE_REQUIRED")

        cited_records: list[EvidenceRecord] = []
        for evidence_id in cited:
            record = state.evidence.get(evidence_id)
            if record is None:
                raise PolicyError("UNKNOWN_CLAIM_EVIDENCE")
            if record.tenant_id != state.tenant_id:
                raise PolicyError("CLAIM_EVIDENCE_TENANT_VIOLATION")
            cited_records.append(record)
        if not cited.issubset(artifact_evidence_ids):
            raise PolicyError("CLAIM_EVIDENCE_NOT_IN_ARTIFACT")
        if any(record.evidence_id not in records_by_id for record in cited_records):
            raise PolicyError("CLAIM_EVIDENCE_NOT_IN_ARTIFACT")

        cited_facts = {key for record in cited_records for key in record.facts}
        if not fact_keys.issubset(cited_facts):
            raise PolicyError("UNSUPPORTED_CLAIM")
    return artifact


def retry_disposition(
    failure: FailureCode, *, attempt_number: int, max_attempts: int
) -> str:
    if failure in {FailureCode.AUTH_DENIED, FailureCode.POLICY_BLOCKED}:
        return "DO_NOT_RETRY"
    if failure is FailureCode.SOURCE_UNAVAILABLE:
        return "FALLBACK_OR_ESCALATE"
    if failure in {FailureCode.TIMEOUT, FailureCode.INVALID_ARTIFACT}:
        return "RETRY" if attempt_number < max_attempts else "EXHAUSTED"
    return "DO_NOT_RETRY"


def register_execution(
    state: FlowState,
    record: TaskExecutionRecord,
    *,
    task: TaskDefinition,
) -> None:
    if state.terminal_status is RunStatus.CANCELLED:
        raise PolicyError("RUN_CANCELLED")
    if record.attempt_id in state.attempted_ids:
        raise PolicyError("DUPLICATE_ATTEMPT")
    if record.logical_task_execution_id in state.executed_logical_ids:
        raise PolicyError("DUPLICATE_TASK_EXECUTION")
    if len(state.executed_logical_ids) >= state.budget.max_tasks:
        raise PolicyError("TASK_BUDGET_EXCEEDED")
    if state.worker_calls >= state.budget.max_worker_calls:
        raise PolicyError("WORKER_CALL_BUDGET_EXCEEDED")
    if record.task_id != task.task_id:
        raise PolicyError("TASK_EXECUTION_MISMATCH")
    allowed_attempts = min(task.max_attempts, state.budget.max_attempts)
    if record.attempt_number > allowed_attempts:
        raise PolicyError("ATTEMPT_BUDGET_EXCEEDED")
    if state.total_cost_usd + record.cost_usd > state.budget.max_cost_usd:
        raise PolicyError("COST_BUDGET_EXCEEDED")
    if state.elapsed_wall_clock_ms + record.elapsed_ms > state.budget.deadline_ms:
        raise PolicyError("DEADLINE_EXCEEDED")
    state.attempted_ids = (*state.attempted_ids, record.attempt_id)
    if record.status is TaskStatus.SUCCEEDED:
        state.executed_logical_ids = (*state.executed_logical_ids, record.logical_task_execution_id)
    state.worker_calls += 1
    state.total_cost_usd += record.cost_usd


def delegation_signature(decision: ManagerDecision) -> str:
    task = decision.proposed_task
    raw = (
        decision.worker_agent_id,
        task.expected_artifact_type.value,
        tuple(item.value for item in task.required_inputs),
        tuple(item.value for item in task.allowed_capabilities),
        decision.evidence_gap,
    )
    return sha256(repr(raw).encode()).hexdigest()


def validate_manager_decision(
    decision: ManagerDecision,
    *,
    state: FlowState,
    crew: CrewDefinition,
    capability_policy: CapabilityPolicy,
    known_task_ids: tuple[str, ...],
) -> DelegationDecision:
    """Validate one manager proposal.

    ``manager_calls`` accounts for an attempted model call once the manager and
    call budget are valid. ``delegations`` advances only after the proposal
    passes every later policy check.
    """
    if state.terminal_status is RunStatus.CANCELLED:
        raise PolicyError("RUN_CANCELLED")
    if crew.manager_agent_id != decision.manager_id:
        raise PolicyError("UNKNOWN_MANAGER")
    if state.manager_calls >= state.budget.max_manager_calls:
        raise PolicyError("MANAGER_CALL_BUDGET_EXCEEDED")
    state.manager_calls += 1
    allowed_parent_ids = {*known_task_ids, ROOT_DELEGATION_CONTEXT}
    if decision.parent_task_id not in allowed_parent_ids:
        raise PolicyError("MANAGER_PARENT_TASK_UNKNOWN")
    allowed_workers = capability_policy.manager_workers.get(decision.manager_id, ())
    if decision.worker_agent_id not in allowed_workers:
        raise PolicyError("MANAGER_UNKNOWN_WORKER")
    if decision.proposed_task.assigned_agent_id != decision.worker_agent_id:
        raise PolicyError("MANAGER_WORKER_MISMATCH")
    if decision.proposed_task.task_id in known_task_ids:
        raise PolicyError("MANAGER_DUPLICATE_TASK")
    allowed_types = capability_policy.manager_artifact_types.get(decision.manager_id, ())
    if decision.proposed_task.expected_artifact_type not in allowed_types:
        raise PolicyError("MANAGER_UNAUTHORIZED_TASK")
    allowed_capabilities = set(capability_policy.manager_capabilities.get(decision.manager_id, ()))
    if not set(decision.proposed_task.allowed_capabilities).issubset(allowed_capabilities):
        raise PolicyError("MANAGER_CAPABILITY_ESCALATION")
    if any(
        cap in {Capability.PRODUCTION_ROLLBACK, Capability.DATABASE_DELETE}
        for cap in decision.proposed_task.allowed_capabilities
    ):
        raise PolicyError("MANAGER_WRITE_DENIED")
    worker_capabilities = set(
        capability_policy.grants.get(decision.worker_agent_id, ())
    )
    if not set(decision.proposed_task.allowed_capabilities).issubset(
        worker_capabilities
    ):
        raise PolicyError("MANAGER_WORKER_CAPABILITY_MISMATCH")
    if decision.depth > state.budget.max_depth:
        raise PolicyError("MANAGER_MAX_DEPTH_EXCEEDED")
    signature = delegation_signature(decision)
    if signature in state.delegation_signatures:
        raise PolicyError("DELEGATION_STALLED")
    if state.delegations >= state.budget.max_delegations:
        raise PolicyError("MANAGER_MAX_DELEGATIONS_EXCEEDED")
    if state.replans >= state.budget.max_replans:
        raise PolicyError("MANAGER_MAX_REPLANS_EXCEEDED")
    if state.total_cost_usd + decision.estimated_cost > state.budget.max_cost_usd:
        raise PolicyError("COST_BUDGET_EXCEEDED")
    state.delegation_signatures = (*state.delegation_signatures, signature)
    state.delegations += 1
    state.replans += 1
    return DelegationDecision.ALLOW


_ALLOWED_EVENTS: Mapping[RunStatus, set[FlowEventType]] = {
    RunStatus.RUNNING: {
        FlowEventType.FLOW_STARTED,
        FlowEventType.TASK_READY,
        FlowEventType.CREW_STARTED,
        FlowEventType.TASK_SUCCEEDED,
        FlowEventType.TASK_FAILED,
        FlowEventType.ARTIFACT_ACCEPTED,
        FlowEventType.ARTIFACT_REJECTED,
        FlowEventType.MANAGER_DELEGATED,
        FlowEventType.REVIEW_REQUIRED,
        FlowEventType.COMPLETED,
        FlowEventType.ESCALATED,
        FlowEventType.CANCELLED,
    },
    RunStatus.COMPLETED: set(),
    RunStatus.ESCALATED: set(),
    RunStatus.CANCELLED: set(),
    RunStatus.BLOCKED: {FlowEventType.ESCALATED, FlowEventType.CANCELLED},
}


def apply_flow_event(state: FlowState, event: FlowEvent) -> None:
    if event.event_type not in _ALLOWED_EVENTS[state.terminal_status]:
        raise PolicyError("INVALID_FLOW_TRANSITION")
    if event.event_type is FlowEventType.CANCELLED:
        state.terminal_status = RunStatus.CANCELLED
        state.task_states = {
            key: TaskStatus.CANCELLED if value not in {TaskStatus.SUCCEEDED, TaskStatus.FAILED} else value
            for key, value in state.task_states.items()
        }
    elif event.event_type is FlowEventType.ESCALATED:
        state.terminal_status = RunStatus.ESCALATED
    elif event.event_type is FlowEventType.REVIEW_REQUIRED:
        state.pending_review = True
    elif event.event_type is FlowEventType.COMPLETED:
        validate_completion(state)
        state.terminal_status = RunStatus.COMPLETED
        state.pending_review = False
    state.events = (*state.events, event)


def assert_crew_may_start(state: FlowState) -> None:
    if state.terminal_status is RunStatus.CANCELLED:
        raise PolicyError("RUN_CANCELLED")
    if state.terminal_status is not RunStatus.RUNNING:
        raise PolicyError("RUN_NOT_ACTIVE")
    if state.worker_calls >= state.budget.max_worker_calls:
        raise PolicyError("WORKER_CALL_BUDGET_EXCEEDED")
    if state.total_cost_usd >= state.budget.max_cost_usd:
        raise PolicyError("COST_BUDGET_EXCEEDED")


def validate_completion(state: FlowState) -> None:
    required = {
        ArtifactType.HEALTH_FINDING,
        ArtifactType.LOG_FINDING,
        ArtifactType.DEPLOYMENT_FINDING,
        ArtifactType.CUSTOMER_IMPACT,
        ArtifactType.RUNBOOK_GUIDANCE,
        ArtifactType.INCIDENT_BRIEF,
        ArtifactType.REVIEW_DECISION,
    }
    types = {artifact.artifact_type for artifact in state.accepted_artifacts.values()}
    if not required.issubset(types):
        raise PolicyError("COMPLETION_MISSING_ARTIFACTS")
    covered_evidence = {
        evidence_id
        for artifact in state.accepted_artifacts.values()
        for evidence_id in artifact.evidence_ids
    }
    if not set(state.required_evidence_ids).issubset(covered_evidence):
        raise PolicyError("COMPLETION_EVIDENCE_GAP")
    reviews = [
        artifact
        for artifact in state.accepted_artifacts.values()
        if artifact.artifact_type is ArtifactType.REVIEW_DECISION
    ]
    if not reviews or reviews[-1].payload.get("decision") != "REVIEW_PASS":
        raise PolicyError("COMPLETION_REVIEW_NOT_PASSED")
    if any(status in {TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.RETRYABLE} for status in state.task_states.values()):
        raise PolicyError("COMPLETION_BLOCKING_TASK")
    if state.pending_review:
        raise PolicyError("COMPLETION_REVIEW_PENDING")


def authorize_production_action(*, review_decision: str, validated_approval: bool) -> bool:
    """Proposal review is deliberately separate from production approval."""
    if review_decision != "REVIEW_PASS":
        raise PolicyError("PRODUCTION_REVIEW_NOT_PASSED")
    if not validated_approval:
        raise PolicyError("PRODUCTION_APPROVAL_REQUIRED")
    return True


def architecture_gate(
    sequential: CrewMetrics,
    hierarchical: CrewMetrics,
    *,
    minimum_recovery_gain: float = 0.10,
    latency_sla_ms: int = 1_000,
    max_cost_usd: float,
) -> str:
    recovery_gain = hierarchical.recovery_rate - sequential.recovery_rate
    quality_gain = hierarchical.task_success - sequential.task_success
    safe = (
        hierarchical.unsupported_claim_rate <= sequential.unsupported_claim_rate
        and hierarchical.privileged_capability_exposure
        <= sequential.privileged_capability_exposure
    )
    within_bounds = (
        hierarchical.wall_clock_latency_ms <= latency_sla_ms
        and hierarchical.cost_usd <= max_cost_usd
    )
    return (
        "ACCEPT_HIERARCHY"
        if (recovery_gain >= minimum_recovery_gain or quality_gain >= minimum_recovery_gain)
        and safe
        and within_bounds
        else "KEEP_SEQUENTIAL"
    )
