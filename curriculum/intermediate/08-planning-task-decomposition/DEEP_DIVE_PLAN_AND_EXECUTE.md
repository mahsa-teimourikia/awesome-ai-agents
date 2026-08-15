# Deep Dive: Plan-and-Execute Architectures

Standard ReAct agents suffer from the "Lost in the Middle" phenomenon. If a user provides a complex, long-horizon goal (e.g., "Research these 5 competitors, summarize their pricing, and generate a competitive matrix spreadsheet"), a standard agent attempts to solve it dynamically step-by-step. By step 12, the context window is bloated with unrelated web search results, and the agent forgets the original goal, resulting in infinite loops or hallucinated completion.

The **State-of-the-Art (SOTA)** solution to this is **Task Decomposition**, commonly implemented as the **Plan-and-Execute** architecture.

---

## 1. The Core Architecture

The architecture relies on decoupling the "thinking" from the "doing" by using distinct agent personas.

### A. The Planner (The Architect)
The Planner's sole responsibility is task decomposition. It does *not* have access to execution tools (like Web Search or Python interpreters).
- **Input:** The user's complex goal.
- **Output:** A strict JSON array containing a Directed Acyclic Graph (DAG) of explicit sub-tasks.

### B. The Worker (The Executor)
The Worker is a standard ReAct agent, but its context window is heavily restricted.
- **Input:** *Exactly one* sub-task from the Planner.
- **Execution:** It runs a tight loop to solve just that sub-task, utilizing tools.
- **Output:** A concise string summarizing the result of the sub-task.

### C. The Controller / Scratchpad
As the Worker completes tasks, the Controller collects the results and appends them to a "Scratchpad." When handing the *next* task to the Worker, it only provides the current task and the summarized Scratchpad—it **never** provides the raw, messy execution logs from previous steps. 

**Why it's SOTA:** This architecture strictly bounds the context window. The Worker never gets overwhelmed, because its memory is wiped clean before every new sub-task.

---

## 2. Advanced Pattern: Re-Planning (Plan-and-Solve)

The standard Plan-and-Execute pattern is brittle if the environment changes. If the Planner creates Task 3 ("Scrape pricing from Competitor A"), but Competitor A's website is down, the Worker will fail. 

SOTA implementations (like LangGraph's "Plan-and-Solve") introduce a **Re-Planner Node**.

### The Re-Planning Loop
1. **Plan:** The Planner generates 5 tasks.
2. **Execute:** The Worker attempts Task 1.
3. **Re-Plan:** Instead of blindly moving to Task 2, the execution halts. The Controller sends the result of Task 1 back to the **Re-Planner**.
4. The Re-Planner evaluates the result:
   - Did Task 1 fail? If yes, it rewrites the remaining plan (e.g., "Skip Competitor A, try Competitor B").
   - Did Task 1 succeed but reveal new information? It dynamically injects new tasks into the queue.

---

## 3. Implementation Concepts (LangGraph)

Implementing this pattern in LangGraph involves creating a State Machine where the `State` holds the queue of remaining tasks and the rolling scratchpad of results.

```python
from typing import TypedDict, Annotated
import operator
from pydantic import BaseModel

# 1. State Definition
class PlanExecuteState(TypedDict):
    input: str
    plan: list[str]            # The queue of upcoming tasks
    past_steps: Annotated[list[tuple], operator.add] # The scratchpad (Task, Result)

# 2. Node: The Planner
def planner_node(state: PlanExecuteState):
    print("🧠 [Planner] Decomposing complex goal...")
    # LLM Call requesting a JSON array of steps
    plan = ["Task 1", "Task 2", "Task 3"] 
    return {"plan": plan}

# 3. Node: The Worker
def execute_node(state: PlanExecuteState):
    # Pop the first task off the queue
    current_task = state["plan"][0]
    print(f"👷 [Worker] Executing strictly: {current_task}")
    
    # Run the ReAct agent for this single task...
    result = "Success." 
    
    # Return the remaining plan and append to past_steps
    return {
        "plan": state["plan"][1:], 
        "past_steps": [(current_task, result)]
    }

# 4. Node: The Re-Planner
def replan_node(state: PlanExecuteState):
    print("🔄 [Re-Planner] Evaluating results and updating the plan...")
    # LLM Call to analyze past_steps and update the plan
    return {"plan": state["plan"]} # Return modified plan

# 5. Routing Edge
def should_end(state: PlanExecuteState):
    if len(state["plan"]) == 0:
        return "end"
    return "execute"
```

## 4. Enterprise Considerations

- **Latency:** Plan-and-Execute is significantly slower than standard ReAct because of the overhead of Planner and Re-Planner nodes. Use it *only* for complex, multi-step goals.
- **Model Selection:** The Planner requires extremely high reasoning capabilities (e.g., Claude 3.5 Sonnet, GPT-4o). However, the Worker can often be a cheaper, faster model (e.g., GPT-4o-mini, Haiku) because its task scope is so narrow. This is known as **Model Cascading** and is a key driver of cost-efficiency in enterprise agents.
