# Deep Dive: DAGs vs Agents

When automating a business process, engineering teams face a critical architectural decision: Should we build a deterministic Workflow (DAG) or a non-deterministic Agent?

Choosing the wrong architecture leads to brittle systems or catastrophic, unpredictable errors.

---

## 1. Deterministic Workflows (DAGs)

A DAG (Directed Acyclic Graph) is a strict, hardcoded sequence of steps. If Step A succeeds, execute Step B. If Step A fails, execute Step C.

Tools like Airflow, Prefect, or simple Python scripts represent this. 

### Characteristics:
- **Predictable:** The code path is defined entirely by the engineer. 
- **Reliable:** It does the exact same thing every time.
- **Brittle:** If a user says "I want to refund this order, but actually send it to my new credit card instead of the old one", a standard refund workflow will crash or fail because it wasn't explicitly programmed for that edge case.

---

## 2. Non-Deterministic Agents

An Agent is an LLM with access to tools (like `refund_order`, `lookup_user`). The *sequence* of operations is not hardcoded. The LLM decides what tools to use, in what order, based on the user's prompt.

### Characteristics:
- **Flexible:** It can handle thousands of edge cases automatically. If a user changes their mind mid-sentence, the agent dynamically adjusts its tool calls.
- **Unpredictable:** Because the LLM generates the path dynamically, it might take 3 steps today and 5 steps tomorrow to solve the exact same problem.
- **Prone to Failure:** LLMs hallucinate. An agent might decide to execute `issue_refund` before executing `verify_identity`, causing a security breach.

---

## 3. The Enterprise SOTA: Agentic Workflows

State-of-the-Art enterprise systems do not choose one or the other. They combine them into **Agentic Workflows**.

In an Agentic Workflow, the *macro-architecture* is a strict, hardcoded DAG, but specific nodes within the DAG are autonomous Agents.

### Scenario: Customer Support Triage

1. **Node 1 (Agent):** The "Router Agent" reads an incoming email. It has two options: classify it as `Billing` or `Technical`. It handles the messy, unstructured language.
2. **Edge (Deterministic):** If `Billing`, the system explicitly routes to the Billing Workflow. The agent *cannot* route anywhere else.
3. **Node 2 (Deterministic):** The system automatically looks up the user's billing history in the SQL database. (No LLM required, 100% reliable).
4. **Node 3 (Agent):** The "Billing Agent" reads the SQL output and drafts a polite email to the user explaining their invoice.

### Why this is SOTA
You use Agents only where you absolutely need flexibility (understanding messy human language, drafting text). You use deterministic Workflows for everything else (fetching data, making API calls, enforcing security boundaries). This minimizes hallucinations and dramatically reduces API costs.
