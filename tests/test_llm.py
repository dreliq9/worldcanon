import pytest

from worldcanon.llm import (
    LLMUnavailableError,
    OllamaBackend,
    StubBackend,
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


def test_build_llm_backend_returns_stub_when_env_set(monkeypatch):
    monkeypatch.setenv("WORLDCANON_LLM_BACKEND", "stub")
    backend = build_llm_backend()
    assert isinstance(backend, StubBackend)


def test_build_llm_backend_returns_ollama_by_default(monkeypatch):
    monkeypatch.delenv("WORLDCANON_LLM_BACKEND", raising=False)
    backend = build_llm_backend()
    assert isinstance(backend, OllamaBackend)
