"""SQLite + sqlite-vec store for chunks. Fact-ledger tables live in ledger.py.

Schema:
- chunks: text + metadata, keyed by chunk_id
- chunks_vec (sqlite-vec virtual): vector embeddings, keyed by rowid

Concurrency model: `Store` hands out one sqlite3.Connection per OS thread via
`threading.local()`. Callers that need to run SQL grab one via
`store.connection()` at the point of use — never store it across thread
boundaries. sqlite itself serializes writes at the file level, so concurrent
writers from different threads are safe.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np
import sqlite_vec


@dataclass
class Chunk:
    chunk_id: str
    corpus: str
    source_path: str
    source_abs_path: str
    title: str | None
    body: str
    metadata: dict[str, Any]
    mtime: int


@dataclass
class ChunkRow:
    chunk_id: str
    corpus: str
    source_path: str
    source_abs_path: str
    title: str | None
    body: str
    metadata: dict[str, Any]
    mtime: int
    body_hash: str
    indexed_at: int


class Store:
    """Thread-local sqlite3 connection factory."""

    def __init__(self, path: str | Path, dim: int):
        self._path = str(path)
        self._dim = dim
        self._local = threading.local()
        # Touch one connection to install schema on disk.
        _install_schema(self.connection(), dim)

    def connection(self) -> sqlite3.Connection:
        existing = getattr(self._local, "con", None)
        if existing is not None:
            return existing
        con = sqlite3.connect(self._path)
        con.row_factory = sqlite3.Row
        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        con.execute("PRAGMA foreign_keys = ON")
        self._local.con = con
        return con

    def close(self) -> None:
        existing = getattr(self._local, "con", None)
        if existing is not None:
            existing.close()
            self._local.con = None


def open_store(path: str | Path, dim: int) -> Store:
    return Store(path, dim)


def _install_schema(con: sqlite3.Connection, dim: int) -> None:
    con.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id        TEXT PRIMARY KEY,
            corpus          TEXT NOT NULL,
            source_path     TEXT NOT NULL,
            source_abs_path TEXT NOT NULL,
            title           TEXT,
            body            TEXT NOT NULL,
            metadata_json   TEXT NOT NULL,
            mtime           INTEGER NOT NULL,
            body_hash       TEXT NOT NULL,
            indexed_at      INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_corpus ON chunks(corpus);
        CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(corpus, source_path);

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
            embedding float[{dim}]
        );

        CREATE TABLE IF NOT EXISTS chunk_vec_map (
            chunk_id TEXT PRIMARY KEY,
            vec_rowid INTEGER NOT NULL UNIQUE
        );
        """
    )
    con.commit()


def row_to_chunk_row(row: sqlite3.Row) -> ChunkRow:
    return ChunkRow(
        chunk_id=row["chunk_id"],
        corpus=row["corpus"],
        source_path=row["source_path"],
        source_abs_path=row["source_abs_path"],
        title=row["title"],
        body=row["body"],
        metadata=json.loads(row["metadata_json"]),
        mtime=row["mtime"],
        body_hash=row["body_hash"],
        indexed_at=row["indexed_at"],
    )


def upsert_chunk(con: sqlite3.Connection, chunk: Chunk, embedding: np.ndarray) -> None:
    body_hash = hashlib.sha256(chunk.body.encode("utf-8")).hexdigest()
    now = int(time.time())
    con.execute(
        """
        INSERT INTO chunks (
            chunk_id, corpus, source_path, source_abs_path, title, body,
            metadata_json, mtime, body_hash, indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chunk_id) DO UPDATE SET
            corpus=excluded.corpus,
            source_path=excluded.source_path,
            source_abs_path=excluded.source_abs_path,
            title=excluded.title,
            body=excluded.body,
            metadata_json=excluded.metadata_json,
            mtime=excluded.mtime,
            body_hash=excluded.body_hash,
            indexed_at=excluded.indexed_at
        """,
        (
            chunk.chunk_id,
            chunk.corpus,
            chunk.source_path,
            chunk.source_abs_path,
            chunk.title,
            chunk.body,
            json.dumps(chunk.metadata),
            chunk.mtime,
            body_hash,
            now,
        ),
    )
    row = con.execute(
        "SELECT vec_rowid FROM chunk_vec_map WHERE chunk_id = ?", (chunk.chunk_id,)
    ).fetchone()
    vec_blob = embedding.astype(np.float32).tobytes()
    if row is None:
        cur = con.execute("INSERT INTO chunks_vec (embedding) VALUES (?)", (vec_blob,))
        con.execute(
            "INSERT INTO chunk_vec_map (chunk_id, vec_rowid) VALUES (?, ?)",
            (chunk.chunk_id, cur.lastrowid),
        )
    else:
        con.execute(
            "UPDATE chunks_vec SET embedding = ? WHERE rowid = ?",
            (vec_blob, row["vec_rowid"]),
        )
    con.commit()


def get_chunk(con: sqlite3.Connection, chunk_id: str) -> ChunkRow | None:
    row = con.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
    return row_to_chunk_row(row) if row else None


def delete_chunks_for_path(con: sqlite3.Connection, corpus: str, source_path: str) -> int:
    rows = con.execute(
        "SELECT chunk_id FROM chunks WHERE corpus = ? AND source_path = ?",
        (corpus, source_path),
    ).fetchall()
    if not rows:
        return 0
    ids = [r["chunk_id"] for r in rows]
    placeholders = ",".join("?" for _ in ids)
    vec_rows = con.execute(
        f"SELECT vec_rowid FROM chunk_vec_map WHERE chunk_id IN ({placeholders})",
        ids,
    ).fetchall()
    for vr in vec_rows:
        con.execute("DELETE FROM chunks_vec WHERE rowid = ?", (vr["vec_rowid"],))
    con.execute(f"DELETE FROM chunk_vec_map WHERE chunk_id IN ({placeholders})", ids)
    con.execute(f"DELETE FROM chunks WHERE chunk_id IN ({placeholders})", ids)
    con.commit()
    return len(ids)


def all_chunks_for_corpus(con: sqlite3.Connection, corpus: str) -> Iterator[ChunkRow]:
    for row in con.execute("SELECT * FROM chunks WHERE corpus = ?", (corpus,)):
        yield row_to_chunk_row(row)
