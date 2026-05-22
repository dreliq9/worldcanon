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
    con = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    app = build_app(con=con, embedder=embedder, cfgs=cfgs, llm=stub)
    return TestClient(app)


def test_propose_facts_returns_extracted_facts(tmp_path):
    stub = StubBackend(responses=[
        json.dumps({
            "proposed_facts": [
                {"entity": "Aerin", "claim": "has green eyes", "confidence": "high"},
                {"entity": "Stormholm", "claim": "is a port city", "confidence": "high"},
            ]
        })
    ])
    client = _build_client(stub, tmp_path)
    r = client.post(
        "/propose-facts",
        json={"text": "Aerin's green eyes searched the cliffs of Stormholm.",
              "source": "drafts/ch03.md"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["proposed_facts"]) == 2
    entities = {f["entity"] for f in body["proposed_facts"]}
    assert entities == {"Aerin", "Stormholm"}


def test_propose_facts_handles_empty_extraction(tmp_path):
    stub = StubBackend(responses=[json.dumps({"proposed_facts": []})])
    client = _build_client(stub, tmp_path)
    r = client.post("/propose-facts", json={"text": "the wind blew.", "source": "x"})
    assert r.status_code == 200
    assert r.json()["proposed_facts"] == []


def test_propose_facts_tolerates_malformed_json(tmp_path):
    stub = StubBackend(responses=["this is not JSON"])
    client = _build_client(stub, tmp_path)
    r = client.post("/propose-facts", json={"text": "anything", "source": "x"})
    assert r.status_code == 200
    assert r.json()["proposed_facts"] == []


def test_propose_facts_503_when_llm_unavailable(tmp_path):
    from worldcanon.llm import LLMUnavailableError

    class BoomLLM:
        def chat(self, *, messages, model, response_format=None):
            raise LLMUnavailableError("test")

    client = _build_client(BoomLLM(), tmp_path)
    r = client.post("/propose-facts", json={"text": "anything", "source": "x"})
    assert r.status_code == 503
