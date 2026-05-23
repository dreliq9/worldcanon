"""watchdog wrapper that re-indexes files on save.

Routes each path change to the corpus whose configured paths contain it,
or ignores it if the file isn't in any corpus. Debouncing handles the
multi-event-per-save behavior of some platforms.
"""
from __future__ import annotations

import fnmatch
import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .embedder import Embedder
from .indexer import index_file, remove_file
from .registry import CorpusConfig
from .store import Store

logger = logging.getLogger("worldcanon.watcher")

DEBOUNCE_SECONDS = 0.5


class _Handler(FileSystemEventHandler):
    def __init__(self, owner: "VaultWatcher"):
        self._owner = owner

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if event.event_type == "deleted":
            self._owner._schedule(path, deleted=True)
        elif event.event_type in {"created", "modified", "moved"}:
            target = Path(getattr(event, "dest_path", event.src_path) or event.src_path)
            self._owner._schedule(target, deleted=False)


class VaultWatcher:
    def __init__(
        self,
        *,
        store: Store,
        embedder: Embedder,
        cfgs: list[CorpusConfig],
        vault_root: Path,
    ):
        self._store = store
        self._embedder = embedder
        self._cfgs = cfgs
        self._vault_root = vault_root.resolve()
        self._observer: Observer | None = None
        self._lock = threading.Lock()
        self._pending: dict[Path, threading.Timer] = {}

    def _match_corpus(self, file: Path) -> CorpusConfig | None:
        try:
            file_abs = file.resolve()
        except OSError:
            return None
        for cfg in self._cfgs:
            for root in cfg.paths:
                try:
                    rel = file_abs.relative_to(root.resolve()).as_posix()
                except ValueError:
                    continue
                patterns = [cfg.glob or "**/*.md", *cfg.globs]
                if not any(fnmatch.fnmatch(rel, p) or file.match(p) for p in patterns):
                    continue
                if any(fnmatch.fnmatch(rel, pat) for pat in cfg.exclude):
                    continue
                return cfg
        return None

    def _schedule(self, file: Path, *, deleted: bool) -> None:
        with self._lock:
            existing = self._pending.pop(file, None)
            if existing:
                existing.cancel()
            timer = threading.Timer(
                DEBOUNCE_SECONDS, self._apply, args=(file, deleted)
            )
            timer.daemon = True
            self._pending[file] = timer
            timer.start()

    def _apply(self, file: Path, deleted: bool) -> None:
        with self._lock:
            self._pending.pop(file, None)
        cfg = self._match_corpus(file)
        if cfg is None:
            return
        # store.connection() returns this thread's connection — the watcher
        # daemon thread gets its own, distinct from any FastAPI worker.
        con = self._store.connection()
        try:
            if deleted:
                remove_file(con, cfg, file)
            else:
                index_file(con, cfg, file, self._embedder)
        except Exception as exc:
            logger.exception("watcher: failed to apply %s: %s", file, exc)

    def start(self) -> None:
        if self._observer is not None:
            return
        self._observer = Observer()
        self._observer.schedule(_Handler(self), str(self._vault_root), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join()
        self._observer = None
        with self._lock:
            for timer in self._pending.values():
                timer.cancel()
            self._pending.clear()
