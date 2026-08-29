"""Utilities for lfx-swarms bundle — local-first Brain resolution + tool conversion.

Spec: resolve_model_name(brain: str) -> str probing :11434/api/tags via httpx 0.5s SSRF-safe.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

# Display labels — dropdown values shown to founders
BRAIN_OPTIONS: list[str] = [
    "Auto (local-first)",
    "Local — Ollama: llama3.1 (recommended)",
    "Local — Ollama: mistral",
    "Local — LM Studio",
    "Bring your own key — gpt-4o-mini",
    "Bring your own key — Claude Sonnet",
]

# Mapping for explicit BYOK and lmstudio/ollama — litellm prefixes
_BRAIN_MAP: dict[str, str] = {
    "Local — Ollama: llama3.1 (recommended)": "ollama/llama3.1",
    "Local — Ollama: mistral": "ollama/mistral",
    "Local — LM Studio": "openai/local-model",
    "Bring your own key — gpt-4o-mini": "openai/gpt-4o-mini",
    "Bring your own key — Claude Sonnet": "anthropic/claude-3-5-sonnet-20241022",
}

# SSRF-safe allowlist — only local loopback
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _is_allowed_local_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return host in _ALLOWED_HOSTS and parsed.scheme in {"http", "https"}
    except Exception:
        return False


def _probe_ollama_tags(base_url: str = "http://localhost:11434") -> bool:
    """Probe :11434/api/tags via httpx 0.5s — SSRF-safe, only loopback."""
    tags_url = base_url.rstrip("/") + "/api/tags"
    if not _is_allowed_local_url(tags_url):
        return False
    try:
        resp = httpx.get(tags_url, timeout=0.5)
        return resp.status_code < 500  # any non-server-error means reachable
    except (httpx.RequestError, httpx.TimeoutException, OSError):
        return False


def _probe_lmstudio(base_url: str = "http://localhost:1234/v1") -> bool:
    if not _is_allowed_local_url(base_url):
        return False
    try:
        # LM Studio exposes /v1/models — probe it
        models_url = base_url.rstrip("/") + "/models" if not base_url.endswith("/models") else base_url
        # also accept base_url itself if already /v1
        probe = base_url if base_url.endswith("/v1") else models_url
        if probe.endswith("/v1"):
            probe = probe + "/models"
        resp = httpx.get(probe, timeout=0.5)
        return resp.status_code < 500
    except (httpx.RequestError, httpx.TimeoutException, OSError):
        return False


def resolve_model_name(brain: str) -> str:
    """Resolve Brain dropdown label to litellm model string.

    Probes :11434/api/tags via httpx 0.5s SSRF-safe for Auto and explicit Ollama.
    LM Studio maps to openai/... via http://localhost:1234/v1.
    BYOK maps to openai/gpt-4o-mini and anthropic/claude-3-5-sonnet with litellm prefixes.
    Raises ValueError with actionable message if local unreachable.
    """
    label = (brain or "").strip()

    # BYOK explicit — no probe, direct litellm prefix
    if label in _BRAIN_MAP and not label.startswith("Local — Ollama") and label != "Auto (local-first)":
        # Handles LM Studio and BYOK
        if label == "Local — LM Studio":
            return "openai/local-model"
        return _BRAIN_MAP[label]

    # Explicit Ollama options — probe to verify local is up, else error
    if label in ("Local — Ollama: llama3.1 (recommended)", "Local — Ollama: mistral"):
        if _probe_ollama_tags("http://localhost:11434"):
            return _BRAIN_MAP[label]
        msg = (
            "Local Ollama not reachable at http://localhost:11434. "
            "Start Ollama (`ollama serve` + `ollama pull llama3.1` or `ollama pull mistral`) "
            "or pick 'Auto (local-first)' or a BYOK option."
        )
        raise ValueError(msg)

    # Auto local-first — probe ollama then lmstudio
    if label == "Auto (local-first)":
        if _probe_ollama_tags("http://localhost:11434"):
            return "ollama/llama3.1"
        if _probe_lmstudio("http://localhost:1234/v1"):
            return "openai/local-model"
        msg = (
            "No local model found. Auto tried Ollama at http://localhost:11434/api/tags "
            "and LM Studio at http://localhost:1234/v1 — both unreachable. "
            "Start Ollama (`ollama run llama3.1`) or LM Studio, or pick "
            "'Bring your own key — gpt-4o-mini' / 'Bring your own key — Claude Sonnet' "
            "and set OPENAI_API_KEY / ANTHROPIC_API_KEY in Settings → Environment."
        )
        raise ValueError(msg)

    # Fallback — treat as raw litellm string (advanced)
    return label


def convert_tools(tools: Any) -> list[Any]:
    """Convert Langflow tools to list[BaseTool] for swarms.

    Handles None/list, unwraps ComponentToolkit (exposes .tools or .get_tools()),
    and returns list[BaseTool]/callables. Swarms Agent accepts list[BaseTool] or callables.
    """
    if tools is None:
        return []
    # Normalize to list
    if not isinstance(tools, list):
        tools = [tools]

    out: list[Any] = []
    for t in tools:
        if t is None:
            continue
        # Unwrap ComponentToolkit — common wrapper that holds .tools or .get_tools()
        # Check for toolkit shape before generic unwrap
        toolkit_tools = None
        if hasattr(t, "get_tools") and callable(t.get_tools):
            try:
                toolkit_tools = t.get_tools()
            except Exception:
                toolkit_tools = None
        elif hasattr(t, "tools") and isinstance(t.tools, list):
            toolkit_tools = t.tools
        if isinstance(toolkit_tools, list):
            out.extend(toolkit_tools)
            continue
        # Generic unwrap for Tool-like objects that wrap .tool / .base_tool
        unwrapped = None
        for attr in ("base_tool", "tool", "_tool", "func"):
            if hasattr(t, attr):
                val = getattr(t, attr)
                if val is not None:
                    unwrapped = val
                    break
        if unwrapped is not None:
            out.append(unwrapped)
            continue
        out.append(t)
    return out
