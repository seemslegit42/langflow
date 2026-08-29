"""Assembly Line — sequential loop over a team of agents.

Work passes from one Team Member to the next in order: the output of
step 1 becomes the input of step 2. Mirrors the lfx-swarms
SequentialWorkflow pattern standalone in lfx.
"""

from __future__ import annotations

import json
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


class SequentialWorkflowComponent(Component):
    """Work passes from one teammate to the next. Perfect for Research → Write → Review."""

    display_name = "Assembly Line"
    description = (
        "Work passes from one teammate to the next. Perfect for Research → Write → Review. "
        "The output of step 1 becomes the input of step 2."
    )
    documentation = "https://docs.swarms.world/api/sequential-workflow"
    icon = "Swarms"
    name = "SequentialWorkflow"

    inputs = [
        HandleInput(
            name="agents",
            display_name="Your Team (drag Team Members here, in order)",
            info="Drag Team Members here in the order they should work. Example: Researcher → Writer → Editor.",
            input_types=["Agent"],
            is_list=True,
            required=True,
        ),
        MessageTextInput(
            name="task",
            display_name="What should the team do?",
            info="One clear instruction for the whole team.",
            placeholder="Research the top 3 AI hiring trends and write a short LinkedIn post with sources.",
            required=True,
        ),
        IntInput(
            name="max_loops",
            display_name="Max loops",
            info="How many times the line should run.",
            value=1,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="final_result", display_name="Final Result", method="build_workflow"),
    ]

    def _run_one(self, agent: Any, current_input: Any) -> Message:
        """Run one agent against the current input, chaining the result."""
        run = getattr(agent, "run", None)
        if run is None:
            msg = f"Agent {agent!r} does not expose a run() method."
            raise ValueError(msg)
        result = run(current_input)
        return _to_message(result)

    def build_workflow(self) -> Message:
        if not self.agents:
            msg = "Add at least one Team Member to Your Team."
            raise ValueError(msg)
        if not self.task or not self.task.strip():
            msg = "Tell the team what to do — fill in 'What should the team do?'."
            raise ValueError(msg)

        max_loops = self.max_loops or 1
        current_input = self.task
        results: list[Message] = []
        each: list[dict[str, Any]] = []

        for loop in range(max_loops):
            for agent in self.agents:
                result = self._run_one(agent, current_input)
                results.append(result)
                each.append({"agent": agent, "loop": loop, "result": result})
                # Chain output into next agent's input
                current_input = result.text

        self.status = each
        final_text = "\n---\n".join(item.text for item in results)
        return Message(text=final_text)
