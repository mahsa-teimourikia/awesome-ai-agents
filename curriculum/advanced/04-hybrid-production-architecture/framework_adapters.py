"""Optional framework adapters for the framework-neutral Course 04 core.

The application admits an ``ExecutionContract`` before either framework sees
the request. These helpers only translate that bounded contract into framework
objects; they do not delegate policy, authorization, budgets, or completion.
"""

from __future__ import annotations

from importlib import metadata, util
from typing import Any, TypedDict

from policy import ArchitectureType, ExecutionContract


TESTED_LANGGRAPH_VERSION = "1.2.11"
TESTED_OPENAI_AGENTS_VERSION = "0.20.0"
COMPATIBLE_LANGGRAPH_RANGE = ">=1.2.0,<2.0.0"
COMPATIBLE_OPENAI_AGENTS_RANGE = ">=0.20.0,<0.21.0"


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def adapter_status() -> dict[str, dict[str, object]]:
    """Report optional installation state without importing either framework."""
    return {
        "langgraph": {
            "installed": util.find_spec("langgraph") is not None,
            "installed_version": _version("langgraph"),
            "tested_version": TESTED_LANGGRAPH_VERSION,
            "compatible_range": COMPATIBLE_LANGGRAPH_RANGE,
            "credentials_required_to_instantiate": False,
        },
        "openai_agents": {
            "installed": util.find_spec("agents") is not None,
            "installed_version": _version("openai-agents"),
            "tested_version": TESTED_OPENAI_AGENTS_VERSION,
            "compatible_range": COMPATIBLE_OPENAI_AGENTS_RANGE,
            "credentials_required_to_instantiate": False,
        },
    }


class WorkflowState(TypedDict):
    request_id: str
    stage: str
    policy_events: list[str]


def build_langgraph_workflow_adapter(contract: ExecutionContract) -> Any:
    """Build a credential-free graph from an already-admitted workflow contract."""
    if util.find_spec("langgraph") is None:
        raise RuntimeError("Install the frameworks extra to use the LangGraph adapter.")
    if contract.architecture is not ArchitectureType.DETERMINISTIC_WORKFLOW:
        raise ValueError("LangGraph example requires a deterministic-workflow contract")

    from langgraph.graph import END, START, StateGraph

    def send_otp(state: WorkflowState) -> WorkflowState:
        return {
            **state,
            "stage": "WAITING_FOR_OTP",
            "policy_events": [*state.get("policy_events", []), "OTP_SENT"],
        }

    graph = StateGraph(WorkflowState)
    graph.add_node("send_otp", send_otp)
    graph.add_edge(START, "send_otp")
    graph.add_edge("send_otp", END)
    return graph.compile()


def build_openai_agent_adapter(contract: ExecutionContract) -> Any:
    """Build an Agent object without making a model call or reading credentials."""
    if util.find_spec("agents") is None:
        raise RuntimeError(
            "Install the frameworks extra to use the OpenAI Agents SDK adapter."
        )
    if contract.architecture is not ArchitectureType.BOUNDED_SINGLE_AGENT:
        raise ValueError("Agents SDK example requires a bounded-agent contract")

    from agents import Agent

    capabilities = ", ".join(item.value for item in contract.allowed_capabilities)
    return Agent(
        name="Northstar bounded incident analyst",
        instructions=(
            "Return a candidate diagnosis grounded in the supplied evidence. "
            f"Allowed capabilities: {capabilities}. "
            f"Maximum model calls: {contract.max_model_calls}; maximum tool calls: "
            f"{contract.max_tool_calls}. Never execute actions or widen this contract."
        ),
        tools=[],
    )
