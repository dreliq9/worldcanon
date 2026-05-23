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


def _build_client(tmp_path):
    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    app = build_app(store=store, embedder=embedder, cfgs=cfgs,
                    llm=StubBackend(responses=[]), vault_root=FIXTURE_VAULT)
    return TestClient(app)


def test_unprocessed_brainstorm_returns_list(tmp_path):
    client = _build_client(tmp_path)
    r = client.get("/unprocessed-brainstorm")
    assert r.status_code == 200
    body = r.json()
    assert "notes" in body
    # The fixture vault has one unprocessed brainstorm (2026-05-22-1430.md)
    assert any(n["source_path"].endswith("2026-05-22-1430.md") for n in body["notes"])


def test_unprocessed_brainstorm_returns_one_entry_per_file(tmp_path):
    client = _build_client(tmp_path)
    body = client.get("/unprocessed-brainstorm").json()
    paths = [n["source_path"] for n in body["notes"]]
    assert len(paths) == len(set(paths))  # dedup by source_path


def test_unprocessed_brainstorm_includes_preview(tmp_path):
    client = _build_client(tmp_path)
    notes = client.get("/unprocessed-brainstorm").json()["notes"]
    for n in notes:
        assert "source_path" in n
        assert "preview" in n
        assert "date" in n
