from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentops_lab.workflow_or_agent import get_recent_deployments, query_region_logs


class ToolTimeout(Exception):
    pass


class RateLimit(Exception):
    pass


class InvalidService(Exception):
    pass


class PermissionDenied(Exception):
    pass


ALLOWED_SERVICES = {"checkout", "payments", "catalog"}


def admin_api(command: str) -> dict[str, str]:
    """A deliberately terrible tool: broad, stringly typed, and high risk."""
    lowered = command.lower()
    if "delete" in lowered:
        return {"status": "executed", "risk": "critical", "message": "records deleted"}
    if "restart" in lowered:
        return {"status": "executed", "risk": "high", "message": "service restarted"}
    if "deploy" in lowered:
        return {"status": "executed", "risk": "high", "message": "software deployed"}
    if "notify" in lowered:
        return {"status": "executed", "risk": "medium", "message": "notification sent"}
    return {"status": "executed", "risk": "unknown", "message": "command accepted"}


@dataclass
class RestartRequest:
    service: Literal["checkout", "payments", "catalog"]
    reason: str
    incident_id: str

    def validate(self) -> None:
        if self.service not in ALLOWED_SERVICES:
            raise InvalidService(f"Unsupported service: {self.service}")
        if len(self.reason.strip()) < 20:
            raise ValueError("Restart reason must be at least 20 characters.")
        if not self.incident_id.startswith("INC-"):
            raise ValueError("incident_id must look like INC-1234.")


def query_logs(service: str, time_range_minutes: int, severity: Literal["INFO", "WARN", "ERROR"]) -> dict:
    if service not in ALLOWED_SERVICES:
        raise InvalidService(service)
    if time_range_minutes <= 0 or time_range_minutes > 240:
        raise ValueError("time_range_minutes must be between 1 and 240.")
    return query_region_logs(service, "eu-west", severity)


def restart_service(request: RestartRequest, approved: bool = False) -> dict[str, str]:
    request.validate()
    if not approved:
        raise PermissionDenied("Restart requires human approval in this lab.")
    return {"status": "restarted", "service": request.service, "incident_id": request.incident_id}


def create_incident_ticket(title: str, severity: Literal["sev1", "sev2", "sev3"], evidence: list[str]) -> dict[str, str]:
    if severity not in {"sev1", "sev2", "sev3"}:
        raise ValueError("severity must be sev1, sev2, or sev3.")
    if len(evidence) < 2:
        raise ValueError("incident tickets require at least two evidence items.")
    return {"ticket_id": "INC-2001", "title": title, "severity": severity, "status": "created"}


def flaky_logs(service: str, attempts_before_success: int, attempt: int) -> dict:
    if attempt < attempts_before_success:
        raise ToolTimeout("regional log backend timed out")
    return query_logs(service, 60, "ERROR")


def retry_policy(error: Exception) -> Literal["retry", "escalate", "stop"]:
    if isinstance(error, (ToolTimeout, RateLimit)):
        return "retry"
    if isinstance(error, PermissionDenied):
        return "escalate"
    return "stop"


def run_with_retry(max_attempts: int = 3, attempts_before_success: int = 2) -> dict:
    errors = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = flaky_logs("checkout", attempts_before_success, attempt)
            return {"status": "success", "attempts": attempt, "result": result, "errors": errors}
        except Exception as exc:
            decision = retry_policy(exc)
            errors.append({"attempt": attempt, "error": type(exc).__name__, "decision": decision})
            if decision != "retry":
                return {"status": decision, "attempts": attempt, "errors": errors}
    return {"status": "stop", "attempts": max_attempts, "errors": errors}


def compare_bad_and_good_tools() -> dict:
    risky = admin_api("restart checkout and delete failed payment records")
    deployments = get_recent_deployments("checkout")
    ticket = create_incident_ticket(
        title="European checkout 3DS failures",
        severity="sev2",
        evidence=["eu-west 3DS callback errors", "active checkout payment incident"],
    )
    retry = run_with_retry()
    return {"admin_api_result": risky, "deployments": deployments, "ticket": ticket, "retry": retry}


if __name__ == "__main__":
    print(compare_bad_and_good_tools())
    try:
        restart_service(RestartRequest("checkout", "Need approval for regional checkout recovery", "INC-1042"))
    except Exception as exc:
        print({"restart_decision": retry_policy(exc), "error": type(exc).__name__, "message": str(exc)})
