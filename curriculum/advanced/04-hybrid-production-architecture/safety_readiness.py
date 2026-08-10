"""Advanced safety lab: turn threat-model findings into a readiness gate."""


def readiness(*, prompt_injection_test: bool, authorization_test: bool, budget_test: bool, rollback: bool) -> dict:
    checks = {"prompt_injection": prompt_injection_test, "authorization": authorization_test, "budget": budget_test, "rollback": rollback}
    return {"ready": all(checks.values()), "checks": checks, "missing": [name for name, passed in checks.items() if not passed]}


if __name__ == "__main__":
    print(readiness(prompt_injection_test=True, authorization_test=True, budget_test=True, rollback=False))
