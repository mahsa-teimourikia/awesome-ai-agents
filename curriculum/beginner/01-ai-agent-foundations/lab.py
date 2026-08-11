"""Deterministic architecture-selection lab for the Agent Foundations lesson."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Architecture(str, Enum):
    AUTOMATION = "traditional_automation"
    WORKFLOW = "deterministic_workflow"
    RAG = "rag_assistant"
    AGENT = "bounded_agent"
    HUMAN = "human_approved_workflow"


@dataclass(frozen=True)
class Task:
    name: str
    known_path: bool
    needs_current_evidence: bool
    dynamic_tool_choice: bool
    irreversible_action: bool = False


def choose_architecture(task: Task) -> Architecture:
    """Apply the least-autonomous-reliable-design rule deterministically."""
    if task.irreversible_action:
        return Architecture.HUMAN
    if task.known_path and not task.needs_current_evidence:
        return Architecture.AUTOMATION
    if task.known_path:
        return Architecture.WORKFLOW
    if task.needs_current_evidence and not task.dynamic_tool_choice:
        return Architecture.RAG
    return Architecture.AGENT


def architecture_rationale(task: Task, chosen: Architecture) -> str:
    reasons = {
        Architecture.AUTOMATION: "Known steps and no current-evidence reasoning: fixed code is safer and cheaper.",
        Architecture.WORKFLOW: "The path is known; use explicit branching and audit each step.",
        Architecture.RAG: "The primary need is current evidence, not model-directed action selection.",
        Architecture.AGENT: "The evidence path is uncertain; permit bounded tool selection with budgets and policy.",
        Architecture.HUMAN: "The action is consequential or irreversible; prepare evidence but require approval.",
    }
    return reasons[chosen]


DEMO_TASKS = [
    Task("Copy CRM tier to a ticket", known_path=True, needs_current_evidence=False, dynamic_tool_choice=False),
    Task("Create a daily checkout health report", known_path=True, needs_current_evidence=True, dynamic_tool_choice=False),
    Task("Answer a policy question with citations", known_path=False, needs_current_evidence=True, dynamic_tool_choice=False),
    Task("Investigate regional checkout failures", known_path=False, needs_current_evidence=True, dynamic_tool_choice=True),
    Task("Restart checkout during an incident", known_path=False, needs_current_evidence=True, dynamic_tool_choice=True, irreversible_action=True),
]


if __name__ == "__main__":
    for task in DEMO_TASKS:
        choice = choose_architecture(task)
        print(f"{task.name}: {choice.value}\n  {architecture_rationale(task, choice)}")
