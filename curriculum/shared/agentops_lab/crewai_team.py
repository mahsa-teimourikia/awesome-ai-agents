from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentProfile:
    role: str
    goal: str
    backstory: str


@dataclass
class CrewTask:
    name: str
    description: str
    agent: AgentProfile
    context: list[str] = field(default_factory=list)
    output: str | None = None


OBSERVABILITY = AgentProfile(
    role="Observability Engineer",
    goal="Find operational evidence explaining the incident",
    backstory="Expert in logs, metrics, service health, and telemetry confidence.",
)

DEPLOYMENT = AgentProfile(
    role="Release Engineer",
    goal="Determine whether recent deployments contributed",
    backstory="Expert in rollout timelines, release notes, feature flags, and rollback risk.",
)

CUSTOMER_IMPACT = AgentProfile(
    role="Customer Impact Analyst",
    goal="Identify affected segments and support impact",
    backstory="Expert in customer tiers, SLAs, tickets, and regional segmentation.",
)

ANALYST = AgentProfile(
    role="Incident Commander",
    goal="Determine the most likely cause and recommend action",
    backstory="Synthesizes engineering evidence into a bounded incident plan.",
)


def execute_task(task: CrewTask, prior_outputs: dict[str, str]) -> str:
    if task.name == "metrics_task":
        return (
            "eu-west checkout-to-payment conversion is down 35%; cart-to-checkout clicks "
            "and payment authorization errors are normal; 3DS callback errors increased."
        )
    if task.name == "deployment_task":
        return (
            "checkout-ui 2026-08-07.1 changed VAT validation and 3DS redirect handling "
            "for eu-west before the conversion drop."
        )
    if task.name == "customer_task":
        return (
            "Enterprise VAT-registered EU customers are disproportionately affected; "
            "support tickets describe a 3DS redirect loop after VAT entry."
        )
    if task.name == "analysis_task":
        context = " ".join(prior_outputs[name] for name in task.context)
        return (
            "Likely cause: eu-west checkout UI VAT/3DS redirect change. "
            "Recommended plan: disable the feature flag or roll back checkout-ui in eu-west, "
            "monitor checkout-to-payment recovery, keep support messaging scoped to affected "
            f"enterprise EU customers, and mark root cause as likely until validated. Evidence: {context}"
        )
    raise ValueError(f"Unknown task: {task.name}")


def build_crew_tasks() -> list[CrewTask]:
    metrics_task = CrewTask(
        name="metrics_task",
        description="Investigate service telemetry.",
        agent=OBSERVABILITY,
    )
    deployment_task = CrewTask(
        name="deployment_task",
        description="Inspect recent deployments.",
        agent=DEPLOYMENT,
    )
    customer_task = CrewTask(
        name="customer_task",
        description="Analyze affected customer segments.",
        agent=CUSTOMER_IMPACT,
    )
    analysis_task = CrewTask(
        name="analysis_task",
        description="Synthesize evidence and produce an incident plan.",
        agent=ANALYST,
        context=["metrics_task", "deployment_task", "customer_task"],
    )
    return [metrics_task, deployment_task, customer_task, analysis_task]


def kickoff_crew() -> dict[str, object]:
    outputs: dict[str, str] = {}
    trace: list[dict[str, str]] = []
    for task in build_crew_tasks():
        task.output = execute_task(task, outputs)
        outputs[task.name] = task.output
        trace.append(
            {
                "task": task.name,
                "agent_role": task.agent.role,
                "description": task.description,
                "uses_context": ", ".join(task.context) if task.context else "none",
                "output": task.output,
            }
        )
    return {
        "mental_model": "Agents + Tasks + Crew",
        "trace": trace,
        "final_plan": outputs["analysis_task"],
        "comparison": {
            "crewai_help": "Clear role/task mapping and readable collaboration plan.",
            "langgraph_control": "More explicit state, branching, persistence, and policy checkpoints.",
            "autogen_conversation": "More natural shared conversation and selector-based speaker choice.",
            "openai_agents_sdk_simplicity": "Simpler for one bounded agent with tools, guardrails, tracing, and sessions.",
        },
    }


if __name__ == "__main__":
    result = kickoff_crew()
    print(result["mental_model"])
    for event in result["trace"]:
        print(f"{event['task']} -> {event['agent_role']} -> {event['uses_context']}")
    print(result["final_plan"])
