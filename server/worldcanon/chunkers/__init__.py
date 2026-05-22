"""Chunker contract and shared parsers.

A chunker reads one file and returns a `ChunkerOutput`: text chunks for
the embedding store, plus optional fact/relationship/rule/name records
that the indexer mirrors into the ledger tables.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml

from ..store import Chunk


@dataclass
class Fact:
    entity: str
    claim: str
    status: str
    introduced_in: str
    chapter_index: int | None
    source_file: str  # the entity sheet this fact lives in


@dataclass
class Relationship:
    from_entity: str  # the entity sheet this lives in
    with_entity: str
    type: str
    status: str
    notes: str | None
    source_file: str


@dataclass
class Rule:
    system: str
    rule: str
    status: str
    source_file: str


@dataclass
class NameRecord:
    culture: str
    name: str
    status: str  # used | candidate
    used_by: str | None
    notes: str | None
    source_file: str


@dataclass
class ChunkerOutput:
    chunks: list[Chunk]
    facts: list[Fact] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    names: list[NameRecord] = field(default_factory=list)


ChunkerFn = Callable[..., ChunkerOutput]


def _coerce(obj: Any) -> Any:
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _coerce(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce(v) for v in obj]
    return obj


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw_meta = parts[1]
    body = parts[2].lstrip("\n")
    try:
        meta = yaml.safe_load(raw_meta) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return _coerce(meta), body


_SECTION_PATTERN = re.compile(r"^##\s+(?P<title>[^\n]+)\s*\n", re.MULTILINE)


def _extract_section(body: str, title: str) -> str | None:
    """Return the YAML-list block under `## {title}`. Returns None if missing."""
    matches = list(_SECTION_PATTERN.finditer(body))
    for i, m in enumerate(matches):
        if m.group("title").strip().lower() == title.lower():
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            return body[start:end].strip()
    return None


def _parse_yaml_list(block: str | None) -> list[dict]:
    if not block:
        return []
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return []
    if not isinstance(data, list):
        return []
    return [_coerce(item) for item in data if isinstance(item, dict)]


def parse_facts(body: str) -> list[dict]:
    return _parse_yaml_list(_extract_section(body, "Facts"))


def parse_relationships(body: str) -> list[dict]:
    return _parse_yaml_list(_extract_section(body, "Relationships"))


def parse_rules(body: str) -> list[dict]:
    return _parse_yaml_list(_extract_section(body, "Rules"))


def parse_names(body: str) -> list[dict]:
    return _parse_yaml_list(_extract_section(body, "Names"))
