# Deep Dive: Evaluator Agents

A standard LLM-as-a-Judge is **static**. It reads the Agent's trace and makes a judgment based purely on the text. 

What if the Agent hallucinated?
* **Agent Trace:** "I have successfully deleted the user `john@example.com` from the database."
* **LLM Judge:** "Score 5/5. The agent followed instructions perfectly."

The LLM Judge is blind. It doesn't know that the Agent actually failed to execute the SQL query and is just lying in the text log.

## The Evaluator Agent
To solve this, we upgrade the Judge from a static prompt to an **Evaluator Agent**.

An Evaluator Agent is given its own tools. When it reads the primary agent's trace, it doesn't just trust it. It verifies it.

1. **Primary Agent Trace:** "I deleted the user."
2. **Evaluator Agent:** Reads the trace.
3. **Evaluator Agent:** Uses the `query_database("SELECT * FROM users WHERE email='john@example.com'")` tool.
4. **Evaluator Agent:** The database returns the user record.
5. **Evaluator Agent:** "Score 1/5. The primary agent hallucinated success. The user still exists in the database."

Evaluator Agents are the ultimate defense against silent failures and hallucinations, because they provide cryptographic proof of outcome, rather than just semantic text analysis.
