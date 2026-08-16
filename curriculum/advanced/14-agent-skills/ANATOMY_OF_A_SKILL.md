# Deep Dive: Anatomy of a Skill

A Skill is an architectural abstraction that sits above raw tools. It represents **Procedural Knowledge**: telling an agent *how* to perform a workflow, rather than just giving it a tool and hoping for the best.

## The Skill Directory Structure

Skills should be version-controlled packages, structured like this:

```text
incident-analysis/
├── SKILL.md          # Metadata, triggers, workflow, guardrails
├── scripts/          # Deterministic Python/bash validators
├── references/       # Extra documentation (loaded only if needed)
└── assets/           # Report templates, JSON schemas
```

### The `SKILL.md` File
This is the heart of the skill. It MUST contain YAML frontmatter at the top:

```yaml
---
name: incident-analysis
version: 1.2.0
description: "Use for tenant-scoped SaaS checkout incidents. Produces a cited mitigation proposal."
---
```

Below the frontmatter, you write the Markdown instructions for the LLM. 
- *Step 1: Check Datadog metrics.*
- *Step 2: Compare against recent GitHub commits.*
- *Guardrail: DO NOT execute any rollbacks.*

## Progressive Disclosure
If you load 50 different skills into an agent's context window, you will burn massive amounts of tokens, and the agent will become hopelessly confused by conflicting instructions.

This is solved by **Progressive Disclosure**:
1. **Discovery:** The Orchestrator only loads the YAML `description` strings for the 50 skills. (Very cheap).
2. **Activation:** The Orchestrator picks one skill, and *only* loads the `SKILL.md` for that specific skill.
3. **Execution:** The agent reads the instructions. If the instructions say "Read the deep reference on database schemas", the agent explicitly tools into the `references/` folder to load it.

## Semantic Memory vs Procedural Knowledge
- **Semantic Memory:** "Deploy 842 changed the payment timeout." (A fact). This belongs in a RAG database.
- **Procedural Knowledge:** "To investigate a release, always check the payment timeout first." (A workflow). This belongs in a Skill.

Never hardcode semantic facts into a Skill, because when facts change, you don't want to have to rewrite your procedural workflows.
