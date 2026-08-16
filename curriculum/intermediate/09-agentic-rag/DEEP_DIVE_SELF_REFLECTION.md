# Deep Dive: Self-Reflective Retrieval (CRAG & Self-RAG)

Standard Retrieval-Augmented Generation (RAG) is a blind, forward-only pipeline:
`Embed Query -> Fetch Top K -> Generate Answer`.

If the Vector DB fetches irrelevant documents, the LLM will either hallucinate an answer based on bad data, or confidently state it doesn't know the answer. 

**Agentic RAG** introduces **Self-Reflection**—a cognitive feedback loop where the agent evaluates its own intermediate steps before responding to the user.

---

## 1. Corrective RAG (CRAG)

CRAG (Corrective Retrieval Augmented Generation) introduces an explicit **Evaluator Node** immediately after the retrieval step.

### The CRAG Workflow
1. **Retrieve:** Fetch documents from the local database.
2. **Evaluate:** A lightweight LLM (the Evaluator) looks at the documents and the user's query. It scores the retrieval as `Correct`, `Incorrect`, or `Ambiguous`.
3. **Branching Logic:**
   - If `Correct`: Proceed to final generation.
   - If `Incorrect`: **Corrective Action.** The agent discards the bad documents and searches the live Web (e.g., using a Google/Tavily API) instead.
   - If `Ambiguous`: **Knowledge Refinement.** The agent uses another LLM call to rewrite or broaden the user's search query, and tries the local database again.

### Why CRAG is SOTA
In enterprise deployments, internal knowledge bases are often out of date. If a user asks about a policy updated yesterday, the local Vector DB might return the old policy (which the Evaluator flags as `Ambiguous`), prompting the agent to fetch the live document from an external API, preventing a hallucination.

---

## 2. Self-RAG

While CRAG evaluates the *retrieval*, **Self-RAG** evaluates the *generation*. Self-RAG trains or prompts the LLM to insert explicit **Reflection Tokens** into its own output stream.

### The Self-RAG Workflow
1. **Retrieve & Generate:** The LLM begins drafting the answer.
2. **Self-Critique (Relevance):** The LLM generates a hidden tag `<is_relevant>`. If it determines its draft isn't answering the user's prompt, it halts generation and retries.
3. **Self-Critique (Support):** The LLM generates a hidden tag `<is_supported>`. It checks if its current sentence is directly backed by the retrieved documents. If not (it catches itself hallucinating), it deletes the sentence and tries again.
4. **Final Output:** The user only sees the final, perfectly supported text.

---

## 3. Implementation Example (LangGraph)

Implementing these reflective loops is extremely difficult with linear frameworks (like standard LangChain pipelines). **LangGraph** (State Machines) is the industry standard for this pattern because it allows cyclic loops.

```python
from typing import TypedDict
from typing import Literal

# 1. Define the Graph State
class AgentState(TypedDict):
    question: str
    documents: list[str]
    generation: str

# 2. Define the Nodes
def retrieve_node(state: AgentState):
    print("[Action] Retrieving documents from Vector DB...")
    # Mock retrieval
    return {"documents": ["Doc 1: Apples are red."]}

def generate_node(state: AgentState):
    print("[Action] Generating final answer...")
    return {"generation": "Apples are a red fruit."}

# 3. The Reflection / Evaluator Edge
def grade_documents(state: AgentState) -> Literal["generate", "rewrite_query"]:
    print("🧠 [Evaluator] Grading retrieved documents...")
    doc_content = " ".join(state["documents"])
    
    # In reality, this would be an LLM call asking: 
    # "Does this document answer the question?"
    if "Apples" in state["question"] and "Apples" in doc_content:
        print("   ✅ Documents are relevant. Proceed to generation.")
        return "generate"
    else:
        print("   ❌ Documents are irrelevant. Triggering corrective loop.")
        return "rewrite_query"

def rewrite_query_node(state: AgentState):
    print("🔄 [Action] Rewriting query to be more specific...")
    return {"question": state["question"] + " (specifically about apples)"}

# 4. The Graph Architecture
# retrieve_node -> grade_documents -> [if pass] -> generate_node
#                                  -> [if fail] -> rewrite_query_node -> retrieve_node
```

## 4. Enterprise Considerations

Self-reflection drastically increases accuracy, but it comes with significant trade-offs:
- **Latency:** A standard RAG pipeline might take 1.5 seconds. A Self-RAG pipeline that loops twice could take 6-10 seconds.
- **Cost:** Every evaluation node requires an LLM inference call. 

**Recommendation:** Use semantic routing first. Only route complex, high-risk queries (e.g., legal or medical compliance) through a CRAG or Self-RAG loop. For simple informational queries, bypass the reflection loop to save latency.
