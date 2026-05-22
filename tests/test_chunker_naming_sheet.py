from pathlib import Path

from worldcanon.chunkers.naming_sheet import chunk_naming_sheet_file


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _run():
    return chunk_naming_sheet_file(
        corpus="naming",
        source_root=FIXTURE_VAULT / "naming",
        path=FIXTURE_VAULT / "naming" / "northern.md",
        extras={},
    )


def test_naming_sheet_emits_file_chunk():
    out = _run()
    assert any(c.metadata.get("kind") == "naming_sheet" for c in out.chunks)


def test_naming_sheet_emits_names():
    out = _run()
    assert len(out.names) == 4
    used = [n for n in out.names if n.status == "used"]
    assert len(used) == 2


def test_naming_sheet_culture_from_frontmatter():
    out = _run()
    for n in out.names:
        assert n.culture == "northern"
