"""Workflow-versus-agent comparison plus a cited research-assistant capstone."""
from dataclasses import dataclass
from pathlib import Path
import runpy
import sys


@dataclass(frozen=True)
class Evidence:
    """A retrieved passage with a stable source identifier."""
    source_id: str
    text: str


def answer_with_evidence(question: str, evidence: list[Evidence], budget: int = 3) -> dict:
    """A deterministic RAG-style baseline: evidence and citations, no agent loop."""
    selected = evidence[:budget]
    if not selected:
        return {"answer": "I do not have enough evidence.", "citations": [], "abstained": True}
    return {
        "answer": f"Answer grounded in {len(selected)} passages for: {question}",
        "citations": [item.source_id for item in selected],
        "abstained": False,
    }


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone"))
from agentops_lab.workflow_or_agent import *  # noqa: F401,F403

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone" / "agentops_lab" / "workflow_or_agent.py"), run_name="__main__")
    print(answer_with_evidence("What is the checkout policy?", [Evidence("policy-1", "Use the fallback path."), Evidence("policy-2", "Escalate active incidents.")]))
    print(answer_with_evidence("Unsupported question", []))
