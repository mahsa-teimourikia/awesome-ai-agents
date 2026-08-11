"""Agent-loop foundations plus the runnable checkout investigation harness."""
from dataclasses import dataclass, field
from pathlib import Path
import runpy
import sys


@dataclass
class FoundationState:
    """Minimal explicit state machine used before the richer tool loop."""
    goal: str
    observations: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    remaining_steps: int = 4
    terminal_reason: str | None = None


def run_foundation_loop(goal: str) -> FoundationState:
    """Run Observe → Decide → Act with an application-owned step budget."""
    state = FoundationState(goal=goal)
    while state.remaining_steps and state.terminal_reason is None:
        action = "search_policy" if not state.observations else "complete"
        state.transitions.append(f"decide:{action}")
        if action == "search_policy":
            state.observations.append("policy evidence retrieved")
            state.transitions.append("observe:policy evidence retrieved")
        else:
            state.terminal_reason = "success"
        state.remaining_steps -= 1
    if state.terminal_reason is None:
        state.terminal_reason = "step_budget_exhausted"
    return state


# The scenario harness is intentionally imported after the tiny loop, so learners
# can see the same control boundary scale from a state machine to tool calls.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone"))
from agentops_lab.loop_yourself import *  # noqa: F401,F403

if __name__ == "__main__":
    print(run_foundation_loop("find evidence for a product policy"))
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone" / "agentops_lab" / "loop_yourself.py"), run_name="__main__")
