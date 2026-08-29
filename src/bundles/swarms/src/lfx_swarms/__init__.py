"""lfx-swarms: Swarms bundle — founder-friendly AI teams (local-first)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx_swarms.components.swarms.concurrent_workflow import SwarmsConcurrentWorkflowComponent
    from lfx_swarms.components.swarms.sequential_workflow import SwarmsSequentialWorkflowComponent
    from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

_dynamic_imports = {
    "SwarmsAgentComponent": "swarms_agent",
    "SwarmsConcurrentWorkflowComponent": "concurrent_workflow",
    "SwarmsSequentialWorkflowComponent": "sequential_workflow",
}

__all__ = [
    "SwarmsAgentComponent",
    "SwarmsConcurrentWorkflowComponent",
    "SwarmsSequentialWorkflowComponent",
]


def __getattr__(attr_name: str) -> Any:
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], "lfx_swarms.components.swarms")
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result
