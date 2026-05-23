import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from worldcanon.api import build_app
from worldcanon.embedder import HashEmbedBackend
from worldcanon.ideation import install_ideation_schema
from worldcanon.indexer import full_index_corpus
from worldcanon.ledger import install_ledger_schema
from worldcanon.llm import StubBackend
from worldcanon.registry import load_registry
from worldcanon.store import open_store


REPO = Path(__file__).parent.parent


def _build_client(stub, tmp_path):
    vault = tmp_path / "vault"
    (vault / "_inbox").mkdir(parents=True)
    (vault / "_inbox" / "chap1.md").write_text(
        "# Chapter 1\n\nThe cliffs of Stormholm.", encoding="utf-8")

    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=vault)
    app = build_app(store=store, embedder=embedder, cfgs=cfgs,
                    llm=stub, vault_root=vault)
    return TestClient(app)


def test_triage_suggest_returns_classification(tmp_path):
    stub = StubBackend(responses=[
        json.dumps({
            "classification": "drafts",
            "confidence": "high",
            "reasoning": "It's a partial chapter.",
        })
    ])
    client = _build_client(stub, tmp_path)
    r = client.post("/triage-suggest", json={"path": "chap1.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] == "drafts"
    assert body["confidence"] == "high"


def test_triage_suggest_404_when_file_missing(tmp_path):
    stub = StubBackend(responses=[])
    client = _build_client(stub, tmp_path)
    r = client.post("/triage-suggest", json={"path": "nonexistent.md"})
    assert r.status_code == 404


def test_triage_suggest_rejects_path_traversal(tmp_path):
    stub = StubBackend(responses=[])
    client = _build_client(stub, tmp_path)
    r = client.post("/triage-suggest", json={"path": "../entities/characters/Aerin.md"})
    assert r.status_code == 400


def test_triage_suggest_tolerates_malformed_llm_response(tmp_path):
    stub = StubBackend(responses=["this is not JSON"])
    client = _build_client(stub, tmp_path)
    r = client.post("/triage-suggest", json={"path": "chap1.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] == "drafts"
    assert body["confidence"] == "low"


def test_triage_suggest_503_when_llm_unavailable(tmp_path):
    from worldcanon.llm import LLMUnavailableError

    class BoomLLM:
        def chat(self, *, messages, model, response_format=None):
            raise LLMUnavailableError("test")

    client = _build_client(BoomLLM(), tmp_path)
    r = client.post("/triage-suggest", json={"path": "chap1.md"})
    assert r.status_code == 503
