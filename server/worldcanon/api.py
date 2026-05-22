"""FastAPI app. `build_app(...)` wires dependencies; `main.py` runs uvicorn.

Tests instantiate the app directly via build_app so they don't need to
spin up a real HTTP server.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException

from .embedder import Embedder
from .ledger import list_facts, list_relationships, list_rules
from .registry import CorpusConfig
from .search import search


def build_app(
    *,
    con: sqlite3.Connection,
    embedder: Embedder,
    cfgs: list[CorpusConfig],
) -> FastAPI:
    app = FastAPI(title="worldcanon-sidecar")

    @app.get("/stats")
    def stats() -> dict[str, Any]:
        corpora_stats: list[dict] = []
        for cfg in cfgs:
            row = con.execute(
                "SELECT COUNT(*) AS n, MAX(indexed_at) AS last FROM chunks WHERE corpus = ?",
                (cfg.name,),
            ).fetchone()
            corpora_stats.append({
                "name": cfg.name,
                "chunk_count": row["n"],
                "last_indexed": row["last"],
                "chunker": cfg.chunker_name,
            })
        fact_count = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        rel_count = con.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        rule_count = con.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
        name_count = con.execute("SELECT COUNT(*) FROM names").fetchone()[0]
        return {
            "corpora": corpora_stats,
            "fact_count": fact_count,
            "relationship_count": rel_count,
            "rule_count": rule_count,
            "name_count": name_count,
            "embedder": embedder.name,
        }

    @app.get("/search")
    def search_endpoint(
        q: str,
        corpus: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        corpus_list = [c.strip() for c in corpus.split(",")] if corpus else None
        results = search(con, embedder, query=q, corpus=corpus_list, limit=limit)
        return {"results": results}

    @app.get("/entity/{name}")
    def entity_endpoint(name: str) -> dict[str, Any]:
        row = con.execute(
            """SELECT * FROM chunks
               WHERE corpus = 'entities'
                 AND json_extract(metadata_json, '$.kind') = 'entity_sheet'
                 AND json_extract(metadata_json, '$.name') = ?
               LIMIT 1""",
            (name,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"entity not found: {name}")
        facts = list_facts(con, entity=name)
        rels = list_relationships(con, entity=name)
        mentions = []
        like = f"%[[{name}]]%"
        for r in con.execute(
            """SELECT chunk_id, corpus, source_path, body, mtime
               FROM chunks
               WHERE corpus IN ('canon', 'drafts')
                 AND body LIKE ?""",
            (like,),
        ):
            mentions.append(dict(r))
        return {
            "name": name,
            "sheet": {
                "source_path": row["source_path"],
                "title": row["title"],
                "body": row["body"],
                "metadata": json.loads(row["metadata_json"]),
            },
            "facts": facts,
            "relationships": rels,
            "mentions": mentions,
        }

    @app.get("/facts")
    def facts_endpoint(
        entity: str | None = None,
        status: str | None = None,
        chapter_max: int | None = None,
    ) -> dict[str, Any]:
        return {
            "facts": list_facts(
                con, entity=entity, status=status, chapter_max=chapter_max,
            )
        }

    @app.get("/relationships")
    def relationships_endpoint(entity: str | None = None) -> dict[str, Any]:
        return {"relationships": list_relationships(con, entity=entity)}

    @app.get("/system/{name}")
    def system_endpoint(name: str) -> dict[str, Any]:
        row = con.execute(
            """SELECT * FROM chunks
               WHERE corpus = 'systems'
                 AND json_extract(metadata_json, '$.kind') = 'system_sheet'
                 AND json_extract(metadata_json, '$.name') = ?
               LIMIT 1""",
            (name,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"system not found: {name}")
        return {
            "name": name,
            "sheet": {
                "source_path": row["source_path"],
                "body": row["body"],
                "metadata": json.loads(row["metadata_json"]),
            },
            "rules": list_rules(con, system=name),
        }

    @app.get("/timeline")
    def timeline_endpoint(range: str | None = None) -> dict[str, Any]:
        events: list[dict] = []
        for row in con.execute(
            "SELECT * FROM facts WHERE chapter_index IS NOT NULL ORDER BY chapter_index"
        ):
            events.append({
                "kind": "fact",
                "entity": row["entity"],
                "claim": row["claim"],
                "chapter_index": row["chapter_index"],
                "source_file": row["source_file"],
            })
        for row in con.execute(
            """SELECT * FROM chunks
               WHERE corpus = 'entities'
                 AND json_extract(metadata_json, '$.type') = 'event'
                 AND json_extract(metadata_json, '$.date') IS NOT NULL"""
        ):
            meta = json.loads(row["metadata_json"])
            events.append({
                "kind": "event",
                "name": meta.get("name"),
                "date": meta.get("date"),
                "source_file": row["source_path"],
            })
        return {"events": events}

    return app
