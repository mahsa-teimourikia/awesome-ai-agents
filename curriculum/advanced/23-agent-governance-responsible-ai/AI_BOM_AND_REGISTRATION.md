# Deep Dive: The AI BOM and Agent Registration

Before a software artifact is deployed, modern CI/CD pipelines require a Software Bill of Materials (SBOM) to track dependencies (like `requests==2.31.0`). 

For AI Agents, this must be expanded into an **AI BOM (Bill of Materials)**.

## The AI Bill of Materials (AI BOM)

An AI BOM cryptographically binds the specific components of an agent to a specific release version. If an incident occurs, investigators must know exactly what was running.

An Agent AI BOM must include:
- **Foundation Models:** e.g., `gpt-4o-2024-08-06` or `claude-3-5-sonnet-20240620`.
- **System Prompts:** The exact Git commit hash of the prompt template used.
- **Tool Dependencies:** The exact version of the MCP servers or API SDKs the agent relies on.
- **Data Provenance:** The specific vector database collections the agent has access to.

### Raw JSON AI BOM Example
```json
{
  "agent_id": "support-adviser-agent",
  "version": "v1.4.2",
  "owner": "jane.doe@northstar.internal",
  "foundation_model": "gpt-4o-2024-08-06",
  "system_prompt_hash": "a1b2c3d4e5f6...",
  "tools": [
    {"name": "query_tickets", "version": "1.0.0"},
    {"name": "issue_refund", "version": "2.1.0", "requires_approval": true}
  ],
  "risk_tier": "High Risk (Tier 2)",
  "compliance_frameworks": ["NIST AI RMF", "SOC2"]
}
```

## Deployment Gates and Human Ownership

**An agent must never be deployed without an accountable Human Owner.**

If the CI/CD pipeline detects that the AI BOM's `owner` field is missing, or points to a generic distribution list (`support-team@domain`), the pipeline must fail the deployment. When an agent breaks the law, deletes a database, or hallucinates financial advice, a specific human must be legally and operationally accountable.

## The Global Kill Switch

If an agent is hijacked via Prompt Injection, it might enter an infinite loop, calling `issue_refund` 1,000 times a second. 

A human cannot SSH into a server fast enough to stop this. You must implement a **Global Kill Switch**.

### How it works:
1. The Security Operations Center (SOC) detects an anomaly (e.g., Action Budget exceeded).
2. The SOC invokes the Kill Switch API for `support-adviser-agent`.
3. The IAM system instantly revokes the agent's Workload Identity (e.g., its SPIFFE SVID or AWS IAM Role).
4. Any active tool executions immediately fail with `401 Unauthorized`.
5. The orchestration framework crashes safely.

The Kill Switch must operate at the Identity and Network layers, not inside the agent's code. A hijacked agent cannot be trusted to shut itself down.
