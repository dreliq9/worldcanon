from pathlib import Path

import pytest

from worldcanon.embedder import HashEmbedBackend
from worldcanon.indexer import full_index_corpus, index_file
from worldcanon.ledger import install_ledger_schema, list_facts, list_relationships, list_rules, list_names
from worldcanon.registry import load_registry
from worldcanon.store import open_store


REPO = Path(__file__).parent.parent
FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


@pytest.fixture
def setup(tmp_path):
    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    yield embedder, con, cfgs
    con.close()


def test_full_index_entities_populates_chunks(setup):
    embedder, con, cfgs = setup
    entities_cfg = next(c for c in cfgs if c.name == "entities")
    stats = full_index_corpus(con, entities_cfg, embedder)
    assert stats["chunks_upserted"] > 0
    n = con.execute("SELECT COUNT(*) FROM chunks WHERE corpus='entities'").fetchone()[0]
    assert n > 0


def test_full_index_entities_populates_facts(setup):
    embedder, con, cfgs = setup
    entities_cfg = next(c for c in cfgs if c.name == "entities")
    full_index_corpus(con, entities_cfg, embedder)
    aerin_facts = list_facts(con, entity="Aerin")
    assert len(aerin_facts) == 3


def test_full_index_entities_populates_relationships(setup):
    embedder, con, cfgs = setup
    entities_cfg = next(c for c in cfgs if c.name == "entities")
    full_index_corpus(con, entities_cfg, embedder)
    aerin_rels = list_relationships(con, entity="Aerin")
    assert len(aerin_rels) >= 2


def test_full_index_systems_populates_rules(setup):
    embedder, con, cfgs = setup
    sys_cfg = next(c for c in cfgs if c.name == "systems")
    full_index_corpus(con, sys_cfg, embedder)
    rules = list_rules(con, system="Magic of the Northern Kingdom")
    assert len(rules) == 3


def test_full_index_naming_populates_names(setup):
    embedder, con, cfgs = setup
    naming_cfg = next(c for c in cfgs if c.name == "naming")
    full_index_corpus(con, naming_cfg, embedder)
    names = list_names(con, culture="northern")
    assert len(names) == 4


def test_index_file_is_idempotent(setup):
    embedder, con, cfgs = setup
    entities_cfg = next(c for c in cfgs if c.name == "entities")
    aerin = FIXTURE_VAULT / "entities" / "characters" / "Aerin.md"
    index_file(con, entities_cfg, aerin, embedder)
    first = con.execute("SELECT COUNT(*) FROM chunks WHERE corpus='entities'").fetchone()[0]
    index_file(con, entities_cfg, aerin, embedder)
    second = con.execute("SELECT COUNT(*) FROM chunks WHERE corpus='entities'").fetchone()[0]
    assert first == second
