# Deep Dive: Workflows vs Agents: Architectural Trade-offs

When automating a business process, engineering teams face a critical architectural decision: Should we build a Deterministic Workflow or an Agent?

## 1. Deterministic Workflows

A common misconception is that a workflow is strictly a DAG (Directed Acyclic Graph). In reality, a DAG is just one representation. Deterministic workflows may also be represented as:
- Ordinary application code
- Finite-state machines (FSM)
- Statecharts
- BPM/workflow systems
- Event-driven workflows
- Durable workflows
- Graphs with bounded cycles and retries

A workflow can contain branching, retries, loops, waiting, events, human approvals, and parallel work. 

### Clarifying Determinism

"Deterministic" refers to the **control flow**, not the external outcome. In a deterministic workflow, application code defines the valid execution paths. However, external systems and data may still produce variable outcomes (e.g., API timeouts, database changes, concurrent updates, network failures, human input). 

*Deterministic control flow != deterministic external outcome.*

### Strengths and Weaknesses
- **Strength:** Explicit known behavior. Predictable costs and latency. Easy to evaluate and audit.
- **Weakness:** They must be explicitly programmed for known edge cases. If a highly unstructured, unpredictable scenario arises that was not modeled, the workflow will fail.

---

## 2. Agents

An agent dynamically directs its process and tool use based on evidence discovered at runtime.

### Strengths and Weaknesses
- **Strength:** Adaptive behavior where the correct path cannot be enumerated economically. Excellent for messy, uncertain environments (like diagnosing an incident).
- **Weakness:** An agent can misunderstand the case, choose the wrong tool, miss an edge case, hallucinate, violate a business rule, or get stuck in a loop. It inherently increases latency, cost, and evaluation burden.

Do not fall for the oversimplification that "workflows are brittle" while "agents handle all edge cases automatically." Both have distinct failure modes.

---

## 3. The 6-Level Architecture Spectrum

State-of-the-art enterprise systems do not choose "Agent OR Workflow". They use the least autonomous architecture that reliably solves the problem.

- **Level 0 — Deterministic Code:** Application code controls everything.
- **Level 1 — Deterministic Workflow:** Branches are explicitly coded.
- **Level 2 — Workflow with LLM Nodes:** The model performs a bounded cognitive task (e.g., classification) but does not own the overall process.
- **Level 3 — Agentic Workflow:** The macro process is controlled, but a model may decide locally which evidence source to inspect.
- **Level 4 — Bounded Agent:** The model dynamically chooses the next approved action from state, constrained by authorization and terminal conditions.
- **Level 5 — Multi-Agent System:** Multiple independent agents collaborate only where specialization, context isolation, or organizational boundaries justify it.
