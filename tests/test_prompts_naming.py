from worldcanon.prompts import render_name_suggest


def test_render_name_suggest_substitutes_all_fields():
    out = render_name_suggest(
        culture="northern",
        conventions=["two-syllable", "hard consonants", "common endings -in -ar -dr"],
        used_names=["Aerin", "Lira"],
        candidate_names=["Bjorn", "Sigrid"],
        role="warrior",
        vibe="grizzled veteran",
        count=5,
    )
    assert "northern" in out
    assert "two-syllable" in out
    assert "Aerin" in out
    assert "Bjorn" in out
    assert "warrior" in out
    assert "grizzled veteran" in out
    assert '"suggestions"' in out


def test_render_name_suggest_omits_optional_lines():
    out = render_name_suggest(
        culture="northern",
        conventions=[],
        used_names=[],
        candidate_names=[],
        role=None,
        vibe=None,
        count=3,
    )
    assert "northern" in out
    assert "3" in out
    assert "(none)" in out


def test_render_name_suggest_conventions_as_bullets():
    out = render_name_suggest(
        culture="elven",
        conventions=["flowing vowels", "soft consonants"],
        used_names=[],
        candidate_names=[],
        role=None,
        vibe=None,
        count=1,
    )
    assert "- flowing vowels" in out
    assert "- soft consonants" in out
