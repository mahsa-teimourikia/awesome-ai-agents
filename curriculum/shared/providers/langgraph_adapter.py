"""Provider-neutral LangGraph adapter seam.

The graph owns state transitions; a model adapter can be injected into nodes
without changing policy or evaluation code.
"""
from dataclasses import dataclass


@dataclass
class ModelAdapter:
    provider: str
    model: str

    def invoke(self, prompt: str) -> str:
        return f"{self.provider}/{self.model}: {prompt}"


if __name__ == "__main__":
    print(ModelAdapter("local-or-hosted", "configured-model").invoke("plan next safe step"))
