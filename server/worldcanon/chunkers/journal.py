"""Journal chunker — brainstorm and ideation notes.

Date metadata is sourced from frontmatter `date:` first, then filename
pattern `YYYY-MM-DD-HHMM.md` or `YYYY-MM-DD.md`.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from . import ChunkerOutput, parse_frontmatter
from ..store import Chunk


_FILENAME_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[-T](\d{2})(\d{2}))?")


def _date_from_filename(stem: str) -> str | None:
    m = _FILENAME_DATE.match(stem)
    if not m:
        return None
    date_part = m.group(1)
    hh = m.group(2)
    mm = m.group(3)
    if hh and mm:
        return f"{date_part}T{hh}:{mm}:00"
    return date_part


def _split_paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def chunk_journal_file(
    *,
    corpus: str,
    source_root: Path,
    path: Path,
    extras: dict[str, Any],
) -> ChunkerOutput:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    rel = path.relative_to(source_root).as_posix()
    mtime = int(path.stat().st_mtime)
    abs_path = str(path.resolve())

    date_value = meta.get("date") or _date_from_filename(path.stem)
    status = meta.get("status", "unprocessed")
    title = str(meta.get("title") or path.stem)

    paragraphs = _split_paragraphs(body)
    chunks: list[Chunk] = []
    for i, para in enumerate(paragraphs):
        chunks.append(
            Chunk(
                chunk_id=f"{corpus}:{rel}:{i}",
                corpus=corpus,
                source_path=rel,
                source_abs_path=abs_path,
                title=title,
                body=para,
                metadata={
                    **meta,
                    "date": date_value,
                    "status": status,
                    "paragraph_index": i,
                },
                mtime=mtime,
            )
        )
    if not chunks:
        chunks.append(
            Chunk(
                chunk_id=f"{corpus}:{rel}:0",
                corpus=corpus,
                source_path=rel,
                source_abs_path=abs_path,
                title=title,
                body="",
                metadata={**meta, "date": date_value, "status": status,
                          "paragraph_index": 0},
                mtime=mtime,
            )
        )
    return ChunkerOutput(chunks=chunks)
