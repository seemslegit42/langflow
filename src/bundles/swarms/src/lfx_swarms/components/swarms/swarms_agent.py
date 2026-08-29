from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    BoolInput,
    DropdownInput,
    FloatInput,
    HandleInput,
    IntInput,
    MessageTextInput,
    MultilineInput,
)
from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.message import Message

from lfx_swarms.components.swarms._utils import BRAIN_OPTIONS, convert_tools, resolve_model_name


class SwarmsAgentComponent(Component):
    display_name = "Team Member"
    description = (
        "A dedicated team member you can give a job to — describe what you want them to do and pick their brain."
    )
    documentation = "https://docs.swarms.world/api/agent"
    icon = "Swarms"
    name = "SwarmsAgent"

    inputs = [
        MessageTextInput(
            name="agent_name",
            display_name="Name",
            info="What you'd call this teammate. Example: Researcher, Writer, Critic.",
            value="Researcher",
            placeholder="Researcher",
            required=True,
        ),
        MultilineInput(
            name="job_description",
            display_name="Job Description",
            info="Describe what you want this teammate to do — like writing a job post. Example: You are a market researcher. Find 3 trends with sources.",
            placeholder="You are a market researcher. Find 3 trends about ... Be concise and cite sources.",
            required=True,
        ),
        DropdownInput(
            name="brain",
            display_name="Brain",
            info="Auto tries your local model first. No key needed. Add cloud key only if you want it.",
            options=BRAIN_OPTIONS,
            value="Auto (local-first)",
        ),
        FloatInput(
            name="creativity",
            display_name="Creativity",
            info="0 = precise, 1 = creative.",
            value=0.7,
            advanced=True,
        ),
        IntInput(
            name="max_retries",
            display_name="Max retries",
            info="How many times the teammate should retry.",
            value=1,
            advanced=True,
        ),
        HandleInput(
            name="tools",
            display_name="Tools (optional)",
            info="Drag tools here (e.g. web search, calculator).",
            input_types=["Tool"],
            is_list=True,
            advanced=True,
        ),
        BoolInput(
            name="verbose",
            display_name="Verbose",
            value=False,
            advanced=True,
        ),
        # Back-compat aliases — keep system_prompt/temperature/max_loops/creativity in sync
        MultilineInput(
            name="system_prompt",
            display_name="System Prompt (deprecated)",
            info="Deprecated — use Job Description.",
            value="",
            advanced=True,
            show=False,
        ),
        FloatInput(
            name="temperature",
            display_name="Temperature (deprecated)",
            value=0.7,
            advanced=True,
            show=False,
        ),
        MessageTextInput(
            name="max_loops",
            display_name="Max loops (deprecated)",
            value="",
            advanced=True,
            show=False,
        ),
    ]

    outputs = [
        Output(display_name="Agent", name="agent", method="build_agent"),
        Output(display_name="Agent Output", name="output", method="build_output"),
    ]

    def _resolve_job_description(self) -> str:
        # Prefer job_description, fall back to deprecated system_prompt
        jd = (getattr(self, "job_description", None) or "").strip()
        if jd:
            return jd
        sp = (getattr(self, "system_prompt", None) or "").strip()
        return sp

    def _resolve_creativity(self) -> float:
        # Prefer creativity, fall back to deprecated temperature
        if getattr(self, "creativity", None) is not None:
            try:
                return float(self.creativity)
            except (TypeError, ValueError):
                pass
        if getattr(self, "temperature", None) is not None:
            try:
                return float(self.temperature)
            except (TypeError, ValueError):
                pass
        return 0.7

    def _resolve_max_retries(self) -> int:
        # Prefer max_retries, fall back to deprecated max_loops (int or "auto")
        mr = getattr(self, "max_retries", None)
        if mr is not None and str(mr).strip() != "":
            try:
                return int(str(mr).strip())
            except (TypeError, ValueError):
                pass
        ml = getattr(self, "max_loops", None)
        if ml is not None and str(ml).strip() != "":
            raw = str(ml).strip().lower()
            if raw == "auto":
                return 3
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
        return 1

    def build_agent(self):
        """Build the swarms Agent — lazily imports swarms."""
        try:
            from swarms import Agent
        except ImportError as e:
            msg = "swarms is not installed. Please install it with `uv pip install swarms` or `uv sync` with lfx-swarms enabled."
            raise ImportError(msg) from e

        job_desc = self._resolve_job_description()
        if not job_desc:
            msg = "Tell your teammate what to do — fill in Job Description."
            raise ValueError(msg)

        model_name = resolve_model_name(self.brain)
        creativity = self._resolve_creativity()
        max_retries = self._resolve_max_retries()
        tools = convert_tools(self.tools)

        # LM Studio needs base_url — resolve_model_name returns openai/local-model for it,
        # so we pass extra via model_name only; swarms/litellm will use OPENAI_API_BASE if set.
        # Keep it simple: extra handling is done by resolve_model_name's httpx probe.
        extra: dict = {}
        if model_name == "openai/local-model":
            extra["llm_base_url"] = "http://localhost:1234/v1"

        agent = Agent(
            agent_name=self.agent_name,
            system_prompt=job_desc,
            model_name=model_name,
            temperature=creativity,
            max_loops=max_retries,
            tools=tools,
            verbose=self.verbose,
            **extra,
        )
        self.status = f"Team Member '{self.agent_name}' ready — brain: {model_name}"
        return agent

    def build_output(self) -> Data | Message:
        """Return agent output as Data/Message — convenience output for flows."""
        agent = self.build_agent()
        # This output just returns the agent handle wrapped as Data for downstream
        # workflows (Assembly Line/Think Tank expect Agent). Keep as Data envelope.
        return Data(data={"agent": agent, "agent_name": self.agent_name})
