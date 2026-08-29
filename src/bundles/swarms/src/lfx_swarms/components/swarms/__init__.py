"""Swarms bundle components — lazy re-export via import_mod pattern like other bundles."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx_swarms.components.swarms._utils import convert_tools, resolve_model_name
    from lfx_swarms.components.swarms.concurrent_workflow import SwarmsConcurrentWorkflowComponent
    from lfx_swarms.components.swarms.sequential_workflow import SwarmsSequentialWorkflowComponent
    from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

_dynamic_imports = {
    "SwarmsAgentComponent": "swarms_agent",
    "SwarmsSequentialWorkflowComponent": "sequential_workflow",
    "SwarmsConcurrentWorkflowComponent": "concurrent_workflow",
    "resolve_model_name": "_utils",
    "convert_tools": "_utils",
}

__all__ = [
    "SwarmsAgentComponent",
    "SwarmsConcurrentWorkflowComponent",
    "SwarmsSequentialWorkflowComponent",
    "convert_tools",
    "resolve_model_name",
]


def __getattr__(attr_name: str) -> Any:
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result
