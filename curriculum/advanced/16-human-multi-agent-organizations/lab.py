"""Credential-free human + multi-agent organization simulator."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class Status(str, Enum): PROPOSED="proposed"; ACTIVE="active"; ESCALATED="escalated"; REVIEW="review"; COMPLETE="complete"

@dataclass(frozen=True)
class WorkOrder:
    id: str; owner: str; objective: str; allowed_sources: tuple[str,...]; write_access: bool=False

@dataclass
class Artifact:
    work_order_id: str; owner: str; claim: str; evidence_ids: list[str]; confidence: float; limits: list[str]

@dataclass
class OrganizationRun:
    tenant: str; objective: str; status: Status=Status.PROPOSED; work: list[WorkOrder]=field(default_factory=list)
    artifacts: list[Artifact]=field(default_factory=list); events: list[str]=field(default_factory=list); approved: bool=False

def delegate(run: OrganizationRun) -> None:
    """Manager decomposes a bounded task; specialists receive least-privilege read scope."""
    run.status=Status.ACTIVE
    run.work=[
      WorkOrder("research","research-agent","Find relevant runbook and historical-incident evidence.",("runbooks","incidents")),
      WorkOrder("data","data-agent","Measure EU and Gold-tier impact from approved telemetry.",("metrics","customers")),
      WorkOrder("code","coding-agent","Inspect deployment diff; do not modify production.",("deployments","repository")),
      WorkOrder("analysis","analysis-agent","Synthesize only supplied artifacts into hypotheses.",()),
      WorkOrder("review","review-agent","Challenge evidence, scope, risk, and proposed action.",()),
    ]
    run.events.append("manager:delegated-5-bounded-work-orders")

def produce_artifacts(run: OrganizationRun) -> None:
    """Specialists return attributable artifacts, not free-form messages or effects."""
    facts=[
      ("research","Provider region-mismatch runbook matches symptoms.",["runbook:payment-region-v3","incident:418"],.82,["Runbook is advisory, not authorization."]),
      ("data","EU conversion is down 31%; Gold-tier cohort has 17 affected accounts.",["metric:eu-conversion","customer:gold-cohort"],.95,["Correlation does not prove deployment cause."]),
      ("code","08:42 deployment changed EU provider-region mapping.",["deployment:842","diff:provider-map"],.91,["No live configuration was inspected."]),
      ("analysis","Most likely cause: region mapping regression; prepare scoped rollback proposal.",["artifact:research","artifact:data","artifact:code"],.84,["Requires reviewer validation before action."]),
      ("review","Evidence supports a proposal, not execution; confirm change window and exact rollback scope.",["artifact:analysis"],.9,["Human approver must validate scope and impact."]),
    ]
    for owner,claim,evidence,confidence,limits in facts:
        run.artifacts.append(Artifact(owner,owner,claim,evidence,confidence,limits))
    run.status=Status.REVIEW; run.events.append("manager:assembled-review-packet")

def human_review(run: OrganizationRun, approve: bool) -> None:
    """Human owns the consequential decision; approval is deliberately external to specialists."""
    if run.status is not Status.REVIEW: raise RuntimeError("Review packet required before approval")
    run.approved=approve
    run.status=Status.COMPLETE if approve else Status.ESCALATED
    run.events.append("human:approved-proposal" if approve else "human:escalated-for-more-evidence")

def run_demo() -> OrganizationRun:
    run=OrganizationRun("northstar-acme","Investigate EU checkout conversion drop; prepare but do not execute mitigation.")
    delegate(run); produce_artifacts(run); human_review(run, approve=False)
    assert not run.approved and run.status is Status.ESCALATED
    assert all(not w.write_access for w in run.work)
    assert all(a.evidence_ids for a in run.artifacts)
    return run

if __name__=="__main__":
    result=run_demo(); print(result.status.value); print("\n".join(result.events))
