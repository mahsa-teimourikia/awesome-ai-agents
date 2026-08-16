# Deep Dive: The ReAct Pattern

Before the ReAct (Reason + Act) pattern, LLMs were strictly conversational. If you asked an LLM to solve a complex math problem or query a database, it would attempt to output the final answer immediately in a single inference pass, often resulting in hallucinations.

The ReAct pattern, introduced by researchers at Princeton and Google, forces the LLM to "show its work" by explicitly alternating between internal reasoning and external action.

---

## 1. The Core Loop

The ReAct pattern enforces a strict syntax on the LLM's output. The LLM must output specific keywords in a specific order:

1. **Thought:** The LLM explains its reasoning and decides what to do next.
2. **Action:** The LLM specifies a tool to use and the arguments to pass to it.
3. **Observation:** *[The LLM halts. The execution framework runs the tool and injects the raw result back into the prompt as the Observation.]*

This loop repeats until the LLM decides it has enough information to formulate a `Final Answer`.

### Example Trace
```text
User: How many users are in the database, and what is the current stock price of Apple?

Thought: I need to check the database for the user count, and then use the finance API for Apple's stock price. I will start with the database.
Action: execute_sql(query="SELECT count(*) FROM users;")
Observation: "Count: 1450"
Thought: Now I need to get Apple's stock price. The ticker is AAPL.
Action: get_stock_price(ticker="AAPL")
Observation: "$150.25"
Thought: I have both pieces of information. I can answer the user.
Action: final_answer(text="There are 1450 users in the database, and Apple's stock price is $150.25.")
```

---

## 2. Why ReAct is (Was) SOTA

- **Grounding:** By forcing the LLM to output an `Action` and wait for an `Observation`, you prevent it from hallucinating facts. It is anchored to external reality.
- **Explainability:** Because the LLM outputs a `Thought` before every action, engineers can read the logs and understand *why* an agent made a mistake, allowing for targeted prompt engineering.

---

## 3. The Enterprise Limitations of Standard ReAct

While ReAct is the foundation of agentic behavior, standard ReAct implementations (like `langchain.agents.create_react_agent`) fail in production for three reasons:

1. **Context Window Bloat:** Standard ReAct agents append the entire trace (Thought, Action, Observation) to the system prompt in a single, ever-growing string. By step 10, the prompt is massive, slowing down inference and costing money.
2. **Infinite Loops:** If a tool fails and returns `"Error: Invalid syntax"`, the LLM might continuously retry the exact same bad `Action`, burning through thousands of tokens until the orchestrator hits a hard timeout.
3. **Parsing Fragility:** Standard ReAct relies on Regex to parse the LLM's text output. If the LLM outputs `Action :` instead of `Action:`, the regex fails and the agent crashes. 

*To solve these limitations, modern architectures use **State Machines (LangGraph)** and **Native Tool Calling (JSON)**, overriding standard text-based ReAct.*
