"""Credential-free durable-job simulation with checkpoints and external-event resume."""
from dataclasses import dataclass, field

@dataclass
class Job:
    job_id: str; tenant: str; state: str = "new"; steps: int = 0; deadline_step: int = 5; audit: list[str] = field(default_factory=list)

def checkpoint(job: Job, state: str) -> None:
    job.state = state; job.audit.append(f"checkpoint:{state}")

def start(job: Job) -> None:
    checkpoint(job, "waiting-for-evidence")

def resume(job: Job, event: str) -> str:
    if job.state not in {"waiting-for-evidence", "waiting-for-approval"}: return "ignored"
    if job.steps >= job.deadline_step: checkpoint(job, "expired"); return "expired"
    job.steps += 1
    if event == "evidence-ready": checkpoint(job, "waiting-for-approval"); return "approval-requested"
    if event == "approved" and job.state == "waiting-for-approval": checkpoint(job, "complete"); return "complete"
    if event == "rejected": checkpoint(job, "cancelled"); return "cancelled"
    return "ignored"

def recover(serialized: Job) -> Job:
    serialized.audit.append("recovered-from-checkpoint"); return serialized

def run_demo() -> Job:
    job = Job("job-42", "acme"); start(job)
    assert resume(job, "evidence-ready") == "approval-requested"
    recovered = recover(job)
    assert resume(recovered, "approved") == "complete"
    return recovered

if __name__ == "__main__": print(run_demo())
