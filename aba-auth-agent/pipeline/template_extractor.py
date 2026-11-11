"""Derive a reusable reauthorization template (structure + style) from a past report.

Only section titles, generic guidance and style notes are kept. The uploaded report is
never stored, and the prompt forbids copying client details into the result.
"""

import json
import re

import anthropic

from pipeline.extractor import (
    _build_content_blocks_for_docx,
    _build_content_blocks_for_pdf,
    _strip_markdown_fences,
    load_prompt,
)
from pipeline.llm import EFFORT_LIGHT, MAIN_MODEL, MAX_TOKENS_SMALL, response_text
from schemas.narrative import TemplateSection

MAX_SECTIONS = 20


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "section"


def sections_from_rows(rows: list[dict]) -> list[TemplateSection]:
    """Build template sections from {title, guidance} rows, with unique keys.

    Blank titles are dropped. Used for both model output and user edits.
    """
    sections: list[TemplateSection] = []
    seen: dict[str, int] = {}
    for row in rows:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        if len(sections) >= MAX_SECTIONS:
            break
        base = _slugify(title)
        seen[base] = seen.get(base, 0) + 1
        key = base if seen[base] == 1 else f"{base}_{seen[base]}"
        sections.append(
            TemplateSection(key=key, title=title, guidance=str(row.get("guidance") or "").strip())
        )
    return sections


def extract_template_structure(file_bytes: bytes, filename: str) -> dict:
    """Return {"sections": [TemplateSection], "style_notes": str} for a past report."""
    if filename.lower().endswith(".docx"):
        doc_blocks = _build_content_blocks_for_docx(file_bytes)
    else:
        doc_blocks = _build_content_blocks_for_pdf(file_bytes)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MAIN_MODEL,
        max_tokens=MAX_TOKENS_SMALL,
        output_config={"effort": EFFORT_LIGHT},
        system=load_prompt("template_extraction_system.txt"),
        messages=[
            {
                "role": "user",
                "content": doc_blocks
                + [
                    {
                        "type": "text",
                        "text": "Describe this report's section structure and writing style as the JSON template.",
                    }
                ],
            }
        ],
    )

    parsed = json.loads(_strip_markdown_fences(response_text(message)))
    sections = sections_from_rows(parsed.get("sections") or [])
    if len(sections) < 2:
        raise ValueError("Could not find at least two sections in that report.")
    return {"sections": sections, "style_notes": str(parsed.get("style_notes") or "").strip()}
