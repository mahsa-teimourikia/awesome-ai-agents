"""Advanced capstone: bounded research team with evidence and evaluation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    role: str
    claim: str
    source_ids: tuple[str, ...]


def run_team(question: str) -> dict:
    findings = [
        Finding("searcher", f"evidence about {question}", ("source-1",)),
        Finding("critic", f"limitation of evidence about {question}", ("source-2",)),
    ]
    sources = sorted({source for finding in findings for source in finding.source_ids})
    return {"claims": [finding.claim for finding in findings], "citations": sources, "escalate": not sources}


if __name__ == "__main__":
    print(run_team("agent safety"))
