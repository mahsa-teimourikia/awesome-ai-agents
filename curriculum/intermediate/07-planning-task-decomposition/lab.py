"""A deterministic planning harness for the Adaptive RAG research-agent lesson.

The lesson intentionally uses a small in-memory source library.  It lets learners
inspect decomposition, DAG scheduling, checkpoints, and replanning without an API
key or a live-search dependency.  A production planner can replace
``initial_plan`` and ``execute_task`` only after preserving the validation and
policy boundaries shown here.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Task:
    """A planner proposal, not an executable instruction by itself."""

    id: str
    title: str
    objective: str
    depends_on: tuple[str, ...] = ()
    kind: str = "retrieve"
    tool_scope: tuple[str, ...] = ("source_library",)
    attempt_limit: int = 1
    milestone: bool = False


@dataclass(frozen=True)
class Constraints:
    required_sections: tuple[str, ...] = (
        "what adaptive RAG changes",
        "routing strategies",
        "evaluation and trade-offs",
    )
    allowed_tools: tuple[str, ...] = ("source_library", "compare", "synthesize")
    max_tasks: int = 10
    max_replans: int = 2
    max_attempts_per_task: int = 2


@dataclass
class PlanState:
    goal: str
    constraints: Constraints = field(default_factory=Constraints)
    tasks: dict[str, Task] = field(default_factory=dict)
    status: dict[str, TaskStatus] = field(default_factory=dict)
    findings: dict[str, str] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events: list[str] = field(default_factory=list)
    replan_count: int = 0


SOURCE_LIBRARY = {
    "adaptive-rag-paper": {
        "title": "Adaptive-RAG: Learning to Adapt Retrieval-Augmented LLMs through Question Complexity",
        "claim": "Adaptive-RAG routes questions among no retrieval, one-step retrieval, and iterative retrieval according to predicted complexity.",
        "url": "https://arxiv.org/abs/2403.14403",
    },
    "rag-foundation": {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "claim": "RAG combines parametric generation with non-parametric retrieved evidence; retrieval quality and provenance matter to the final answer.",
        "url": "https://arxiv.org/abs/2005.11401",
    },
    "workflow-guidance": {
        "title": "LangGraph workflows and agents guide",
        "claim": "A workflow uses predetermined code paths, while an agent can choose a dynamic process and tool usage; both need observable state and explicit boundaries.",
        "url": "https://docs.langchain.com/oss/python/langgraph/workflows-agents",
    },
    "adaptive-rag-survey": {
        "title": "Adaptive retrieval follow-up source",
        "claim": "Adaptive retrieval is a policy decision: its value must be evaluated against accuracy, latency, retrieval cost, and abstention behavior for the task distribution.",
        "url": "https://arxiv.org/abs/2403.14403",
    },
}


def initial_plan() -> list[Task]:
    """Return a hierarchical plan: evidence tasks feed a comparison and report."""

    return [
        Task("scope", "Define report contract", "Fix audience, required sections, citation policy, and budget.", kind="scope", milestone=True),
        Task("adaptive-paper", "Read Adaptive-RAG primary source", "Extract routing modes, classifier role, and stated trade-offs.", kind="retrieve"),
        Task("rag-foundation", "Read RAG foundation", "Separate fixed RAG foundations from adaptive routing claims.", kind="retrieve"),
        Task("implementation-guidance", "Read workflow guidance", "Map routing to a controlled implementation topology.", kind="retrieve"),
        Task(
            "compare",
            "Compare routing strategies",
            "Contrast no retrieval, one-shot RAG, and iterative retrieval using source-backed claims.",
            ("adaptive-paper", "rag-foundation", "implementation-guidance"),
            kind="compare",
            tool_scope=("compare",),
        ),
        Task(
            "checkpoint",
            "Evidence and constraint checkpoint",
            "Check coverage, source provenance, and unresolved conflicts before synthesis.",
            ("scope", "compare"),
            kind="evaluate",
            tool_scope=("compare",),
            milestone=True,
        ),
        Task(
            "report",
            "Produce technical report",
            "Synthesize a concise, cited report without inventing unsupported claims.",
            ("checkpoint",),
            kind="synthesize",
            tool_scope=("synthesize",),
            milestone=True,
        ),
    ]


def validate_plan(tasks: Iterable[Task], constraints: Constraints) -> list[str]:
    """Reject unsafe or unschedulable planner output before execution."""

    task_list = list(tasks)
    errors: list[str] = []
    ids = [task.id for task in task_list]
    if len(ids) != len(set(ids)):
        errors.append("Task IDs must be unique.")
    if len(task_list) > constraints.max_tasks:
        errors.append(f"Plan exceeds max_tasks={constraints.max_tasks}.")
    known = set(ids)
    for task in task_list:
        unknown = set(task.depends_on) - known
        if unknown:
            errors.append(f"{task.id} depends on missing tasks: {sorted(unknown)}")
        if task.attempt_limit > constraints.max_attempts_per_task:
            errors.append(f"{task.id} exceeds the retry budget.")
        if set(task.tool_scope) - set(constraints.allowed_tools):
            errors.append(f"{task.id} requests an unauthorized tool.")
    if not errors:
        try:
            topological_layers(task_list)
        except ValueError as error:
            errors.append(str(error))
    return errors


def topological_layers(tasks: Iterable[Task]) -> list[list[str]]:
    """Kahn-style scheduling layers: tasks in one layer can run in parallel."""

    task_list = list(tasks)
    by_id = {task.id: task for task in task_list}
    indegree = {task.id: len(task.depends_on) for task in task_list}
    children: dict[str, list[str]] = defaultdict(list)
    for task in task_list:
        for dependency in task.depends_on:
            if dependency not in by_id:
                raise ValueError(f"Missing dependency: {dependency}")
            children[dependency].append(task.id)
    ready = deque(sorted(task_id for task_id, count in indegree.items() if count == 0))
    layers: list[list[str]] = []
    completed = 0
    while ready:
        layer = list(ready)
        ready.clear()
        layers.append(layer)
        for task_id in layer:
            completed += 1
            for child in children[task_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
    if completed != len(task_list):
        raise ValueError("Task graph contains a dependency cycle.")
    return layers


def make_state(goal: str = "Research adaptive RAG and produce a technical report") -> PlanState:
    state = PlanState(goal=goal)
    tasks = initial_plan()
    errors = validate_plan(tasks, state.constraints)
    if errors:
        raise ValueError("Invalid initial plan: " + "; ".join(errors))
    state.tasks = {task.id: task for task in tasks}
    state.status = {task.id: TaskStatus.PENDING for task in tasks}
    state.events.append("planner: accepted a constrained initial research DAG")
    return state


def _retrieve(source_id: str, simulate_missing_source: bool) -> str:
    if source_id == "workflow-guidance" and simulate_missing_source:
        raise LookupError("Source temporarily unavailable")
    source = SOURCE_LIBRARY[source_id]
    return f"[{source['title']}] {source['claim']} ({source['url']})"


def execute_task(state: PlanState, task_id: str, simulate_missing_source: bool = False) -> str:
    """A deterministic executor. It executes only validated, ready tasks."""

    task = state.tasks[task_id]
    if state.status[task_id] is not TaskStatus.PENDING:
        raise ValueError(f"{task_id} is not pending")
    if any(state.status[dep] is not TaskStatus.COMPLETE for dep in task.depends_on):
        raise ValueError(f"{task_id} has incomplete dependencies")
    state.status[task_id] = TaskStatus.RUNNING
    state.attempts[task_id] += 1
    try:
        if task_id == "scope":
            output = "Audience: technical builders; deliverable: cited report; limits: 10 tasks, 2 replans, no unsupported claims."
        elif task_id == "adaptive-paper":
            output = _retrieve("adaptive-rag-paper", simulate_missing_source)
        elif task_id == "rag-foundation":
            output = _retrieve("rag-foundation", simulate_missing_source)
        elif task_id == "implementation-guidance":
            output = _retrieve("workflow-guidance", simulate_missing_source)
        elif task_id == "replacement-guidance":
            output = _retrieve("adaptive-rag-survey", False)
        elif task_id == "compare":
            evidence = "\n".join(state.findings[dep] for dep in task.depends_on)
            output = "Comparison: route only when complexity or evidence need warrants it. Fixed RAG is predictable; adaptive routing can avoid unnecessary retrieval but needs a measurable router.\n" + evidence
        elif task_id == "checkpoint":
            output = quality_checkpoint(state)
        elif task_id == "report":
            output = synthesize_report(state)
        else:
            raise KeyError(f"No executor registered for {task_id}")
    except (LookupError, KeyError) as error:
        state.status[task_id] = TaskStatus.FAILED
        state.events.append(f"executor: {task_id} failed safely: {error}")
        return f"FAILED: {error}"
    state.status[task_id] = TaskStatus.COMPLETE
    state.findings[task_id] = output
    state.events.append(f"executor: completed {task_id}")
    return output


def quality_checkpoint(state: PlanState) -> str:
    """Return structured gaps; do not let a model decide quality by free-form vibe."""

    required = {"adaptive-paper", "rag-foundation"}
    completed = {task_id for task_id, status in state.status.items() if status is TaskStatus.COMPLETE}
    gaps = []
    if not required.issubset(completed):
        gaps.append("primary evidence missing")
    if state.status.get("implementation-guidance") is TaskStatus.FAILED and "replacement-guidance" not in completed:
        gaps.append("implementation guidance missing")
    if not any("Comparison:" in finding for finding in state.findings.values()):
        gaps.append("routing comparison missing")
    return "PASS" if not gaps else "GAPS: " + ", ".join(gaps)


def replan_for_failures(state: PlanState) -> bool:
    """Make one safe, auditable graph change for a known failed dependency."""

    if state.replan_count >= state.constraints.max_replans:
        state.events.append("replanner: budget exhausted; escalate to a human")
        return False
    if state.status.get("implementation-guidance") is not TaskStatus.FAILED:
        return False
    replacement = Task(
        "replacement-guidance",
        "Use an alternative adaptive-retrieval source",
        "Replace unavailable implementation guidance with a source that explains routing trade-offs.",
        kind="retrieve",
    )
    state.tasks[replacement.id] = replacement
    state.status[replacement.id] = TaskStatus.PENDING
    compare = state.tasks["compare"]
    state.tasks["compare"] = Task(
        **{**compare.__dict__, "depends_on": ("adaptive-paper", "rag-foundation", "replacement-guidance")}
    )
    state.status["compare"] = TaskStatus.PENDING
    state.status["checkpoint"] = TaskStatus.PENDING
    state.status["report"] = TaskStatus.PENDING
    state.replan_count += 1
    errors = validate_plan(state.tasks.values(), state.constraints)
    if errors:
        raise ValueError("Unsafe replan rejected: " + "; ".join(errors))
    state.events.append("replanner: replaced unavailable guidance and rewired compare dependency")
    return True


def synthesize_report(state: PlanState) -> str:
    evidence = state.findings.get("compare", "")
    return "\n".join(
        [
            "# Adaptive RAG: a planning-oriented technical report",
            "## What changes",
            "Adaptive RAG is a routing policy over retrieval strategies, not a guarantee that more retrieval is better.",
            "## Routing strategies",
            "Use a cheap, predictable route for simple questions; escalate to retrieval or iterative evidence gathering when the question and evaluation evidence justify it.",
            "## Evaluation and trade-offs",
            "Measure answer support, route accuracy, retrieval cost, latency, abstention behavior, and the harm from choosing the wrong route.",
            "## Evidence",
            evidence,
        ]
    )


def run_research_agent(simulate_missing_source: bool = False) -> PlanState:
    """Run plan → execute ready tasks → checkpoint → bounded replan → report."""

    state = make_state()
    safety_steps = 0
    while state.status.get("report") is not TaskStatus.COMPLETE:
        safety_steps += 1
        if safety_steps > 20:
            raise RuntimeError("Harness safety limit reached")
        ready = [
            task_id
            for task_id, task in state.tasks.items()
            if state.status[task_id] is TaskStatus.PENDING
            and all(state.status[dep] is TaskStatus.COMPLETE for dep in task.depends_on)
        ]
        if not ready:
            if replan_for_failures(state):
                continue
            raise RuntimeError("No executable task remains; escalate with the trace")
        for task_id in sorted(ready):
            execute_task(state, task_id, simulate_missing_source)
        if state.status.get("checkpoint") is TaskStatus.COMPLETE and state.findings["checkpoint"] != "PASS":
            replan_for_failures(state)
    return state


if __name__ == "__main__":
    run = run_research_agent(simulate_missing_source=True)
    print("\n".join(run.events))
    print("\n" + run.findings["report"])
