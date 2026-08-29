"""Tests for lfx-swarms workflows — mirrors agentics component tests.

Covers HandleInput list wiring and Message wrapping helper
(Message(text=str(value)) / json.dumps for dicts) per recommendation.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from lfx.schema.message import Message


# Reuse helpers from bundle — import via package
try:
    from lfx_swarms.components.swarms.concurrent_workflow import _to_message as concurrent_to_message
    from lfx_swarms.components.swarms.sequential_workflow import _to_message as seq_to_message

    HAS_SWARMS_BUNDLE = True
except ImportError:
    HAS_SWARMS_BUNDLE = False
    pytest.skip("lfx-swarms bundle not installed", allow_module_level=True)


@pytest.mark.unit
class TestToMessageHelper:
    def test_passthrough_message(self):
        m = Message(text="hello")
        assert seq_to_message(m) is m
        assert concurrent_to_message(m) is m

    def test_dict_becomes_json(self):
        d = {"output": "done", "tokens": 42}
        msg = seq_to_message(d)
        assert isinstance(msg, Message)
        assert json.loads(msg.text) == d

    def test_list_becomes_json(self):
        lst = [{"a": 1}, {"a": 2}]
        msg = seq_to_message(lst)
        assert isinstance(msg, Message)
        assert json.loads(msg.text) == lst

    def test_str_passthrough(self):
        msg = seq_to_message("plain result")
        assert msg.text == "plain result"


@pytest.mark.unit
class TestSwarmsSequentialWorkflowComponent:
    def test_handleinput_list_and_message_output(self):
        from lfx_swarms.components.swarms.sequential_workflow import SwarmsSequentialWorkflowComponent

        comp = SwarmsSequentialWorkflowComponent()
        # HandleInput list spec must match hierarchical_crew / loop template
        agents_input = next(i for i in comp.inputs if i.name == "agents")
        assert agents_input.is_list is True
        assert "Agent" in agents_input.input_types

        # build_workflow with mocked swarms
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = {"output": "final text"}
        with patch.dict("sys.modules", {"swarms": MagicMock(SequentialWorkflow=MagicMock(return_value=mock_workflow))}):
            comp.agents = [MagicMock(), MagicMock()]
            comp.task = "Research AI trends"
            comp.max_loops = 1
            result = comp.build_workflow()
            assert isinstance(result, Message)
            assert "final text" in result.text or "output" in result.text

    def test_requires_agents_and_task(self):
        from lfx_swarms.components.swarms.sequential_workflow import SwarmsSequentialWorkflowComponent

        comp = SwarmsSequentialWorkflowComponent()
        comp.agents = []
        comp.task = "do work"
        with pytest.raises(ValueError, match="Team Member"):
            comp.build_workflow()

        comp.agents = [MagicMock()]
        comp.task = "   "
        with pytest.raises(ValueError, match="what to do"):
            comp.build_workflow()


@pytest.mark.unit
class TestSwarmsConcurrentWorkflowComponent:
    def test_handleinput_list_and_message_output(self):
        from lfx_swarms.components.swarms.concurrent_workflow import SwarmsConcurrentWorkflowComponent

        comp = SwarmsConcurrentWorkflowComponent()
        agents_input = next(i for i in comp.inputs if i.name == "agents")
        assert agents_input.is_list is True
        assert "Agent" in agents_input.input_types

        mock_workflow = MagicMock()
        mock_workflow.run.return_value = ["a", "b"]
        with patch.dict("sys.modules", {"swarms": MagicMock(ConcurrentWorkflow=MagicMock(return_value=mock_workflow))}):
            comp.agents = [MagicMock(), MagicMock()]
            comp.task = "Brainstorm taglines"
            comp.max_loops = 1
            result = comp.build_workflow()
            assert isinstance(result, Message)
            assert json.loads(result.text) == ["a", "b"]
