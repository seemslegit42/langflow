"""Tests for Assembly Line (SequentialWorkflow) — pure lfx implementation.

Mirrors test_swarms_workflows.py but targets the lfx native component
lfx.components.agentics.sequential_workflow which chains agents directly
without requiring the swarms package.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from lfx.components.agentics.sequential_workflow import (
    SequentialWorkflowComponent,
    _to_message,
)
from lfx.schema.message import Message


@pytest.mark.unit
class TestSequentialToMessage:
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
class TestSequentialWorkflowComponent:
    def test_handleinput_list_and_metadata(self):
        comp = SequentialWorkflowComponent()
        assert comp.display_name == "Assembly Line"
        agents_input = next(i for i in comp.inputs if i.name == "agents")
        assert agents_input.is_list is True
        assert "Agent" in agents_input.input_types
        assert next(i for i in comp.inputs if i.name == "task").display_name == "What should the team do?"
        assert next(i for i in comp.inputs if i.name == "max_loops").value == 1
        assert comp.outputs[0].name == "final_result"

    def test_build_workflow_chains_agents_sequentially(self):
        comp = SequentialWorkflowComponent()

        # Agent 1 returns "step1", agent 2 receives "step1" and returns "step2"
        agent1 = MagicMock()
        agent1.run.return_value = "step1"
        agent2 = MagicMock()
        agent2.run.return_value = "step2"

        comp.agents = [agent1, agent2]
        comp.task = "Research AI trends"
        comp.max_loops = 1

        result = comp.build_workflow()

        assert isinstance(result, Message)
        agent1.run.assert_called_once_with("Research AI trends")
        agent2.run.assert_called_once_with("step1")
        assert "step1" in result.text
        assert "step2" in result.text
        assert result.text == "step1\n---\nstep2"

    def test_build_workflow_dict_and_message_wrapping(self):
        comp = SequentialWorkflowComponent()
        agent = MagicMock()
        agent.run.return_value = {"output": "final text"}

        comp.agents = [agent]
        comp.task = "Do work"
        comp.max_loops = 1

        result = comp.build_workflow()
        assert isinstance(result, Message)
        assert json.loads(result.text) == {"output": "final text"}

    def test_max_loops_repeats_chain(self):
        comp = SequentialWorkflowComponent()
        agent = MagicMock()
        agent.run.side_effect = ["a", "b", "c", "d"]

        # 2 agents, 2 loops = 4 calls, chaining through all
        comp.agents = [MagicMock(run=MagicMock(return_value="a")), MagicMock(run=MagicMock(return_value="b"))]
        # simpler: single agent looping
        comp.agents = [agent]
        comp.task = "loop task"
        comp.max_loops = 3

        result = comp.build_workflow()
        assert agent.run.call_count == 3
        assert isinstance(result, Message)

    def test_requires_agents_and_task(self):
        comp = SequentialWorkflowComponent()

        comp.agents = []
        comp.task = "do work"
        with pytest.raises(ValueError, match="Team Member"):
            comp.build_workflow()

        comp.agents = [MagicMock()]
        comp.task = "   "
        with pytest.raises(ValueError, match="what to do"):
            comp.build_workflow()

    def test_agent_without_run_raises(self):
        comp = SequentialWorkflowComponent()
        comp.agents = [object()]  # no run()
        comp.task = "hello"
        with pytest.raises(ValueError, match="does not expose a run"):
            comp.build_workflow()
