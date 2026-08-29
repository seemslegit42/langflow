import json

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, IntInput, MessageTextInput
from lfx.io import Output
from lfx.schema.message import Message


def _to_message(value) -> Message:
    """Normalize swarms output to Message — mirrors Loop + agentics helpers."""
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


class SwarmsConcurrentWorkflowComponent(Component):
    """Everyone works at the same time, then you compare answers. Great for brainstorming or voting."""

    display_name = "Think Tank"
    description = "Everyone works at the same time, then you compare answers. Great for brainstorming or voting."
    documentation = "https://docs.swarms.world/api/concurrent-workflow"
    icon = "Swarms"
    name = "SwarmsConcurrentWorkflow"

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
            value=1,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Combined Result", name="result", method="build_workflow"),
    ]

    def build_workflow(self) -> Message:
        try:
            from swarms import ConcurrentWorkflow
        except ImportError as e:
            msg = "swarms is not installed. Please install it with `uv pip install swarms`."
            raise ImportError(msg) from e

        if not self.agents:
            msg = "Add at least two Team Members to Your Team."
            raise ValueError(msg)
        if not self.task or not self.task.strip():
            msg = "Tell the team what to do — fill in 'What should the team do?'."
            raise ValueError(msg)

        workflow = ConcurrentWorkflow(
            agents=self.agents,
            max_loops=self.max_loops or 1,
        )
        result = workflow.run(self.task)

        return _to_message(result)
