from worldcanon.prompts import render_triage_suggest


def test_render_triage_suggest_substitutes_fields():
    out = render_triage_suggest(
        filename="ch01_first_pass.md",
        content="The cliffs of Stormholm glittered at dawn...",
    )
    assert "ch01_first_pass.md" in out
    assert "cliffs of Stormholm" in out
    assert "canon" in out
    assert "drafts" in out
    assert "entities/characters" in out
    assert '"classification"' in out


def test_render_triage_suggest_truncates_long_content():
    long_body = "x" * 5000
    out = render_triage_suggest(filename="big.md", content=long_body)
    assert len(out) < 4000
