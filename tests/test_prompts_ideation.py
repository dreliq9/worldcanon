from worldcanon.prompts import (
    load_gap_priorities,
    render_ideation_question,
    render_ideation_response,
    render_fact_extraction,
)


def test_load_gap_priorities_parses_character():
    priorities = load_gap_priorities("character")
    assert "Motivation / what they want" in priorities
    assert "Defining wound or origin" in priorities
    assert priorities.index("Motivation / what they want") < priorities.index("Fears")


def test_load_gap_priorities_handles_place():
    priorities = load_gap_priorities("place")
    assert "History" in priorities
    assert "Geography" in priorities


def test_load_gap_priorities_unknown_type_returns_empty():
    assert load_gap_priorities("nonsense") == []


def test_render_ideation_question_substitutes_fields():
    out = render_ideation_question(
        entity_type="character",
        entity_name="Aerin",
        entity_state="(sparse sheet)",
        relevant_canon="(none)",
        addressed_gaps=[],
    )
    assert "Aerin" in out
    assert "character" in out
    assert "Motivation / what they want" in out


def test_render_ideation_response_substitutes_fields():
    out = render_ideation_response(
        entity_type="character",
        entity_name="Aerin",
        transcript="Q: ...\nA: ...",
        answer="She wants to be free.",
        addressed_gaps=["Defining wound or origin"],
    )
    assert "She wants to be free" in out
    assert '"facts":' in out
    assert "addressed_gap" in out
    assert "Defining wound or origin" in out


def test_render_fact_extraction_substitutes_text_and_source():
    out = render_fact_extraction(
        text="Aerin's green eyes glittered. [[Stormholm]] stood empty.",
        source="canon/ch01.md",
    )
    assert "canon/ch01.md" in out
    assert "green eyes glittered" in out
    assert '"proposed_facts":' in out
