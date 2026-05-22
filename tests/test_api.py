from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from worldcanon.api import build_app
from worldcanon.embedder import HashEmbedBackend
from worldcanon.indexer import full_index_corpus
from worldcanon.ledger import install_ledger_schema
from worldcanon.registry import load_registry
from worldcanon.store import open_store


REPO = Path(__file__).parent.parent
FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


@pytest.fixture
def client(tmp_path):
    embedder = HashEmbedBackend(dim=32)
    con = open_store(tmp_path / "t.sqlite", dim=embedder.dim, check_same_thread=False)
    install_ledger_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    app = build_app(con=con, embedder=embedder, cfgs=cfgs)
    yield TestClient(app)
    con.close()


# Task 15 — /stats
def test_stats_endpoint(client):
    r = client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert "corpora" in body
    assert any(c["name"] == "entities" for c in body["corpora"])
    assert "fact_count" in body
    assert body["fact_count"] >= 4


# Task 16 — /search
def test_search_endpoint(client):
    r = client.get("/search", params={"q": "green eyes", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert isinstance(body["results"], list)


def test_search_endpoint_corpus_filter(client):
    r = client.get("/search", params={"q": "dagger", "corpus": "canon", "limit": 5})
    assert r.status_code == 200
    for hit in r.json()["results"]:
        assert hit["corpus"] == "canon"


def test_search_endpoint_empty_query(client):
    r = client.get("/search", params={"q": ""})
    assert r.status_code == 200
    assert r.json()["results"] == []


# Task 17 — /entity/{name}
def test_entity_endpoint_returns_sheet(client):
    r = client.get("/entity/Aerin")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Aerin"
    assert "facts" in body
    assert len(body["facts"]) == 3
    assert "relationships" in body
    assert "mentions" in body


def test_entity_endpoint_404_when_unknown(client):
    r = client.get("/entity/Nonexistent")
    assert r.status_code == 404


# Task 18 — /facts
def test_facts_endpoint_filter_entity(client):
    r = client.get("/facts", params={"entity": "Aerin"})
    assert r.status_code == 200
    facts = r.json()["facts"]
    assert len(facts) == 3
    for f in facts:
        assert f["entity"] == "Aerin"


def test_facts_endpoint_filter_status(client):
    r = client.get("/facts", params={"entity": "Aerin", "status": "canon"})
    facts = r.json()["facts"]
    assert all(f["status"] == "canon" for f in facts)


def test_facts_endpoint_chapter_max(client):
    r = client.get("/facts", params={"chapter_max": 0})
    assert r.json()["facts"] == []


# Task 19 — /relationships, /system/{name}, /timeline
def test_relationships_endpoint(client):
    r = client.get("/relationships", params={"entity": "Aerin"})
    assert r.status_code == 200
    rels = r.json()["relationships"]
    assert any(rel["with_entity"] == "Lira" for rel in rels)


def test_system_endpoint(client):
    r = client.get("/system/Magic of the Northern Kingdom")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Magic of the Northern Kingdom"
    assert len(body["rules"]) == 3


def test_system_endpoint_404(client):
    r = client.get("/system/NoSuchSystem")
    assert r.status_code == 404


def test_timeline_endpoint(client):
    r = client.get("/timeline")
    assert r.status_code == 200
    assert "events" in r.json()
