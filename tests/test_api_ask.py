from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from worldcanon.api import build_app
from worldcanon.embedder import HashEmbedBackend
from worldcanon.indexer import full_index_corpus
from worldcanon.ledger import install_ledger_schema
from worldcanon.llm import StubBackend
from worldcanon.registry import load_registry
from worldcanon.store import open_store


REPO = Path(__file__).parent.parent
FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _build_client(stub, tmp_path):
    embedder = HashEmbedBackend(dim=32)
    con = open_store(tmp_path / "t.sqlite", dim=embedder.dim, check_same_thread=False)
    install_ledger_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    app = build_app(con=con, embedder=embedder, cfgs=cfgs, llm=stub, vault_root=FIXTURE_VAULT)
    return TestClient(app)


def test_ask_endpoint_returns_answer_and_citations(tmp_path):
    stub = StubBackend(responses=[
        "Her eyes are green."
    ])
    client = _build_client(stub, tmp_path)
    r = client.post("/ask", json={"question": "What color are Aerin's eyes?"})
    assert r.status_code == 200
    body = r.json()
    assert "green" in body["answer"]
    assert isinstance(body["citations"], list)
    assert len(body["citations"]) > 0


def test_ask_endpoint_records_retrieval_in_llm_messages(tmp_path):
    stub = StubBackend(responses=["irrelevant"])
    client = _build_client(stub, tmp_path)
    client.post("/ask", json={"question": "tell me about Stormholm"})
    msgs = stub.calls[0]["messages"]
    user_content = next(m for m in msgs if m["role"] == "user")["content"]
    assert "Stormholm" in user_content


def test_ask_endpoint_llm_unavailable(tmp_path):
    from worldcanon.llm import LLMUnavailableError

    class BoomLLM:
        def chat(self, *, messages, model, response_format=None):
            raise LLMUnavailableError("test-induced")

    client = _build_client(BoomLLM(), tmp_path)
    r = client.post("/ask", json={"question": "anything"})
    assert r.status_code == 503
    body = r.json()
    assert body["detail"]["status"] == "llm_unavailable"


def test_ask_endpoint_rejects_empty_question(tmp_path):
    stub = StubBackend(responses=["never called"])
    client = _build_client(stub, tmp_path)
    r = client.post("/ask", json={"question": "   "})
    assert r.status_code == 422
