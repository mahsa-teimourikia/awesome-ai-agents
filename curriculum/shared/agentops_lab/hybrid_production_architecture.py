from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncidentRequest:
    text: str
    risk: str
    ambiguity: str
    known_path: bool
    customer_impact: str


@dataclass(frozen=True)
class RoutedPlan:
    route: str
    architecture: str
    reason: str
    policy_checks: list[str]
    approval_required: bool
    action: str


def classify_task(request: IncidentRequest) -> str:
    if request.known_path and request.risk == "low":
        return "simple_lookup"
    if request.risk == "high" or request.customer_impact == "major":
        return "high_risk_case"
    if request.ambiguity in {"medium", "high"}:
        return "investigation"
    return "simple_lookup"


def policy_checks(route: str) -> list[str]:
    checks = ["tool allowlist", "evidence required", "budget limit", "audit log"]
    if route == "high_risk_case":
        checks.extend(["human approval", "rollback preview", "customer-impact review"])
    if route == "investigation":
        checks.append("confidence threshold")
    return checks


def plan_architecture(request: IncidentRequest) -> RoutedPlan:
    route = classify_task(request)
    if route == "simple_lookup":
        return RoutedPlan(
            route=route,
            architecture="deterministic workflow",
            reason="The steps are known and the task does not need dynamic tool selection.",
            policy_checks=policy_checks(route),
            approval_required=False,
            action="Read service status and format a report.",
        )
    if route == "investigation":
        return RoutedPlan(
            route=route,
            architecture="single bounded agent",
            reason="The evidence path is not obvious, but one agent can inspect health, incidents, logs, deployments, and runbooks within budgets.",
            policy_checks=policy_checks(route),
            approval_required=False,
            action="Investigate, summarize evidence, and propose a non-destructive recommendation.",
        )
    return RoutedPlan(
        route=route,
        architecture="agent team inside deterministic workflow",
        reason="The case is high-impact and benefits from specialist evidence plus risk review, but policy and approval remain outside the agents.",
        policy_checks=policy_checks(route),
        approval_required=True,
        action="Run specialist team, apply policy checks, pause for human approval before rollback or notification.",
    )


def run_examples() -> list[RoutedPlan]:
    examples = [
        IncidentRequest(
            text="Retrieve current checkout status.",
            risk="low",
            ambiguity="low",
            known_path=True,
            customer_impact="minor",
        ),
        IncidentRequest(
            text="European customers report intermittent checkout failures.",
            risk="medium",
            ambiguity="high",
            known_path=False,
            customer_impact="moderate",
        ),
        IncidentRequest(
            text="Checkout conversion has fallen 35% for enterprise EU customers.",
            risk="high",
            ambiguity="high",
            known_path=False,
            customer_impact="major",
        ),
    ]
    return [plan_architecture(example) for example in examples]


if __name__ == "__main__":
    for plan in run_examples():
        print(f"{plan.route}: {plan.architecture}")
        print(f"  reason: {plan.reason}")
        print(f"  checks: {', '.join(plan.policy_checks)}")
        print(f"  approval_required: {plan.approval_required}")
