"""Think Tank — parallel fan-out over a team of agents.

Everyone works on the same task at the same time, then you compare the
combined answers. Great for brainstorming or voting. Mirrors the
lfx-swarms ConcurrentWorkflow pattern standalone in lfx.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, IntInput, MessageTextInput
from lfx.io import Output
from lfx.schema.message import Message


def _to_message(value: Any) -> Message:
    """Normalize agent output to Message — mirrors swarms + agentics helpers.

    - Message -> pass through
    - dict -> json.dumps (preserves structure, avoids str(dict) single-quotes)
    - list -> json.dumps if items are dicts else str join
    - else -> Message(text=str(value))
    """
    if isinstance(value, Message):
        return value
    if isinstance(value, dict):
        return Message(text=json.dumps(value, ensure_ascii=False, indent=2))
    if isinstance(value, list):
        try:
            return Message(text=json.dumps(value, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            return Message(text="\n".join(str(v) for v in value))
    return Message(text=str(value))


class ConcurrentWorkflowComponent(Component):
    """Everyone works at the same time, then you compare answers. Great for brainstorming or voting."""

    display_name = "Think Tank"
    description = (
        "Parallel — Team Members brainstorm the same task at the same time, "
        "then you compare the combined answers. Great for brainstorming or voting."
    )
    documentation = "https://docs.swarms.world/api/concurrent-workflow"
    icon = "Swarms"
    name = "ConcurrentWorkflow"

    inputs = [
        HandleInput(
            name="agents",
            display_name="Your Team (drag Team Members here)",
            info="Drag 2+ Team Members here. They will all work in parallel on the same task.",
            input_types=["Agent"],
            is_list=True,
            required=True,
        ),
        MessageTextInput(
            name="task",
            display_name="What should the team do?",
            info="One clear instruction — everyone tackles it at once.",
            placeholder="Brainstorm 3 different taglines for a local-first AI team product.",
            required=True,
        ),
        IntInput(
            name="max_loops",
            display_name="Max loops",
            info="How many times each teammate should loop on the task.",
            value=1,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="final_result", display_name="Final Result", method="build_workflow"),
    ]

    def _run_one(self, agent: Any) -> Message:
        """Run one agent's run(task), returning its normalized Message output."""
        run = getattr(agent, "run", None)
        if run is None:
            msg = f"Agent {agent!r} does not expose a run() method."
            raise ValueError(msg)
        result = run(self.task)
        return _to_message(result)

    def build_workflow(self) -> Message:
        if not self.agents:
            msg = "Add at least two Team Members to the Think Tank."
            raise ValueError(msg)
        if not self.task or not self.task.strip():
            msg = "Tell the team what to do — fill in 'What should the team do?'."
            raise ValueError(msg)

        each: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            futures = [executor.submit(self._run_one, agent) for agent in self.agents]
            for agent, future in zip(self.agents, futures, strict=False):
                result = future.result()
                each.append({"agent": agent, "result": result})

        self.status = each
        final_text = "\n---\n".join(item["result"].text for item in each)
        return Message(text=final_text)
