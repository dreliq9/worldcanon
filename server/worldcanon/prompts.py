"""Render LLM prompt templates from the prompts/ directory.

Each `render_*` function takes the substitution kwargs and returns the
fully-rendered string ready to send to an LLM.
"""
from __future__ import annotations

import re as _re
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


def load_gap_priorities(entity_type: str) -> list[str]:
    """Return the ordered list of gap categories for an entity type.

    Reads `prompts/gap_priorities.md` and finds the section `## {type}`.
    Returns an empty list if the type isn't defined.
    """
    text = _load("gap_priorities")
    section_re = _re.compile(rf"^##\s+{_re.escape(entity_type)}\s*$", _re.MULTILINE)
    match = section_re.search(text)
    if not match:
        return []
    rest = text[match.end():]
    end = rest.find("\n## ")
    if end != -1:
        rest = rest[:end]
    out: list[str] = []
    for line in rest.splitlines():
        m = _re.match(r"^\s*\d+\.\s*(.+?)\s*$", line)
        if m:
            out.append(m.group(1))
    return out


def render_ideation_question(
    *,
    entity_type: str,
    entity_name: str,
    entity_state: str,
    relevant_canon: str,
    addressed_gaps: list[str],
) -> str:
    gap_list = load_gap_priorities(entity_type)
    gap_priorities = (
        "\n".join(f"{i + 1}. {g}" for i, g in enumerate(gap_list))
        if gap_list
        else "(none defined for this type)"
    )
    addressed = (
        "\n".join(f"- {g}" for g in addressed_gaps) if addressed_gaps else "(none yet)"
    )
    return _load("ideation_question").format(
        entity_type=entity_type,
        entity_name=entity_name,
        entity_state=entity_state,
        relevant_canon=relevant_canon,
        gap_priorities=gap_priorities,
        addressed_gaps=addressed,
    )


def render_ideation_response(
    *,
    entity_type: str,
    entity_name: str,
    transcript: str,
    answer: str,
    addressed_gaps: list[str],
) -> str:
    gap_list = load_gap_priorities(entity_type)
    gap_priorities = (
        "\n".join(f"{i + 1}. {g}" for i, g in enumerate(gap_list))
        if gap_list
        else "(none defined for this type)"
    )
    addressed = (
        "\n".join(f"- {g}" for g in addressed_gaps) if addressed_gaps else "(none yet)"
    )
    return _load("ideation_response").format(
        entity_type=entity_type,
        entity_name=entity_name,
        transcript=transcript,
        answer=answer,
        gap_priorities=gap_priorities,
        addressed_gaps=addressed,
    )


def render_fact_extraction(*, text: str, source: str) -> str:
    return _load("fact_extraction").format(text=text, source=source)


def render_name_suggest(
    *,
    culture: str,
    conventions: list[str],
    used_names: list[str],
    candidate_names: list[str],
    role: str | None,
    vibe: str | None,
    count: int,
) -> str:
    conventions_block = (
        "\n".join(f"- {c}" for c in conventions) if conventions else "(no conventions documented)"
    )
    used_block = ", ".join(used_names) if used_names else "(none)"
    candidate_block = ", ".join(candidate_names) if candidate_names else "(none)"
    role_line = f"Role context: {role}" if role else ""
    vibe_line = f"Vibe context: {vibe}" if vibe else ""
    return _load("name_suggest").format(
        culture=culture,
        conventions_block=conventions_block,
        used_names=used_block,
        candidate_names=candidate_block,
        role_line=role_line,
        vibe_line=vibe_line,
        count=count,
    )


_TRIAGE_MAX_CONTENT_CHARS = 2000


def render_triage_suggest(*, filename: str, content: str) -> str:
    truncated = content[:_TRIAGE_MAX_CONTENT_CHARS]
    if len(content) > _TRIAGE_MAX_CONTENT_CHARS:
        truncated += "\n\n[…truncated…]"
    return _load("triage_suggest").format(
        filename=filename,
        content=truncated,
    )
