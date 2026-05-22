import numpy as np

from worldcanon.embedder import HashEmbedBackend, build_embedder


def test_hash_backend_is_deterministic():
    e = HashEmbedBackend(dim=32)
    a = e.embed(["hello world"])
    b = e.embed(["hello world"])
    assert np.allclose(a[0], b[0])


def test_hash_backend_normalized():
    e = HashEmbedBackend(dim=32)
    v = e.embed(["something"])[0]
    norm = float(np.linalg.norm(v))
    assert abs(norm - 1.0) < 1e-5 or norm == 0.0


def test_hash_backend_dim():
    e = HashEmbedBackend(dim=64)
    assert e.dim == 64
    assert e.embed(["x"])[0].shape == (64,)


def test_build_embedder_returns_hash_when_env_set(monkeypatch):
    monkeypatch.setenv("WORLDCANON_EMBEDDER", "hash")
    e = build_embedder()
    assert isinstance(e, HashEmbedBackend)
