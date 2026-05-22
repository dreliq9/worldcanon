"""Naming sheet chunker — one file per culture.

Emits a file-level chunk for retrieval ("tell me about northern naming")
and name records for the ledger (`## Names` section).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ChunkerOutput, NameRecord, parse_frontmatter, parse_names
from ..store import Chunk


def chunk_naming_sheet_file(
    *,
    corpus: str,
    source_root: Path,
    path: Path,
    extras: dict[str, Any],
) -> ChunkerOutput:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    rel = path.relative_to(source_root).as_posix()
    culture = str(meta.get("culture") or path.stem)
    mtime = int(path.stat().st_mtime)
    abs_path = str(path.resolve())

    file_chunk = Chunk(
        chunk_id=f"{corpus}:{rel}:sheet",
        corpus=corpus,
        source_path=rel,
        source_abs_path=abs_path,
        title=f"{culture} naming",
        body=body.strip(),
        metadata={**meta, "kind": "naming_sheet", "culture": culture},
        mtime=mtime,
    )

    names = [
        NameRecord(
            culture=culture,
            name=n["name"],
            status=n.get("status", "candidate"),
            used_by=n.get("used_by"),
            notes=n.get("notes"),
            source_file=rel,
        )
        for n in parse_names(body)
        if n.get("name")
    ]

    return ChunkerOutput(chunks=[file_chunk], names=names)
