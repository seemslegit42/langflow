"""Mocked unit tests for _utils — patch httpx.get, litellm not imported."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from lfx_swarms.components.swarms._utils import BRAIN_OPTIONS, convert_tools, resolve_model_name


@pytest.mark.unit
class TestResolveModelName:
    def test_brain_options_include_all(self):
        assert "Auto (local-first)" in BRAIN_OPTIONS
        assert "Local — LM Studio" in BRAIN_OPTIONS
        assert "Bring your own key — gpt-4o-mini" in BRAIN_OPTIONS

    def test_auto_prefers_ollama_when_tags_ok(self):
        mock_resp = MagicMock(status_code=200)
        with patch("lfx_swarms.components.swarms._utils.httpx.get", return_value=mock_resp) as mock_get:
            model = resolve_model_name("Auto (local-first)")
            assert model == "ollama/llama3.1"
            # first call is /api/tags probe
            assert "/api/tags" in mock_get.call_args_list[0].args[0]
            assert mock_get.call_args_list[0].kwargs.get("timeout") == 0.5

    def test_auto_falls_back_to_lmstudio_when_ollama_down(self):
        def fake_get(url, timeout):
            if "/api/tags" in url:
                raise httpx.RequestError("down")
            return MagicMock(status_code=200)

        with patch("lfx_swarms.components.swarms._utils.httpx.get", side_effect=fake_get):
            model = resolve_model_name("Auto (local-first)")
            assert model == "openai/local-model"

    def test_auto_raises_friendly_error_when_both_down(self):
        with patch("lfx_swarms.components.swarms._utils.httpx.get", side_effect=httpx.RequestError("down")):
            with pytest.raises(ValueError, match="No local model found"):
                resolve_model_name("Auto (local-first)")

    def test_explicit_ollama_probes_and_returns(self):
        mock_resp = MagicMock(status_code=200)
        with patch("lfx_swarms.components.swarms._utils.httpx.get", return_value=mock_resp):
            assert resolve_model_name("Local — Ollama: mistral") == "ollama/mistral"

    def test_explicit_ollama_raises_when_unreachable(self):
        with patch("lfx_swarms.components.swarms._utils.httpx.get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ValueError, match="Local Ollama not reachable"):
                resolve_model_name("Local — Ollama: llama3.1 (recommended)")

    def test_lmstudio_maps_to_openai_prefix(self):
        # Direct LM Studio choice does not probe, just maps
        assert resolve_model_name("Local — LM Studio") == "openai/local-model"

    def test_byok_maps_to_litellm_prefixes(self):
        assert resolve_model_name("Bring your own key — gpt-4o-mini") == "openai/gpt-4o-mini"
        assert resolve_model_name("Bring your own key — Claude Sonnet") == "anthropic/claude-3-5-sonnet-20241022"

    def test_ssrf_safe_probing_only_loopback(self):
        # internal helper should reject non-loopback
        from lfx_swarms.components.swarms._utils import _is_allowed_local_url

        assert _is_allowed_local_url("http://localhost:11434/api/tags") is True
        assert _is_allowed_local_url("http://127.0.0.1:11434/api/tags") is True
        assert _is_allowed_local_url("http://evil.com/api/tags") is False
        assert _is_allowed_local_url("http://192.168.1.1:11434/api/tags") is False


@pytest.mark.unit
class TestConvertTools:
    def test_none_returns_empty(self):
        assert convert_tools(None) == []

    def test_empty_list_returns_empty(self):
        assert convert_tools([]) == []

    def test_callable_passthrough(self):
        def my_tool(x): return x

        assert convert_tools([my_tool]) == [my_tool]

    def test_unwraps_component_toolkit_via_get_tools(self):
        fake_tool = MagicMock()
        toolkit = MagicMock()
        toolkit.get_tools.return_value = [fake_tool]
        # ensure it has get_tools callable
        assert convert_tools(toolkit) == [fake_tool]
        assert convert_tools([toolkit]) == [fake_tool]

    def test_unwraps_component_toolkit_via_tools_attr(self):
        fake_tool = MagicMock()
        toolkit = MagicMock()
        toolkit.tools = [fake_tool]
        # remove get_tools to force .tools path
        del toolkit.get_tools
        assert convert_tools(toolkit) == [fake_tool]

    def test_unwraps_base_tool_attr(self):
        inner = MagicMock()
        wrapper = MagicMock()
        wrapper.base_tool = inner
        # toolkit checks fail, base_tool unwraps
        assert convert_tools([wrapper]) == [inner]

    def test_mixed_list(self):
        t1 = MagicMock()
        t2 = lambda x: x
        toolkit = MagicMock()
        toolkit.get_tools.return_value = [t1]
        result = convert_tools([toolkit, t2, None])
        assert t1 in result
        assert t2 in result
        assert None not in result
