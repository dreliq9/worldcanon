from worldcanon.chunkers import (
    parse_frontmatter,
    parse_facts,
    parse_relationships,
    parse_rules,
    parse_names,
)


def test_parse_frontmatter_basic():
    text = "---\ntype: character\nname: Aerin\n---\nbody text"
    meta, body = parse_frontmatter(text)
    assert meta == {"type": "character", "name": "Aerin"}
    assert body == "body text"


def test_parse_frontmatter_missing():
    text = "no frontmatter here"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == "no frontmatter here"


def test_parse_facts_extracts_section():
    body = """# Aerin

prose

## Facts

- claim: "has green eyes"
  status: canon
  introduced_in: drafts/ch02_draft.md#L8
  chapter_index: 3

- claim: "carries a dagger"
  status: draft
  introduced_in: drafts/ch02_draft.md
  chapter_index: null
"""
    facts = parse_facts(body)
    assert len(facts) == 2
    assert facts[0]["claim"] == "has green eyes"
    assert facts[0]["status"] == "canon"
    assert facts[0]["chapter_index"] == 3
    assert facts[1]["chapter_index"] is None


def test_parse_facts_missing_section_returns_empty():
    body = "no facts section here"
    assert parse_facts(body) == []


def test_parse_relationships_extracts_section():
    body = """# Aerin

## Relationships

- with: Lira
  type: sister
  status: canon
  notes: estranged
"""
    rels = parse_relationships(body)
    assert len(rels) == 1
    assert rels[0]["with"] == "Lira"
    assert rels[0]["type"] == "sister"


def test_parse_rules_extracts_section():
    body = """# Magic

## Rules

- rule: "Casting drains a year of the wielder's life per major spell"
  status: canon
"""
    rules = parse_rules(body)
    assert len(rules) == 1
    assert "year" in rules[0]["rule"]


def test_parse_names_extracts_section():
    body = """# Northern

## Names

- name: Aerin
  status: used
  used_by: entities/characters/Aerin.md

- name: Bjorn
  status: candidate
"""
    names = parse_names(body)
    assert len(names) == 2
    assert names[0]["name"] == "Aerin"
    assert names[0]["status"] == "used"
    assert names[1]["status"] == "candidate"
