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


def test_name_cultures_returns_list(tmp_path):
    client = _build_client(tmp_path)
    r = client.get("/name/cultures")
    assert r.status_code == 200
    body = r.json()
    assert "cultures" in body
    assert any(c["culture"] == "northern" for c in body["cultures"])


def test_name_cultures_includes_counts(tmp_path):
    client = _build_client(tmp_path)
    body = client.get("/name/cultures").json()
    northern = next(c for c in body["cultures"] if c["culture"] == "northern")
    assert northern["used_count"] == 2
    assert northern["candidate_count"] == 2
