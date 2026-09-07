# CrewAI Flows as an application control plane

A Flow can place deterministic, inspectable control around specialized crews. It does not make model output authoritative.

## State and events

Course 03 state records tenant, incident, task lifecycle, accepted artifacts, evidence registry, budgets, pending review, terminal status, and flow version. Events describe facts the application has validated: crew start, task result, artifact acceptance, review requirement, completion, escalation, or cancellation.

The control loop is:

1. policy computes ready tasks;
2. Flow chooses a bounded crew;
3. the crew returns candidate structured outputs;
4. policy validates artifacts and updates state;
5. Flow evaluates retry, fallback, review, escalation, or completion.

A model can suggest a route or event. Only application code applies it.

## Current decorator model

CrewAI Flows use `@start()` for entry methods, `@listen(...)` for dependent methods, and `@router(...)` when one result selects a labelled branch. A minimal shape is:

```python
from crewai.flow.flow import Flow, listen, router, start

class IncidentFlow(Flow):
    @start()
    def admit(self):
        return "investigate"

    @router(admit)
    def route(self, decision):
        return decision

    @listen("investigate")
    def investigate(self):
        return "candidate artifacts"
```

In production, each method would call the same application policy before invoking a crew or mutating state. A returned string is routing data, not authority.

## Cancellation precedence

Cancellation is checked before the next crew and before the next worker call. Once terminal state is `CANCELLED`, neither worker nor manager counters may increase. Rejecting a result after an expensive call is too late.

## Completion

Crew kickoff returning is not business completion. Northstar completion requires all five evidence artifact types, a grounded incident brief, a reviewer-produced `REVIEW_PASS`, and no failed, blocked, or retryable task.

`REVIEW_PASS` advances review state only. It is not production approval and cannot authorize rollback.

## Persistence and restart

The deterministic lab serializes structured state and resumes unfinished tasks without re-running completed logical task identities. This illustrates the checkpoint boundary.

CrewAI also provides Flow persistence with `@persist`; its default examples use SQLite. A production deployment still needs storage appropriate to its availability model, atomic state transitions, event deduplication, version migration, and idempotent side effects. Intermediate Course 10 covers those durable-state concerns in depth.

## Framework boundary

CrewAI owns orchestration mechanics inside the adapter. The application still owns:

- tenant and capability enforcement;
- artifact and provenance validation;
- global budgets and retry rules;
- routing and recovery admission;
- cancellation and terminal completion.

See the official [Flows documentation](https://docs.crewai.com/en/concepts/flows) for current decorators, state, routers, and persistence. The example is verified against CrewAI `1.15.20`.
