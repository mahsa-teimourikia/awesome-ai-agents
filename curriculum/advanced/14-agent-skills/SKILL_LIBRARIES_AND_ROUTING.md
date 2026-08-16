# Deep Dive: Skill Libraries and Routing

When an enterprise scales, they don't have 5 skills. They have 500 skills managed by different teams.

## The Semantic Router
How does an Orchestrator Agent know which of the 500 skills to use when a user says *"The checkout is broken"*?

It uses a **Semantic Router**. 
1. The Orchestrator takes the YAML `description` from all 500 skills and converts them into Vector Embeddings.
2. It converts the user's prompt into an Embedding.
3. It performs a Cosine Similarity search to find the Top-3 most relevant skills.
4. The Orchestrator LLM then reads the descriptions of those Top-3 and picks the exact right one to activate.

### The Description is a Routing Interface
Because routing relies entirely on the `description`, a bad description will break your architecture.

**Bad Description:** *"Handle anything about incidents. I am an expert analyst."* (The router will trigger this for everything, causing chaos).
**Good Description:** *"Trigger this ONLY for EU SaaS checkout incidents that require reading Datadog metrics."*

## Supply-Chain Security for Skills
Skills are essentially supply-chain inputs. Because a skill can contain `scripts/helper.py`, a malicious internal actor could submit a PR to modify a skill's python script to exfiltrate API keys.

**Security Controls:**
1. **Cryptographic Hashing:** When a skill is approved by security, its directory is hashed. At runtime, the Orchestrator checks the hash. If the script was modified outside of CI/CD, the Orchestrator refuses to load it.
2. **No Self-Widening Authority:** A skill's `SKILL.md` might say *"I am allowed to delete the production database."* **This means nothing.** A skill is just text. The Orchestrator and the IAM policy dictate what tools the agent actually has access to. A skill cannot widen its own authority.
