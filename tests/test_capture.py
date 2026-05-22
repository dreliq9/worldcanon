from pathlib import Path

import yaml

from worldcanon.capture import write_brainstorm_note, brainstorm_template


def test_brainstorm_template_includes_frontmatter():
    out = brainstorm_template(
        date="2026-05-22T14:30:00",
        body="A wild idea.",
        source="webhook",
        entities=["Aerin"],
        topics=["weapon"],
    )
    assert out.startswith("---\n")
    assert "type: brainstorm" in out
    assert "date: 2026-05-22T14:30:00" in out
    assert "status: unprocessed" in out
    assert "source: webhook" in out
    assert "A wild idea." in out


def test_brainstorm_template_empty_lists_serialize_inline():
    out = brainstorm_template(
        date="2026-05-22T14:30:00",
        body="",
        source="obsidian",
        entities=[],
        topics=[],
    )
    assert "entities_mentioned: []" in out
    assert "topics: []" in out


def test_write_brainstorm_note_creates_file(tmp_path):
    vault = tmp_path / "vault"
    (vault / "brainstorm").mkdir(parents=True)
    result = write_brainstorm_note(
        vault_root=vault,
        text="A new thought about [[Aerin]].",
        source="webhook",
        entities=["Aerin"],
        topics=["character-detail"],
        now_iso="2026-05-22T14:30:00",
    )
    assert result["status"] == "ok"
    written = result["path"]
    abs_path = vault / written
    assert abs_path.exists()
    content = abs_path.read_text(encoding="utf-8")
    assert "[[Aerin]]" in content
    meta, _ = parse_frontmatter_for_test(content)
    assert meta["type"] == "brainstorm"
    assert meta["status"] == "unprocessed"
    assert meta["entities_mentioned"] == ["Aerin"]


def test_write_brainstorm_note_filename_format(tmp_path):
    vault = tmp_path / "vault"
    (vault / "brainstorm").mkdir(parents=True)
    result = write_brainstorm_note(
        vault_root=vault,
        text="x",
        source="webhook",
        entities=[],
        topics=[],
        now_iso="2026-05-22T14:30:42",
    )
    assert result["path"] == "brainstorm/2026-05-22-1430.md"


def test_write_brainstorm_note_avoids_collisions(tmp_path):
    vault = tmp_path / "vault"
    (vault / "brainstorm").mkdir(parents=True)
    r1 = write_brainstorm_note(
        vault_root=vault, text="first", source="webhook",
        entities=[], topics=[], now_iso="2026-05-22T14:30:00",
    )
    r2 = write_brainstorm_note(
        vault_root=vault, text="second", source="webhook",
        entities=[], topics=[], now_iso="2026-05-22T14:30:00",
    )
    assert r1["path"] != r2["path"]
    assert (vault / r1["path"]).exists()
    assert (vault / r2["path"]).exists()


def parse_frontmatter_for_test(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body
