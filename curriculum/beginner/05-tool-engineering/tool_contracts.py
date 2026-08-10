"""Keep tool validation and authorization outside the model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    user_id: str
    operation: str
    amount: int
    idempotency_key: str


def authorize(request: Request) -> None:
    if request.operation not in {"preview", "charge"}:
        raise ValueError("operation is not allowlisted")
    if request.amount <= 0 or request.amount > 100:
        raise ValueError("amount is outside the policy range")
    if not request.idempotency_key:
        raise ValueError("writes require an idempotency key")


def charge(request: Request, *, dry_run: bool = True) -> str:
    authorize(request)
    if request.operation == "charge" and dry_run:
        return f"preview: would charge {request.amount} for {request.user_id}"
    return f"executed {request.operation} for {request.user_id}"


if __name__ == "__main__":
    print(charge(Request("learner-1", "charge", 25, "demo-1")))
    try:
        charge(Request("learner-1", "charge", 500, "demo-2"))
    except ValueError as error:
        print("blocked:", error)
