import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from worldcanon.import_cli import (
    convert_file,
    convert_tree,
    sanitize_basename,
)


@pytest.fixture
def src_and_dest(tmp_path):
    src = tmp_path / "source"
    dest = tmp_path / "_inbox"
    src.mkdir()
    dest.mkdir()
    return src, dest


def test_convert_file_copies_markdown(src_and_dest):
    src, dest = src_and_dest
    f = src / "a.md"
    f.write_text("# heading\nbody", encoding="utf-8")
    out = convert_file(f, src, dest)
    assert out["status"] == "ok"
    assert (dest / "a.md").exists()
    assert (dest / "a.md").read_text(encoding="utf-8") == "# heading\nbody"


def test_convert_file_normalizes_txt(src_and_dest):
    src, dest = src_and_dest
    f = src / "note.txt"
    f.write_text("plain text body", encoding="utf-8")
    out = convert_file(f, src, dest)
    assert out["status"] == "ok"
    written = dest / "note.md"
    assert written.exists()
    assert "plain text body" in written.read_text(encoding="utf-8")


def test_convert_file_calls_pandoc_for_docx(src_and_dest, monkeypatch):
    src, dest = src_and_dest
    f = src / "story.docx"
    f.write_bytes(b"fake docx bytes")

    calls: list[list] = []
    def fake_run(cmd, **kw):
        calls.append(list(cmd))
        Path(cmd[-3]).write_text("converted body", encoding="utf-8")
        return MagicMock(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)

    out = convert_file(f, src, dest)
    assert out["status"] == "ok"
    assert (dest / "story.md").exists()
    assert any("pandoc" in c[0] for c in calls)
    assert any("-f" in c and "docx" in c for c in calls)


def test_convert_file_reports_pandoc_failure(src_and_dest, monkeypatch):
    src, dest = src_and_dest
    f = src / "broken.docx"
    f.write_bytes(b"fake")

    def fake_run(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd, stderr="boom")
    monkeypatch.setattr(subprocess, "run", fake_run)

    out = convert_file(f, src, dest)
    assert out["status"] == "failed"
    assert "boom" in out["reason"]


def test_convert_file_skips_unknown_extension(src_and_dest):
    src, dest = src_and_dest
    f = src / "spreadsheet.xlsx"
    f.write_bytes(b"x")
    out = convert_file(f, src, dest)
    assert out["status"] == "skipped"
    assert ".xlsx" in out["reason"]


def test_convert_file_skips_pdf_with_clear_note(src_and_dest):
    src, dest = src_and_dest
    f = src / "old.pdf"
    f.write_bytes(b"x")
    out = convert_file(f, src, dest)
    assert out["status"] == "skipped"
    assert "PDF" in out["reason"] or ".pdf" in out["reason"]


def test_convert_tree_walks_recursively(src_and_dest, monkeypatch):
    src, dest = src_and_dest
    (src / "sub").mkdir()
    (src / "sub" / "a.md").write_text("a", encoding="utf-8")
    (src / "b.txt").write_text("b", encoding="utf-8")
    summary = convert_tree(src, dest, pandoc_path="pandoc")
    assert summary["ok"] >= 2
    assert (dest / "sub" / "a.md").exists()
    assert (dest / "b.md").exists()


def test_sanitize_basename_strips_invalid_chars():
    assert sanitize_basename("ok name.md") == "ok name.md"
    assert sanitize_basename("weird:/path.md") == "weird__path.md"
    assert sanitize_basename("trailing dots...") == "trailing dots"
