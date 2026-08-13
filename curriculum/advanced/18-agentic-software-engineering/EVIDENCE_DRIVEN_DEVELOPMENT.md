# Deep Dive: Evidence-Driven Development

One of the most common failure modes for Coding Agents is the **"Infinite Loop of Hopeless Fixes."**

An agent writes some code, runs a Python script, gets a syntax error, tries to fix it, gets a type error, tries to fix it, gets an import error... and burns $10 in API credits before timing out.

Worse is **"Greenwashing,"** where an agent writes a fix, assumes it works, and submits a PR. The PR is merged, and production breaks because the agent's code didn't actually solve the problem.

To build reliable Agentic SWE pipelines, you must enforce **Evidence-Driven Development (Test-Driven Development for Agents)**.

## The Evidence Loop

You must restrict the agent's workflow to the following strict loop:

### 1. Write the Failing Test First
Before the agent is allowed to modify any production code, it **must** write a unit test that perfectly replicates the bug described in the GitHub Issue.
The agent must run the test and prove to the system that the test **FAILS**. 
*If the agent cannot write a failing test, it has not understood the bug, and it should not be allowed to edit the codebase.*

### 2. Isolate the Fix
Once the failing test is committed to the sandbox, the agent is allowed to edit the application code.

### 3. Run the Test (Provide the Evidence)
The agent runs the test suite. If the test fails, the agent reads the traceback and modifies its code.
If the test **PASSES**, the agent has provided mathematical evidence that it fixed the specific bug it was asked to fix.

### 4. Run the Regression Suite
Finally, the agent must run the entire repository's test suite. If it fixed the bug but broke 5 other tests, it must revert its changes and try a different approach.

## Why this is critical for Agents
LLMs are highly persuasive. If an agent says, *"I have thoroughly analyzed the codebase and implemented an optimal fix for the race condition,"* a human reviewer might believe it and click Merge.

By enforcing Evidence-Driven Development, the human reviewer doesn't have to trust the LLM's persuasive summary. They just look at the CI/CD pipeline:
1. Did it add a test?
2. Does the test cover the edge case?
3. Is the pipeline green?

If yes, the PR is safe to merge.
