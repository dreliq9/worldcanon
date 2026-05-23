"""Spoiler-control + GM/Player view tests.

Schema migration, chunker parsing, list_facts filtering, and the new
/entity?view= and /export/player-wiki endpoints.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from worldcanon.api import build_app
from worldcanon.chunkers.entity_sheet import _coerce_visibility
from worldcanon.embedder import HashEmbedBackend
from worldcanon.ideation import install_ideation_schema
from worldcanon.indexer import full_index_corpus
from worldcanon.ledger import (
    PLAYER_VISIBLE,
    install_ledger_schema,
    list_facts,
    sync_facts_for_file,
)
from worldcanon.llm import StubBackend
from worldcanon.registry import load_registry
from worldcanon.store import open_store


REPO = Path(__file__).parent.parent


def _store(tmp_path):
    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    install_ledger_schema(store.connection())
    return store, embedder


# ---------- Schema migration ----------

def test_install_ledger_is_idempotent_when_columns_already_present(tmp_path):
    store, _ = _store(tmp_path)
    # Second call must not raise — install is run on every sidecar start.
    install_ledger_schema(store.connection())
    cols = {row[1] for row in store.connection().execute("PRAGMA table_info(facts)")}
    assert "player_visibility" in cols
    assert "revealed_in_session" in cols


def test_install_ledger_migrates_existing_facts_table(tmp_path):
    """Simulate a pre-existing index from before the schema change."""
    db = tmp_path / "legacy.sqlite"
    import sqlite3
    legacy = sqlite3.connect(str(db))
    legacy.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            claim TEXT NOT NULL,
            status TEXT NOT NULL,
            introduced_in TEXT NOT NULL,
            chapter_index INTEGER,
            source_file TEXT NOT NULL,
            created INTEGER NOT NULL,
            UNIQUE(entity, claim, source_file)
        );
        """
    )
    legacy.execute(
        "INSERT INTO facts (entity, claim, status, introduced_in, source_file, created) VALUES (?, ?, ?, ?, ?, ?)",
        ("Aerin", "old fact", "canon", "x", "x", 0),
    )
    legacy.commit()
    legacy.close()

    # Now open the store the regular way — install_ledger_schema must add
    # the missing columns and existing rows must default to 'revealed'.
    store = open_store(db, dim=4)
    install_ledger_schema(store.connection())
    rows = list(store.connection().execute("SELECT * FROM facts"))
    assert len(rows) == 1
    assert rows[0]["player_visibility"] == "revealed"
    assert rows[0]["revealed_in_session"] is None


# ---------- Chunker ----------

def test_coerce_visibility_accepts_valid_values():
    for v in ("secret", "revealed", "hinted", "red_herring"):
        assert _coerce_visibility(v) == v


def test_coerce_visibility_rejects_unknown_to_safe_default():
    assert _coerce_visibility("public") == "revealed"
    assert _coerce_visibility(None) == "revealed"
    assert _coerce_visibility(42) == "revealed"


def test_entity_sheet_chunker_reads_player_visibility(tmp_path):
    sheet = tmp_path / "sheet.md"
    sheet.write_text(
        "---\ntype: character\nname: Lyra\n---\n\n"
        "# Lyra\n\nIntro.\n\n## Facts\n\n"
        "- claim: \"is brave\"\n"
        "  status: canon\n"
        "  introduced_in: x\n"
        "  chapter_index: null\n"
        "  player_visibility: secret\n"
        "  revealed_in_session: 3\n\n"
        "- claim: \"has green eyes\"\n"
        "  status: canon\n"
        "  introduced_in: x\n"
        "  chapter_index: null\n",
        encoding="utf-8",
    )
    from worldcanon.chunkers.entity_sheet import chunk_entity_sheet_file
    out = chunk_entity_sheet_file(
        corpus="entities", source_root=tmp_path, path=sheet, extras={}
    )
    secrets = [f for f in out.facts if f.claim == "is brave"]
    assert len(secrets) == 1
    assert secrets[0].player_visibility == "secret"
    assert secrets[0].revealed_in_session == 3

    public = [f for f in out.facts if f.claim == "has green eyes"]
    assert public[0].player_visibility == "revealed"
    assert public[0].revealed_in_session is None


# ---------- Ledger filtering ----------

def test_list_facts_gm_view_returns_all(tmp_path):
    store, _ = _store(tmp_path)
    con = store.connection()
    sync_facts_for_file(con, entity="Lyra", source_file="lyra.md", facts=[
        {"claim": "secret backstory", "status": "canon",
         "player_visibility": "secret"},
        {"claim": "wears green", "status": "canon",
         "player_visibility": "revealed"},
        {"claim": "carries amulet", "status": "canon",
         "player_visibility": "hinted"},
    ])
    facts = list_facts(con, entity="Lyra")  # default view = gm
    assert {f["claim"] for f in facts} == {"secret backstory", "wears green", "carries amulet"}


def test_list_facts_player_view_excludes_secrets(tmp_path):
    store, _ = _store(tmp_path)
    con = store.connection()
    sync_facts_for_file(con, entity="Lyra", source_file="lyra.md", facts=[
        {"claim": "secret backstory", "status": "canon",
         "player_visibility": "secret"},
        {"claim": "wears green", "status": "canon",
         "player_visibility": "revealed"},
        {"claim": "carries amulet", "status": "canon",
         "player_visibility": "hinted"},
        {"claim": "is actually friendly", "status": "canon",
         "player_visibility": "red_herring"},
    ])
    facts = list_facts(con, entity="Lyra", view="player")
    claims = {f["claim"] for f in facts}
    assert "secret backstory" not in claims
    assert "wears green" in claims
    assert "carries amulet" in claims
    assert "is actually friendly" in claims  # red herring stays visible


def test_list_facts_explicit_visibility_filter(tmp_path):
    store, _ = _store(tmp_path)
    con = store.connection()
    sync_facts_for_file(con, entity="Lyra", source_file="lyra.md", facts=[
        {"claim": "a", "status": "canon", "player_visibility": "secret"},
        {"claim": "b", "status": "canon", "player_visibility": "secret"},
        {"claim": "c", "status": "canon", "player_visibility": "revealed"},
    ])
    only_secrets = list_facts(con, player_visibility="secret")
    assert {f["claim"] for f in only_secrets} == {"a", "b"}


def test_list_facts_default_visibility_is_revealed_for_legacy_inserts(tmp_path):
    store, _ = _store(tmp_path)
    con = store.connection()
    # Caller didn't set the field — defaults to 'revealed'.
    sync_facts_for_file(con, entity="Lyra", source_file="lyra.md", facts=[
        {"claim": "old fact", "status": "canon"},
    ])
    facts = list_facts(con, entity="Lyra", view="player")
    assert {f["claim"] for f in facts} == {"old fact"}


def test_sync_records_visibility_change_as_edit(tmp_path):
    store, _ = _store(tmp_path)
    con = store.connection()
    sync_facts_for_file(con, entity="Lyra", source_file="lyra.md", facts=[
        {"claim": "x", "status": "canon", "player_visibility": "secret"},
    ])
    sync_facts_for_file(con, entity="Lyra", source_file="lyra.md", facts=[
        {"claim": "x", "status": "canon", "player_visibility": "revealed",
         "revealed_in_session": 4},
    ])
    rows = list(con.execute(
        "SELECT player_visibility, revealed_in_session FROM facts WHERE entity = 'Lyra'"
    ))
    assert rows[0]["player_visibility"] == "revealed"
    assert rows[0]["revealed_in_session"] == 4


# ---------- API + export endpoint ----------

def _client(tmp_path):
    store, embedder = _store(tmp_path)
    install_ideation_schema(store.connection())
    fixture_vault = REPO / "tests" / "fixtures" / "sample_vault"
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=fixture_vault)
    for cfg in cfgs:
        full_index_corpus(store.connection(), cfg, embedder)
    app = build_app(
        store=store, embedder=embedder, cfgs=cfgs,
        llm=StubBackend(responses=[]), vault_root=fixture_vault,
    )
    return TestClient(app)


def test_entity_endpoint_gm_view_includes_all_facts(tmp_path):
    """The Aerin fixture has 3 facts. GM sees all of them."""
    client = _client(tmp_path)
    r = client.get("/entity/Aerin")
    assert r.status_code == 200
    assert len(r.json()["facts"]) >= 3


def _mark_first_fact_secret(tmp_path, entity: str) -> str:
    """Promote the lowest-id fact for `entity` to player_visibility=secret.
    Returns its claim text so the test can assert on it."""
    store = open_store(tmp_path / "t.sqlite", dim=32)
    con = store.connection()
    row = con.execute(
        "SELECT id, claim FROM facts WHERE entity = ? ORDER BY id LIMIT 1",
        (entity,),
    ).fetchone()
    assert row is not None, f"fixture seed missing facts for {entity}"
    con.execute(
        "UPDATE facts SET player_visibility = 'secret' WHERE id = ?",
        (row["id"],),
    )
    con.commit()
    return row["claim"]


def test_entity_endpoint_player_view_hides_secrets(tmp_path):
    client = _client(tmp_path)
    secret_claim = _mark_first_fact_secret(tmp_path, "Aerin")

    gm_facts = client.get("/entity/Aerin?view=gm").json()["facts"]
    player_facts = client.get("/entity/Aerin?view=player").json()["facts"]
    assert any(f["claim"] == secret_claim for f in gm_facts)
    assert not any(f["claim"] == secret_claim for f in player_facts)


def test_facts_endpoint_respects_view(tmp_path):
    client = _client(tmp_path)
    _mark_first_fact_secret(tmp_path, "Aerin")
    gm = client.get("/facts?entity=Aerin&view=gm").json()["facts"]
    player = client.get("/facts?entity=Aerin&view=player").json()["facts"]
    assert len(gm) > len(player)


def test_export_player_wiki_omits_secret_facts(tmp_path):
    client = _client(tmp_path)
    _mark_first_fact_secret(tmp_path, "Aerin")
    r = client.get("/export/player-wiki")
    assert r.status_code == 200
    body = r.json()
    assert "generated_at" in body
    assert body["entry_count"] >= 1
    aerin_entry = next((e for e in body["entries"] if e["name"] == "Aerin"), None)
    assert aerin_entry is not None
    all_facts_count = len(client.get("/entity/Aerin?view=gm").json()["facts"])
    assert len(aerin_entry["facts"]) < all_facts_count


def test_export_player_wiki_one_entry_per_entity(tmp_path):
    client = _client(tmp_path)
    r = client.get("/export/player-wiki")
    names = [e["name"] for e in r.json()["entries"]]
    # Fixture seed has Aerin, Lira (characters) + Stormholm (place) + Northern (faction)
    assert "Aerin" in names
    assert "Lira" in names
    assert "Stormholm" in names
    assert len(names) == len(set(names))  # no duplicates


# ---------- Constants ----------

def test_player_visible_constants_match_expected_levels():
    assert "secret" not in PLAYER_VISIBLE
    assert set(PLAYER_VISIBLE) == {"revealed", "hinted", "red_herring"}
