"""Intermediate capstone: route support requests before allowing side effects."""


def route(request: str) -> str:
    lowered = request.lower()
    if "refund" in lowered or "charge" in lowered:
        return "approval-required"
    if "status" in lowered or "invoice" in lowered:
        return "account-lookup"
    return "human-escalation"


def handle(request: str, approved: bool = False) -> dict:
    destination = route(request)
    if destination == "approval-required" and not approved:
        return {"route": destination, "side_effect": False, "reason": "human approval required"}
    return {"route": destination, "side_effect": destination == "approval-required", "reason": "bounded path"}


if __name__ == "__main__":
    print(handle("please refund my order"))
    print(handle("please refund my order", approved=True))
