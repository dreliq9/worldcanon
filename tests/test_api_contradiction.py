import json
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
    app = build_app(con=con, embedder=embedder, cfgs=cfgs, llm=stub)
    return TestClient(app)


def test_contradiction_check_extracts_entities_from_wikilinks(tmp_path):
    stub = StubBackend(responses=[
        json.dumps({"contradictions": []}),
        json.dumps({"contradictions": []}),
    ])
    client = _build_client(stub, tmp_path)
    r = client.post(
        "/contradiction-check",
        json={"text": "Today [[Aerin]] visited [[Stormholm]]."},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(stub.calls) == 2
    # Each call's user-message prompt should name the specific entity.
    prompts = [c["messages"][0]["content"] for c in stub.calls]
    entities = set()
    for p in prompts:
        # Prompt says "Established canon about <entity>:"
        marker = "Established canon about "
        idx = p.find(marker)
        if idx >= 0:
            entities.add(p[idx + len(marker):].split(":")[0].strip())
    assert entities == {"Aerin", "Stormholm"}
    assert body["findings"] == []


def test_contradiction_check_flags_contradiction(tmp_path):
    stub = StubBackend(responses=[
        json.dumps({
            "contradictions": [
                {
                    "new_claim": "Aerin has blue eyes",
                    "conflicting_canon": "has green eyes",
                    "reasoning": "Direct color conflict.",
                }
            ]
        }),
    ])
    client = _build_client(stub, tmp_path)
    r = client.post(
        "/contradiction-check",
        json={"text": "Aerin's blue eyes scanned the harbor.", "entities": ["Aerin"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["findings"]) == 1
    f = body["findings"][0]
    assert f["entity"] == "Aerin"
    assert "blue" in f["new_claim"]
    assert "green" in f["conflicting_canon"]


def test_contradiction_check_skips_entity_with_no_facts(tmp_path):
    stub = StubBackend(responses=[])  # Will raise IndexError if called!
    client = _build_client(stub, tmp_path)
    r = client.post(
        "/contradiction-check",
        json={"text": "[[Unknown]] did something", "entities": ["Unknown"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["findings"] == []
    assert len(stub.calls) == 0


def test_contradiction_check_returns_503_when_llm_unavailable(tmp_path):
    from worldcanon.llm import LLMUnavailableError

    class BoomLLM:
        def chat(self, *, messages, model):
            raise LLMUnavailableError("test-induced")

    client = _build_client(BoomLLM(), tmp_path)
    r = client.post(
        "/contradiction-check",
        json={"text": "[[Aerin]] did something", "entities": ["Aerin"]},
    )
    assert r.status_code == 503
    assert r.json()["detail"]["status"] == "llm_unavailable"


def test_contradiction_check_tolerates_malformed_llm_response(tmp_path):
    stub = StubBackend(responses=["this is not JSON"])
    client = _build_client(stub, tmp_path)
    r = client.post(
        "/contradiction-check",
        json={"text": "[[Aerin]]", "entities": ["Aerin"]},
    )
    assert r.status_code == 200
    assert r.json()["findings"] == []
