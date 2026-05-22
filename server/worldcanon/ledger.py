"""Fact ledger — atomic claims, relationships, rules, naming records, history.

Source-of-truth lives in markdown (entity sheets' `## Facts`, etc.). This
module mirrors them into SQLite for queries. Every change writes a row to
`fact_history` so the friend can see how the world has evolved.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any


def install_ledger_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS facts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            entity          TEXT NOT NULL,
            claim           TEXT NOT NULL,
            status          TEXT NOT NULL,
            introduced_in   TEXT NOT NULL,
            chapter_index   INTEGER,
            source_file     TEXT NOT NULL,
            created         INTEGER NOT NULL,
            UNIQUE(entity, claim, source_file)
        );
        CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity);
        CREATE INDEX IF NOT EXISTS idx_facts_source ON facts(source_file);

        CREATE TABLE IF NOT EXISTS fact_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entity      TEXT NOT NULL,
            claim       TEXT NOT NULL,
            event       TEXT NOT NULL,
            from_status TEXT,
            to_status   TEXT,
            source_file TEXT NOT NULL,
            at          INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fact_history_entity ON fact_history(entity);

        CREATE TABLE IF NOT EXISTS relationships (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_entity  TEXT NOT NULL,
            with_entity  TEXT NOT NULL,
            type         TEXT NOT NULL,
            status       TEXT NOT NULL,
            notes        TEXT,
            source_file  TEXT NOT NULL,
            UNIQUE(from_entity, with_entity, type, source_file)
        );
        CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_entity);
        CREATE INDEX IF NOT EXISTS idx_rel_with ON relationships(with_entity);

        CREATE TABLE IF NOT EXISTS rules (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            system       TEXT NOT NULL,
            rule         TEXT NOT NULL,
            status       TEXT NOT NULL,
            source_file  TEXT NOT NULL,
            UNIQUE(system, rule, source_file)
        );
        CREATE INDEX IF NOT EXISTS idx_rules_system ON rules(system);

        CREATE TABLE IF NOT EXISTS names (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            culture      TEXT NOT NULL,
            name         TEXT NOT NULL,
            status       TEXT NOT NULL,
            used_by      TEXT,
            notes        TEXT,
            source_file  TEXT NOT NULL,
            UNIQUE(culture, name, source_file)
        );
        CREATE INDEX IF NOT EXISTS idx_names_culture ON names(culture);
        """
    )
    con.commit()


def _now() -> int:
    return int(time.time())


def sync_facts_for_file(
    con: sqlite3.Connection,
    *,
    entity: str,
    source_file: str,
    facts: list[dict[str, Any]],
) -> None:
    """Replace the set of facts contributed by `source_file` for `entity`.

    Diffs the new list against existing rows from the same source and writes
    fact_history entries for set / edit / status_change / delete events.
    """
    existing = {
        row["claim"]: row
        for row in con.execute(
            "SELECT * FROM facts WHERE entity = ? AND source_file = ?",
            (entity, source_file),
        )
    }
    now = _now()
    incoming_claims: set[str] = set()
    for f in facts:
        claim = f.get("claim")
        if not claim:
            continue
        incoming_claims.add(claim)
        status = f.get("status", "draft")
        introduced_in = f.get("introduced_in", source_file)
        chapter_index = f.get("chapter_index")
        prev = existing.get(claim)
        if prev is None:
            con.execute(
                """INSERT INTO facts (entity, claim, status, introduced_in,
                   chapter_index, source_file, created)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entity, claim, status, introduced_in, chapter_index, source_file, now),
            )
            con.execute(
                """INSERT INTO fact_history (entity, claim, event, from_status,
                   to_status, source_file, at)
                   VALUES (?, ?, 'set', NULL, ?, ?, ?)""",
                (entity, claim, status, source_file, now),
            )
        else:
            if prev["status"] != status:
                con.execute(
                    """UPDATE facts SET status = ?, introduced_in = ?, chapter_index = ?
                       WHERE id = ?""",
                    (status, introduced_in, chapter_index, prev["id"]),
                )
                con.execute(
                    """INSERT INTO fact_history (entity, claim, event, from_status,
                       to_status, source_file, at)
                       VALUES (?, ?, 'status_change', ?, ?, ?, ?)""",
                    (entity, claim, prev["status"], status, source_file, now),
                )
            elif prev["introduced_in"] != introduced_in or prev["chapter_index"] != chapter_index:
                con.execute(
                    """UPDATE facts SET introduced_in = ?, chapter_index = ?
                       WHERE id = ?""",
                    (introduced_in, chapter_index, prev["id"]),
                )
                con.execute(
                    """INSERT INTO fact_history (entity, claim, event, from_status,
                       to_status, source_file, at)
                       VALUES (?, ?, 'edit', ?, ?, ?, ?)""",
                    (entity, claim, prev["status"], status, source_file, now),
                )
    for claim, prev in existing.items():
        if claim not in incoming_claims:
            con.execute("DELETE FROM facts WHERE id = ?", (prev["id"],))
            con.execute(
                """INSERT INTO fact_history (entity, claim, event, from_status,
                   to_status, source_file, at)
                   VALUES (?, ?, 'delete', ?, NULL, ?, ?)""",
                (entity, claim, prev["status"], source_file, now),
            )
    con.commit()


def list_facts(
    con: sqlite3.Connection,
    *,
    entity: str | None = None,
    chapter_max: int | None = None,
    status: str | None = None,
) -> list[dict]:
    sql = "SELECT * FROM facts WHERE 1=1"
    args: list[Any] = []
    if entity is not None:
        sql += " AND entity = ?"
        args.append(entity)
    if chapter_max is not None:
        sql += " AND chapter_index IS NOT NULL AND chapter_index <= ?"
        args.append(chapter_max)
    if status is not None:
        sql += " AND status = ?"
        args.append(status)
    return [dict(row) for row in con.execute(sql, args)]


def sync_relationships_for_file(
    con: sqlite3.Connection,
    *,
    from_entity: str,
    source_file: str,
    relationships: list[dict[str, Any]],
) -> None:
    con.execute(
        "DELETE FROM relationships WHERE from_entity = ? AND source_file = ?",
        (from_entity, source_file),
    )
    for r in relationships:
        with_entity = r.get("with")
        rel_type = r.get("type")
        if not with_entity or not rel_type:
            continue
        con.execute(
            """INSERT OR REPLACE INTO relationships
               (from_entity, with_entity, type, status, notes, source_file)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (from_entity, with_entity, rel_type, r.get("status", "canon"),
             r.get("notes"), source_file),
        )
    con.commit()


def list_relationships(con: sqlite3.Connection, *, entity: str | None = None) -> list[dict]:
    if entity is None:
        return [dict(row) for row in con.execute("SELECT * FROM relationships")]
    return [
        dict(row)
        for row in con.execute(
            "SELECT * FROM relationships WHERE from_entity = ? OR with_entity = ?",
            (entity, entity),
        )
    ]


def sync_rules_for_file(
    con: sqlite3.Connection,
    *,
    system: str,
    source_file: str,
    rules: list[dict[str, Any]],
) -> None:
    con.execute(
        "DELETE FROM rules WHERE system = ? AND source_file = ?",
        (system, source_file),
    )
    for r in rules:
        rule = r.get("rule")
        if not rule:
            continue
        con.execute(
            """INSERT OR REPLACE INTO rules (system, rule, status, source_file)
               VALUES (?, ?, ?, ?)""",
            (system, rule, r.get("status", "canon"), source_file),
        )
    con.commit()


def list_rules(con: sqlite3.Connection, *, system: str | None = None) -> list[dict]:
    if system is None:
        return [dict(row) for row in con.execute("SELECT * FROM rules")]
    return [
        dict(row)
        for row in con.execute("SELECT * FROM rules WHERE system = ?", (system,))
    ]


def sync_names_for_file(
    con: sqlite3.Connection,
    *,
    culture: str,
    source_file: str,
    names: list[dict[str, Any]],
) -> None:
    con.execute(
        "DELETE FROM names WHERE culture = ? AND source_file = ?",
        (culture, source_file),
    )
    for n in names:
        name = n.get("name")
        if not name:
            continue
        con.execute(
            """INSERT OR REPLACE INTO names
               (culture, name, status, used_by, notes, source_file)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (culture, name, n.get("status", "candidate"),
             n.get("used_by"), n.get("notes"), source_file),
        )
    con.commit()


def list_names(con: sqlite3.Connection, *, culture: str | None = None) -> list[dict]:
    if culture is None:
        return [dict(row) for row in con.execute("SELECT * FROM names")]
    return [
        dict(row)
        for row in con.execute("SELECT * FROM names WHERE culture = ?", (culture,))
    ]


def clear_ledger_for_file(con: sqlite3.Connection, source_file: str) -> None:
    """When a file is deleted, drop all its contributions."""
    con.execute("DELETE FROM facts WHERE source_file = ?", (source_file,))
    con.execute("DELETE FROM relationships WHERE source_file = ?", (source_file,))
    con.execute("DELETE FROM rules WHERE source_file = ?", (source_file,))
    con.execute("DELETE FROM names WHERE source_file = ?", (source_file,))
    con.commit()
