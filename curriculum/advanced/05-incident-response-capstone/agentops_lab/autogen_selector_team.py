from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


MAX_TEAM_MESSAGES = 12
MAX_AGENT_TURNS = 4


@dataclass
class TeamMessage:
    speaker: str
    content: str


@dataclass
class SelectorTeamRun:
    messages: list[TeamMessage] = field(default_factory=list)
    turns_by_agent: dict[str, int] = field(default_factory=dict)
    stopped_reason: str = ""

    def add(self, speaker: str, content: str) -> None:
        self.messages.append(TeamMessage(speaker, content))
        self.turns_by_agent[speaker] = self.turns_by_agent.get(speaker, 0) + 1


AGENT_OWNERSHIP = {
    "observability": "Owns metrics and logs. Must not diagnose deployments.",
    "deployment": "Owns release history. Must not infer customer impact.",
    "customer_impact": "Owns affected segments and support reports.",
    "incident_analyst": "Synthesizes evidence and asks targeted follow-ups.",
    "risk_reviewer": "Challenges unsupported recommendations and risk.",
}


def selector_next(run: SelectorTeamRun) -> str:
    sequence = ["observability", "deployment", "customer_impact", "incident_analyst", "risk_reviewer", "incident_analyst"]
    return sequence[min(len(run.messages), len(sequence) - 1)]


def speak(agent: str) -> str:
    responses = {
        "observability": "Metrics show eu-west checkout-to-payment redirect down 38%; logs show 3DS callback errors.",
        "deployment": "A eu-west checkout UI release changed VAT validation and 3DS redirect handling before the drop.",
        "customer_impact": "Enterprise VAT-registered EU customers are most affected; support tickets mention redirect loops.",
        "incident_analyst": "Likely cause is the eu-west VAT/3DS UI change; recommend rollback or feature flag disablement.",
        "risk_reviewer": "Phrase as likely cause, verify rollback safety, and monitor conversion recovery before broad notification.",
    }
    return responses[agent]


def run_selector_team() -> SelectorTeamRun:
    run = SelectorTeamRun()
    while len(run.messages) < MAX_TEAM_MESSAGES:
        agent = selector_next(run)
        if run.turns_by_agent.get(agent, 0) >= MAX_AGENT_TURNS:
            run.stopped_reason = f"{agent} reached MAX_AGENT_TURNS"
            return run
        run.add(agent, speak(agent))
        if agent == "incident_analyst" and len(run.messages) >= 6:
            run.stopped_reason = "recommendation_ready"
            return run
    run.stopped_reason = "MAX_TEAM_MESSAGES"
    return run


def run_failure_loop() -> SelectorTeamRun:
    run = SelectorTeamRun()
    sequence = ["observability", "deployment", "incident_analyst"] * 5
    content = {
        "observability": "Probably deployment. Ask deployment.",
        "deployment": "Probably database. Ask observability.",
        "incident_analyst": "Evidence conflicts. Ask observability again.",
    }
    for agent in sequence:
        if len(run.messages) >= MAX_TEAM_MESSAGES:
            run.stopped_reason = "MAX_TEAM_MESSAGES"
            return run
        if run.turns_by_agent.get(agent, 0) >= MAX_AGENT_TURNS:
            run.stopped_reason = f"{agent} reached MAX_AGENT_TURNS"
            return run
        run.add(agent, content[agent])
    run.stopped_reason = "completed"
    return run


def ownership_rules() -> list[str]:
    return [f"{agent}: {rule}" for agent, rule in AGENT_OWNERSHIP.items()]


if __name__ == "__main__":
    successful = run_selector_team()
    print(successful.stopped_reason, len(successful.messages), successful.turns_by_agent)
    failure = run_failure_loop()
    print(failure.stopped_reason, len(failure.messages), failure.turns_by_agent)
