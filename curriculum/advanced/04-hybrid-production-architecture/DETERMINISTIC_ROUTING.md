# Deep Dive: Deterministic Routing and Policy

The most common mistake when building an agentic system is giving the LLM too much control over its own execution environment.

If you give an LLM a `reset_password` tool and ask it to "only use this if the user is authorized", you have built an insecure system. LLMs are non-deterministic; they can be tricked by prompt injection, or they can simply hallucinate an authorization check.

## The Control Plane
In a Hybrid Architecture, the LLM is just a worker. The **Control Plane** is deterministic code (Python, Go, etc.).

1. **Deterministic Classifier:** When a user request arrives, a classifier (which can be a fast LLM or a traditional ML model) determines the *intent*.
2. **Deterministic Routing:** A hardcoded `if/else` statement reads the intent and routes the request to the correct worker (Workflow, Agent, or Team).
3. **Policy Gateway:** After the worker generates an output, the output must pass through a Deterministic Policy Gateway. This gateway checks for PII, validates the JSON schema, and checks role-based access control (RBAC) *before* the action executes.

The LLM never decides if it is allowed to use a tool. The code decides.
