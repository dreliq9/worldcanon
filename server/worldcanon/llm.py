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
    """Raised when the LLM backend can't fulfill a request.

    `code` identifies the failure class so the API + plugin can choose a
    user-facing message. `hint` is a single sentence telling the user
    what to do next, written for a non-technical reader.
    """

    def __init__(self, message: str, *, code: str = "unknown", hint: str = ""):
        super().__init__(message)
        self.code = code
        self.hint = hint


class LLMBackend(Protocol):
    def chat(
        self,
        *,
        messages: list[dict],
        model: str | None,
        response_format: str | None = None,
    ) -> str: ...


class StubBackend:
    """Returns canned responses in order. Records every call for assertions."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def chat(
        self,
        *,
        messages: list[dict],
        model: str | None,
        response_format: str | None = None,
    ) -> str:
        self.calls.append({"messages": messages, "model": model, "response_format": response_format})
        return self._responses.pop(0)


def _classify_http_error(exc: httpx.HTTPError, base_url: str) -> LLMUnavailableError:
    if isinstance(exc, httpx.ConnectError):
        return LLMUnavailableError(
            f"ollama unreachable at {base_url}: {exc}",
            code="ollama_not_running",
            hint=(
                "Ollama isn't running. Look for the llama icon in your system "
                "tray (bottom-right of the taskbar). If it isn't there: open the "
                "Start menu, type 'Ollama', press Enter, and wait a few seconds "
                "for the tray icon to appear. If that still doesn't work, open "
                "PowerShell and run 'ollama serve'."
            ),
        )
    if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return LLMUnavailableError(
            f"ollama timed out at {base_url}: {exc}",
            code="ollama_timeout",
            hint=(
                "Ollama is running but didn't answer in time. The model may be "
                "loading for the first time — wait a minute and try again. If it "
                "keeps timing out, restart the Ollama app."
            ),
        )
    return LLMUnavailableError(
        f"ollama unreachable at {base_url}: {exc}",
        code="ollama_unreachable",
        hint=(
            "Couldn't reach Ollama. Check that the Ollama app is running and "
            "that no firewall is blocking localhost:11434."
        ),
    )


def _classify_status_error(status: int, body: str, model: str) -> LLMUnavailableError:
    body_excerpt = body[:200]
    body_lower = body.lower()
    if status == 404 and "not found" in body_lower and "model" in body_lower:
        return LLMUnavailableError(
            f"ollama returned 404: {body_excerpt}",
            code="model_not_installed",
            hint=(
                f"The model '{model}' isn't installed in Ollama. Open PowerShell "
                f"and run 'ollama pull {model}', or change WORLDCANON_LLM_MODEL "
                "to a model you already have. See INSTALL.md for model picks by RAM."
            ),
        )
    if status == 401 or status == 403:
        return LLMUnavailableError(
            f"ollama returned {status}: {body_excerpt}",
            code="auth_failed",
            hint=(
                "Ollama rejected our credentials. If you're using Ollama Cloud, "
                "check that WORLDCANON_OLLAMA_API_KEY is set correctly."
            ),
        )
    if 500 <= status < 600:
        return LLMUnavailableError(
            f"ollama returned {status}: {body_excerpt}",
            code="ollama_server_error",
            hint=(
                "Ollama hit an internal error. Restart the Ollama app and try "
                "again. If it keeps happening, the model may not fit in available "
                "RAM — try a smaller model (see INSTALL.md)."
            ),
        )
    return LLMUnavailableError(
        f"ollama returned {status}: {body_excerpt}",
        code="ollama_unexpected",
        hint=f"Ollama returned HTTP {status}, which isn't expected. Restart Ollama and try again.",
    )


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

    def chat(
        self,
        *,
        messages: list[dict],
        model: str | None,
        response_format: str | None = None,
    ) -> str:
        effective_model = model or self._model_default
        body: dict[str, object] = {
            "model": effective_model,
            "messages": messages,
            "stream": False,
        }
        if response_format == "json":
            body["format"] = "json"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        url = f"{self._base}/api/chat"
        try:
            resp = httpx.post(url, json=body, headers=headers, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise _classify_http_error(exc, self._base) from exc
        if resp.status_code != 200:
            raise _classify_status_error(resp.status_code, resp.text, effective_model)
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError(
                f"ollama returned non-JSON: {exc}",
                code="ollama_bad_response",
                hint="Ollama returned garbage instead of JSON. Restart Ollama and try again.",
            ) from exc
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMUnavailableError(
                f"ollama response missing content: {data}",
                code="ollama_bad_response",
                hint="Ollama returned a malformed reply. Restart Ollama and try again.",
            )
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
