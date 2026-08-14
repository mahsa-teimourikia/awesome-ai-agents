# Deep Dive: CrewAI Flows

A single Crew is rarely enough for a production application. What if the user asks for a Python script, but your Crew is designed to write marketing copy?

CrewAI recently introduced **Flows**—an event-driven state machine that wraps Crews in deterministic python logic.

## The Flow Architecture
Instead of cramming all your agents into one massive Crew, you build focused, specialized Crews:
- `CodeWriterCrew`
- `MarketingCrew`
- `SupportCrew`

You then use a `Flow` to manage the state and routing:
```python
@start()
def classify_intent(self):
    # Deterministic or cheap-LLM classification
    return "coding"

@listen("coding")
def run_coding_crew(self):
    return CodeWriterCrew().kickoff()

@listen("marketing")
def run_marketing_crew(self):
    return MarketingCrew().kickoff()
```

By keeping the routing deterministic and the Crews specialized, you significantly improve reliability and reduce the "Multi-Agent Tax."
