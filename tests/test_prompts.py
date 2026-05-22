from worldcanon.prompts import render_contradiction_check, render_ask_world


def test_contradiction_check_substitutes_fields():
    out = render_contradiction_check(
        entity="Aerin",
        facts=[
            {"claim": "has green eyes", "status": "canon"},
            {"claim": "carries a dagger", "status": "draft"},
        ],
        text="Aerin's blue eyes scanned the page.",
    )
    assert "Aerin" in out
    assert "has green eyes" in out
    assert "carries a dagger" in out
    assert "blue eyes scanned" in out
    # The JSON example survives format() — outer braces are literal.
    assert '{"contradictions"' in out


def test_ask_world_substitutes_context():
    out = render_ask_world(
        question="What color are Aerin's eyes?",
        chunks=[
            {"source_path": "canon/ch01.md", "body": "Her green eyes glittered."},
            {"source_path": "drafts/ch02.md", "body": "Aerin scanned the harbor."},
        ],
    )
    assert "What color" in out
    assert "[canon/ch01.md]" in out
    assert "Her green eyes glittered." in out


def test_ask_world_handles_empty_chunks():
    out = render_ask_world(question="anything", chunks=[])
    assert "Question: anything" in out
