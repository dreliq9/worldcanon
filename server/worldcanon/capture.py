"""Brainstorm capture helper. Writes timestamped notes into <vault>/brainstorm/.

Filename pattern: `YYYY-MM-DD-HHMM.md`. If a file with the same minute already
exists, we append `-2`, `-3`, … until we land on an unused name.

Frontmatter is fixed-format YAML — type, date, status, entities_mentioned,
topics, source. The body of the note is the captured text verbatim.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import yaml


def _yaml_inline_list(items: list[str]) -> str:
    if not items:
        return "[]"
    dumped = yaml.safe_dump(
        {"_": items},
        default_flow_style=True,
        allow_unicode=True,
        width=10**9,
    ).strip()
    # dumped is "{_: [...]}" — strip the wrapper to get just the list.
    return dumped[len("{_: "):-1]


def _yaml_inline_scalar(value: str) -> str:
    dumped = yaml.safe_dump(
        {"_": value},
        default_flow_style=True,
        allow_unicode=True,
        width=10**9,
    ).strip()
    return dumped[len("{_: "):-1]


def brainstorm_template(
    *,
    date: str,
    body: str,
    source: str,
    entities: list[str],
    topics: list[str],
) -> str:
    entities_inline = _yaml_inline_list(entities)
    topics_inline = _yaml_inline_list(topics)
    source_inline = _yaml_inline_scalar(source)
    lines = [
        "---",
        "type: brainstorm",
        f"date: {date}",
        "status: unprocessed",
        f"entities_mentioned: {entities_inline}",
        f"topics: {topics_inline}",
        f"source: {source_inline}",
        "---",
        "",
        "# ",
        "",
        body,
        "",
    ]
    return "\n".join(lines)


def _slug_for_filename(iso_timestamp: str) -> str:
    dt = datetime.datetime.fromisoformat(iso_timestamp)
    return dt.strftime("%Y-%m-%d-%H%M")


def write_brainstorm_note(
    *,
    vault_root: Path,
    text: str,
    source: str,
    entities: list[str],
    topics: list[str],
    now_iso: str,
) -> dict[str, Any]:
    folder = vault_root / "brainstorm"
    folder.mkdir(parents=True, exist_ok=True)

    base_slug = _slug_for_filename(now_iso)
    candidate = folder / f"{base_slug}.md"
    counter = 2
    while candidate.exists():
        candidate = folder / f"{base_slug}-{counter}.md"
        counter += 1

    content = brainstorm_template(
        date=now_iso,
        body=text,
        source=source,
        entities=entities,
        topics=topics,
    )
    candidate.write_text(content, encoding="utf-8")
    rel = candidate.relative_to(vault_root).as_posix()
    return {"status": "ok", "path": rel}
