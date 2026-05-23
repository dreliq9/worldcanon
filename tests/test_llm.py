import httpx
import pytest

from worldcanon.llm import (
    LLMUnavailableError,
    OllamaBackend,
    StubBackend,
    _classify_http_error,
    _classify_status_error,
    build_llm_backend,
)


def test_stub_backend_returns_canned_response():
    stub = StubBackend(responses=["hello"])
    out = stub.chat(messages=[{"role": "user", "content": "hi"}], model="any")
    assert out == "hello"


def test_stub_backend_cycles_responses():
    stub = StubBackend(responses=["a", "b"])
    assert stub.chat(messages=[], model="any") == "a"
    assert stub.chat(messages=[], model="any") == "b"
    with pytest.raises(IndexError):
        stub.chat(messages=[], model="any")


def test_stub_backend_records_calls():
    stub = StubBackend(responses=["x"])
    stub.chat(messages=[{"role": "user", "content": "q"}], model="gemma3:4b")
    assert len(stub.calls) == 1
    assert stub.calls[0]["model"] == "gemma3:4b"


def test_ollama_backend_raises_on_network_failure(monkeypatch):
    backend = OllamaBackend(base_url="http://127.0.0.1:1", model_default="gemma3:4b")
    with pytest.raises(LLMUnavailableError):
        backend.chat(messages=[{"role": "user", "content": "hi"}], model=None)


def test_ollama_backend_classifies_connect_error_as_not_running():
    backend = OllamaBackend(base_url="http://127.0.0.1:1", model_default="gemma3:4b")
    with pytest.raises(LLMUnavailableError) as info:
        backend.chat(messages=[{"role": "user", "content": "hi"}], model=None)
    assert info.value.code == "ollama_not_running"
    assert "Ollama" in info.value.hint
    assert "tray" in info.value.hint.lower()
    assert "ollama serve" in info.value.hint.lower()


def test_classify_connect_error():
    exc = httpx.ConnectError("connection refused")
    err = _classify_http_error(exc, "http://localhost:11434")
    assert err.code == "ollama_not_running"


def test_classify_timeout_error():
    exc = httpx.ReadTimeout("timed out")
    err = _classify_http_error(exc, "http://localhost:11434")
    assert err.code == "ollama_timeout"
    assert "loading" in err.hint.lower() or "wait" in err.hint.lower()


def test_classify_404_with_model_not_found():
    err = _classify_status_error(
        404,
        '{"error":"model \\"phi3:mini\\" not found, try pulling it first"}',
        model="phi3:mini",
    )
    assert err.code == "model_not_installed"
    assert "phi3:mini" in err.hint
    assert "ollama pull" in err.hint


def test_classify_401_returns_auth_failed():
    err = _classify_status_error(401, "Unauthorized", model="gemma3:4b")
    assert err.code == "auth_failed"


def test_classify_5xx_returns_server_error():
    err = _classify_status_error(503, "service unavailable", model="gemma3:4b")
    assert err.code == "ollama_server_error"
    assert "smaller model" in err.hint.lower() or "ram" in err.hint.lower()


def test_classify_other_status_returns_unexpected():
    err = _classify_status_error(418, "I'm a teapot", model="gemma3:4b")
    assert err.code == "ollama_unexpected"


def test_classify_404_without_model_text_returns_unexpected():
    """A bare 404 that isn't about a missing model shouldn't be miscategorized."""
    err = _classify_status_error(404, "endpoint missing", model="gemma3:4b")
    assert err.code == "ollama_unexpected"


def test_build_llm_backend_returns_stub_when_env_set(monkeypatch):
    monkeypatch.setenv("WORLDCANON_LLM_BACKEND", "stub")
    backend = build_llm_backend()
    assert isinstance(backend, StubBackend)


def test_build_llm_backend_returns_ollama_by_default(monkeypatch):
    monkeypatch.delenv("WORLDCANON_LLM_BACKEND", raising=False)
    backend = build_llm_backend()
    assert isinstance(backend, OllamaBackend)
