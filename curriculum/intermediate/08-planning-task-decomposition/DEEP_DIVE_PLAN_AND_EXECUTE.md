# Deep Dive: Plan-and-Execute Architectures

Standard ReAct agents suffer from state accumulation. If a user provides a complex, long-horizon goal, a standard agent attempts to solve it dynamically step-by-step. By step 12, the context window is bloated with unrelated web search results, and the agent forgets the original goal, resulting in infinite loops or hallucinated completion.

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
The Worker is an agent whose context window is heavily restricted to the current task.
- **Input:** *Exactly one* sub-task from the Planner.
- **Execution:** It runs a tight loop to solve just that sub-task, utilizing tools.
- **Output:** A concise string or typed artifact summarizing the result of the sub-task.

### D. The Evaluator / Checkpoint
As the Worker completes tasks, the Evaluator verifies the result against the `GoalContract`. If an artifact is missing required sections or evidence, the Checkpoint fails. 

**Why it's useful:** This architecture bounds the context window. The Worker never gets overwhelmed because its context is limited to the current task, while the application durably stores completed artifacts.

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
    status: str = "PENDING"

class PlanPatch(BaseModel):
    add_tasks: List[Task]
    remove_tasks: List[str]
    add_edges: List[tuple]
    remove_edges: List[tuple]
    reason: str
```

## 4. Enterprise Considerations

- **Latency and Cost:** Plan-and-Execute is significantly slower and more expensive than standard ReAct because of the overhead of Planner, Evaluator, and Replanner nodes. Use it *only* for complex, multi-step goals.
- **Model Selection:** The Planner requires extremely high reasoning capabilities (e.g., Claude 3.5 Sonnet, GPT-4o). However, the Worker can often be a cheaper, faster model (e.g., Gemini Flash) because its task scope is so narrow. This is known as **Model Cascading** and is a key driver of cost-efficiency in enterprise agents.
- **Durable State:** Always persist the `Plan`, `PlanPatch` history, and `TaskState`s to a database. If the execution is interrupted, you must be able to resume without starting from scratch.
