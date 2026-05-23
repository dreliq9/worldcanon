"""worldcanon-import — a one-shot CLI that converts a folder of docs into
markdown under <vault>/_inbox/. Then the friend uses `Canon: Triage inbox`
in Obsidian to route each file into its real home.

Supported formats:
- `.md` / `.markdown` — copied as-is
- `.txt` — converted to markdown (plain text becomes the body)
- `.rtf`, `.docx`, `.html` / `.htm` — converted via Pandoc

Skipped formats:
- PDF — text extraction quality is too variable for v1; the importer reports
  PDF files as skipped so the friend knows to convert them manually if needed
- Scrivener `.scriv` projects — folder-format conversion deferred
- Anything else — reported as skipped with the unknown extension

The CLI never crashes the whole batch on a single failure. Failed files are
reported in the summary alongside successes.
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("worldcanon.import_cli")

_PANDOC_FORMATS = {
    ".docx": "docx",
    ".html": "html",
    ".htm":  "html",
    ".rtf":  "rtf",
}
_COPY_FORMATS = {".md", ".markdown"}
_WRAP_PLAIN_FORMATS = {".txt"}
_DEFERRED_SKIP_REASONS = {
    ".pdf": "PDF text extraction deferred — convert manually if needed",
    ".scriv": "Scrivener .scriv project import deferred",
}

_INVALID_BASENAME_RE = re.compile(r'[<>:"/\\|?*]')


def sanitize_basename(name: str) -> str:
    cleaned = _INVALID_BASENAME_RE.sub("_", name)
    cleaned = cleaned.rstrip(". ")
    return cleaned or "untitled"


def convert_file(src: Path, source_root: Path, dest_root: Path,
                 *, pandoc_path: str = "pandoc") -> dict[str, Any]:
    """Convert a single file. Returns {status, reason?, dest_path?}.

    status is one of: 'ok', 'skipped', 'failed'.
    """
    ext = src.suffix.lower()

    if ext in _DEFERRED_SKIP_REASONS:
        return {"status": "skipped", "reason": _DEFERRED_SKIP_REASONS[ext]}

    rel = src.relative_to(source_root)
    safe_parts = [sanitize_basename(p) for p in rel.parent.parts]
    safe_stem = sanitize_basename(rel.stem)
    dest_rel_dir = dest_root.joinpath(*safe_parts) if safe_parts else dest_root
    dest_rel_dir.mkdir(parents=True, exist_ok=True)

    if ext in _COPY_FORMATS:
        target = dest_rel_dir / f"{safe_stem}.md"
        shutil.copyfile(src, target)
        return {"status": "ok", "dest_path": str(target.relative_to(dest_root))}

    if ext in _WRAP_PLAIN_FORMATS:
        target = dest_rel_dir / f"{safe_stem}.md"
        body = src.read_text(encoding="utf-8", errors="replace")
        target.write_text(body, encoding="utf-8")
        return {"status": "ok", "dest_path": str(target.relative_to(dest_root))}

    if ext in _PANDOC_FORMATS:
        target = dest_rel_dir / f"{safe_stem}.md"
        try:
            subprocess.run(
                [pandoc_path, "-f", _PANDOC_FORMATS[ext], str(src),
                 "-o", str(target), "-t", "markdown"],
                check=True, capture_output=True, text=True, timeout=120,
            )
            return {"status": "ok", "dest_path": str(target.relative_to(dest_root))}
        except subprocess.CalledProcessError as exc:
            reason = (exc.stderr or "").strip() or f"pandoc returned {exc.returncode}"
            return {"status": "failed", "reason": reason}
        except FileNotFoundError:
            return {"status": "failed",
                    "reason": "pandoc not found on PATH — install Pandoc and retry"}
        except subprocess.TimeoutExpired:
            return {"status": "failed", "reason": "pandoc timed out (>120s)"}

    return {"status": "skipped", "reason": f"unsupported extension: {ext}"}


def convert_tree(source: Path, dest: Path,
                 *, pandoc_path: str = "pandoc") -> dict[str, Any]:
    source = source.resolve()
    dest = dest.resolve()
    if not source.exists():
        raise FileNotFoundError(f"source does not exist: {source}")
    dest.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "ok": 0, "skipped": 0, "failed": 0,
        "files": [],
    }
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        result = convert_file(path, source, dest, pandoc_path=pandoc_path)
        summary["files"].append({
            "source": str(path.relative_to(source)),
            **result,
        })
        summary[result["status"]] += 1
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a folder of docs into <vault>/_inbox/ markdown.",
    )
    parser.add_argument("--source", required=True, help="Source folder to walk")
    parser.add_argument("--dest", required=True, help="Destination inbox folder")
    parser.add_argument("--pandoc", default="pandoc",
                        help="Path to the pandoc binary (default: 'pandoc' on PATH)")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    src = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    logger.info("walking %s -> %s", src, dest)
    summary = convert_tree(src, dest, pandoc_path=args.pandoc)

    print(f"\nImport summary: {summary['ok']} ok, "
          f"{summary['skipped']} skipped, {summary['failed']} failed.\n")
    for f in summary["files"]:
        print(f"  [{f['status']}] {f['source']}"
              + (f"  ->  {f.get('dest_path', '')}" if f.get("dest_path") else "")
              + (f"   ({f.get('reason')})" if f.get("reason") else ""))
    if summary["failed"]:
        sys.exit(2)
