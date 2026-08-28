# Deep Dive: Selecting Models for Agentic Systems

The landscape of foundation models evolves rapidly. Rather than relying on static rankings of which model is the "industry leader," enterprise engineers must evaluate models based on specific agentic capabilities. General reasoning models have converged on native support for **Tool Calling** (Function Calling), strict **JSON outputs**, and deep **Instruction Following**, but they differ in latency, cost, and reliability under stress.

## Key Evaluation Dimensions

When choosing a model for an agent, raw parameter counts matter less than these factors:

1. **Tool-Call Accuracy (Reliability):** The ability to consistently output valid JSON that matches your schema without hallucinating parameters or dropping required fields.
2. **Instruction Following & Reasoning Quality:** Can the model synthesize multiple constraints (e.g., "Do not call X if Y is true") over a long context?
3. **Latency:** For critical agent loops (especially voice or real-time chat), specialized "Flash" or "Mini" models are preferred over their larger, slower counterparts.
4. **Cost:** Agentic loops consume significantly more tokens than simple chatbots because the prompt, schema, and tool history are re-submitted on every turn.
5. **Context Size:** The ability to hold large tool definitions (often dozens of tools) and long conversation histories without truncation or "lost in the middle" amnesia.
6. **Multimodality / Computer Use:** Does the agent need to process images, PDFs, audio, or drive a headless browser?
7. **Long-Horizon Behavior:** Does the model stay on track over 20+ steps, or does it lose the plot and loop?
8. **Deployment Model & Data Residency:** Does your organization require VPC deployment, open-weights hosting, or HIPAA compliance?

## Example Model Families (Mid-2026 Context)

*Note: Model capabilities and pricing change constantly. Always check official provider documentation for the most current specifications.*

- **OpenAI (GPT Family):** Often used for high-reliability tool calling, strict JSON validation, and complex reasoning.
- **Anthropic (Claude Family):** Highly favored for massive context windows and deep instruction following over long-horizon tasks.
- **Google (Gemini Family):** Known for massive multimodal context processing, cross-MCP coordination, and high throughput.
- **Meta (Llama Family):** Powerful open-weights models natively tuned for tool calling, ideal for local or air-gapped deployments.
- **DeepSeek:** Often chosen for high-accuracy function calling at a highly competitive cost-to-performance ratio.

## Internal Benchmarking (The Right Way to Choose)

Model selection should be benchmarked on your organization's **own tool schemas and task distribution**. A model that excels at standard SQL generation might fail at a highly nested proprietary JSON schema.

### Example Evaluation Matrix

| Capability | Model A (Frontier) | Model B (Flash/Mini) | Model C (Open Weights) |
| :--- | :--- | :--- | :--- |
| **Valid Schema Rate** | 99.5% | 96.0% | 94.5% |
| **Avg Latency (Time to First Token)**| 800ms | 250ms | Varies by hardware |
| **Context Limit** | 200k+ | 128k+ | 32k - 128k |
| **Cost per 1M Input Tokens** | $$$ | $ | $$ (Compute Cost) |
| **Best Fit** | Complex planning, recovery | High-volume fast routing | Air-gapped environments |

## Schema Design (Prompt Engineering 2.0)

The biggest improvement in tool-calling accuracy often comes from engineering the schema itself, rather than changing the underlying model:
- **Enums:** Using strict `enum` values instead of open strings forces the model onto tracks.
- **Descriptions:** Adding highly detailed descriptions to every parameter resolves ambiguity.
- **Routing:** If you have 20+ tools, use a two-step routing approach to avoid overwhelming the model's attention mechanism.

## Specialized Frameworks & Protocols

The industry is moving toward standardizing how models interact with infrastructure:
- **[MCP (Model Context Protocol)](https://modelcontextprotocol.io/):** Standardizes how models interact with infrastructure, databases, and APIs.
- **OpenAI Agents SDK & PydanticAI:** Tools to force models to output structured, validated JSON and manage handoffs smoothly.
- **LangGraph:** Graph-based orchestration ensuring predictable state transitions and durable execution for long-running agents.
