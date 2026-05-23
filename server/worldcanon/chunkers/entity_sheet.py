"""Entity sheet chunker.

Emits, per file:
- one file-level chunk (metadata + frontmatter + first ~3 paragraphs of body)
- N body chunks (prose-style, for retrieval against the body)
- N fact records (mirrored to the ledger)
- N relationship records (mirrored to the ledger)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import (
    ChunkerOutput,
    Fact,
    Relationship,
    parse_facts,
    parse_frontmatter,
    parse_relationships,
)
from ..store import Chunk

WIKILINK = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]")
SECTION = re.compile(r"^##\s+", re.MULTILINE)

_ALLOWED_VISIBILITY = {"secret", "revealed", "hinted", "red_herring"}


def _coerce_visibility(value: object) -> str:
    """Sheets authored without TTRPG awareness omit this field; treat as
    fully revealed. Unknown strings collapse to 'revealed' so a typo never
    accidentally hides content from the GM."""
    if isinstance(value, str) and value in _ALLOWED_VISIBILITY:
        return value
    return "revealed"


def _strip_sections(body: str) -> str:
    """Return body with `## Facts` / `## Relationships` sections removed."""
    parts = SECTION.split(body)
    if len(parts) == 1:
        return body
    out = [parts[0]]
    for chunk in parts[1:]:
        title_line, _, rest = chunk.partition("\n")
        if title_line.strip().lower() in {"facts", "relationships"}:
            continue
        out.append("## " + chunk)
    return "".join(out)


def _split_paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def chunk_entity_sheet_file(
    *,
    corpus: str,
    source_root: Path,
    path: Path,
    extras: dict[str, Any],
) -> ChunkerOutput:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    rel = path.relative_to(source_root).as_posix()
    entity_name = str(meta.get("name") or path.stem)
    mtime = int(path.stat().st_mtime)
    abs_path = str(path.resolve())

    narrative = _strip_sections(body)
    paragraphs = _split_paragraphs(narrative)
    summary_body = "\n\n".join(paragraphs[:3])
    file_chunk = Chunk(
        chunk_id=f"{corpus}:{rel}:sheet",
        corpus=corpus,
        source_path=rel,
        source_abs_path=abs_path,
        title=entity_name,
        body=summary_body,
        metadata={**meta, "kind": "entity_sheet", "name": entity_name},
        mtime=mtime,
    )

    body_chunks: list[Chunk] = []
    for i, para in enumerate(paragraphs):
        entities = sorted({m.group(1).strip() for m in WIKILINK.finditer(para)})
        body_chunks.append(
            Chunk(
                chunk_id=f"{corpus}:{rel}:body:{i}",
                corpus=corpus,
                source_path=rel,
                source_abs_path=abs_path,
                title=entity_name,
                body=para,
                metadata={
                    "kind": "body",
                    "name": entity_name,
                    "entities": entities,
                    "paragraph_index": i,
                },
                mtime=mtime,
            )
        )

    facts = [
        Fact(
            entity=entity_name,
            claim=f["claim"],
            status=f.get("status", "draft"),
            introduced_in=f.get("introduced_in", rel),
            chapter_index=f.get("chapter_index"),
            source_file=rel,
            player_visibility=_coerce_visibility(f.get("player_visibility")),
            revealed_in_session=f.get("revealed_in_session"),
        )
        for f in parse_facts(body)
        if f.get("claim")
    ]
    relationships = [
        Relationship(
            from_entity=entity_name,
            with_entity=r["with"],
            type=r.get("type", "unknown"),
            status=r.get("status", "canon"),
            notes=r.get("notes"),
            source_file=rel,
        )
        for r in parse_relationships(body)
        if r.get("with")
    ]

    return ChunkerOutput(
        chunks=[file_chunk, *body_chunks],
        facts=facts,
        relationships=relationships,
    )
