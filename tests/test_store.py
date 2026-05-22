import sqlite3
from pathlib import Path

import numpy as np
import pytest

from worldcanon.store import Chunk, ChunkRow, open_store, upsert_chunk, get_chunk, delete_chunks_for_path, all_chunks_for_corpus


@pytest.fixture
def tmp_store(tmp_path):
    con = open_store(tmp_path / "t.sqlite", dim=4)
    yield con
    con.close()


def test_open_store_creates_schema(tmp_store):
    cur = tmp_store.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'")
    assert cur.fetchone() is not None


def test_upsert_and_get_chunk(tmp_store):
    chunk = Chunk(
        chunk_id="entities:characters/Aerin.md:0",
        corpus="entities",
        source_path="characters/Aerin.md",
        source_abs_path="/abs/characters/Aerin.md",
        title="Aerin",
        body="green eyes",
        metadata={"type": "character"},
        mtime=1234567890,
    )
    vec = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    upsert_chunk(tmp_store, chunk, vec)
    row = get_chunk(tmp_store, "entities:characters/Aerin.md:0")
    assert row is not None
    assert row.body == "green eyes"
    assert row.metadata == {"type": "character"}


def test_upsert_replaces_existing(tmp_store):
    chunk = Chunk(
        chunk_id="x:y:0",
        corpus="x",
        source_path="y",
        source_abs_path="/y",
        title="t",
        body="old",
        metadata={},
        mtime=1,
    )
    vec = np.array([1.0, 0, 0, 0], dtype=np.float32)
    upsert_chunk(tmp_store, chunk, vec)
    chunk.body = "new"
    chunk.mtime = 2
    upsert_chunk(tmp_store, chunk, vec)
    row = get_chunk(tmp_store, "x:y:0")
    assert row.body == "new"
    assert row.mtime == 2


def test_delete_chunks_for_path(tmp_store):
    for i in range(3):
        chunk = Chunk(
            chunk_id=f"c:p:{i}",
            corpus="c",
            source_path="p",
            source_abs_path="/p",
            title=None,
            body=f"b{i}",
            metadata={},
            mtime=1,
        )
        upsert_chunk(tmp_store, chunk, np.array([0, 0, 0, 1.0], dtype=np.float32))
    deleted = delete_chunks_for_path(tmp_store, corpus="c", source_path="p")
    assert deleted == 3
    assert get_chunk(tmp_store, "c:p:0") is None


def test_all_chunks_for_corpus(tmp_store):
    for i in range(2):
        chunk = Chunk(
            chunk_id=f"c:p:{i}",
            corpus="c",
            source_path="p",
            source_abs_path="/p",
            title=None,
            body=f"b{i}",
            metadata={},
            mtime=1,
        )
        upsert_chunk(tmp_store, chunk, np.array([0, 0, 0, 1.0], dtype=np.float32))
    rows = list(all_chunks_for_corpus(tmp_store, "c"))
    assert len(rows) == 2
