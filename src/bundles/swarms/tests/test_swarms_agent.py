"""Mocked unit tests for Team Member component — patch httpx.get, litellm not imported."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestSwarmsAgentComponent:
    def test_display_and_founder_copy(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        assert SwarmsAgentComponent.display_name == "Team Member"
        assert SwarmsAgentComponent.icon == "Swarms"
        assert "dedicated team member" in SwarmsAgentComponent.description.lower()
        assert any(i.name == "job_description" and i.display_name == "Job Description" for i in SwarmsAgentComponent.inputs)
        assert any(i.name == "brain" and i.display_name == "Brain" for i in SwarmsAgentComponent.inputs)
        assert any(i.name == "creativity" and i.display_name == "Creativity" for i in SwarmsAgentComponent.inputs)

    def test_handles_tools_is_list(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        comp = SwarmsAgentComponent()
        tools_input = next(i for i in comp.inputs if i.name == "tools")
        assert tools_input.is_list is True
        assert "Tool" in tools_input.input_types

    def test_build_agent_calls_resolve_and_convert(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        comp = SwarmsAgentComponent()
        comp.agent_name = "Researcher"
        comp.job_description = "You are a researcher."
        comp.brain = "Bring your own key — gpt-4o-mini"
        comp.creativity = 0.7
        comp.max_retries = 2
        comp.tools = []
        comp.verbose = False
        # ensure deprecated fields don't interfere
        comp.system_prompt = ""
        comp.temperature = 0.7
        comp.max_loops = ""

        mock_agent_cls = MagicMock()
        with patch.dict("sys.modules", {"swarms": MagicMock(Agent=mock_agent_cls)}):
            agent = comp.build_agent()
            mock_agent_cls.assert_called_once()
            kwargs = mock_agent_cls.call_args.kwargs
            assert kwargs["agent_name"] == "Researcher"
            assert kwargs["system_prompt"] == "You are a researcher."
            assert kwargs["model_name"] == "openai/gpt-4o-mini"
            assert kwargs["temperature"] == 0.7
            assert kwargs["max_loops"] == 2

    def test_build_agent_lazy_import_error(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        comp = SwarmsAgentComponent()
        comp.job_description = "do work"
        comp.brain = "Bring your own key — gpt-4o-mini"
        with patch.dict("sys.modules", {"swarms": None}):
            # force ImportError by making __import__ fail
            with patch("builtins.__import__", side_effect=ImportError("no swarms")):
                with pytest.raises(ImportError, match="swarms is not installed"):
                    comp.build_agent()

    def test_build_agent_requires_job_description(self):
        from lfx_swarms.components.swarms.swarms_agent import SwarmsAgentComponent

        comp = SwarmsAgentComponent()
        comp.job_description = "   "
        comp.system_prompt = ""
        comp.brain = "Bring your own key — gpt-4o-mini"
        with pytest.raises(ValueError, match="Job Description"):
            comp.build_agent()
