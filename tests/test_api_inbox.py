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


def _build_client(tmp_path):
    vault = tmp_path / "vault"
    (vault / "_inbox").mkdir(parents=True)
    (vault / "_inbox" / "chap1.md").write_text(
        "# Chapter 1\n\nThe cliffs of Stormholm.", encoding="utf-8")
    (vault / "_inbox" / "sub").mkdir()
    (vault / "_inbox" / "sub" / "notes.md").write_text(
        "research notes about something.", encoding="utf-8")

    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=vault)
    app = build_app(store=store, embedder=embedder, cfgs=cfgs,
                    llm=StubBackend(responses=[]), vault_root=vault)
    return TestClient(app), vault


def test_inbox_lists_all_files(tmp_path):
    client, vault = _build_client(tmp_path)
    r = client.get("/inbox")
    assert r.status_code == 200
    body = r.json()
    paths = {item["path"] for item in body["items"]}
    assert "chap1.md" in paths
    assert "sub/notes.md" in paths


def test_inbox_items_include_preview(tmp_path):
    client, _ = _build_client(tmp_path)
    body = client.get("/inbox").json()
    for item in body["items"]:
        assert "preview" in item
        assert "size" in item


def test_inbox_empty_when_no_files(tmp_path):
    vault = tmp_path / "empty_vault"
    (vault / "_inbox").mkdir(parents=True)
    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "empty.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    install_ideation_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=vault)
    app = build_app(store=store, embedder=embedder, cfgs=cfgs,
                    llm=StubBackend(responses=[]), vault_root=vault)
    client = TestClient(app)
    body = client.get("/inbox").json()
    assert body["items"] == []
