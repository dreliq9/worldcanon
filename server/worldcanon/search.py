"""Hybrid semantic + keyword search across one or more corpora.

Strategy:
1. Embed the query, run vec0 MATCH to get top-K semantic candidates
2. Run a LIKE-based keyword scan for exact-substring matches
3. Merge: dedup by chunk_id, blend scores (semantic + keyword bonus)
4. Filter by corpus if requested, return top `limit`

The hash embedder has low semantic fidelity, so the keyword fallback
matters for tests and minimal-machine deployments. For fastembed the
semantic component dominates.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Iterable

import numpy as np

from .embedder import Embedder
from .store import row_to_chunk_row


def _to_dict(row, score: float, source: str) -> dict:
    chunk = row_to_chunk_row(row)
    return {
        "chunk_id": chunk.chunk_id,
        "corpus": chunk.corpus,
        "source_path": chunk.source_path,
        "source_abs_path": chunk.source_abs_path,
        "title": chunk.title,
        "body": chunk.body,
        "metadata": chunk.metadata,
        "score": score,
        "match_source": source,
    }


def _semantic(
    con: sqlite3.Connection,
    embedder: Embedder,
    query: str,
    corpus: Iterable[str] | None,
    limit: int,
) -> list[dict]:
    vec = embedder.embed([query])[0]
    if np.linalg.norm(vec) == 0.0:
        return []
    vec_blob = vec.astype(np.float32).tobytes()
    sql = """
      SELECT chunks.*, chunks_vec.distance AS distance
      FROM chunks_vec
      JOIN chunk_vec_map ON chunk_vec_map.vec_rowid = chunks_vec.rowid
      JOIN chunks ON chunks.chunk_id = chunk_vec_map.chunk_id
      WHERE chunks_vec.embedding MATCH ?
        AND k = ?
    """
    args: list = [vec_blob, limit * 4]
    if corpus:
        placeholders = ",".join("?" for _ in corpus)
        sql += f" AND chunks.corpus IN ({placeholders})"
        args.extend(list(corpus))
    out: list[dict] = []
    for row in con.execute(sql, args):
        score = 1.0 - float(row["distance"]) / 2.0
        out.append(_to_dict(row, score, "semantic"))
    return out


def _keyword(
    con: sqlite3.Connection,
    query: str,
    corpus: Iterable[str] | None,
    limit: int,
) -> list[dict]:
    like = f"%{query.lower()}%"
    sql = "SELECT * FROM chunks WHERE LOWER(body) LIKE ?"
    args: list = [like]
    if corpus:
        placeholders = ",".join("?" for _ in corpus)
        sql += f" AND corpus IN ({placeholders})"
        args.extend(list(corpus))
    sql += " LIMIT ?"
    args.append(limit * 4)
    return [_to_dict(row, 0.6, "keyword") for row in con.execute(sql, args)]


def search(
    con: sqlite3.Connection,
    embedder: Embedder,
    *,
    query: str,
    corpus: Iterable[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    if not query.strip():
        return []
    seen: dict[str, dict] = {}
    for hit in _semantic(con, embedder, query, corpus, limit):
        seen[hit["chunk_id"]] = hit
    for hit in _keyword(con, query, corpus, limit):
        prev = seen.get(hit["chunk_id"])
        if prev is None:
            seen[hit["chunk_id"]] = hit
        else:
            prev["score"] = min(1.0, prev["score"] + 0.2)
            prev["match_source"] = "both"
    results = sorted(seen.values(), key=lambda r: r["score"], reverse=True)
    return results[:limit]
