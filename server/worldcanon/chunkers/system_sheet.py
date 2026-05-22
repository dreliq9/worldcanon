"""System sheet chunker — magic, technology, economy, religion, etc.

Mirrors entity_sheet's shape but uses `## Rules` instead of `## Facts`/
`## Relationships`. Emits one file-level chunk, paragraph body chunks, and
rule records for the ledger.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import ChunkerOutput, Rule, parse_frontmatter, parse_rules
from ..store import Chunk

SECTION = re.compile(r"^##\s+", re.MULTILINE)


def _strip_rules_section(body: str) -> str:
    parts = SECTION.split(body)
    if len(parts) == 1:
        return body
    out = [parts[0]]
    for chunk in parts[1:]:
        title_line, _, _ = chunk.partition("\n")
        if title_line.strip().lower() == "rules":
            continue
        out.append("## " + chunk)
    return "".join(out)


def _split_paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def chunk_system_sheet_file(
    *,
    corpus: str,
    source_root: Path,
    path: Path,
    extras: dict[str, Any],
) -> ChunkerOutput:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    rel = path.relative_to(source_root).as_posix()
    system_name = str(meta.get("name") or path.stem)
    mtime = int(path.stat().st_mtime)
    abs_path = str(path.resolve())

    narrative = _strip_rules_section(body)
    paragraphs = _split_paragraphs(narrative)
    summary_body = "\n\n".join(paragraphs[:3])

    file_chunk = Chunk(
        chunk_id=f"{corpus}:{rel}:sheet",
        corpus=corpus,
        source_path=rel,
        source_abs_path=abs_path,
        title=system_name,
        body=summary_body,
        metadata={**meta, "kind": "system_sheet", "name": system_name},
        mtime=mtime,
    )

    body_chunks: list[Chunk] = []
    for i, para in enumerate(paragraphs):
        body_chunks.append(
            Chunk(
                chunk_id=f"{corpus}:{rel}:body:{i}",
                corpus=corpus,
                source_path=rel,
                source_abs_path=abs_path,
                title=system_name,
                body=para,
                metadata={"kind": "body", "name": system_name, "paragraph_index": i},
                mtime=mtime,
            )
        )

    rules = [
        Rule(
            system=system_name,
            rule=r["rule"],
            status=r.get("status", "canon"),
            source_file=rel,
        )
        for r in parse_rules(body)
        if r.get("rule")
    ]

    return ChunkerOutput(chunks=[file_chunk, *body_chunks], rules=rules)
