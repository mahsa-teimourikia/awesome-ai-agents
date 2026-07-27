"""A dependency-free manager/worker team with explicit agent contracts."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    role: str
    question: str


def worker(task: Task) -> dict:
    return {"role": task.role, "finding": f"{task.role} evidence for: {task.question}", "source_ids": [task.role + "-1"]}


def manager(question: str) -> dict:
    tasks = [Task("researcher", question), Task("critic", question)]
    findings = [worker(task) for task in tasks]
    sources = [source for finding in findings for source in finding["source_ids"]]
    return {"answer": "synthesized from specialist findings", "sources": sources, "workers": findings}


if __name__ == "__main__":
    print(manager("what are the safety trade-offs?"))
