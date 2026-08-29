"""Tests for Team Member (SwarmsAgent) — HandleInput list for tools, Brain local-first."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lfx_swarms.components.swarms._utils import BRAIN_OPTIONS, resolve_model_name


@pytest.mark.unit
class TestBrainLocalFirst:
    def test_brain_options_include_auto_local_first(self):
        assert "Auto (local-first)" in BRAIN_OPTIONS

    def test_resolve_local_ollama(self):
        model, extra = resolve_model_name("Local — Ollama: llama3.1 (recommended)")
        assert model == "ollama/llama3.1"
        assert extra == {}

    def test_resolve_auto_prefers_ollama_when_alive(self):
        with patch("lfx_swarms.components.swarms._utils.ollama_alive", return_value=True), patch(
            "lfx_swarms.components.swarms._utils.lmstudio_alive", return_value=False
        ):
            model, extra = resolve_model_name("Auto (local-first)")
            assert model == "ollama/llama3.1"

    def test_resolve_auto_raises_when_no_local(self):
        with patch("lfx_swarms.components.swarms._utils.ollama_alive", return_value=False), patch(
            "lfx_swarms.components.swarms._utils.lmstudio_alive", return_value=False
        ):
            with pytest.raises(ValueError, match="No local model"):
                resolve_model_name("Auto (local-first)")


@pytest.mark.unit
class TestSwarmsAgentComponent:
    def test_handleinput_tools_is_list(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        comp = SwarmsAgentComponent()
        tools_input = next(i for i in comp.inputs if i.name == "tools")
        assert tools_input.is_list is True
        assert "Tool" in tools_input.input_types

    def test_display_names_founder_copy(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        assert SwarmsAgentComponent.display_name == "Team Member"
        assert SwarmsAgentComponent.icon == "Swarms"
        # Job Description label
        assert any(i.display_name == "Job Description" for i in SwarmsAgentComponent.inputs)
        assert any(i.display_name == "Brain" for i in SwarmsAgentComponent.inputs)

    def test_build_agent_lazy_import_and_message_wrapping(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        comp = SwarmsAgentComponent()
        comp.agent_name = "Researcher"
        comp.system_prompt = "You are a researcher."
        comp.brain = "Local — Ollama: llama3.1 (recommended)"
        comp.temperature = 0.7
        comp.max_loops = "1"
        comp.tools = []
        comp.verbose = False

        mock_agent_cls = MagicMock()
        with patch.dict("sys.modules", {"swarms": MagicMock(Agent=mock_agent_cls)}):
            agent = comp.build_agent()
            mock_agent_cls.assert_called_once()
            kwargs = mock_agent_cls.call_args.kwargs
            assert kwargs["agent_name"] == "Researcher"
            assert kwargs["model_name"] == "ollama/llama3.1"
