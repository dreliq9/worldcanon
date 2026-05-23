"""Worldcanon sidecar entry point.

Loads config (env + corpora.yaml), opens the store, runs a one-shot
opportunistic index sweep, starts the file watcher, and serves the
FastAPI app on a local port.
"""
from __future__ import annotations

import argparse
import ipaddress
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn

from .api import build_app
from .embedder import build_embedder
from .ideation import install_ideation_schema
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


def _default_corpora_path() -> Path:
    # In a PyInstaller bundle, sys._MEIPASS points at the bundle's data
    # root (_internal/ in onedir mode). corpora.yaml is shipped there.
    # In a source checkout, walk up from this file to the repo root.
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "corpora.yaml"
    return Path(__file__).resolve().parents[2] / "corpora.yaml"


def _require_loopback(host: str) -> str:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError as exc:
        raise SystemExit(
            f"--host must be a loopback IP literal (127.0.0.1 or ::1), got {host!r}"
        ) from exc
    if not addr.is_loopback:
        raise SystemExit(
            f"--host must be a loopback address; {host} is reachable off-host"
        )
    return host


def main() -> None:
    parser = argparse.ArgumentParser(description="Worldbuilder Canon sidecar")
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault root")
    parser.add_argument("--corpora", default=str(_default_corpora_path()))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--db", default=str(_default_db_path()))
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    host = _require_loopback(args.host)

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
    store = open_store(db_path, dim=embedder.dim)
    install_ledger_schema(store.connection())
    install_ideation_schema(store.connection())
    cfgs = load_registry(args.corpora, vault_root=vault)

    log.info("opportunistic index sweep starting (vault=%s)", vault)
    for cfg in cfgs:
        stats = full_index_corpus(store.connection(), cfg, embedder)
        log.info("indexed corpus %s: %s", cfg.name, stats)

    watcher = VaultWatcher(store=store, embedder=embedder, cfgs=cfgs, vault_root=vault)
    watcher.start()
    log.info("watcher started")

    app = build_app(store=store, embedder=embedder, cfgs=cfgs, llm=llm, vault_root=vault)

    def _shutdown(*_):
        log.info("shutting down")
        watcher.stop()
        store.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    uvicorn.run(app, host=host, port=args.port, log_level=args.log_level)
