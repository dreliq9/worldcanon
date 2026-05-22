from pathlib import Path

from worldcanon.chunkers.journal import chunk_journal_file


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _run():
    return chunk_journal_file(
        corpus="brainstorm",
        source_root=FIXTURE_VAULT / "brainstorm",
        path=FIXTURE_VAULT / "brainstorm" / "2026-05-22-1430.md",
        extras={},
    )


def test_journal_extracts_date_from_filename():
    out = _run()
    assert out.chunks[0].metadata["date"] == "2026-05-22T14:30:00"


def test_journal_extracts_status_from_frontmatter():
    out = _run()
    assert out.chunks[0].metadata["status"] == "unprocessed"


def test_journal_chunks_body_into_paragraphs():
    out = _run()
    assert len(out.chunks) >= 1
