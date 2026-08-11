"""Credential-free model-routing lab: policy, cascade, fallback, and ensemble evidence."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    name: str
    modality: str = "text"
    complexity: int = 1
    latency_slo_ms: int = 2_000
    risk: str = "low"
    needs_code: bool = False


@dataclass(frozen=True)
class Route:
    model: str
    reason: str
    estimated_cost_cents: float
    estimated_latency_ms: int


CATALOG = {
    "fast-text": Route("fast-text", "known, text-only path", 0.08, 450),
    "reasoning": Route("reasoning", "ambiguous, multi-step evidence synthesis", 1.20, 3_100),
    "multimodal": Route("multimodal", "image, screen, or document understanding", 0.65, 1_800),
    "coding": Route("coding", "repository, patch, or test-oriented task", 0.90, 2_400),
}


def choose_route(task: Task, available: set[str] | None = None) -> Route:
    """Apply capability requirements first, then choose the least costly eligible route."""
    available = available or set(CATALOG)
    required = "multimodal" if task.modality in {"image", "screen", "document", "audio"} else None
    if task.needs_code:
        required = "coding"
    if required:
        if required not in available:
            return Route("human-review", f"required {required} capability unavailable", 0, 0)
        return CATALOG[required]
    if task.complexity >= 7 or task.risk == "high":
        return CATALOG["reasoning"] if "reasoning" in available else Route("human-review", "quality floor unavailable", 0, 0)
    if "fast-text" in available and CATALOG["fast-text"].estimated_latency_ms <= task.latency_slo_ms:
        return CATALOG["fast-text"]
    return CATALOG["reasoning"] if "reasoning" in available else Route("human-review", "no eligible model", 0, 0)


def run_cascade(task: Task, quality_signal: float) -> list[Route]:
    """Start cheaply, then promote only when an external quality signal misses the floor."""
    first = choose_route(task)
    if first.model != "fast-text" or quality_signal >= 0.80:
        return [first]
    return [first, CATALOG["reasoning"]]


def select_ensemble(task: Task, disagreement: float) -> str:
    """Ensembles are for high-value uncertainty, not a default cost-control mechanism."""
    if task.risk == "high" and disagreement > 0.25:
        return "independent-models-plus-verifier"
    return "single-route-with-evaluation"


def run_demo() -> list[Route]:
    tasks = [
        Task("format EU status"),
        Task("investigate regional checkout regression", complexity=9, risk="high"),
        Task("read checkout dashboard screenshot", modality="screen"),
        Task("prepare test-backed retry patch", needs_code=True),
    ]
    routes = [choose_route(task) for task in tasks]
    assert [route.model for route in routes] == ["fast-text", "reasoning", "multimodal", "coding"]
    assert [route.model for route in run_cascade(tasks[0], 0.52)] == ["fast-text", "reasoning"]
    assert select_ensemble(tasks[1], 0.40) == "independent-models-plus-verifier"
    return routes


if __name__ == "__main__":
    for route in run_demo():
        print(f"{route.model}: {route.reason} ({route.estimated_cost_cents} cents)")
