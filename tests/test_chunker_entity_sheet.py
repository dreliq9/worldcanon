from pathlib import Path

from worldcanon.chunkers.entity_sheet import chunk_entity_sheet_file


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _run(name):
    return chunk_entity_sheet_file(
        corpus="entities",
        source_root=FIXTURE_VAULT / "entities",
        path=FIXTURE_VAULT / "entities" / "characters" / name,
        extras={},
    )


def test_entity_sheet_emits_file_level_chunk():
    out = _run("Aerin.md")
    assert any(c.metadata.get("kind") == "entity_sheet" for c in out.chunks)


def test_entity_sheet_emits_facts():
    out = _run("Aerin.md")
    assert len(out.facts) == 3
    claims = {f.claim for f in out.facts}
    assert "has green eyes" in claims
    assert "carries a black-iron dagger" in claims


def test_entity_sheet_emits_relationships():
    out = _run("Aerin.md")
    assert len(out.relationships) == 2
    targets = {r.with_entity for r in out.relationships}
    assert "Lira" in targets


def test_entity_sheet_indexes_body_paragraphs():
    out = _run("Aerin.md")
    body_chunks = [c for c in out.chunks if c.metadata.get("kind") == "body"]
    assert len(body_chunks) >= 1


def test_entity_sheet_facts_carry_source_file():
    out = _run("Aerin.md")
    for f in out.facts:
        assert f.source_file.endswith("Aerin.md")
        assert f.entity == "Aerin"


def test_entity_sheet_handles_missing_facts_section():
    out = chunk_entity_sheet_file(
        corpus="entities",
        source_root=FIXTURE_VAULT / "entities",
        path=FIXTURE_VAULT / "entities" / "factions" / "Northern.md",
        extras={},
    )
    assert len(out.facts) == 1
    assert out.relationships == []
