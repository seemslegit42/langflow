"""Tests for Think Tank (ConcurrentWorkflow) — pure lfx implementation.

Mirrors test_swarms_workflows.py but targets the lfx native component
lfx.components.agentics.concurrent_workflow which fans out in parallel.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from lfx.components.agentics.concurrent_workflow import (
    ConcurrentWorkflowComponent,
    _to_message,
)
from lfx.schema.message import Message


@pytest.mark.unit
class TestConcurrentToMessage:
    def test_passthrough_message(self):
        m = Message(text="hello")
        assert _to_message(m) is m

    def test_dict_becomes_json(self):
        d = {"output": "done", "tokens": 42}
        msg = _to_message(d)
        assert isinstance(msg, Message)
        assert json.loads(msg.text) == d

    def test_list_becomes_json(self):
        lst = [{"a": 1}, {"a": 2}]
        msg = _to_message(lst)
        assert isinstance(msg, Message)
        assert json.loads(msg.text) == lst

    def test_str_passthrough(self):
        msg = _to_message("plain result")
        assert msg.text == "plain result"


@pytest.mark.unit
class TestConcurrentWorkflowComponent:
    def test_handleinput_list_and_metadata(self):
        comp = ConcurrentWorkflowComponent()
        assert comp.display_name == "Think Tank"
        agents_input = next(i for i in comp.inputs if i.name == "agents")
        assert agents_input.is_list is True
        assert "Agent" in agents_input.input_types
        assert next(i for i in comp.inputs if i.name == "task").display_name == "What should the team do?"
        assert next(i for i in comp.inputs if i.name == "max_loops").value == 1
        assert comp.outputs[0].name == "final_result"

    def test_build_workflow_fans_out_parallel(self):
        comp = ConcurrentWorkflowComponent()

        agent1 = MagicMock()
        agent1.run.return_value = "idea A"
        agent2 = MagicMock()
        agent2.run.return_value = "idea B"
        agent3 = MagicMock()
        agent3.run.return_value = "idea C"

        comp.agents = [agent1, agent2, agent3]
        comp.task = "Brainstorm taglines"
        comp.max_loops = 1

        result = comp.build_workflow()

        assert isinstance(result, Message)
        agent1.run.assert_called_once_with("Brainstorm taglines")
        agent2.run.assert_called_once_with("Brainstorm taglines")
        agent3.run.assert_called_once_with("Brainstorm taglines")
        # Preserve input order in output
        assert result.text == "idea A\n---\nidea B\n---\nidea C"

    def test_build_workflow_dict_wrapping(self):
        comp = ConcurrentWorkflowComponent()

        agent1 = MagicMock()
        agent1.run.return_value = {"idea": "A"}
        agent2 = MagicMock()
        agent2.run.return_value = {"idea": "B"}

        comp.agents = [agent1, agent2]
        comp.task = "Generate ideas"
        comp.max_loops = 1

        result = comp.build_workflow()
        assert isinstance(result, Message)
        parts = result.text.split("\n---\n")
        assert json.loads(parts[0]) == {"idea": "A"}
        assert json.loads(parts[1]) == {"idea": "B"}

    def test_status_stores_results(self):
        comp = ConcurrentWorkflowComponent()
        agent1 = MagicMock()
        agent1.run.return_value = "x"
        agent2 = MagicMock()
        agent2.run.return_value = "y"

        comp.agents = [agent1, agent2]
        comp.task = "task"
        comp.build_workflow()

        assert hasattr(comp, "status")
        assert len(comp.status) == 2
        assert comp.status[0]["result"].text == "x"
        assert comp.status[1]["result"].text == "y"

    def test_requires_agents_and_task(self):
        comp = ConcurrentWorkflowComponent()

        comp.agents = []
        comp.task = "do work"
        with pytest.raises(ValueError, match="Team Members"):
            comp.build_workflow()

        comp.agents = [MagicMock(), MagicMock()]
        comp.task = "   "
        with pytest.raises(ValueError, match="what to do"):
            comp.build_workflow()

    def test_agent_without_run_raises(self):
        comp = ConcurrentWorkflowComponent()
        comp.agents = [object(), MagicMock()]
        comp.task = "hello"
        with pytest.raises(ValueError, match="does not expose a run"):
            comp.build_workflow()
