# Deep Dive: Sequential vs Hierarchical

Once you have defined your Agents and Tasks, you must define the `Process`—how the Crew orchestrates the work.

## Process.sequential
This is the default and most reliable method. Tasks are executed in the exact order they are defined.

**Example: Incident Report Crew**
1. **Task 1 (Telemetry Agent):** Fetch metrics.
2. **Task 2 (Release Agent):** Fetch deployments.
3. **Task 3 (Analyst Agent):** Combine the outputs of Task 1 and Task 2 into a final report.

*Pros:* Highly predictable, lower token cost.
*Cons:* Rigid. If Task 1 fails unexpectedly, the pipeline breaks.

## Process.hierarchical
This method introduces a **Manager Agent** (usually powered by an advanced model like GPT-4 or Claude 3.5 Sonnet). You give the Manager the ultimate goal, and it dynamically delegates sub-tasks to the worker agents.

**Example: Autonomous Research**
The Manager asks the `Researcher Agent` to find a paper. The Researcher fails. The Manager realizes this, rewrites the search query, and asks the Researcher to try again.

*Pros:* Highly resilient, handles ambiguous edge cases.
*Cons:* Very expensive in both latency and tokens. The Manager has to reason through every step. Use this only when the path to success is unknown.
