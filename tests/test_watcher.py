import time
from pathlib import Path

import pytest

from worldcanon.embedder import HashEmbedBackend
from worldcanon.ledger import install_ledger_schema, list_facts
from worldcanon.registry import load_registry
from worldcanon.store import open_store
from worldcanon.watcher import VaultWatcher


REPO = Path(__file__).parent.parent


@pytest.fixture
def vault_setup(tmp_path):
    vault = tmp_path / "vault"
    (vault / "entities" / "characters").mkdir(parents=True)
    (vault / "entities" / "characters" / "Aerin.md").write_text(
        "---\ntype: character\nname: Aerin\n---\n\n# Aerin\n\nbody\n\n## Facts\n\n"
        "- claim: \"has green eyes\"\n  status: canon\n  introduced_in: x\n  chapter_index: null\n"
    )

    embedder = HashEmbedBackend(dim=32)
    store = open_store(tmp_path / "t.sqlite", dim=embedder.dim)
    con = store.connection()
    install_ledger_schema(con)
    cfgs = load_registry(REPO / "corpora.yaml", vault_root=vault)
    yield vault, store, con, embedder, cfgs
    store.close()


def test_watcher_picks_up_new_file(vault_setup):
    vault, store, con, embedder, cfgs = vault_setup
    watcher = VaultWatcher(store=store, embedder=embedder, cfgs=cfgs, vault_root=vault)
    watcher.start()
    try:
        (vault / "entities" / "characters" / "Lira.md").write_text(
            "---\ntype: character\nname: Lira\n---\n\n# Lira\n\nbody\n\n## Facts\n\n"
            "- claim: \"is elder sister\"\n  status: canon\n  introduced_in: x\n  chapter_index: null\n"
        )
        for _ in range(50):
            time.sleep(0.1)
            if list_facts(con, entity="Lira"):
                break
        assert list_facts(con, entity="Lira")
    finally:
        watcher.stop()


def test_watcher_picks_up_modification(vault_setup):
    vault, store, con, embedder, cfgs = vault_setup
    from worldcanon.indexer import full_index_corpus
    for cfg in cfgs:
        full_index_corpus(con, cfg, embedder)
    assert len(list_facts(con, entity="Aerin")) == 1

    watcher = VaultWatcher(store=store, embedder=embedder, cfgs=cfgs, vault_root=vault)
    watcher.start()
    try:
        (vault / "entities" / "characters" / "Aerin.md").write_text(
            "---\ntype: character\nname: Aerin\n---\n\n# Aerin\n\nbody\n\n## Facts\n\n"
            "- claim: \"has green eyes\"\n  status: canon\n  introduced_in: x\n  chapter_index: null\n"
            "- claim: \"carries dagger\"\n  status: draft\n  introduced_in: x\n  chapter_index: null\n"
        )
        for _ in range(50):
            time.sleep(0.1)
            if len(list_facts(con, entity="Aerin")) == 2:
                break
        assert len(list_facts(con, entity="Aerin")) == 2
    finally:
        watcher.stop()
