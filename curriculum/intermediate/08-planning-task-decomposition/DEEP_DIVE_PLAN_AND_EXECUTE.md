# Deep Dive: Plan-and-Execute Architectures

Long-running reactive loops can accumulate irrelevant context, duplicate work, and lose track of constraints unless state and progress are explicitly managed. This is distinct from long-context attention degradation: the engineering problem is that an unbounded loop has no durable task contract, milestone, or termination proof.

One useful architecture to mitigate this is **Task Decomposition**, commonly implemented as the **Plan-and-Execute** architecture.

---

## 1. The Core Architecture

The architecture relies on decoupling the "thinking" from the "doing" by using distinct agent personas and application constraints.

### A. The Planner (The Architect)
The Planner's sole responsibility is task decomposition. It does *not* have access to execution tools.
- **Input:** The user's complex goal, formalized as a `GoalContract`.
- **Output:** A strict JSON array containing a Directed Acyclic Graph (DAG) of explicit sub-tasks.

### B. The Scheduler (The Dispatcher)
The Scheduler sits in application code. It computes topological layers and ensures dependencies are met.
- **Validation:** Ensures there are no cycles, missing dependencies, or unauthorized tools.
- **Readiness:** Only moves a task to `READY` when all prerequisites are `SUCCEEDED`.

### C. The Worker (The Executor)
The Worker is an agent whose context is scoped to the current task.
- **Input:** One task contract plus the parent goal constraints, authorized capability, required dependency artifacts, and selected prior state.
- **Execution:** It runs a tight loop to solve just that sub-task, utilizing tools.
- **Output:** A typed, immutable artifact with provenance, execution identity, and a result hash.

### D. The Evaluator / Checkpoint
As the Worker completes tasks, the Evaluator verifies the result against the `GoalContract`. If an artifact is missing required sections or evidence, the Checkpoint fails. 

**Why it's useful:** This architecture bounds task context while the application durably stores completed artifacts. A successful task normally advances the existing plan; replanning runs only after explicit failure, evidence conflict, missing coverage, or changed constraints.

---

## 2. Advanced Pattern: Bounded Replanning (Plan Patching)

The naive Plan-and-Execute pattern is brittle. If the Planner creates Task 3 ("Read Implementation Guide"), but the source is down, the Worker will fail. 

Robust implementations introduce a **Bounded Replanner**.

### The Re-Planning Loop
1. **Plan:** The Planner generates a graph of 5 tasks.
2. **Execute:** The Worker attempts Task 3 but fails (e.g., `SOURCE_UNAVAILABLE`).
3. **Re-Plan:** Instead of generating a new plan from scratch (which wipes out history and creates chaos), the Replanner issues a **PlanPatch**.
4. The PlanPatch defines specific mutations:
   - `add_tasks`: Create a replacement task (e.g., "Read alternate guide").
   - `remove_edges`: Disconnect the failed task from dependents.
   - `add_edges`: Connect the new replacement task to the dependents.
5. **Re-Validate:** The application re-validates the patched DAG to ensure no cycles were introduced.

---

## 3. Implementation Concepts

Implementing this pattern involves creating a State Machine where the `State` holds the explicit definitions of tasks, dependencies, and their individual statuses.

```python
from pydantic import BaseModel
from typing import List, Optional

class Task(BaseModel):
    task_id: str
    task_type: str
    dependencies: List[str]
    expected_artifact_type: str

class TaskState(BaseModel):
    task_id: str
    status: str = "PENDING"

class PlanPatch(BaseModel):
    add_tasks: List[Task]
    remove_tasks: List[str]
    add_edges: List[tuple[str, str]]
    remove_edges: List[tuple[str, str]]
    reason: str  # a bounded enum in the executable lab
```

Task definitions remain immutable; runtime state records attempts and status separately. A patch is applied to a deep copy, then the full graph, coverage, capability, attempt, cost, and deadline policy is revalidated before the plan version changes.

## 4. Explicit DAGs versus manager/specialist delegation

| Pattern | What stays explicit | Best fit |
| --- | --- | --- |
| Validated DAG | dependencies, artifacts, ready sets, plan versions | auditable research and analysis with known joins |
| Manager with specialists | manager retains ownership and chooses specialists dynamically | delegation depends on observations |
| Handoff | conversation ownership transfers to a specialist | a specialist should directly continue the interaction |

The [OpenAI Agents SDK comparison](https://developers.openai.com/api/docs/guides/agents#compare-the-responses-api-and-agents-sdk) documents agents-as-tools and handoffs as multi-agent options. They do not replace application-owned authorization or deterministic plan validation.

## 5. Evaluation and enterprise considerations

- **Latency and cost:** Measure planner cost + worker cost + replan cost + coordination overhead per successful, policy-compliant result. Plan-and-execute can reduce duplicate work, but extra calls can also cost more than a fixed workflow or bounded reactive loop.
- **Model selection:** Match planner capability to decomposition complexity and benchmark the planner separately from workers. A higher-capability planner with lower-cost workers is one hypothesis to evaluate, not an automatic saving.
- **Plan evaluation:** Track valid-plan rate, structured coverage, dependency correctness, unauthorized-tool rejection, unnecessary tasks, parallelism opportunity, replan rate, checkpoint failures, and cost per success.
- **Durable State:** Always persist the `Plan`, `PlanPatch` history, and `TaskState`s to a database. If the execution is interrupted, you must be able to resume without starting from scratch.
