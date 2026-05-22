from pathlib import Path

from worldcanon.chunkers.prose import chunk_prose_file


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def test_prose_chunker_returns_chunks_only():
    out = chunk_prose_file(
        corpus="canon",
        source_root=FIXTURE_VAULT / "canon",
        path=FIXTURE_VAULT / "canon" / "ch01.md",
        extras={},
    )
    assert len(out.chunks) >= 1
    assert out.facts == []
    assert out.relationships == []


def test_prose_chunker_extracts_wikilinks_to_metadata():
    out = chunk_prose_file(
        corpus="canon",
        source_root=FIXTURE_VAULT / "canon",
        path=FIXTURE_VAULT / "canon" / "ch01.md",
        extras={},
    )
    all_entities = set()
    for c in out.chunks:
        all_entities.update(c.metadata.get("entities", []))
    assert "Stormholm" in all_entities


def test_prose_chunker_strips_frontmatter_from_body():
    out = chunk_prose_file(
        corpus="canon",
        source_root=FIXTURE_VAULT / "canon",
        path=FIXTURE_VAULT / "canon" / "ch01.md",
        extras={},
    )
    for c in out.chunks:
        assert "type: chapter" not in c.body
        assert "---" not in c.body.splitlines()[0:1] if c.body else True


def test_prose_chunker_source_path_relative():
    out = chunk_prose_file(
        corpus="canon",
        source_root=FIXTURE_VAULT / "canon",
        path=FIXTURE_VAULT / "canon" / "ch01.md",
        extras={},
    )
    assert out.chunks[0].source_path == "ch01.md"
