"""Model a resumable side-effecting step with idempotency and a kill switch."""
from dataclasses import dataclass, field


@dataclass
class Runtime:
    completed_keys: set[str] = field(default_factory=set)
    killed: bool = False

    def execute_once(self, key: str, action: str) -> str:
        if self.killed:
            return "blocked by kill switch"
        if key in self.completed_keys:
            return "replayed safely; side effect not repeated"
        self.completed_keys.add(key)
        return f"executed: {action}"


if __name__ == "__main__":
    runtime = Runtime()
    print(runtime.execute_once("payment-1", "charge customer"))
    print(runtime.execute_once("payment-1", "charge customer"))
    runtime.killed = True
    print(runtime.execute_once("payment-2", "send email"))
