from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentops_lab.loop_yourself import get_runbook, get_service_status, search_incidents


@dataclass
class FrameworkTraceEvent:
    kind: str
    name: str
    detail: dict[str, Any]


@dataclass
class FrameworkRun:
    final_output: str
    trace: list[FrameworkTraceEvent] = field(default_factory=list)
    framework_owns: list[str] = field(default_factory=list)


class OfflineAgentsSDKRuntime:
    """A tiny teaching double that mirrors the responsibilities of an agent SDK.

    This is not a replacement for the OpenAI Agents SDK. It exists so the lab
    remains runnable without credentials while learners compare what a framework
    packages around the manual loop.
    """

    def __init__(self, tools: dict[str, Callable[..., dict[str, Any]]]) -> None:
        self.tools = tools

    async def run(self, prompt: str) -> FrameworkRun:
        trace: list[FrameworkTraceEvent] = [
            FrameworkTraceEvent("session", "start", {"prompt": prompt}),
            FrameworkTraceEvent("model", "plan", {"decision": "collect checkout evidence before diagnosing"}),
        ]

        planned_calls = [
            ("get_service_status", {"service_name": "checkout"}),
            ("search_incidents", {"query": "active checkout payment eu europe failures"}),
            ("get_runbook", {"service_name": "checkout"}),
        ]
        observations = []

        for name, arguments in planned_calls:
            trace.append(FrameworkTraceEvent("tool_schema", name, {"arguments": arguments}))
            result = self.tools[name](**arguments)
            observations.append({"tool": name, "result": result})
            trace.append(FrameworkTraceEvent("tool_call", name, {"arguments": arguments, "result": result}))

        status = observations[0]["result"]
        incidents = observations[1]["result"]["matches"]
        active = [incident for incident in incidents if incident["status"] == "active"]
        runbook = observations[2]["result"]

        trace.append(FrameworkTraceEvent("guardrail", "evidence_required", {"passed": bool(status["found"] and active and runbook["found"])}))

        if status["found"] and active and runbook["found"]:
            incident = active[0]
            final = (
                f"Checkout is degraded and an active incident ({incident['id']}) matches payment failures. "
                "Support should acknowledge impact for European checkout users, prioritize SLA customers, "
                "use the fallback payment path where eligible, and avoid claiming root cause until deployment and regional logs are confirmed."
            )
        else:
            final = "The evidence is not sufficient to confirm an active checkout incident. Escalate to the checkout owner."

        trace.append(FrameworkTraceEvent("model", "final", {"output": final}))
        return FrameworkRun(
            final_output=final,
            trace=trace,
            framework_owns=[
                "tool schemas",
                "turn loop",
                "tool dispatch",
                "message state",
                "stopping behavior",
                "tracing spans",
                "session continuity",
            ],
        )


TOOLS = {
    "get_service_status": get_service_status,
    "search_incidents": search_incidents,
    "get_runbook": get_runbook,
}


def compare_manual_and_framework() -> dict[str, Any]:
    from agentops_lab.loop_yourself import run_manual_loop

    prompt = "European users report checkout failures."
    manual = run_manual_loop(prompt)
    runtime = OfflineAgentsSDKRuntime(TOOLS)
    framework = asyncio.run(runtime.run(prompt))
    return {
        "manual": {
            "final_output": manual.final_answer,
            "steps": manual.steps,
            "tool_calls": manual.tool_calls,
            "owned_by_application": ["loop", "tool dispatch", "messages", "budget checks", "trace formatting"],
        },
        "framework": {
            "final_output": framework.final_output,
            "trace": [event.__dict__ for event in framework.trace],
            "framework_owns": framework.framework_owns,
        },
    }


if __name__ == "__main__":
    comparison = compare_manual_and_framework()
    print("Manual implementation")
    print(json.dumps(comparison["manual"], indent=2))
    print("\nFramework-style implementation")
    print(json.dumps(comparison["framework"], indent=2))
