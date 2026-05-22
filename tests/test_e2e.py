"""Spins the full app against the fixture vault and exercises the API the
way the Obsidian plugin will. This is the regression net for the whole
sidecar foundation.
"""
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


@pytest.fixture
def client(tmp_path):
    embedder = HashEmbedBackend(dim=32)
    con = open_store(tmp_path / "t.sqlite", dim=embedder.dim, check_same_thread=False)
    install_ledger_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    yield TestClient(build_app(con=con, embedder=embedder, cfgs=cfgs, llm=StubBackend(responses=[]), vault_root=FIXTURE_VAULT))
    con.close()


def test_e2e_full_pipeline(client):
    # Every corpus indexed and reported
    stats = client.get("/stats").json()
    names = {c["name"] for c in stats["corpora"]}
    assert {"canon", "drafts", "entities", "systems",
            "naming", "brainstorm", "research"} <= names

    # Search hits across corpora
    results = client.get("/search", params={"q": "Aerin"}).json()["results"]
    assert len(results) > 0

    # Entity lookup chains together sheet + facts + relationships + mentions
    aerin = client.get("/entity/Aerin").json()
    assert aerin["name"] == "Aerin"
    assert {f["claim"] for f in aerin["facts"]} == {
        "has green eyes",
        "is the sister of Lira",
        "carries a black-iron dagger",
    }
    assert any(rel["with_entity"] == "Lira" for rel in aerin["relationships"])
    assert isinstance(aerin["mentions"], list)

    # System lookup
    magic = client.get("/system/Magic of the Northern Kingdom").json()
    assert len(magic["rules"]) == 3

    # Facts filter
    canon_facts = client.get("/facts", params={"status": "canon"}).json()["facts"]
    assert all(f["status"] == "canon" for f in canon_facts)
    assert len(canon_facts) >= 4
