"""Optional CrewAI 1.15.20 adapter for the framework-neutral Course 03 core.

The adapter is intentionally thin. CrewAI receives already-admitted tasks and
its output is converted back into an application artifact before policy
validation. Importing this module does not require CrewAI.
"""

from __future__ import annotations

import importlib.util
import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lab import (
    agent,
    build_agents,
    build_artifact,
    build_capability_policy,
    build_flow_state,
    build_tasks,
)
from policy import (
    ArtifactEnvelope,
    FlowState,
    TaskStatus,
    assert_crew_may_start,
    validate_artifact,
)


TESTED_CREWAI_VERSION = "1.15.20"


class CrewAIClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    text: str
    evidence_ids: list[str] = Field(min_length=1)
    fact_keys: list[str] = Field(min_length=1)


class CrewAIArtifactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[CrewAIClaim] = Field(min_length=1)
    decision: str | None = None
    reviewed_task_id: str | None = None


def adapter_status() -> dict[str, object]:
    return {
        "tested_version": TESTED_CREWAI_VERSION,
        "installed": importlib.util.find_spec("crewai") is not None,
        "core_requires_credentials": False,
        "live_example_enabled": bool(os.getenv("OPENAI_API_KEY")),
    }


def _require_crewai() -> Any:
    if importlib.util.find_spec("crewai") is None:
        raise RuntimeError(
            "Install the advanced extra to use the optional adapter: "
            "uv sync --extra advanced"
        )
    import crewai

    return crewai


def build_offline_replay_llm() -> Any:
    """Return a no-network BaseLLM used only to instantiate/test the adapter."""
    _require_crewai()
    from crewai.llms.base_llm import BaseLLM

    class OfflineReplayLLM(BaseLLM):
        def call(
            self,
            messages: Any,
            tools: Any = None,
            callbacks: Any = None,
            available_functions: Any = None,
            from_task: Any = None,
            from_agent: Any = None,
            response_model: Any = None,
        ) -> str:
            return '{"claims": []}'

    return OfflineReplayLLM(model="offline-course03-replay", provider="local")


def build_sequential_crew(*, llm: Any | None = None) -> Any:
    """Build a direct ``Task.context`` chain for framework API demonstration.

    This construction is useful for inspecting CrewAI's dependency API, but its
    raw context chain is not the authoritative governed application-state path.
    """
    crewai = _require_crewai()
    llm = llm or build_offline_replay_llm()
    crew_agents: dict[str, Any] = {}
    for definition in build_agents():
        if definition.agent_id == "manager":
            continue
        crew_agents[definition.agent_id] = crewai.Agent(
            role=definition.role.value,
            goal=definition.goal,
            backstory=definition.backstory,
            tools=[],
            allow_delegation=False,
            llm=llm,
            verbose=False,
        )

    crew_tasks: dict[str, Any] = {}
    for definition in build_tasks():
        contexts = [crew_tasks[item] for item in definition.dependencies]
        crew_tasks[definition.task_id] = crewai.Task(
            name=definition.task_id,
            description=definition.objective,
            expected_output=(
                "A JSON object matching CrewAIArtifactPayload. This is a candidate "
                "result and remains subject to application policy validation."
            ),
            output_pydantic=CrewAIArtifactPayload,
            context=contexts,
            agent=crew_agents[definition.assigned_agent_id],
        )
    return crewai.Crew(
        name="northstar-contract-driven-sequential",
        agents=list(crew_agents.values()),
        tasks=list(crew_tasks.values()),
        process=crewai.Process.sequential,
        verbose=False,
    )


def _validated_context(task_id: str, state: FlowState) -> str:
    """Project scoped source records plus policy-accepted dependency artifacts."""
    definition = next(item for item in build_tasks() if item.task_id == task_id)
    accepted_dependencies = [
        artifact.model_dump(mode="json")
        for artifact in state.accepted_artifacts.values()
        if artifact.task_id in definition.dependencies
    ]
    scoped_evidence = [
        record.model_dump(mode="json")
        for record in state.evidence.values()
        if record.capability in definition.allowed_capabilities
    ]
    return json.dumps(
        {
            "accepted_dependency_artifacts": accepted_dependencies,
            "scoped_source_evidence": scoped_evidence,
        },
        sort_keys=True,
    )


def build_bounded_task_crew(
    task_id: str,
    state: FlowState,
    *,
    llm: Any | None = None,
) -> Any:
    """Build one bounded task from application-validated dependency context."""
    crewai = _require_crewai()
    llm = llm or build_offline_replay_llm()
    definition = next(item for item in build_tasks() if item.task_id == task_id)
    worker = agent(definition.assigned_agent_id)
    crew_agent = crewai.Agent(
        role=worker.role.value,
        goal=worker.goal,
        backstory=worker.backstory,
        tools=[],
        allow_delegation=False,
        llm=llm,
        verbose=False,
    )
    crew_task = crewai.Task(
        name=definition.task_id,
        description=(
            f"{definition.objective}\n"
            "Use only this application-validated dependency context: "
            f"{_validated_context(task_id, state)}"
        ),
        expected_output=(
            "A JSON object matching CrewAIArtifactPayload. The application will "
            "independently validate and admit or reject it."
        ),
        output_pydantic=CrewAIArtifactPayload,
        agent=crew_agent,
    )
    return crewai.Crew(
        name=f"northstar-bounded-{task_id}",
        agents=[crew_agent],
        tasks=[crew_task],
        process=crewai.Process.sequential,
        verbose=False,
    )


def build_hierarchical_crew(*, llm: Any | None = None) -> Any:
    """Build the measured hierarchical variant with an explicit manager agent."""
    crewai = _require_crewai()
    llm = llm or build_offline_replay_llm()
    sequential = build_sequential_crew(llm=llm)
    manager_definition = agent("manager")
    manager = crewai.Agent(
        role=manager_definition.role.value,
        goal=manager_definition.goal,
        backstory=manager_definition.backstory,
        tools=[],
        allow_delegation=True,
        llm=llm,
        verbose=False,
    )
    return crewai.Crew(
        name="northstar-bounded-hierarchical",
        agents=sequential.agents,
        tasks=sequential.tasks,
        process=crewai.Process.hierarchical,
        manager_agent=manager,
        verbose=False,
    )


def build_flow_adapter(state: FlowState) -> Any:
    """Map application FlowState to current CrewAI start/router/listen APIs."""
    _require_crewai()
    from crewai.flow.flow import Flow, listen, router, start

    class NorthstarFlow(Flow[FlowState]):
        @start()
        def admit(self) -> str:
            assert_crew_may_start(self.state)
            return "investigate"

        @router(admit)
        def choose_crew(self, route: str) -> str:
            return route

        @listen("investigate")
        def investigation_checkpoint(self) -> str:
            return "INVESTIGATION_CREW_ADMITTED"

    return NorthstarFlow(initial_state=state)


def _parse_crewai_payload(raw_output: Any) -> CrewAIArtifactPayload:
    if isinstance(raw_output, CrewAIArtifactPayload):
        return raw_output
    tasks_output = getattr(raw_output, "tasks_output", None)
    if tasks_output:
        if len(tasks_output) != 1:
            raise ValueError("admission requires one bounded CrewAI task output")
        return _parse_crewai_payload(tasks_output[0])
    pydantic_output = getattr(raw_output, "pydantic", None)
    if pydantic_output is not None:
        return CrewAIArtifactPayload.model_validate(pydantic_output)
    json_output = getattr(raw_output, "json_dict", None)
    if json_output is not None:
        return CrewAIArtifactPayload.model_validate(json_output)
    raw_text = getattr(raw_output, "raw", raw_output)
    if isinstance(raw_text, str):
        return CrewAIArtifactPayload.model_validate_json(raw_text)
    return CrewAIArtifactPayload.model_validate(raw_text)


def admit_crewai_output(
    raw_output: Any,
    *,
    task_id: str,
    state: FlowState,
) -> ArtifactEnvelope:
    """Parse, validate, and admit one CrewAI candidate into application state."""
    parsed = _parse_crewai_payload(raw_output)
    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id
            for claim in parsed.claims
            for evidence_id in claim.evidence_ids
        )
    )
    envelope = build_artifact(
        task_id,
        payload=parsed.model_dump(exclude_none=True),
        evidence_ids=evidence_ids,
    )
    accepted = validate_artifact(
        envelope,
        task=next(item for item in build_tasks() if item.task_id == task_id),
        producer=agent(envelope.producer_agent_id),
        state=state,
        capability_policy=build_capability_policy(),
    )
    state.accepted_artifacts = {
        **state.accepted_artifacts,
        accepted.artifact_id: accepted,
    }
    state.task_states[task_id] = TaskStatus.SUCCEEDED
    return accepted


def run_live_sequential_if_configured() -> FlowState | str:
    """Optional paid path; it never runs without explicit environment setup."""
    if not os.getenv("OPENAI_API_KEY"):
        return "SKIPPED_NO_OPENAI_API_KEY"
    crewai = _require_crewai()
    llm = crewai.LLM(model="openai/gpt-4.1-mini")
    state = build_flow_state()
    for definition in build_tasks():
        assert_crew_may_start(state)
        crew = build_bounded_task_crew(definition.task_id, state, llm=llm)
        result = crew.kickoff(inputs={"incident_id": state.incident_id})
        admit_crewai_output(result, task_id=definition.task_id, state=state)
    return state
