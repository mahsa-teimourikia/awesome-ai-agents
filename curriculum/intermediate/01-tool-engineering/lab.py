"""Credential-free Tool Engineering scenario for Northstar Commerce."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from time import sleep
from typing import Literal

class ToolError(Exception): pass
class ToolTimeout(ToolError): pass
class RateLimit(ToolError): pass
class InvalidRequest(ToolError): pass
class PermissionDenied(ToolError): pass
class ToolResultRejected(ToolError): pass

@dataclass(frozen=True)
class Actor:
    actor_id: str
    tenant_id: str
    scopes: frozenset[str]
    approved_actions: frozenset[str] = frozenset()

@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict
    tenant_id: str
    idempotency_key: str | None = None

@dataclass(frozen=True)
class ToolResult:
    source_id: str
    data: dict
    trusted_fields: tuple[str, ...]
    stale: bool = False

TOOLS = {
    "get_service_status": {"risk": "read", "scope": "ops.read"},
    "query_error_logs": {"risk": "read", "scope": "ops.read"},
    "get_recent_deployment": {"risk": "read", "scope": "ops.read"},
    "search_support_tickets": {"risk": "read", "scope": "support.read"},
    "create_incident_draft": {"risk": "propose", "scope": "ops.propose"},
    "restart_service": {"risk": "execute", "scope": "ops.execute"},
}
_IDEMPOTENCY: dict[str, ToolResult] = {}

def available_tools(actor: Actor, task: str) -> list[str]:
    candidates = ["get_service_status", "query_error_logs", "get_recent_deployment"]
    if "customer" in task.lower(): candidates.append("search_support_tickets")
    if "draft" in task.lower() or "incident" in task.lower(): candidates.append("create_incident_draft")
    return [name for name in candidates if TOOLS[name]["scope"] in actor.scopes]

def validate_call(call: ToolCall) -> None:
    if call.name not in TOOLS: raise InvalidRequest(f"Unknown tool: {call.name}")
    if call.tenant_id != "northstar": raise PermissionDenied("Cross-tenant tool call blocked.")
    if call.name == "query_error_logs":
        minutes = call.arguments.get("minutes")
        if not isinstance(minutes, int) or not 1 <= minutes <= 240: raise InvalidRequest("minutes must be 1..240")
    if TOOLS[call.name]["risk"] == "execute" and not call.idempotency_key: raise InvalidRequest("Execute tools need an idempotency key.")

def authorize(actor: Actor, call: ToolCall) -> None:
    meta = TOOLS[call.name]
    if meta["scope"] not in actor.scopes: raise PermissionDenied(f"Missing {meta['scope']}")
    if meta["risk"] == "execute" and call.name not in actor.approved_actions: raise PermissionDenied("Approval required.")

def _result(source_id: str, **data: object) -> ToolResult:
    return ToolResult(source_id, dict(data), tuple(data))

def execute(call: ToolCall, actor: Actor) -> ToolResult:
    validate_call(call); authorize(actor, call)
    if call.idempotency_key in _IDEMPOTENCY: return _IDEMPOTENCY[call.idempotency_key]
    if call.name == "get_service_status": result = _result("status-eu-482", service="checkout", health="degraded")
    elif call.name == "query_error_logs": result = _result("logs-eu-482", error="3DS signature mismatch", count=147, minutes=call.arguments["minutes"])
    elif call.name == "get_recent_deployment": result = _result("deploy-2026.08.10.1", version="2026.08.10.1", minutes_ago=22)
    elif call.name == "search_support_tickets": result = _result("tickets-eu-482", complaints=6, sla_risk=True)
    elif call.name == "create_incident_draft": result = _result("draft-inc-482", incident="INC-482", status="draft")
    elif call.name == "restart_service": result = _result("action-482", status="executed", service=call.arguments["service"])
    else: raise InvalidRequest(call.name)
    if call.idempotency_key: _IDEMPOTENCY[call.idempotency_key] = result
    return result

def validate_result(result: ToolResult) -> ToolResult:
    if result.stale or not result.source_id or not result.trusted_fields: raise ToolResultRejected("Unattributable result")
    if "ignore previous" in str(result.data).lower(): raise ToolResultRejected("Instruction-like tool output")
    return result

def classify_failure(error: Exception) -> Literal["retry", "escalate", "stop"]:
    if isinstance(error, (ToolTimeout, RateLimit)): return "retry"
    if isinstance(error, PermissionDenied): return "escalate"
    return "stop"

def retry_read(call: ToolCall, actor: Actor, failures_before_success=0, max_attempts=3) -> ToolResult:
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt <= failures_before_success: raise ToolTimeout("simulated timeout")
            return validate_result(execute(call, actor))
        except ToolError as error:
            if classify_failure(error) != "retry" or attempt == max_attempts: raise
            sleep(0.01 * attempt)
    raise AssertionError("unreachable")

def parallel_read(calls: list[ToolCall], actor: Actor) -> list[ToolResult]:
    if any(TOOLS[c.name]["risk"] != "read" for c in calls): raise InvalidRequest("Parallel calls must be read-only.")
    with ThreadPoolExecutor(max_workers=min(4, len(calls))) as pool:
        return list(pool.map(lambda c: validate_result(execute(c, actor)), calls))

def sequential_investigation(actor: Actor) -> list[ToolResult]:
    status = retry_read(ToolCall("c1", "get_service_status", {}, "northstar"), actor, failures_before_success=1)
    logs = retry_read(ToolCall("c2", "query_error_logs", {"minutes": 60}, "northstar"), actor)
    deploy = retry_read(ToolCall("c3", "get_recent_deployment", {}, "northstar"), actor)
    return [status, logs, deploy]

if __name__ == "__main__":
    reader = Actor("incident-agent", "northstar", frozenset({"ops.read", "support.read", "ops.propose"}))
    results = sequential_investigation(reader) + parallel_read([ToolCall("c4", "search_support_tickets", {}, "northstar")], reader)
    print([asdict(x) for x in results])
    print(execute(ToolCall("c5", "create_incident_draft", {}, "northstar", "draft-482-v1"), reader))
