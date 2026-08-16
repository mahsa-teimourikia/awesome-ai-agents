# Deep Dive: Dynamic Context Windows

In early Agent architectures (like standard LangChain Conversational Agents), the agent's "Memory" was just a single, ever-growing array of `messages`. Every user prompt, every tool call, every JSON API response, and every LLM thought was appended to the end of the array.

This approach fails catastrophically in production due to three reasons:
1. **Cost:** LLM APIs charge per token. If step 10 of a trajectory sends the entire history of steps 1-9 to the API, you are paying exponentially more money for every subsequent step.
2. **Latency:** Processing 30,000 tokens of context takes significantly longer than processing 500 tokens.
3. **"Lost in the Middle":** Research shows that LLMs suffer from severe recall degradation when context windows get too large. If the user's core instruction is buried at line 400 of a 2000-line prompt, the LLM will often ignore it or hallucinate.

---

## 1. The SOTA Solution: Dynamic State Wiping

State-of-the-Art (SOTA) agent architectures do not use a single, monolithic chat history. Instead, they use a **State Machine** (like LangGraph) where the context is dynamically wiped and rebuilt for the specific node that is executing.

### The Phased Context Architecture

Imagine an agent tasked with debugging a server issue.
1. **Phase 1: The Planner Node.** 
   - *Needs:* The user's original request.
   - *Doesn't Need:* Tool schemas for fetching logs.
   - *Action:* Outputs a JSON array of tasks.
2. **Phase 2: The Worker Node.**
   - *Needs:* Exactly *one* sub-task from the Planner, and the specific tool schemas to execute it.
   - *Doesn't Need:* The user's original request, the rest of the plan, or the chat history.
   - *Action:* Executes the tool and gets a massive 5000-line server log.
3. **Phase 3: The Synthesizer Node.**
   - *Needs:* A summary of the server log, and the user's original request.
   - *Doesn't Need:* Tool schemas, the Planner's JSON output, or the raw 5000-line log.

By defining explicit prompts for each Node, you ensure the LLM only ever sees the exact tokens it needs to make the immediate decision.

---

## 2. Implementation in LangGraph

LangGraph forces you to define a `State` object (typically a `TypedDict`). How you define this State determines how context is handled.

### A. Appending Context (The Danger Zone)
If you use `operator.add` (or LangGraph's built-in `add_messages` reducer), the state key will grow infinitely.
```python
from typing import Annotated
import operator

class AgentState(TypedDict):
    # This array grows forever. Every node adds to it.
    messages: Annotated[list, operator.add] 
```
*Use this ONLY for the final conversational history you show to the user.*

### B. Overwriting Context (The SOTA Pattern)
If you define a key without a reducer, any node that returns that key will completely overwrite the previous value. This allows you to wipe the context window.
```python
class AgentState(TypedDict):
    # Wiped clean and replaced on every transition!
    current_task: str 
    latest_tool_result: str
```

### C. The Summarization Pattern
What if you *need* historical context, but the logs are too big? You introduce a dedicated Summarizer node.

1. The Worker fetches a 10,000-token PDF.
2. It passes the PDF to the `SummarizerNode` state key.
3. A fast, cheap model (like `Claude-3-Haiku`) reads the PDF and outputs a 200-token summary.
4. The state is updated: the raw PDF string is *deleted* (overwritten with an empty string) and the 200-token summary is saved to `historical_summaries`.
5. The expensive main agent (like `GPT-4o`) is invoked, reading only the 200-token summary, saving thousands of tokens and drastically reducing latency.
