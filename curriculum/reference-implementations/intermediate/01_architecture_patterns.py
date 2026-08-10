"""Compare bounded agent architecture patterns with the same task."""
from dataclasses import dataclass


@dataclass
class Result:
    pattern: str
    steps: list[str]
    cost: int


def routed(task: str) -> Result:
    specialist = "billing" if "invoice" in task else "general"
    return Result("routing", [f"route:{specialist}", "answer"], 2)


def parallel(task: str) -> Result:
    return Result("parallelization", ["research", "critique", "merge"], 3)


def evaluator_optimizer(task: str) -> Result:
    return Result("evaluator-optimizer", ["draft", "evaluate", "revise"], 3)


if __name__ == "__main__":
    for run in (routed("check an invoice"), parallel("compare three options"), evaluator_optimizer("write a policy summary")):
        print(run)
