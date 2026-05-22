"""Ideation session storage. One session per `Canon: Develop this entity` run.

A session keeps:
- entity + entity_type (so prompts know the gap-priority list)
- transcript (list of turns: {role, content, at})
- addressed_gaps (set of gap categories the writer has already covered)
- started_at, ended_at
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import time


class SessionNotFoundError(Exception):
    pass


def install_ideation_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS ideation_sessions (
            id            TEXT PRIMARY KEY,
            entity        TEXT NOT NULL,
            entity_type   TEXT NOT NULL,
            transcript_json TEXT NOT NULL,
            addressed_gaps_json TEXT NOT NULL,
            started_at    INTEGER NOT NULL,
            ended_at      INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_ideation_entity ON ideation_sessions(entity);
        """
    )
    con.commit()


def _now() -> int:
    return int(time.time())


def start_session(con: sqlite3.Connection, *, entity: str, entity_type: str) -> str:
    sid = secrets.token_urlsafe(9)
    con.execute(
        """INSERT INTO ideation_sessions
           (id, entity, entity_type, transcript_json, addressed_gaps_json, started_at, ended_at)
           VALUES (?, ?, ?, ?, ?, ?, NULL)""",
        (sid, entity, entity_type, "[]", "[]", _now()),
    )
    con.commit()
    return sid


def get_session(con: sqlite3.Connection, session_id: str) -> dict:
    row = con.execute(
        "SELECT * FROM ideation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if row is None:
        raise SessionNotFoundError(session_id)
    return {
        "id": row["id"],
        "entity": row["entity"],
        "entity_type": row["entity_type"],
        "transcript": json.loads(row["transcript_json"]),
        "addressed_gaps": json.loads(row["addressed_gaps_json"]),
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
    }


def append_turn(
    con: sqlite3.Connection,
    session_id: str,
    *,
    role: str,
    content: str,
    addressed_gap: str | None = None,
) -> None:
    state = get_session(con, session_id)
    transcript = state["transcript"]
    transcript.append({"role": role, "content": content, "at": _now()})
    addressed_gaps = state["addressed_gaps"]
    if addressed_gap and addressed_gap not in addressed_gaps:
        addressed_gaps.append(addressed_gap)
    con.execute(
        """UPDATE ideation_sessions
           SET transcript_json = ?, addressed_gaps_json = ?
           WHERE id = ?""",
        (json.dumps(transcript), json.dumps(addressed_gaps), session_id),
    )
    con.commit()


def end_session(con: sqlite3.Connection, session_id: str) -> None:
    con.execute(
        "UPDATE ideation_sessions SET ended_at = ? WHERE id = ?",
        (_now(), session_id),
    )
    con.commit()
