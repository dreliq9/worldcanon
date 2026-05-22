from pathlib import Path

import pytest

from worldcanon.embedder import HashEmbedBackend
from worldcanon.indexer import full_index_corpus
from worldcanon.ledger import install_ledger_schema
from worldcanon.registry import load_registry
from worldcanon.search import search
from worldcanon.store import open_store


REPO = Path(__file__).parent.parent
FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


@pytest.fixture
def indexed(tmp_path):
    embedder = HashEmbedBackend(dim=32)
    con = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    install_ledger_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    yield con, embedder
    con.close()


def test_search_returns_results(indexed):
    con, embedder = indexed
    results = search(con, embedder, query="green eyes", limit=5)
    assert len(results) > 0
    assert "body" in results[0]
    assert "source_path" in results[0]


def test_search_scoped_to_corpus(indexed):
    con, embedder = indexed
    results = search(con, embedder, query="green eyes", corpus=["canon"], limit=5)
    for r in results:
        assert r["corpus"] == "canon"


def test_search_finds_via_keyword_when_semantic_score_low(indexed):
    con, embedder = indexed
    results = search(con, embedder, query="black-iron dagger", limit=10)
    assert any("dagger" in r["body"].lower() for r in results)


def test_search_empty_query_returns_empty(indexed):
    con, embedder = indexed
    results = search(con, embedder, query="", limit=5)
    assert results == []
