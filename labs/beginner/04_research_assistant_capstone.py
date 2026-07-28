"""Beginner capstone: a cited, budgeted research assistant skeleton."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    source_id: str
    text: str


def answer(question: str, evidence: list[Evidence], budget: int = 3) -> dict:
    selected = evidence[:budget]
    if not selected:
        return {"answer": "I do not have enough evidence.", "citations": [], "abstained": True}
    return {"answer": f"Answer grounded in {len(selected)} passages for: {question}", "citations": [e.source_id for e in selected], "abstained": False}


if __name__ == "__main__":
    print(answer("what is the policy?", [Evidence("policy-1", "..."), Evidence("policy-2", "...")]))
    print(answer("unsupported question", []))
