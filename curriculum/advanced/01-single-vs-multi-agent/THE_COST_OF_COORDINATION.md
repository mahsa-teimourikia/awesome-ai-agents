# Deep Dive: The Cost of Coordination

Multi-agent systems are a **distributed systems problem**, not a prompt engineering trick. 

When you split a single agent into a multi-agent team, you inherit all the failure modes of microservices, plus the non-determinism of LLMs.

## 1. The Latency Tax
If Agent A needs to ask Agent B for data, you incur the cost of a full LLM generation cycle just to format the question, and another full cycle to format the answer. A task that takes 2 seconds for a Single Agent might take 15 seconds for a Team.

## 2. The Token Tax
Every time an agent speaks, the entire shared context window must be re-processed by the LLM. If you have 5 agents in a group chat, you are paying to read the context 5 times.

## 3. State Synchronization
In a single agent, the "state" is just the context window. In a multi-agent system, state is distributed. If the `Database_Agent` knows the user is an Enterprise customer, but fails to explicitly mention that fact when handing off to the `Billing_Agent`, the `Billing_Agent` will hallucinate the tier.

**Rule of Thumb:** Never use a multi-agent team if a single agent can achieve the same success rate. You only pay the coordination cost when the single agent demonstrably fails.
