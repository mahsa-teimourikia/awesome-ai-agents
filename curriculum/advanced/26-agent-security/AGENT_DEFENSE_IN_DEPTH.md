# Deep Dive: Agent Defense-in-Depth

Relying solely on a system prompt (e.g., "Do not do bad things") is not security. Modern agent architectures require layered defenses spanning the network, the runtime environment, and the application layer.

## 1. Input/Output Guardrails (Application Layer)

Guardrails act as a firewall for LLMs. They intercept prompts before they reach the model, and intercept completions before they trigger tools.

### State of the Art Tools:
- **Lakera Guard:** An API-based firewall specifically trained to detect prompt injection, jailbreaks, and PII leakage.
- **NeMo Guardrails (NVIDIA):** An open-source toolkit that lets you define programmatic dialog flows (e.g., "If the user asks about politics, force the agent to reply 'I cannot answer that' and halt execution").

**Implementation Strategy:**
Instead of sending a user's email directly to your Agent, you send it to the Guardrail. If the Guardrail detects an injection attempt, it drops the request and logs an alert.

## 2. Sandboxing & Code Execution (Runtime Layer)

If you grant an agent the ability to write and execute code (e.g., a Data Analysis agent running Python), you are introducing **ASI05: Unexpected Code Execution**. If the agent is hijacked, it could run `os.system("rm -rf /")`.

### State of the Art Tools:
- **E2B (English2Bits):** Secure, micro-VM sandboxes designed specifically for AI agents. They boot in milliseconds.
- **Docker/gVisor:** Traditional containerization with strict seccomp profiles to prevent malicious syscalls.

**Implementation Strategy:**
Never run `eval()` or `exec()` in the same environment hosting your orchestration framework. The agent must pass the code payload to a remote, ephemeral sandbox. The sandbox executes the code, returns the output, and immediately self-destructs.

## 3. Tool Authorization & Egress (Network Layer)

Even if an agent decides to call a malicious tool, the network and identity layers should stop it.

### State of the Art Approaches:
- **Identity (OAuth/Vault):** Agents should retrieve short-lived, scoped tokens from a secret manager (like HashiCorp Vault) just-in-time for a tool call.
- **Egress Allow-listing (VPC):** The server hosting the agent should have strict firewall rules. If the agent tries to send data to `http://attacker-server.com`, the VPC network should block the TCP connection.

## 4. Human-in-the-Loop (HITL)

For irreversible actions (e.g., executing a Git commit, dropping a database table, transferring funds), technical controls are not enough. You must implement HITL.

**Implementation Strategy:**
The agent's state machine pauses, serializes its state to a database, and waits for a human to click "Approve" before the orchestration framework resumes execution. (See module `28-human-agent-collaboration`).
