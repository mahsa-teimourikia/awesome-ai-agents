from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass
class TrajectoryProfile:
    name: str
    trajectory: list[str]
    llm_calls: int
    tool_calls: int
    latency_seconds: float
    cost: float
    success: bool

    @property
    def trajectory_length(self) -> int:
        return len(self.trajectory)


INEFFICIENT = TrajectoryProfile(
    name="deliberately inefficient agent",
    trajectory=[
        "plan",
        "search_incidents",
        "think",
        "query_health",
        "think",
        "search_incidents",
        "retrieve_runbook",
        "think",
        "query_logs",
        "reflection",
        "query_logs",
        "answer",
    ],
    llm_calls=9,
    tool_calls=6,
    latency_seconds=14.2,
    cost=0.041,
    success=True,
)


OPTIMIZED = TrajectoryProfile(
    name="short reliable trajectory",
    trajectory=["query_health", "query_logs", "retrieve_runbook", "answer"],
    llm_calls=3,
    tool_calls=3,
    latency_seconds=5.1,
    cost=0.012,
    success=True,
)


def efficiency_score(profile: TrajectoryProfile) -> float:
    if not profile.success:
        return 0.0
    denominator = profile.latency_seconds + (profile.cost * 100) + profile.trajectory_length
    return round(1 / denominator, 4)


def compare_profiles(before: TrajectoryProfile = INEFFICIENT, after: TrajectoryProfile = OPTIMIZED) -> dict:
    return {
        "before": {
            "name": before.name,
            "llm_calls": before.llm_calls,
            "tool_calls": before.tool_calls,
            "latency_seconds": before.latency_seconds,
            "cost": before.cost,
            "success": before.success,
            "trajectory_length": before.trajectory_length,
            "efficiency_score": efficiency_score(before),
            "trajectory": before.trajectory,
        },
        "after": {
            "name": after.name,
            "llm_calls": after.llm_calls,
            "tool_calls": after.tool_calls,
            "latency_seconds": after.latency_seconds,
            "cost": after.cost,
            "success": after.success,
            "trajectory_length": after.trajectory_length,
            "efficiency_score": efficiency_score(after),
            "trajectory": after.trajectory,
        },
        "improvement": {
            "llm_calls_saved": before.llm_calls - after.llm_calls,
            "tool_calls_saved": before.tool_calls - after.tool_calls,
            "latency_seconds_saved": round(before.latency_seconds - after.latency_seconds, 1),
            "cost_saved": round(before.cost - after.cost, 3),
            "trajectory_steps_saved": before.trajectory_length - after.trajectory_length,
        },
    }


def optimization_rules() -> list[str]:
    return [
        "Merge planning and first evidence request when the next tool is obvious.",
        "Do not repeat incident search unless new evidence changes the query.",
        "Collect high-signal evidence first: health, logs, runbook.",
        "Stop reflection loops when the recommendation is already supported.",
        "Optimize cost per successful task, not cost per model call.",
    ]


if __name__ == "__main__":
    print(compare_profiles())
    print(optimization_rules())
