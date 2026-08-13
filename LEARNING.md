# Learning Guide

## The Study Loop

Every lesson follows this core loop:

1. **Read** concept: Read the `README.md` for the theory and architecture.
2. **Run** notebook: Execute the `.ipynb` file to see the implementation.
3. **Change** one variable: Modify the code to explore its boundaries.
4. **Inspect** failure mode: Trigger the deliberate failure to understand production risks.
5. **Write** a test: Fix the failure and write a test to prevent it.

## The Deliberate Failure Ritual

Every module contains at least one deliberate failure. This is not a bug; it is a feature. Do not skip it. Understanding how a system breaks is more important than seeing it succeed on the happy path.
