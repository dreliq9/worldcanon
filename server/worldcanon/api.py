"""FastAPI app. `build_app(...)` wires dependencies; `main.py` runs uvicorn.

Tests instantiate the app directly via build_app so they don't need to
spin up a real HTTP server.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException

from pydantic import BaseModel, Field

from .capture import write_brainstorm_note

from .embedder import Embedder
from .ideation import (
    SessionNotFoundError,
    append_turn,
    end_session,
    get_session,
    start_session,
)
from .ledger import list_facts, list_names, list_relationships, list_rules
from .llm import LLMBackend, LLMUnavailableError
from .prompts import (
    render_ask_world,
    render_contradiction_check,
    render_ideation_question,
    render_ideation_response,
    render_fact_extraction,
    render_name_suggest,
    render_triage_suggest,
)
from .registry import CorpusConfig
from .search import search


_WIKILINK = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    corpus: list[str] | None = None
    limit: int = 5


class ContradictionRequest(BaseModel):
    text: str = Field(..., min_length=1)
    entities: list[str] | None = None
    scope: str | None = None


class IdeationStartRequest(BaseModel):
    entity: str = Field(..., min_length=1)


class IdeationRespondRequest(BaseModel):
    answer: str = Field(..., min_length=1)


class ProposeFactsRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)


class CaptureRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = "webhook"
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class NameSuggestRequest(BaseModel):
    culture: str = Field(..., min_length=1)
    role: str | None = None
    vibe: str | None = None
    count: int = 5


class TriageSuggestRequest(BaseModel):
    path: str = Field(..., min_length=1)


def build_app(
    *,
    con: sqlite3.Connection,
    embedder: Embedder,
    cfgs: list[CorpusConfig],
    llm: LLMBackend,
    vault_root: Path,
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
        llm_model = os.environ.get("WORLDCANON_LLM_MODEL", "gemma3:4b")
        return {
            "corpora": corpora_stats,
            "fact_count": fact_count,
            "relationship_count": rel_count,
            "rule_count": rule_count,
            "name_count": name_count,
            "embedder": embedder.name,
            "llm_model": llm_model,
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

    @app.post("/ask")
    def ask_endpoint(req: AskRequest) -> dict[str, Any]:
        if not req.question.strip():
            raise HTTPException(status_code=422, detail="question must not be empty")
        hits = search(con, embedder, query=req.question, corpus=req.corpus, limit=req.limit)
        prompt = render_ask_world(question=req.question, chunks=hits)
        try:
            content = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=None,
            )
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "llm_unavailable", "reason": str(exc)},
            ) from exc
        citations = sorted({h["source_path"] for h in hits})
        return {"answer": content, "citations": citations, "hits": hits}

    @app.post("/contradiction-check")
    def contradiction_check(req: ContradictionRequest) -> dict[str, Any]:
        if req.entities is not None:
            entity_names = list(dict.fromkeys(req.entities))
        else:
            entity_names = sorted({m.group(1).strip() for m in _WIKILINK.finditer(req.text)})

        findings: list[dict] = []
        for entity in entity_names:
            facts = list_facts(con, entity=entity)
            canonish = [f for f in facts if f["status"] in {"canon", "draft"}]
            if not canonish:
                continue
            prompt = render_contradiction_check(
                entity=entity,
                facts=canonish,
                text=req.text,
            )
            try:
                content = llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    model=None,
                    response_format="json",
                )
            except LLMUnavailableError as exc:
                raise HTTPException(
                    status_code=503,
                    detail={"status": "llm_unavailable", "reason": str(exc)},
                ) from exc
            for item in _parse_contradictions(content):
                findings.append({"entity": entity, **item})
        return {"findings": findings}

    @app.post("/ideation/start")
    def ideation_start(req: IdeationStartRequest) -> dict[str, Any]:
        sheet_row = con.execute(
            """SELECT * FROM chunks
               WHERE corpus = 'entities'
                 AND json_extract(metadata_json, '$.kind') = 'entity_sheet'
                 AND json_extract(metadata_json, '$.name') = ?
               LIMIT 1""",
            (req.entity,),
        ).fetchone()
        if sheet_row is None:
            raise HTTPException(status_code=404, detail=f"entity not found: {req.entity}")
        sheet_meta = json.loads(sheet_row["metadata_json"])
        entity_type = str(sheet_meta.get("type", "character"))

        existing_facts = list_facts(con, entity=req.entity)
        facts_block = (
            "\n".join(f"- {f['claim']} (status: {f['status']})" for f in existing_facts)
            if existing_facts
            else "(no facts on file yet)"
        )
        entity_state = f"{sheet_row['body']}\n\nKnown facts:\n{facts_block}"

        relevant_hits = search(con, embedder, query=req.entity, corpus=["canon", "drafts"], limit=5)
        if relevant_hits:
            relevant_canon = "\n\n".join(
                f"[{h['source_path']}] {h['body']}" for h in relevant_hits
            )
        else:
            relevant_canon = "(none)"

        sid = start_session(con, entity=req.entity, entity_type=entity_type)
        prompt = render_ideation_question(
            entity_type=entity_type,
            entity_name=req.entity,
            entity_state=entity_state,
            relevant_canon=relevant_canon,
            addressed_gaps=[],
        )
        try:
            question = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=None,
            )
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "llm_unavailable", "reason": str(exc)},
            ) from exc

        question = question.strip()
        append_turn(con, sid, role="ai", content=question)
        return {"session_id": sid, "first_question": question}

    @app.post("/ideation/{session_id}/respond")
    def ideation_respond(session_id: str, req: IdeationRespondRequest) -> dict[str, Any]:
        try:
            state = get_session(con, session_id)
        except SessionNotFoundError:
            raise HTTPException(status_code=404, detail=f"session not found: {session_id}")

        # Record the writer's turn
        append_turn(con, session_id, role="writer", content=req.answer)

        # Re-fetch state to include the writer turn we just appended
        state = get_session(con, session_id)
        transcript_text = _format_transcript(state["transcript"])

        prompt = render_ideation_response(
            entity_type=state["entity_type"],
            entity_name=state["entity"],
            transcript=transcript_text,
            answer=req.answer,
            addressed_gaps=state["addressed_gaps"],
        )
        try:
            content = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=None,
                response_format="json",
            )
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "llm_unavailable", "reason": str(exc)},
            ) from exc

        parsed = _parse_ideation_response(content)
        next_q = parsed.get("next_question")
        addressed = parsed.get("addressed_gap")
        if next_q:
            append_turn(con, session_id, role="ai", content=next_q,
                        addressed_gap=addressed if isinstance(addressed, str) else None)
        elif addressed and isinstance(addressed, str):
            append_turn(con, session_id, role="ai", content="(no further questions)",
                        addressed_gap=addressed)
        return {
            "proposed_facts": parsed.get("facts", []),
            "next_question": next_q,
        }

    @app.post("/propose-facts")
    def propose_facts(req: ProposeFactsRequest) -> dict[str, Any]:
        prompt = render_fact_extraction(text=req.text, source=req.source)
        try:
            content = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=None,
                response_format="json",
            )
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "llm_unavailable", "reason": str(exc)},
            ) from exc
        return {"proposed_facts": _parse_proposed_facts(content)}

    @app.post("/capture")
    def capture_endpoint(req: CaptureRequest) -> dict[str, Any]:
        if not req.text.strip():
            raise HTTPException(status_code=422, detail="text must not be empty")
        now_iso = datetime.datetime.now().isoformat(timespec="seconds")
        return write_brainstorm_note(
            vault_root=vault_root,
            text=req.text,
            source=req.source,
            entities=req.entities,
            topics=req.topics,
            now_iso=now_iso,
        )

    @app.get("/unprocessed-brainstorm")
    def unprocessed_brainstorm() -> dict[str, Any]:
        rows = con.execute(
            """SELECT chunk_id, source_path, body, metadata_json, mtime
               FROM chunks
               WHERE corpus = 'brainstorm'
                 AND json_extract(metadata_json, '$.status') = 'unprocessed'
               ORDER BY mtime DESC""",
        ).fetchall()
        seen: dict[str, dict] = {}
        for row in rows:
            sp = row["source_path"]
            if sp in seen:
                continue
            meta = json.loads(row["metadata_json"])
            preview = (row["body"] or "").strip().replace("\n", " ")
            seen[sp] = {
                "source_path": sp,
                "preview": preview[:140],
                "date": meta.get("date"),
                "mtime": row["mtime"],
            }
        return {"notes": list(seen.values())}

    @app.get("/name/cultures")
    def name_cultures() -> dict[str, Any]:
        rows = con.execute(
            """SELECT culture, status, COUNT(*) AS n
               FROM names
               GROUP BY culture, status""",
        ).fetchall()
        by_culture: dict[str, dict] = {}
        for r in rows:
            entry = by_culture.setdefault(
                r["culture"], {"culture": r["culture"], "used_count": 0, "candidate_count": 0},
            )
            if r["status"] == "used":
                entry["used_count"] = r["n"]
            elif r["status"] == "candidate":
                entry["candidate_count"] = r["n"]
        return {"cultures": sorted(by_culture.values(), key=lambda c: c["culture"])}

    @app.post("/name/suggest")
    def name_suggest(req: NameSuggestRequest) -> dict[str, Any]:
        sheet_row = con.execute(
            """SELECT * FROM chunks
               WHERE corpus = 'naming'
                 AND json_extract(metadata_json, '$.kind') = 'naming_sheet'
                 AND json_extract(metadata_json, '$.culture') = ?
               LIMIT 1""",
            (req.culture,),
        ).fetchone()
        if sheet_row is None:
            raise HTTPException(status_code=404, detail=f"culture not found: {req.culture}")
        meta = json.loads(sheet_row["metadata_json"])
        conventions_raw = meta.get("conventions", {})
        conventions: list[str] = []
        if isinstance(conventions_raw, dict):
            for k, v in conventions_raw.items():
                if isinstance(v, list):
                    conventions.extend(str(x) for x in v)
                else:
                    conventions.append(f"{k}: {v}")
        elif isinstance(conventions_raw, list):
            conventions = [str(c) for c in conventions_raw]

        existing = list_names(con, culture=req.culture)
        used_names = [n["name"] for n in existing if n["status"] == "used"]
        candidate_names = [n["name"] for n in existing if n["status"] == "candidate"]

        prompt = render_name_suggest(
            culture=req.culture,
            conventions=conventions,
            used_names=used_names,
            candidate_names=candidate_names,
            role=req.role,
            vibe=req.vibe,
            count=req.count,
        )
        try:
            content = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=None,
                response_format="json",
            )
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "llm_unavailable", "reason": str(exc)},
            ) from exc
        return {"suggestions": _parse_name_suggestions(content)}

    @app.get("/inbox")
    def inbox_endpoint() -> dict[str, Any]:
        inbox_dir = vault_root / "_inbox"
        if not inbox_dir.exists():
            return {"items": []}
        items: list[dict[str, Any]] = []
        for path in sorted(inbox_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(inbox_dir).as_posix()
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            preview = body.strip().replace("\n", " ")[:200]
            items.append({
                "path": rel,
                "vault_path": f"_inbox/{rel}",
                "preview": preview,
                "size": path.stat().st_size,
            })
        return {"items": items}

    @app.post("/triage-suggest")
    def triage_suggest(req: TriageSuggestRequest) -> dict[str, Any]:
        inbox_dir = (vault_root / "_inbox").resolve()
        target = (inbox_dir / req.path).resolve()
        try:
            target.relative_to(inbox_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="path must be inside _inbox/")
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"file not found: {req.path}")

        body = target.read_text(encoding="utf-8", errors="replace")
        prompt = render_triage_suggest(filename=req.path, content=body)
        try:
            content = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=None,
                response_format="json",
            )
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "llm_unavailable", "reason": str(exc)},
            ) from exc

        return _parse_triage_suggestion(content)

    @app.get("/unlinked-mentions")
    def unlinked_mentions(file: str) -> dict[str, Any]:
        target = (vault_root / file).resolve()
        try:
            target.relative_to(vault_root.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="file must be inside the vault")
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"file not found: {file}")

        body = target.read_text(encoding="utf-8", errors="replace")

        names: set[str] = set()
        for row in con.execute(
            """SELECT metadata_json FROM chunks
               WHERE corpus = 'entities'
                 AND json_extract(metadata_json, '$.kind') = 'entity_sheet'""",
        ):
            meta = json.loads(row["metadata_json"])
            n = meta.get("name")
            if isinstance(n, str):
                names.add(n)
            for alias in meta.get("aliases") or []:
                if isinstance(alias, str):
                    names.add(alias)
        if not names:
            return {"mentions": []}

        wikilink_re = re.compile(r"\[\[[^\]]+\]\]")
        wikilink_spans: list[tuple[int, int]] = [
            (m.start(), m.end()) for m in wikilink_re.finditer(body)
        ]

        def is_inside_wikilink(start: int, end: int) -> bool:
            for ws, we in wikilink_spans:
                if start >= ws and end <= we:
                    return True
            return False

        sorted_names = sorted(names, key=len, reverse=True)
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in sorted_names) + r")\b"
        )

        line_starts: list[int] = [0]
        for i, ch in enumerate(body):
            if ch == "\n":
                line_starts.append(i + 1)

        def position(offset: int) -> tuple[int, int]:
            line = 0
            for i, start in enumerate(line_starts):
                if start <= offset:
                    line = i
                else:
                    break
            col = offset - line_starts[line]
            return line + 1, col

        mentions: list[dict] = []
        for m in pattern.finditer(body):
            if is_inside_wikilink(m.start(), m.end()):
                continue
            line, col = position(m.start())
            mentions.append({
                "line": line,
                "col": col,
                "match": m.group(1),
                "suggested_link": f"[[{m.group(1)}]]",
            })

        return {"mentions": mentions}

    return app


def _parse_contradictions(content: str) -> list[dict]:
    """Lenient JSON parse — strip code fences, locate the first {...} object."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    items = data.get("contradictions") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append({
            "new_claim": str(item.get("new_claim", "")),
            "conflicting_canon": str(item.get("conflicting_canon", "")),
            "reasoning": str(item.get("reasoning", "")),
        })
    return out


def _format_transcript(turns: list[dict]) -> str:
    lines: list[str] = []
    for t in turns:
        role = "AI" if t.get("role") == "ai" else "Writer"
        lines.append(f"{role}: {t.get('content', '')}")
    return "\n\n".join(lines)


def _parse_ideation_response(content: str) -> dict:
    """Lenient parse of the JSON returned by the ideation response prompt."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {"facts": [], "next_question": None, "addressed_gap": None}
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {"facts": [], "next_question": None, "addressed_gap": None}
    if not isinstance(data, dict):
        return {"facts": [], "next_question": None, "addressed_gap": None}
    facts_raw = data.get("facts")
    facts: list[dict] = []
    if isinstance(facts_raw, list):
        for f in facts_raw:
            if not isinstance(f, dict):
                continue
            claim = f.get("claim")
            if not isinstance(claim, str) or not claim.strip():
                continue
            facts.append({
                "claim": claim.strip(),
                "confidence": str(f.get("confidence", "medium")),
            })
    next_q = data.get("next_question")
    if isinstance(next_q, str):
        next_q = next_q.strip() or None
    else:
        next_q = None
    addressed = data.get("addressed_gap")
    if not isinstance(addressed, str):
        addressed = None
    return {"facts": facts, "next_question": next_q, "addressed_gap": addressed}


def _parse_proposed_facts(content: str) -> list[dict]:
    """Lenient parse for /propose-facts response."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    raw = data.get("proposed_facts")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for f in raw:
        if not isinstance(f, dict):
            continue
        entity = f.get("entity")
        claim = f.get("claim")
        if not isinstance(entity, str) or not isinstance(claim, str):
            continue
        out.append({
            "entity": entity.strip(),
            "claim": claim.strip(),
            "confidence": str(f.get("confidence", "medium")),
        })
    return out


def _parse_name_suggestions(content: str) -> list[dict]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    raw = data.get("suggestions")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        name = s.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        out.append({
            "name": name.strip(),
            "reasoning": str(s.get("reasoning", "")),
        })
    return out


_VALID_CLASSIFICATIONS = {
    "canon", "drafts", "research", "discard",
    "entities/characters", "entities/places", "entities/factions",
    "entities/items", "entities/events",
}


def _parse_triage_suggestion(content: str) -> dict:
    """Lenient parse with fallback to drafts/low when the LLM goes off-script."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    fallback = {"classification": "drafts", "confidence": "low",
                "reasoning": "could not parse LLM response"}
    if start == -1 or end == -1 or end < start:
        return fallback
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    cls = data.get("classification")
    if not isinstance(cls, str) or cls not in _VALID_CLASSIFICATIONS:
        return fallback
    conf = data.get("confidence")
    if conf not in {"high", "medium", "low"}:
        conf = "low"
    reasoning = data.get("reasoning")
    if not isinstance(reasoning, str):
        reasoning = ""
    return {"classification": cls, "confidence": conf, "reasoning": reasoning.strip()}
