import json

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, IntInput, MessageTextInput
from lfx.io import Output
from lfx.schema.message import Message


def _to_message(value) -> Message:
    """Normalize swarms output to Message — mirrors Loop + agentics helpers.

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


class SwarmsSequentialWorkflowComponent(Component):
    """Work passes from one teammate to the next. Perfect for Research → Write → Review."""

    display_name = "Assembly Line"
    description = "Work passes from one teammate to the next. Perfect for Research → Write → Review. The output of step 1 becomes the input of step 2."
    documentation = "https://docs.swarms.world/api/sequential-workflow"
    icon = "Swarms"
    name = "SwarmsSequentialWorkflow"

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
        Output(display_name="Final Result", name="result", method="build_workflow"),
    ]

    def build_workflow(self) -> Message:
        try:
            from swarms import SequentialWorkflow
        except ImportError as e:
            msg = "swarms is not installed. Please install it with `uv pip install swarms`."
            raise ImportError(msg) from e

        if not self.agents:
            msg = "Add at least one Team Member to Your Team."
            raise ValueError(msg)
        if not self.task or not self.task.strip():
            msg = "Tell the team what to do — fill in 'What should the team do?'."
            raise ValueError(msg)

        workflow = SequentialWorkflow(
            agents=self.agents,
            max_loops=self.max_loops or 1,
        )
        result = workflow.run(self.task)

        return _to_message(result)
