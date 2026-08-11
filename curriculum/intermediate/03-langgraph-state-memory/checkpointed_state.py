"""Checkpoint a run so a failed step can resume without repeating work."""
from dataclasses import dataclass, field


@dataclass
class RunState:
    pending: list[str]
    completed: list[str] = field(default_factory=list)
    failed: str | None = None

    def checkpoint(self) -> dict:
        return {"pending": self.pending[:], "completed": self.completed[:], "failed": self.failed}

    @classmethod
    def resume(cls, checkpoint: dict) -> "RunState":
        return cls(checkpoint["pending"], checkpoint["completed"], checkpoint["failed"])


def execute(state: RunState, fail_on: str | None = None) -> dict:
    while state.pending:
        task = state.pending.pop(0)
        if task == fail_on:
            state.failed = task
            return state.checkpoint()
        state.completed.append(task)
    return state.checkpoint()


if __name__ == "__main__":
    saved = execute(RunState(["collect", "validate", "publish"]), fail_on="validate")
    print("checkpoint:", saved)
    resumed = execute(RunState.resume(saved))
    print("resumed:", resumed)
