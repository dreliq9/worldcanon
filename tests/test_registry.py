from pathlib import Path

import pytest

from worldcanon.registry import load_registry


REPO = Path(__file__).parent.parent
FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def test_registry_loads_all_corpora_from_repo_yaml(tmp_path):
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    names = {c.name for c in cfgs}
    assert {"canon", "drafts", "entities", "systems",
            "naming", "brainstorm", "research"} <= names


def test_registry_resolves_chunker_callables(tmp_path):
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    by_name = {c.name: c for c in cfgs}
    assert callable(by_name["entities"].chunker_fn)
    assert by_name["entities"].chunker_name == "entity_sheet"


def test_registry_resolves_paths_relative_to_vault(tmp_path):
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=FIXTURE_VAULT)
    by_name = {c.name: c for c in cfgs}
    assert by_name["entities"].paths[0] == FIXTURE_VAULT / "entities"


def test_registry_unknown_chunker_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("corpora:\n  - name: x\n    paths: ['x/']\n    chunker: nonexistent\n")
    with pytest.raises(ValueError, match="unknown chunker"):
        load_registry(bad, vault_root=FIXTURE_VAULT)
