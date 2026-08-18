# Learning Guide

Welcome to the **awesome-ai-agents** curriculum! This guide explains how to get the most out of the repository, from the study loop to navigating the SOTA deep dives.

## 1. The Study Loop

Every lesson in this curriculum follows this core notebook-first learning loop:

1. **Read the Concept**: Read the `README.md` for the theory, architecture, and constraints.
2. **Read the Deep Dives**: (Where applicable) Check out the `DEEP_DIVE_*.md` files to understand the specific State-of-the-Art (SOTA) mechanics underlying the topic (e.g., OmniParser bounding boxes, LangGraph state machines, Typed Errors).
3. **Run the Notebook**: Execute the `[number]_[name].ipynb` file to see the implementation in action.
4. **Change One Variable**: Modify the code to explore its boundaries and constraints.
5. **Inspect the Failure Mode**: Trigger the deliberate failure to understand production risks.
6. **Write a Test**: Fix the failure and write a test to prevent it.

## 2. The Deliberate Failure Ritual

Every module contains at least one deliberate failure. **This is not a bug; it is a feature.** 

Do not skip it. Understanding exactly how a system breaks (e.g., an LLM hallucinating a regex extraction, an infinite ReAct loop, a catastrophic mutation without idempotency) is far more important than seeing it succeed on the happy path.

## 3. Curriculum Architecture

The repository is structured into three ascending altitudes. You should complete them in order to avoid jumping into complex multi-agent architectures without the necessary tool engineering fundamentals.

### Beginner Track (Modules 01 - 05)
**Goal:** Build one trustworthy agent.
- Master the foundations (workflow vs. agent vs. RAG).
- Learn why bounded loops (State Machines) are safer than unbounded loops (ReAct).
- Explore orchestration frameworks and computer-using agents (UI navigation).

### Intermediate Track (Modules 01 - 10)
**Goal:** Improve and measure tools.
- Focus strictly on Tool Engineering (JSON schemas, Typed Errors) and Context Engineering.
- Implement Enterprise Guardrails (Regex sanitization, Output validation, HITL Idempotency).
- Design Agentic RAG, Planning DAGs, and build robust automated Evaluation suites (LLM-as-a-judge).

### Advanced Track (Modules 01 - 31)
**Goal:** Design for coordination and scale to production.
- Scale from single-agent to multi-agent architectures (AutoGen, CrewAI, Hybrid).
- Implement Long-Running Asynchronous Agents and Proactive Agents.
- Operationalize with Enterprise architecture (Governance, Security, Cost/Latency Economics, Protocol Stacks).

## 4. The Interactive Learning Hub

We provide a custom Next.js frontend to help you track your progress, read the material side-by-side with the code, and test your knowledge.

To launch the Interactive Learning Hub:
```bash
npm install
npm run dev
```
Navigate to `http://localhost:3000` to start your guided journey.

## 5. Checkpoint Quizzes

After completing a module, use the built-in quizzes in the Learning Hub to verify your knowledge. The quizzes rigorously test your understanding of the SOTA deep dives, ensuring you actually absorbed the trade-offs before moving to the next track. 

If you prefer to take the entire quiz at once, visit the `/awesome-ai-agents/quiz/` route in the Learning Hub.
