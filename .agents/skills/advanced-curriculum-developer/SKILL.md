---
name: advanced-curriculum-developer
description: Use this skill when asked to create, rewrite, expand, or modify training modules, course materials, or interactive Jupyter notebooks in this repository.
---

# Advanced Curriculum Developer Guidelines

When working on curriculum modules in this repository (e.g., inside the `curriculum/` directory), you **MUST** strictly adhere to the following standards. Do not compromise on depth, realism, or visual fidelity.

## 1. Deep Dive Markdown (README.md)
Never settle for a high-level conceptual summary. You must go deep into the technical weeds:
* **The "Watch For" Section (Anti-Patterns):** Always expand on failure modes. Explicitly detail things like PII leakage, State Checkpoint amnesia, alerting fatigue, or context window limits. Provide concrete examples of what happens when engineers make these mistakes.
* **KPIs and Metrics:** Do not just say "monitor the agent." Specifically list what should be monitored (e.g., TTFT, Reasoning Steps, Token Spikes) and *why* they matter.
* **Technology/Tools Review:** Compare the state-of-the-art platforms (e.g., AgentOps vs LangSmith vs Datadog) to ground the curriculum in real-world choices.
* **Data Examples:** If teaching a concept (like an OTel Span or a Handoff Packet), always include a raw JSON payload example.

## 2. Visual Fidelity (Mermaid SVGs)
Do not rely on the user to compile diagrams, and do not rely on markdown native rendering which can be buggy.
* **Write `.mmd` files:** Draft complex flowcharts or quadrant charts in the scratch space.
* **Compile to SVG locally:** Use `npx -y -p @mermaid-js/mermaid-cli mmdc -i <input.mmd> -o assets/<output.svg>` via the `run_command` tool.
* **Embed cleanly:** Link the SVG directly into the `README.md` and notebook using relative paths (e.g., `![Alt Text](../../../assets/diagram.svg)`).

## 3. Jupyter Notebook Generation & Simulation
Do NOT instruct the user to run scripts, and DO NOT leave empty notebook outputs that require API keys.
* **Remove Legacy Boilerplate:** Automatically delete outdated `lab.py` scaffolding files.
* **Use Generator Scripts:** Always write a Python generator script (e.g., `generate_notebook.py`) utilizing `nbformat` to construct the `.ipynb` file cell-by-cell.
* **Simulate Outputs:** The generator script *must* inject simulated `stdout` outputs into the cells so that when the user opens the `.ipynb` in their IDE, it looks like it was just executed perfectly. Simulate detailed logs, traces, and framework outputs.
* **Use Real Frameworks:** The code cells must contain syntactically valid code utilizing modern frameworks (e.g., `langgraph`, `temporalio`, `agentops`, `crewai`, `autogen`). No pseudocode.

## 4. Dependency Management
After adding new frameworks to a notebook:
* **Check `pyproject.toml`:** Verify that the required SDKs (e.g., `agentops`, `temporalio`) are defined under the appropriate optional dependencies (e.g., `[project.optional-dependencies] learner`).
* **Sync the Environment:** Run `uv sync --all-extras` via the terminal to ensure the user's environment is immediately ready to run the code.
