import pytest

from worldcanon.store import open_store
from worldcanon.ledger import (
    install_ledger_schema,
    sync_facts_for_file,
    list_facts,
    sync_relationships_for_file,
    list_relationships,
    sync_rules_for_file,
    list_rules,
    sync_names_for_file,
    list_names,
)


@pytest.fixture
def con(tmp_path):
    store = open_store(tmp_path / "t.sqlite", dim=4)
    c = store.connection()
    install_ledger_schema(c)
    yield c
    store.close()


def test_sync_facts_inserts(con):
    facts = [
        {"claim": "green eyes", "status": "canon",
         "introduced_in": "drafts/ch02.md", "chapter_index": 2},
        {"claim": "carries dagger", "status": "draft",
         "introduced_in": "brainstorm/x.md", "chapter_index": None},
    ]
    sync_facts_for_file(con, entity="Aerin",
                       source_file="entities/characters/Aerin.md", facts=facts)
    out = list_facts(con, entity="Aerin")
    assert len(out) == 2
    claims = {f["claim"] for f in out}
    assert "green eyes" in claims


def test_sync_facts_replaces_existing_for_same_source(con):
    sync_facts_for_file(con, entity="Aerin", source_file="entities/characters/Aerin.md",
                       facts=[{"claim": "green eyes", "status": "canon",
                               "introduced_in": "x", "chapter_index": None}])
    sync_facts_for_file(con, entity="Aerin", source_file="entities/characters/Aerin.md",
                       facts=[{"claim": "blue eyes", "status": "canon",
                               "introduced_in": "x", "chapter_index": None}])
    out = list_facts(con, entity="Aerin")
    assert len(out) == 1
    assert out[0]["claim"] == "blue eyes"


def test_list_facts_filter_by_chapter_max(con):
    sync_facts_for_file(con, entity="Aerin", source_file="x.md",
                       facts=[
                           {"claim": "a", "status": "canon", "introduced_in": "i", "chapter_index": 1},
                           {"claim": "b", "status": "canon", "introduced_in": "i", "chapter_index": 5},
                           {"claim": "c", "status": "canon", "introduced_in": "i", "chapter_index": None},
                       ])
    out = list_facts(con, entity="Aerin", chapter_max=3)
    claims = {f["claim"] for f in out}
    assert claims == {"a"}


def test_list_facts_filter_by_status(con):
    sync_facts_for_file(con, entity="A", source_file="x.md",
                       facts=[
                           {"claim": "1", "status": "canon", "introduced_in": "i", "chapter_index": None},
                           {"claim": "2", "status": "draft", "introduced_in": "i", "chapter_index": None},
                       ])
    canon = list_facts(con, entity="A", status="canon")
    assert len(canon) == 1
    assert canon[0]["claim"] == "1"


def test_sync_relationships(con):
    sync_relationships_for_file(con, from_entity="Aerin",
                                source_file="entities/characters/Aerin.md",
                                relationships=[
                                    {"with": "Lira", "type": "sister", "status": "canon",
                                     "notes": "estranged"},
                                ])
    out = list_relationships(con, entity="Aerin")
    assert len(out) == 1
    assert out[0]["with_entity"] == "Lira"


def test_sync_rules(con):
    sync_rules_for_file(con, system="Magic",
                       source_file="systems/Magic.md",
                       rules=[{"rule": "Magic cannot resurrect", "status": "canon"}])
    out = list_rules(con, system="Magic")
    assert len(out) == 1


def test_sync_names(con):
    sync_names_for_file(con, culture="northern",
                       source_file="naming/northern.md",
                       names=[
                           {"name": "Aerin", "status": "used", "used_by": "entities/characters/Aerin.md"},
                           {"name": "Bjorn", "status": "candidate"},
                       ])
    out = list_names(con, culture="northern")
    assert len(out) == 2


def test_history_recorded_on_status_change(con):
    sync_facts_for_file(con, entity="A", source_file="x.md",
                       facts=[{"claim": "c", "status": "draft", "introduced_in": "i", "chapter_index": None}])
    sync_facts_for_file(con, entity="A", source_file="x.md",
                       facts=[{"claim": "c", "status": "canon", "introduced_in": "i", "chapter_index": None}])
    rows = con.execute("SELECT * FROM fact_history WHERE entity = 'A' AND claim = 'c'").fetchall()
    assert len(rows) == 2
