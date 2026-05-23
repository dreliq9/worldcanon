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


def test_rename_plan_returns_entity_file_paths(tmp_path):
    client = _build_client(tmp_path)
    r = client.post("/entity/Aerin/rename", json={"new_name": "Erien"})
    assert r.status_code == 200
    body = r.json()
    assert body["old_name"] == "Aerin"
    assert body["new_name"] == "Erien"
    assert body["entity_file"].endswith("Aerin.md")
    assert body["new_entity_file"].endswith("Erien.md")


def test_rename_plan_finds_plain_text_rewrites(tmp_path):
    client = _build_client(tmp_path)
    body = client.post("/entity/Aerin/rename", json={"new_name": "Erien"}).json()
    rewrites = body["plain_text_rewrites"]
    assert any(r["file"].endswith("ch01.md") for r in rewrites)
    assert all(r["old"] == "Aerin" for r in rewrites)
    assert all(r["new"] == "Erien" for r in rewrites)


def test_rename_plan_does_not_include_wikilink_rewrites(tmp_path):
    client = _build_client(tmp_path)
    body = client.post("/entity/Aerin/rename", json={"new_name": "Erien"}).json()
    rewrites = body["plain_text_rewrites"]
    for r in rewrites:
        target_path = FIXTURE_VAULT / r["file"]
        content = target_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        line_idx = r["line"] - 1
        if line_idx >= len(lines):
            continue
        line_text = lines[line_idx]
        idx = r["col"]
        assert "[[" + r["old"] + "]]" not in line_text[max(0, idx - 2):idx + len(r["old"]) + 2]


def test_rename_plan_finds_alias_references(tmp_path):
    client = _build_client(tmp_path)
    body = client.post("/entity/Aerin/rename", json={"new_name": "Erien"}).json()
    alias_updates = body["alias_updates"]
    assert any("Lira" in u["file"] for u in alias_updates)


def test_rename_plan_new_entity_file_replaces_only_basename(tmp_path):
    """If an entity name appears in the directory portion of its path,
    str.replace would corrupt the directory; with_name must only swap
    the final component."""
    client = _build_client(tmp_path)
    body = client.post("/entity/Aerin/rename", json={"new_name": "Erien"}).json()
    new_path = body["new_entity_file"]
    assert new_path.endswith("/Erien.md") or new_path == "entities/Erien.md"
    assert "Aerin" not in new_path.rsplit("/", 1)[-1]


def test_rename_plan_survives_missing_alias_sheet(tmp_path):
    """If an entity sheet file is deleted between index time and the rename
    call, the alias scan must skip it, not raise FileNotFoundError → 500."""
    client = _build_client(tmp_path)
    missing = FIXTURE_VAULT / "entities" / "characters" / "Lira.md"
    backup = missing.read_text(encoding="utf-8")
    missing.unlink()
    try:
        r = client.post("/entity/Aerin/rename", json={"new_name": "Erien"})
        assert r.status_code == 200
        # Lira sheet was removed; it should simply not appear in alias_updates.
        alias_files = [u["file"] for u in r.json()["alias_updates"]]
        assert not any("Lira" in f for f in alias_files)
    finally:
        missing.write_text(backup, encoding="utf-8")


def test_rename_plan_404_for_unknown_entity(tmp_path):
    client = _build_client(tmp_path)
    r = client.post("/entity/Nonexistent/rename", json={"new_name": "Whatever"})
    assert r.status_code == 404


def test_rename_plan_422_for_empty_new_name(tmp_path):
    client = _build_client(tmp_path)
    r = client.post("/entity/Aerin/rename", json={"new_name": ""})
    assert r.status_code == 422
