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
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    app = build_app(store=store, embedder=embedder, cfgs=cfgs, llm=stub, vault_root=FIXTURE_VAULT)
    return TestClient(app), con


def test_ideation_start_returns_session_and_question(tmp_path):
    stub = StubBackend(responses=["What does Aerin want most?"])
    client, _ = _build_client(stub, tmp_path)
    r = client.post("/ideation/start", json={"entity": "Aerin"})
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "first_question" in body
    assert "Aerin" in body["first_question"]


def test_ideation_start_404_for_unknown_entity(tmp_path):
    stub = StubBackend(responses=[])
    client, _ = _build_client(stub, tmp_path)
    r = client.post("/ideation/start", json={"entity": "Nonexistent"})
    assert r.status_code == 404


def test_ideation_start_records_ai_turn_in_session(tmp_path):
    stub = StubBackend(responses=["What does Aerin want?"])
    client, con = _build_client(stub, tmp_path)
    sid = client.post("/ideation/start", json={"entity": "Aerin"}).json()["session_id"]
    rows = con.execute(
        "SELECT transcript_json FROM ideation_sessions WHERE id = ?", (sid,)
    ).fetchone()
    transcript = json.loads(rows["transcript_json"])
    assert len(transcript) == 1
    assert transcript[0]["role"] == "ai"
    assert "Aerin" in transcript[0]["content"]


def test_ideation_start_503_when_llm_unavailable(tmp_path):
    from worldcanon.llm import LLMUnavailableError

    class BoomLLM:
        def chat(self, *, messages, model, response_format=None):
            raise LLMUnavailableError("test")

    client, _ = _build_client(BoomLLM(), tmp_path)
    r = client.post("/ideation/start", json={"entity": "Aerin"})
    assert r.status_code == 503


def test_ideation_respond_returns_facts_and_next_question(tmp_path):
    stub = StubBackend(responses=[
        # First call: the question
        "What does Aerin want?",
        # Second call: response with extracted facts + next question
        json.dumps({
            "facts": [
                {"claim": "Aerin wants to be free", "confidence": "high"},
            ],
            "next_question": "Why does she want freedom?",
            "addressed_gap": "Motivation / what they want",
        }),
    ])
    client, _ = _build_client(stub, tmp_path)
    sid = client.post("/ideation/start", json={"entity": "Aerin"}).json()["session_id"]
    r = client.post(
        f"/ideation/{sid}/respond",
        json={"answer": "She wants to be free."},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["proposed_facts"]) == 1
    assert "be free" in body["proposed_facts"][0]["claim"]
    assert "Why does she want freedom" in body["next_question"]


def test_ideation_respond_null_next_question_when_done(tmp_path):
    stub = StubBackend(responses=[
        "What does Aerin want?",
        json.dumps({
            "facts": [],
            "next_question": None,
            "addressed_gap": "Motivation / what they want",
        }),
    ])
    client, _ = _build_client(stub, tmp_path)
    sid = client.post("/ideation/start", json={"entity": "Aerin"}).json()["session_id"]
    r = client.post(f"/ideation/{sid}/respond", json={"answer": "Nothing."})
    assert r.status_code == 200
    assert r.json()["next_question"] is None


def test_ideation_respond_404_for_unknown_session(tmp_path):
    stub = StubBackend(responses=[])
    client, _ = _build_client(stub, tmp_path)
    r = client.post("/ideation/bogus/respond", json={"answer": "anything"})
    assert r.status_code == 404


def test_ideation_respond_handles_malformed_json(tmp_path):
    stub = StubBackend(responses=[
        "What does Aerin want?",
        "this is not JSON",
    ])
    client, _ = _build_client(stub, tmp_path)
    sid = client.post("/ideation/start", json={"entity": "Aerin"}).json()["session_id"]
    r = client.post(f"/ideation/{sid}/respond", json={"answer": "ok"})
    assert r.status_code == 200
    body = r.json()
    assert body["proposed_facts"] == []
    assert body["next_question"] is None
