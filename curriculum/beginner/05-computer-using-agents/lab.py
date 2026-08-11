"""Credential-free computer-use agent simulator for the support-portal lesson.

No browser, OS, filesystem, network, secret, or real UI is controlled here. The
simulation models the boundary a production controller must enforce: a model can
propose a grounded action, while an application validates target, domain, risk,
confirmation, and state transition before applying it to a disposable sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Risk(str, Enum):
    READ = "read"
    DRAFT = "draft"
    COMMIT = "commit"


@dataclass(frozen=True)
class Element:
    id: str
    role: str
    label: str
    bounds: tuple[int, int, int, int]
    risk: Risk = Risk.READ


@dataclass(frozen=True)
class Action:
    kind: str
    target: str | None = None
    text: str | None = None
    coordinates: tuple[int, int] | None = None
    expected_label: str | None = None


@dataclass
class SandboxPolicy:
    allowed_origins: set[str] = field(default_factory=lambda: {"https://support.northstar.test"})
    allowed_actions: set[str] = field(default_factory=lambda: {"navigate", "click", "type", "observe", "confirm"})
    require_confirmation_for: set[Risk] = field(default_factory=lambda: {Risk.COMMIT})
    max_actions: int = 12


@dataclass
class Session:
    origin: str = "https://support.northstar.test"
    screen: str = "home"
    actions: list[str] = field(default_factory=list)
    pending_confirmation: Action | None = None
    ticket_draft: dict[str, str] = field(default_factory=dict)
    submitted: bool = False
    ui_variant: str = "original"


def visible_elements(session: Session) -> list[Element]:
    """The screenshot/accessibility snapshot presented to the agent controller."""
    if session.screen == "home":
        return [
            Element("tickets", "link", "Tickets", (40, 100, 160, 48)),
            Element("search", "textbox", "Search support cases", (40, 180, 420, 44)),
        ]
    if session.screen == "tickets":
        return [
            Element("case-418", "row", "Case 418 — Acme billing renewal failed", (40, 120, 600, 56)),
            Element("back", "link", "Home", (40, 50, 100, 36)),
        ]
    if session.screen == "case":
        draft_label = "Escalate" if session.ui_variant == "original" else "Create escalation draft"
        return [
            Element("case-title", "heading", "Case 418 — Acme billing renewal failed", (40, 80, 700, 52)),
            Element("notes", "textbox", "Internal escalation notes", (40, 190, 650, 130), Risk.DRAFT),
            Element("draft", "button", draft_label, (40, 345, 260, 46), Risk.DRAFT),
        ]
    if session.screen == "draft":
        return [
            Element("summary", "status", "Draft: Acme billing escalation", (40, 90, 600, 48)),
            Element("submit", "button", "Submit escalation", (40, 180, 260, 46), Risk.COMMIT),
            Element("cancel", "button", "Discard draft", (320, 180, 190, 46), Risk.COMMIT),
        ]
    return []


def screenshot_summary(session: Session) -> list[dict[str, object]]:
    """A stand-in for grounded perception: labels, roles, and pixel rectangles."""
    return [
        {"id": e.id, "role": e.role, "label": e.label, "bounds": e.bounds, "risk": e.risk.value}
        for e in visible_elements(session)
    ]


def resolve_visual_target(session: Session, action: Action) -> Element:
    """Ground a click by label/role and verify an optional coordinate falls inside it."""
    candidates = visible_elements(session)
    if action.target:
        candidates = [e for e in candidates if e.id == action.target]
    if action.expected_label:
        candidates = [e for e in candidates if action.expected_label.casefold() in e.label.casefold()]
    if len(candidates) != 1:
        raise ValueError("Grounding failed: expected exactly one visible target")
    element = candidates[0]
    if action.coordinates:
        x, y = action.coordinates
        left, top, width, height = element.bounds
        if not (left <= x <= left + width and top <= y <= top + height):
            raise ValueError("Grounding failed: click is outside the verified target")
    return element


def validate_action(session: Session, policy: SandboxPolicy, action: Action) -> Element | None:
    if len(session.actions) >= policy.max_actions:
        raise PermissionError("Action budget exhausted")
    if session.origin not in policy.allowed_origins:
        raise PermissionError("Origin is not allowlisted")
    if action.kind not in policy.allowed_actions:
        raise PermissionError(f"Action {action.kind!r} is not allowed")
    if action.kind in {"click", "type"}:
        return resolve_visual_target(session, action)
    return None


def apply_action(session: Session, policy: SandboxPolicy, action: Action, approved: bool = False) -> str:
    """Validate, then apply one simulated action to a disposable state machine."""
    target = validate_action(session, policy, action)
    if target and target.risk in policy.require_confirmation_for and not approved:
        session.pending_confirmation = action
        session.actions.append(f"paused for confirmation: {target.label}")
        return "PAUSED: confirmation required"
    if action.kind == "navigate":
        if action.target != "tickets":
            raise ValueError("Only the sandbox tickets route is available")
        session.screen = "tickets"
    elif action.kind == "click":
        assert target is not None
        if target.id == "tickets":
            session.screen = "tickets"
        elif target.id == "case-418":
            session.screen = "case"
        elif target.id == "draft":
            session.screen = "draft"
        elif target.id == "submit":
            session.submitted = True
            session.pending_confirmation = None
        elif target.id == "cancel":
            session.ticket_draft.clear()
            session.pending_confirmation = None
    elif action.kind == "type":
        assert target is not None
        if target.id != "notes" or not action.text:
            raise ValueError("Only non-empty internal notes may be typed in this simulator")
        session.ticket_draft["notes"] = action.text
    elif action.kind == "confirm":
        if session.pending_confirmation is None:
            raise ValueError("No pending action to confirm")
        pending = session.pending_confirmation
        return apply_action(session, policy, pending, approved=True)
    session.actions.append(f"{action.kind}: {target.label if target else action.target}")
    return "OK"


def dom_click(session: Session, selector: str) -> str:
    """Illustrate brittle selector automation after a non-semantic UI rename."""
    if selector != "#escalate-button" or session.ui_variant != "original":
        raise LookupError("DOM selector unavailable after UI change")
    return apply_action(session, SandboxPolicy(), Action("click", target="draft", expected_label="Escalate"))


def run_safe_support_flow(ui_changed: bool = True) -> Session:
    session = Session(ui_variant="renamed" if ui_changed else "original")
    policy = SandboxPolicy()
    apply_action(session, policy, Action("navigate", target="tickets"))
    apply_action(session, policy, Action("click", target="case-418", expected_label="Acme billing"))
    apply_action(session, policy, Action("type", target="notes", text="Draft only: verify renewal webhook failures and notify billing on-call."))
    # Ground semantically rather than trusting a stale fixed selector or coordinate.
    apply_action(session, policy, Action("click", target="draft", expected_label="escalation"))
    paused = apply_action(session, policy, Action("click", target="submit", expected_label="Submit escalation"))
    assert paused.startswith("PAUSED")
    assert not session.submitted
    apply_action(session, policy, Action("confirm"))
    assert session.submitted
    return session


if __name__ == "__main__":
    session = run_safe_support_flow()
    print("\n".join(session.actions))
    print("submitted:", session.submitted)
