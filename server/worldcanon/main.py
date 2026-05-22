"""Worldcanon sidecar entry point.

Loads config (env + corpora.yaml), opens the store, runs a one-shot
opportunistic index sweep, starts the file watcher, and serves the
FastAPI app on a local port.
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn

from .api import build_app
from .embedder import build_embedder
from .indexer import full_index_corpus
from .ledger import install_ledger_schema
from .llm import build_llm_backend
from .registry import load_registry
from .store import open_store
from .watcher import VaultWatcher


def _default_db_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        return base / "WorldbuilderCanon" / "index.sqlite"
    return Path.home() / ".worldcanon" / "index.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(description="Worldbuilder Canon sidecar")
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault root")
    parser.add_argument("--corpora", default=str(Path(__file__).resolve().parents[2] / "corpora.yaml"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--db", default=str(_default_db_path()))
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("worldcanon.main")

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        raise SystemExit(f"vault not found: {vault}")

    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    embedder = build_embedder()
    llm = build_llm_backend()
    con = open_store(db_path, dim=embedder.dim, check_same_thread=False)
    install_ledger_schema(con)
    cfgs = load_registry(args.corpora, vault_root=vault)

    log.info("opportunistic index sweep starting (vault=%s)", vault)
    for cfg in cfgs:
        stats = full_index_corpus(con, cfg, embedder)
        log.info("indexed corpus %s: %s", cfg.name, stats)

    watcher = VaultWatcher(con=con, embedder=embedder, cfgs=cfgs, vault_root=vault)
    watcher.start()
    log.info("watcher started")

    app = build_app(con=con, embedder=embedder, cfgs=cfgs, llm=llm)

    def _shutdown(*_):
        log.info("shutting down")
        watcher.stop()
        con.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
