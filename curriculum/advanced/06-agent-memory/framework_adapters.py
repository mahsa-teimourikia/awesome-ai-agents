"""Optional storage adapters for the framework-neutral Course 06 policy core.

The application has already admitted a ``MemoryRecord`` before this module sees
it.  The adapter demonstrates namespaced persistence; it does not own memory
admission, authorization, lifecycle, retrieval policy, or verification.
"""

from __future__ import annotations

from importlib import metadata, util
from typing import Any

from policy import MemoryRecord

TESTED_LANGGRAPH_VERSION = "1.2.11"
COMPATIBLE_LANGGRAPH_RANGE = ">=1.2.0,<2.0.0"


def adapter_status() -> dict[str, object]:
    """Describe the optional dependency without requiring it to be installed."""
    try:
        installed_version = metadata.version("langgraph")
    except metadata.PackageNotFoundError:
        installed_version = None
    return {
        "installed": util.find_spec("langgraph") is not None,
        "installed_version": installed_version,
        "tested_version": TESTED_LANGGRAPH_VERSION,
        "compatible_range": COMPATIBLE_LANGGRAPH_RANGE,
        "credentials_required_to_instantiate": False,
    }


class LangGraphStoreAdapter:
    """Persist already-admitted records in a hard tenant/subject namespace."""

    def __init__(self, store: Any):
        self.store = store

    @staticmethod
    def namespace(record: MemoryRecord) -> tuple[str, ...]:
        return (
            "governed-memory",
            record.tenant_id,
            record.subject_id,
            record.scope.value,
        )

    def put_admitted(self, record: MemoryRecord) -> None:
        """Store a policy-admitted record; model output must never call this path."""
        if record.status.value != "ACTIVE":
            raise ValueError("ADAPTER_REQUIRES_ACTIVE_ADMITTED_RECORD")
        self.store.put(
            self.namespace(record),
            record.memory_id,
            record.model_dump(mode="json"),
        )

    def get_exact(self, record: MemoryRecord) -> Any:
        """Read by the same trusted namespace; ranking is intentionally omitted."""
        return self.store.get(self.namespace(record), record.memory_id)


def build_langgraph_store_adapter() -> LangGraphStoreAdapter:
    """Create the tested credential-free in-memory LangGraph Store adapter."""
    if util.find_spec("langgraph") is None:
        raise RuntimeError("Install the frameworks extra to use this adapter.")
    from langgraph.store.memory import InMemoryStore

    return LangGraphStoreAdapter(InMemoryStore())
