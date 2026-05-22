"""Prose chunker — paragraph windows with 1-paragraph overlap.

Used for canon, drafts, and research corpora. Extracts [[wikilinks]] and
#tags as chunk-level metadata.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import ChunkerOutput, parse_frontmatter
from ..store import Chunk


WIKILINK = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]")
HASHTAG = re.compile(r"(?<!\w)#([A-Za-z][\w-]*)")

WINDOW = 3
OVERLAP = 1


def _split_paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def chunk_prose_file(
    *,
    corpus: str,
    source_root: Path,
    path: Path,
    extras: dict[str, Any],
) -> ChunkerOutput:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    paragraphs = _split_paragraphs(body)
    rel = path.relative_to(source_root).as_posix()
    title = str(meta.get("title") or meta.get("name") or path.stem)
    mtime = int(path.stat().st_mtime)
    abs_path = str(path.resolve())

    chunks: list[Chunk] = []
    if not paragraphs:
        return ChunkerOutput(chunks=chunks)

    step = max(1, WINDOW - OVERLAP)
    idx = 0
    i = 0
    while i < len(paragraphs):
        window = paragraphs[i:i + WINDOW]
        chunk_body = "\n\n".join(window)
        entities = sorted({m.group(1).strip() for m in WIKILINK.finditer(chunk_body)})
        tags = sorted({m.group(1) for m in HASHTAG.finditer(chunk_body)})
        chunks.append(
            Chunk(
                chunk_id=f"{corpus}:{rel}:{idx}",
                corpus=corpus,
                source_path=rel,
                source_abs_path=abs_path,
                title=title,
                body=chunk_body,
                metadata={**meta, "entities": entities, "tags": tags,
                          "paragraph_start": i, "paragraph_end": i + len(window) - 1},
                mtime=mtime,
            )
        )
        idx += 1
        if i + WINDOW >= len(paragraphs):
            break
        i += step

    return ChunkerOutput(chunks=chunks)
