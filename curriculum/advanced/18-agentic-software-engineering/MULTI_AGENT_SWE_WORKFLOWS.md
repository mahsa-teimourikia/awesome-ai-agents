# Deep Dive: Multi-Agent SWE Workflows

If you ask a single agent to plan a feature, write the code, and then review its own code, it will almost always say: *"My code is perfect and ready to merge."* 

This is known as the **Rubber-Stamp Anti-Pattern**. LLMs struggle to critically evaluate their own recent outputs in the same context window.

To build production-grade Agentic SWE, you must enforce a **Separation of Duties** using a Multi-Agent workflow (often built with frameworks like LangGraph or Autogen).

## The Roles

### 1. The Planner Agent (The Architect)
**Goal:** Understand the repository and create a blueprint.
**Tools:** AST (Abstract Syntax Tree) Search, Code Navigation (e.g., `grep`, `find`).
**Rules:** The Planner is **not allowed** to write code. It is only allowed to output a `Markdown` document detailing which files need to change, and the specific functions to modify.

### 2. The Coder Agent (The Builder)
**Goal:** Implement the Planner's blueprint and provide evidence it works.
**Tools:** File Editing (`sed`, `cat`, or specialized AST editors), Terminal Execution (to run `pytest` or `npm test`).
**Rules:** The Coder cannot change the architecture. It must follow the plan, write a failing test, write the fix, and ensure the test passes.

### 3. The Adversarial Reviewer Agent (The Gatekeeper)
**Goal:** Find flaws in the Coder's pull request.
**Tools:** `git diff`.
**Rules:** This agent is prompted to be highly critical. It checks for:
- **Scope Creep:** Did the Coder refactor a file that wasn't in the plan?
- **Security:** Did the Coder introduce a SQL injection or hardcode a secret?
- **Maintainability:** Is the code complex or unreadable?

If the Reviewer finds an issue, it rejects the draft and sends feedback back to the Coder. The PR is only presented to a Human when the Reviewer Agent signs off.

## CI/CD: The Ultimate Independent Reviewer
No matter how good your multi-agent system is, it **must never have the permission to merge code directly to the `main` branch or deploy to production.**

The multi-agent system's final output is simply a Draft Pull Request on GitHub.

The Pull Request is then subjected to your company's standard CI/CD pipeline:
- Static Analysis (SonarQube)
- Secret Scanning (TruffleHog)
- Integration Tests
- **Human Review (Required)**

The agent accelerates the writing of the code, but the deployment safety mechanisms remain exactly the same as if a human wrote it.
