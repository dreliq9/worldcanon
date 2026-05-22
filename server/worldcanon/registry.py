"""Loads corpora.yaml into typed CorpusConfig records.

Paths in the YAML are relative to a vault root passed at load time
(so the same corpora.yaml works for any vault location).

Chunker name -> callable convention:
    `chunker: prose` resolves to
        from worldcanon.chunkers.prose import chunk_prose_file
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .chunkers import ChunkerFn


@dataclass
class CorpusConfig:
    name: str
    paths: list[Path]
    chunker_name: str
    chunker_fn: ChunkerFn
    glob: str = "**/*.md"
    globs: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)


def _resolve_chunker(name: str) -> ChunkerFn:
    module_name = f"worldcanon.chunkers.{name}"
    fn_name = f"chunk_{name}_file"
    try:
        module = importlib.import_module(module_name)
        fn = getattr(module, fn_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"unknown chunker '{name}': {e}") from e
    return fn


def load_registry(
    yaml_path: str | Path,
    *,
    vault_root: str | Path,
) -> list[CorpusConfig]:
    yaml_path = Path(yaml_path)
    vault_root = Path(vault_root).expanduser().resolve()
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    out: list[CorpusConfig] = []
    for entry in raw.get("corpora") or []:
        name = entry.get("name")
        if not name:
            raise ValueError(f"corpora.yaml entry missing 'name': {entry!r}")
        chunker_name = entry.get("chunker")
        if not chunker_name:
            raise ValueError(f"corpus '{name}': missing 'chunker' field")
        glob_field = entry.get("glob", "**/*.md")
        if isinstance(glob_field, list):
            primary = glob_field[0] if glob_field else "**/*.md"
            secondary = list(glob_field[1:])
        else:
            primary = glob_field
            secondary = list(entry.get("globs") or [])
        paths = [vault_root / p for p in entry.get("paths") or []]
        out.append(
            CorpusConfig(
                name=name,
                paths=paths,
                chunker_name=chunker_name,
                chunker_fn=_resolve_chunker(chunker_name),
                glob=primary,
                globs=secondary,
                exclude=list(entry.get("exclude") or []),
                extras=dict(entry.get("extras") or {}),
            )
        )
    return out
