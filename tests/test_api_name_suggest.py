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
FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _build_client(stub, tmp_path):
    embedder = HashEmbedBackend(dim=32)
    con = open_store(tmp_path / "t.sqlite", dim=embedder.dim, check_same_thread=False)
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    app = build_app(con=con, embedder=embedder, cfgs=cfgs,
                    llm=stub, vault_root=FIXTURE_VAULT)
    return TestClient(app)


def test_name_suggest_returns_suggestions(tmp_path):
    stub = StubBackend(responses=[
        json.dumps({
            "suggestions": [
                {"name": "Kjeld", "reasoning": "two-syllable, hard consonants, -d ending fits"},
                {"name": "Thorin", "reasoning": "matches -in ending and Norse phonology"},
            ]
        })
    ])
    client = _build_client(stub, tmp_path)
    r = client.post("/name/suggest", json={"culture": "northern", "count": 2})
    assert r.status_code == 200
    body = r.json()
    assert len(body["suggestions"]) == 2
    names = {s["name"] for s in body["suggestions"]}
    assert "Kjeld" in names


def test_name_suggest_prompt_includes_existing_names(tmp_path):
    stub = StubBackend(responses=[json.dumps({"suggestions": []})])
    client = _build_client(stub, tmp_path)
    client.post("/name/suggest", json={"culture": "northern", "role": "warrior"})
    prompt = stub.calls[0]["messages"][0]["content"]
    assert "Aerin" in prompt
    assert "Bjorn" in prompt
    assert "warrior" in prompt


def test_name_suggest_404_for_unknown_culture(tmp_path):
    stub = StubBackend(responses=[])
    client = _build_client(stub, tmp_path)
    r = client.post("/name/suggest", json={"culture": "unknown_culture"})
    assert r.status_code == 404


def test_name_suggest_tolerates_malformed_json(tmp_path):
    stub = StubBackend(responses=["this is not JSON"])
    client = _build_client(stub, tmp_path)
    r = client.post("/name/suggest", json={"culture": "northern"})
    assert r.status_code == 200
    assert r.json()["suggestions"] == []


def test_name_suggest_503_when_llm_unavailable(tmp_path):
    from worldcanon.llm import LLMUnavailableError

    class BoomLLM:
        def chat(self, *, messages, model, response_format=None):
            raise LLMUnavailableError("test")

    client = _build_client(BoomLLM(), tmp_path)
    r = client.post("/name/suggest", json={"culture": "northern"})
    assert r.status_code == 503
