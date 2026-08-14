# Deep Dive: Avoiding Circular Delegation

The most catastrophic failure mode in AutoGen is the Infinite Loop (Circular Delegation). 

This happens when Agent A disagrees with Agent B, and they pass the mic back and forth arguing forever, racking up massive token bills.

## Termination Conditions
You must never run an open-ended Group Chat in production. You must use hard termination constraints.

### 1. MaxMessageTermination
Always set an absolute ceiling on the number of turns.
```python
from autogen_agentchat.conditions import MaxMessageTermination
termination = MaxMessageTermination(10)
```
If the team cannot solve the problem in 10 messages, they are stuck. Hard abort.

### 2. TextMentionTermination
Define a strict keyword that indicates success or unrecoverable failure.
```python
from autogen_agentchat.conditions import TextMentionTermination
termination = TextMentionTermination("FINAL_PROPOSAL") | TextMentionTermination("ESCALATE_TO_HUMAN")
```
Instruct the `Reviewer_Agent` to output `ESCALATE_TO_HUMAN` if it rejects the `Analyst_Agent`'s proposal twice. This breaks the loop gracefully.

### 3. Agent Prompts
Ensure the agents know they are allowed to give up. A common mistake is prompting an agent with "You must solve the problem." If the problem is unsolvable with their tools, they will hallucinate or loop. Prompt them with: "If the metrics do not explain the outage, output ESCALATE_TO_HUMAN."
