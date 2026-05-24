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
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)
    (vault / "brainstorm").mkdir()
    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=vault)
    app = build_app(store=store, embedder=embedder, cfgs=cfgs, llm=stub, vault_root=vault)
    return TestClient(app), vault


def test_capture_writes_file_and_returns_path(tmp_path):
    client, vault = _build_client(StubBackend(responses=[]), tmp_path)
    r = client.post(
        "/capture",
        json={"text": "Aerin's dagger was her mother's.", "source": "webhook",
              "entities": ["Aerin"], "topics": ["weapon"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["path"].startswith("brainstorm/")
    abs_path = vault / body["path"]
    assert abs_path.exists()
    content = abs_path.read_text(encoding="utf-8")
    assert "Aerin's dagger was her mother's." in content
    assert "type: brainstorm" in content
    assert "status: unprocessed" in content


def test_capture_defaults_source_to_webhook(tmp_path):
    client, vault = _build_client(StubBackend(responses=[]), tmp_path)
    r = client.post("/capture", json={"text": "thought"})
    body = r.json()
    abs_path = vault / body["path"]
    content = abs_path.read_text(encoding="utf-8")
    assert "source: webhook" in content


def test_capture_accepts_empty_text(tmp_path):
    """The plugin's 'Log brainstorm' command creates an empty stub note
    that the user types into. Sidecar must accept empty text."""
    client, vault = _build_client(StubBackend(responses=[]), tmp_path)
    r = client.post("/capture", json={"text": ""})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert (vault / body["path"]).exists()


def test_capture_accepts_no_text_field_at_all(tmp_path):
    """All fields have defaults; an empty POST body should still create a stub note."""
    client, vault = _build_client(StubBackend(responses=[]), tmp_path)
    r = client.post("/capture", json={})
    assert r.status_code == 200
    assert (vault / r.json()["path"]).exists()
