"""A dependency-free agent loop with explicit budgets and stop conditions."""
from dataclasses import dataclass, field


@dataclass
class State:
    goal: str
    steps: list[str] = field(default_factory=list)
    budget: int = 4
    done: bool = False


def decide(state: State) -> str:
    """A deterministic stand-in for a model decision."""
    if "evidence" not in state.steps:
        return "search"
    return "finish"


def act(state: State, action: str) -> None:
    if action == "search":
        state.steps.append("evidence")
    elif action == "finish":
        state.done = True
    else:
        raise ValueError(f"unknown action: {action}")


def run(goal: str) -> State:
    state = State(goal=goal)
    while not state.done and state.budget:
        action = decide(state)
        print(f"decision={action!r} remaining_budget={state.budget}")
        act(state, action)
        state.budget -= 1
    if not state.done:
        raise RuntimeError("agent stopped without meeting its goal")
    return state


if __name__ == "__main__":
    result = run("find evidence for a product policy")
    print("completed:", result.steps)
