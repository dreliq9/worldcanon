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


def test_unlinked_mentions_finds_plain_aerin_in_canon(tmp_path):
    client = _build_client(tmp_path)
    r = client.get("/unlinked-mentions", params={"file": "canon/ch01.md"})
    assert r.status_code == 200
    mentions = r.json()["mentions"]
    assert any(m["match"] == "Aerin" for m in mentions)
    # [[Stormholm]] is wikilinked — should NOT be flagged
    assert not any(m["match"] == "Stormholm" for m in mentions)


def test_unlinked_mentions_ignores_wikilink_aliases(tmp_path):
    client = _build_client(tmp_path)
    r = client.get("/unlinked-mentions", params={"file": "drafts/ch02_draft.md"})
    assert r.status_code == 200
    mentions = r.json()["mentions"]
    assert any(m["match"] == "Aerin" for m in mentions)


def test_unlinked_mentions_404_for_missing_file(tmp_path):
    client = _build_client(tmp_path)
    r = client.get("/unlinked-mentions", params={"file": "no/such/file.md"})
    assert r.status_code == 404


def test_unlinked_mentions_rejects_path_traversal(tmp_path):
    client = _build_client(tmp_path)
    r = client.get("/unlinked-mentions", params={"file": "../../etc/passwd"})
    assert r.status_code == 400


def test_unlinked_mentions_includes_line_and_col(tmp_path):
    client = _build_client(tmp_path)
    body = client.get("/unlinked-mentions", params={"file": "canon/ch01.md"}).json()
    for m in body["mentions"]:
        assert "line" in m
        assert "col" in m
        assert "suggested_link" in m
        assert m["suggested_link"].startswith("[[")
