"""LLM backends. Speaks the Ollama HTTP protocol (POST /api/chat).

Backends:
- OllamaBackend: real HTTP call to a local Ollama (default localhost:11434)
  or Ollama Cloud (set WORLDCANON_OLLAMA_URL + WORLDCANON_OLLAMA_API_KEY).
- StubBackend: returns canned responses; used in tests.

Selected via env:
- WORLDCANON_LLM_BACKEND=ollama (default) | stub
- WORLDCANON_OLLAMA_URL (default http://localhost:11434)
- WORLDCANON_OLLAMA_API_KEY (optional; sent as Authorization: Bearer)
- WORLDCANON_LLM_MODEL (default gemma3:4b)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Protocol

import httpx

logger = logging.getLogger("worldcanon.llm")


class LLMUnavailableError(Exception):
    pass


class LLMBackend(Protocol):
    def chat(self, *, messages: list[dict], model: str | None) -> str: ...


class StubBackend:
    """Returns canned responses in order. Records every call for assertions."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, *, messages: list[dict], model: str | None) -> str:
        self.calls.append({"messages": messages, "model": model})
        return self._responses.pop(0)


class OllamaBackend:
    def __init__(
        self,
        *,
        base_url: str,
        model_default: str,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
    ):
        self._base = base_url.rstrip("/")
        self._model_default = model_default
        self._api_key = api_key
        self._timeout = timeout_seconds

    def chat(self, *, messages: list[dict], model: str | None) -> str:
        body = {
            "model": model or self._model_default,
            "messages": messages,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        url = f"{self._base}/api/chat"
        try:
            resp = httpx.post(url, json=body, headers=headers, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"ollama unreachable at {self._base}: {exc}") from exc
        if resp.status_code != 200:
            raise LLMUnavailableError(
                f"ollama returned {resp.status_code}: {resp.text[:200]}"
            )
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError(f"ollama returned non-JSON: {exc}") from exc
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMUnavailableError(f"ollama response missing content: {data}")
        return content


def build_llm_backend() -> LLMBackend:
    kind = os.environ.get("WORLDCANON_LLM_BACKEND", "ollama").lower()
    if kind == "stub":
        return StubBackend(responses=[])
    if kind == "ollama":
        url = os.environ.get("WORLDCANON_OLLAMA_URL", "http://localhost:11434")
        api_key = os.environ.get("WORLDCANON_OLLAMA_API_KEY") or None
        model = os.environ.get("WORLDCANON_LLM_MODEL", "gemma3:4b")
        timeout = float(os.environ.get("WORLDCANON_LLM_TIMEOUT", "60"))
        return OllamaBackend(
            base_url=url,
            model_default=model,
            api_key=api_key,
            timeout_seconds=timeout,
        )
    raise ValueError(f"unknown WORLDCANON_LLM_BACKEND: {kind!r}")
