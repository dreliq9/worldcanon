"""Render LLM prompt templates from the prompts/ directory.

Each `render_*` function takes the substitution kwargs and returns the
fully-rendered string ready to send to an LLM.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_contradiction_check(
    *,
    entity: str,
    facts: list[dict[str, Any]],
    text: str,
) -> str:
    facts_list = (
        "\n".join(f"- {f.get('claim', '?')} (status: {f.get('status', '?')})" for f in facts)
        if facts
        else "(no canon facts on file for this entity)"
    )
    template = _load("contradiction_check")
    return template.format(entity=entity, facts_list=facts_list, text=text)


def render_ask_world(*, question: str, chunks: list[dict[str, Any]]) -> str:
    if chunks:
        blocks: list[str] = []
        for c in chunks:
            sp = c.get("source_path", "<unknown>")
            body = c.get("body", "")
            blocks.append(f"[{sp}]\n{body}")
        context_block = "\n\n".join(blocks)
    else:
        context_block = "(no relevant canon found)"
    template = _load("ask_world")
    return template.format(question=question, context_block=context_block)
