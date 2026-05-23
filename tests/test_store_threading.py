"""Each thread gets its own sqlite3 connection from the Store factory.

Regression test for the QA-hard finding "Shared SQLite connection used
concurrently across watcher thread and FastAPI thread pool" — the fix is
that Store hands out thread-local connections instead of sharing one.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from worldcanon.store import Chunk, Store, open_store, upsert_chunk


def _make_chunk(i: int) -> Chunk:
    return Chunk(
        chunk_id=f"c{i}",
        corpus="canon",
        source_path=f"f{i}.md",
        source_abs_path=f"/tmp/f{i}.md",
        title=f"t{i}",
        body=f"body {i}",
        metadata={},
        mtime=i,
    )


def test_store_returns_distinct_connection_per_thread(tmp_path):
    store = open_store(tmp_path / "t.sqlite", dim=4)
    seen: dict[int, object] = {}
    barrier = threading.Barrier(4)

    def worker():
        barrier.wait()
        con = store.connection()
        seen[threading.get_ident()] = con

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(seen) == 4
    assert len(set(id(c) for c in seen.values())) == 4


def test_store_same_thread_returns_same_connection(tmp_path):
    store = open_store(tmp_path / "t.sqlite", dim=4)
    a = store.connection()
    b = store.connection()
    assert a is b


def test_concurrent_writes_from_many_threads(tmp_path):
    """Hammer the store from multiple threads — none should hit
    'database is locked' or 'Recursive use of cursor not allowed'."""
    store = open_store(tmp_path / "t.sqlite", dim=4)
    embedding = np.zeros(4, dtype=np.float32)

    def worker(i: int) -> None:
        con = store.connection()
        upsert_chunk(con, _make_chunk(i), embedding)

    errors: list[BaseException] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker, i) for i in range(40)]
        for f in futures:
            try:
                f.result()
            except BaseException as exc:
                errors.append(exc)

    assert not errors, errors
    # All 40 rows committed.
    con = store.connection()
    n = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    assert n == 40
