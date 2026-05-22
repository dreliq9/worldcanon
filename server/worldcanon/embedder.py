"""Embedding backends.

`build_embedder()` returns the active backend based on env:
- WORLDCANON_EMBEDDER=fastembed (default) — BAAI/bge-small-en-v1.5, 384-dim
- WORLDCANON_EMBEDDER=hash — deterministic token-hash fallback (tests/offline)

All vectors are L2-normalized so dot product = cosine similarity in
sqlite-vec.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Iterable, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Embedder(Protocol):
    @property
    def dim(self) -> int: ...
    @property
    def name(self) -> str: ...
    def embed(self, texts: Iterable[str]) -> list[np.ndarray]: ...


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n == 0.0:
        return v.astype(np.float32)
    return (v / n).astype(np.float32)


_TOKEN = re.compile(r"\w+")


class HashEmbedBackend:
    def __init__(self, dim: int = 384):
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"hash-{self._dim}"

    def embed(self, texts: Iterable[str]) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        for text in texts:
            vec = np.zeros(self._dim, dtype=np.float32)
            for tok in _TOKEN.findall(text.lower()):
                h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
                idx = h % self._dim
                sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
                vec[idx] += sign
            out.append(_normalize(vec))
        return out


class FastEmbedBackend:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding
        self._model = TextEmbedding(model_name=model_name)
        self._model_name = model_name
        probe = list(self._model.embed(["probe"]))
        self._dim = int(probe[0].shape[0])

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"fastembed/{self._model_name}"

    def embed(self, texts: Iterable[str]) -> list[np.ndarray]:
        texts = list(texts)
        if not texts:
            return []
        vecs = list(self._model.embed(texts))
        return [_normalize(np.asarray(v, dtype=np.float32)) for v in vecs]


def build_embedder() -> Embedder:
    backend = os.environ.get("WORLDCANON_EMBEDDER", "fastembed").lower()
    if backend == "hash":
        dim = int(os.environ.get("WORLDCANON_EMBEDDER_DIM", "384"))
        return HashEmbedBackend(dim=dim)
    if backend == "fastembed":
        model = os.environ.get("WORLDCANON_FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
        return FastEmbedBackend(model_name=model)
    raise ValueError(f"unknown WORLDCANON_EMBEDDER backend: {backend!r}")
