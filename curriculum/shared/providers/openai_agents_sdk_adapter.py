"""Provider adapter seam for the OpenAI Agents SDK.

Install the optional SDK separately; keep this boundary behind your tested
policy, tracing, and tool-validation layers.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    name: str
    instructions: str
    max_turns: int = 6


def build_config() -> AgentConfig:
    return AgentConfig("researcher", "Use approved tools, cite evidence, and abstain when unsupported.")


if __name__ == "__main__":
    print(build_config())
