# Deep Dive: Skills vs MCP (Model Context Protocol)

There is massive confusion in the industry between "Agent Tools" and "Agent Skills." This confusion is often centered around the Model Context Protocol (MCP).

## What is MCP?
MCP is a standardized boundary for exposing **Raw Tools** to an LLM. 
For example, an MCP Server might expose a tool called `read_github_commit(sha)`.

MCP handles:
- **Authorization:** Does this agent's JWT token allow it to read GitHub?
- **Execution:** Running the actual API call to GitHub.

## What is a Skill?
A Skill is the **Procedural Instructions** on *how* and *when* to use that MCP tool.

If an agent just has the `read_github_commit` MCP tool, it might use it randomly or inefficiently. 

If you equip the agent with an `incident-analysis` Skill, the `SKILL.md` instructions will say:
*"Step 1: Check Datadog. Step 2: Only if Datadog shows a spike, use the `read_github_commit` MCP tool to check recent changes. Step 3: Format the output using the `assets/report.json` schema."*

## The Separation of Concerns
1. **MCP** is the Application/Security layer. It enforces hard boundaries.
2. **Skills** are the Prompt/Behavioral layer. They guide the LLM's reasoning.

**Crucial Rule:** A Skill can *recommend* that an agent use an MCP tool. But the MCP gateway is what actually *authorizes* the call. If a Skill tells an agent to use a tool that the agent's identity isn't scoped for, the MCP server will reject the call, and the Skill will fail gracefully.
