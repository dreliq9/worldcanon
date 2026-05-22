from pathlib import Path

from worldcanon.chunkers.system_sheet import chunk_system_sheet_file


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _run():
    return chunk_system_sheet_file(
        corpus="systems",
        source_root=FIXTURE_VAULT / "systems",
        path=FIXTURE_VAULT / "systems" / "Magic.md",
        extras={},
    )


def test_system_sheet_emits_file_level_chunk():
    out = _run()
    assert any(c.metadata.get("kind") == "system_sheet" for c in out.chunks)


def test_system_sheet_emits_rules():
    out = _run()
    assert len(out.rules) == 3
    rule_texts = {r.rule for r in out.rules}
    assert "Magic cannot resurrect the dead" in rule_texts


def test_system_sheet_rules_carry_system_name():
    out = _run()
    for r in out.rules:
        assert r.system == "Magic of the Northern Kingdom"
        assert r.source_file.endswith("Magic.md")


def test_system_sheet_no_facts_or_relationships():
    out = _run()
    assert out.facts == []
    assert out.relationships == []
