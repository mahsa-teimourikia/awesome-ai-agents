"""Optional CrewAI 1.15.20 adapter for the framework-neutral Course 03 core.

The adapter is intentionally thin. CrewAI receives already-admitted tasks and
its output is converted back into an application artifact before policy
validation. Importing this module does not require CrewAI.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lab import agent, build_agents, build_artifact, build_capability_policy, build_tasks
from policy import ArtifactEnvelope, FlowState, assert_crew_may_start, validate_artifact


TESTED_CREWAI_VERSION = "1.15.20"


class CrewAIClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    text: str
    evidence_ids: list[str] = Field(min_length=1)
    fact_keys: list[str] = Field(min_length=1)


class CrewAIArtifactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[CrewAIClaim]
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
    """Map admitted domain definitions to real CrewAI Agent/Task/Crew objects."""
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


def validate_adapter_payload(
    payload: CrewAIArtifactPayload | dict[str, Any],
    *,
    task_id: str,
    state: FlowState,
) -> ArtifactEnvelope:
    """Apply the same policy used by the deterministic core to CrewAI output."""
    parsed = (
        payload
        if isinstance(payload, CrewAIArtifactPayload)
        else CrewAIArtifactPayload.model_validate(payload)
    )
    envelope = build_artifact(task_id, payload=parsed.model_dump(exclude_none=True))
    return validate_artifact(
        envelope,
        task=next(item for item in build_tasks() if item.task_id == task_id),
        producer=agent(envelope.producer_agent_id),
        state=state,
        capability_policy=build_capability_policy(),
    )


def run_live_sequential_if_configured() -> str:
    """Optional paid path; it never runs without explicit environment setup."""
    if not os.getenv("OPENAI_API_KEY"):
        return "SKIPPED_NO_OPENAI_API_KEY"
    crewai = _require_crewai()
    crew = build_sequential_crew(llm=crewai.LLM(model="openai/gpt-4.1-mini"))
    crew.kickoff(inputs={"incident_id": "inc-eu-checkout-1842"})
    return "LIVE_RUN_COMPLETED_OUTPUT_REQUIRES_POLICY_VALIDATION"
