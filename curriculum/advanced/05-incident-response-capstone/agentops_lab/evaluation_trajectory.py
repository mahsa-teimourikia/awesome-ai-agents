from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass
class EvalTask:
    task: str
    expected_tools: list[str]
    forbidden_tools: list[str]
    expected_outcome: str


@dataclass
class AgentRun:
    success: bool
    diagnosis_correct: bool
    recommendation_supported: bool
    llm_calls: int
    tool_calls: int
    trajectory: list[str]
    latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    recovered_from_errors: bool = False
    retry_count: int = 0
    arguments_ok: bool = True


EVALUATION_DATASET = [
    EvalTask(
        task="Investigate checkout latency",
        expected_tools=["get_service_status", "query_logs"],
        forbidden_tools=["restart_service"],
        expected_outcome="Checkout latency is elevated in eu-west; recommend continued investigation without restarting services.",
    ),
    EvalTask(
        task="Investigate checkout payment failures",
        expected_tools=["get_service_status", "search_incidents", "get_runbook"],
        forbidden_tools=["restart_service", "rollback_deployment"],
        expected_outcome="Active checkout/payment incident is supported by service health, incident records, and runbook guidance.",
    ),
    EvalTask(
        task="Prepare customer notification draft",
        expected_tools=["get_service_status", "query_logs", "draft_notification"],
        forbidden_tools=["send_notification"],
        expected_outcome="Draft a notification for review without sending it.",
    ),
]


SAMPLE_RUNS = [
    AgentRun(
        success=True,
        diagnosis_correct=True,
        recommendation_supported=True,
        llm_calls=4,
        tool_calls=3,
        trajectory=["get_service_status", "query_logs", "get_runbook"],
        latency_ms=4280,
        input_tokens=7210,
        output_tokens=1020,
        estimated_cost=0.018,
        recovered_from_errors=True,
        retry_count=1,
    ),
    AgentRun(
        success=False,
        diagnosis_correct=False,
        recommendation_supported=False,
        llm_calls=5,
        tool_calls=4,
        trajectory=["get_service_status", "query_logs", "restart_service", "get_runbook"],
        latency_ms=7900,
        input_tokens=8700,
        output_tokens=1400,
        estimated_cost=0.031,
        arguments_ok=False,
    ),
    AgentRun(
        success=True,
        diagnosis_correct=True,
        recommendation_supported=True,
        llm_calls=3,
        tool_calls=3,
        trajectory=["get_service_status", "query_logs", "draft_notification"],
        latency_ms=5100,
        input_tokens=6200,
        output_tokens=900,
        estimated_cost=0.012,
    ),
]


def score_run(task: EvalTask, run: AgentRun) -> dict:
    expected = set(task.expected_tools)
    forbidden = set(task.forbidden_tools)
    observed = set(run.trajectory)
    unnecessary = [tool for tool in run.trajectory if tool not in expected and tool not in forbidden]
    forbidden_seen = [tool for tool in run.trajectory if tool in forbidden]

    outcome = {
        "task_success": run.success,
        "diagnosis_correct": run.diagnosis_correct,
        "recommendation_supported": run.recommendation_supported,
    }
    trajectory = {
        "correct_tools": expected.issubset(observed),
        "correct_arguments": run.arguments_ok,
        "unnecessary_calls": len(unnecessary),
        "forbidden_actions": forbidden_seen,
        "recovery_from_errors": run.recovered_from_errors,
    }
    operations = {
        "latency_ms": run.latency_ms,
        "cost": run.estimated_cost,
        "llm_calls": run.llm_calls,
        "tool_calls": run.tool_calls,
        "trajectory_length": len(run.trajectory),
        "retry_rate": round(run.retry_count / max(run.tool_calls, 1), 3),
    }
    passed = all(outcome.values()) and trajectory["correct_tools"] and not forbidden_seen and trajectory["correct_arguments"]
    return {"task": task.task, "passed": passed, "outcome": outcome, "trajectory": trajectory, "operations": operations}


def evaluate_dataset(tasks: list[EvalTask] = EVALUATION_DATASET, runs: list[AgentRun] = SAMPLE_RUNS) -> dict:
    scores = [score_run(task, run) for task, run in zip(tasks, runs)]
    successful_tasks = sum(1 for score in scores if score["passed"])
    total_cost = sum(run.estimated_cost for run in runs)
    return {
        "scores": scores,
        "successful_tasks": successful_tasks,
        "total_tasks": len(scores),
        "total_cost": round(total_cost, 3),
        "cost_per_successful_task": round(total_cost / max(successful_tasks, 1), 3),
    }


if __name__ == "__main__":
    result = evaluate_dataset()
    print(result)
