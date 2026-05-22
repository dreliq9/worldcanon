"""Walks corpus paths, calls chunkers, embeds, upserts chunks and ledger rows.

Entry points:
- full_index_corpus: walk every matching file
- index_file: re-index one specific file (used by the watcher)
- remove_file: drop all rows tied to a deleted file
"""
from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

from .chunkers import ChunkerOutput
from .embedder import Embedder
from .ledger import (
    clear_ledger_for_file,
    sync_facts_for_file,
    sync_names_for_file,
    sync_relationships_for_file,
    sync_rules_for_file,
)
from .registry import CorpusConfig
from .store import delete_chunks_for_path, upsert_chunk

logger = logging.getLogger("worldcanon.indexer")


def _iter_files(cfg: CorpusConfig) -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    patterns = [cfg.glob or "**/*.md", *cfg.globs]
    for root in cfg.paths:
        if not root.exists():
            logger.warning("corpus %s: path does not exist: %s", cfg.name, root)
            continue
        if root.is_file():
            key = str(root.resolve())
            if key in seen:
                continue
            seen.add(key)
            out.append((root.parent, root))
            continue
        for pattern in patterns:
            for f in root.glob(pattern):
                if not f.is_file():
                    continue
                rel = f.relative_to(root).as_posix()
                if any(fnmatch.fnmatch(rel, pat) for pat in cfg.exclude):
                    continue
                key = str(f.resolve())
                if key in seen:
                    continue
                seen.add(key)
                out.append((root, f))
    return out


def _file_root(cfg: CorpusConfig, file: Path) -> Path:
    for root in cfg.paths:
        try:
            file.relative_to(root)
            return root
        except ValueError:
            continue
    return cfg.paths[0]


def _apply_output(con, output: ChunkerOutput, corpus: str, rel: str, embedder: Embedder) -> int:
    delete_chunks_for_path(con, corpus=corpus, source_path=rel)
    texts = [c.body for c in output.chunks]
    vecs = embedder.embed(texts)
    for chunk, vec in zip(output.chunks, vecs):
        upsert_chunk(con, chunk, vec)

    facts_by_entity: dict[str, list] = {}
    for f in output.facts:
        facts_by_entity.setdefault(f.entity, []).append({
            "claim": f.claim, "status": f.status,
            "introduced_in": f.introduced_in, "chapter_index": f.chapter_index,
        })
    for entity, facts in facts_by_entity.items():
        sync_facts_for_file(con, entity=entity, source_file=rel, facts=facts)

    rels_by_entity: dict[str, list] = {}
    for r in output.relationships:
        rels_by_entity.setdefault(r.from_entity, []).append({
            "with": r.with_entity, "type": r.type,
            "status": r.status, "notes": r.notes,
        })
    for from_entity, rels in rels_by_entity.items():
        sync_relationships_for_file(con, from_entity=from_entity, source_file=rel,
                                    relationships=rels)

    rules_by_system: dict[str, list] = {}
    for ru in output.rules:
        rules_by_system.setdefault(ru.system, []).append({
            "rule": ru.rule, "status": ru.status,
        })
    for system, rules in rules_by_system.items():
        sync_rules_for_file(con, system=system, source_file=rel, rules=rules)

    names_by_culture: dict[str, list] = {}
    for n in output.names:
        names_by_culture.setdefault(n.culture, []).append({
            "name": n.name, "status": n.status, "used_by": n.used_by, "notes": n.notes,
        })
    for culture, names in names_by_culture.items():
        sync_names_for_file(con, culture=culture, source_file=rel, names=names)

    return len(output.chunks)


def full_index_corpus(con, cfg: CorpusConfig, embedder: Embedder) -> dict[str, int]:
    chunks_upserted = 0
    files_indexed = 0
    for root, file in _iter_files(cfg):
        rel = file.relative_to(root).as_posix()
        output = cfg.chunker_fn(corpus=cfg.name, source_root=root,
                                path=file, extras=cfg.extras)
        chunks_upserted += _apply_output(con, output, cfg.name, rel, embedder)
        files_indexed += 1
    return {"files_indexed": files_indexed, "chunks_upserted": chunks_upserted}


def index_file(con, cfg: CorpusConfig, file: Path, embedder: Embedder) -> int:
    root = _file_root(cfg, file)
    rel = file.relative_to(root).as_posix()
    output = cfg.chunker_fn(corpus=cfg.name, source_root=root,
                            path=file, extras=cfg.extras)
    return _apply_output(con, output, cfg.name, rel, embedder)


def remove_file(con, cfg: CorpusConfig, file: Path) -> int:
    root = _file_root(cfg, file)
    rel = file.relative_to(root).as_posix()
    deleted = delete_chunks_for_path(con, corpus=cfg.name, source_path=rel)
    clear_ledger_for_file(con, source_file=rel)
    return deleted
