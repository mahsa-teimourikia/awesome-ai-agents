# Deep Dive: When to Split Agents

You do not split a monolith into multiple agents to make the system "smarter". You split it because the monolith has hit a structural boundary.

There are three valid reasons to split a single agent into a multi-agent team:

## 1. Separation of Concerns (Too Many Tools)
If you give a single agent 45 tools (Database, AWS, Zendesk, GitHub, Jira), the system prompt becomes too long, and the LLM's attention degrades. It will start hallucinating tool arguments. 
*Solution:* Split into a `Database_Agent` (5 tools) and a `Cloud_Agent` (5 tools).

## 2. Asymmetric Prompts (The Echo Chamber)
If you want an agent to write highly creative, fast code, but also be paranoid and pedantic about security, the single LLM will struggle to balance those conflicting instructions in one prompt. It will compromise and write mediocre, mildly-secure code.
*Solution:* Split into a `Coder_Agent` (prompted for speed/creativity) and a `Security_Reviewer_Agent` (prompted for adversarial paranoia). Let them debate.

## 3. Asymmetric Security (RBAC boundaries)
If a user asks "Delete my account", the agent receiving the chat message should *never* have the `delete_account()` tool, because of Prompt Injection risks.
*Solution:* The `Chat_Agent` receives the message. It extracts the intent and passes a clean, typed JSON artifact to the internal, firewalled `Execution_Agent` which actually holds the high-privilege tool.
