"""The template library: teach the app a payor's report layout from a past report.

Only the section structure and writing style are kept, never the uploaded file or any client
details in it.
"""

from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from api.imports import ALLOWED_SUFFIXES, MAX_UPLOAD_BYTES
from data import store
from pipeline.exporter import list_available_payors
from pipeline.template_extractor import sections_from_rows
from schemas.narrative import ANTHEM_SECTIONS, ReauthTemplate

router = APIRouter(prefix="/api/templates", tags=["templates"])

MAX_NAME = 200
MAX_STYLE = 2000


def _analyze(file_bytes: bytes, filename: str) -> dict:
    from pipeline.template_extractor import extract_template_structure

    return extract_template_structure(file_bytes, filename)


# The model-backed step, swappable so tests don't call the API
hooks = SimpleNamespace(analyze=_analyze)


def _known_payor(payor: str) -> str:
    if payor not in list_available_payors():
        raise HTTPException(404, "Unknown payor.")
    return payor


def _template_json(template: Optional[ReauthTemplate]) -> Optional[dict]:
    if template is None:
        return None
    return {
        "name": template.name,
        "style_notes": template.style_notes,
        "source_filename": template.source_filename,
        "sections": [{"title": s.title, "guidance": s.guidance} for s in template.sections],
    }


@router.get("/{payor}")
def get_template(payor: str) -> dict:
    _known_payor(payor)
    return {
        "payor": payor,
        "payor_name": list_available_payors()[payor]["display_name"],
        "active": _template_json(store.get_active_template(payor)),
        "default_sections": [title for _, title in ANTHEM_SECTIONS],
    }


@router.post("/analyze")
async def analyze_report(file: UploadFile) -> dict:
    name = file.filename or ""
    if not name.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(415, "Upload a PDF or Word (.docx) report.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "That file is larger than 50 MB.")
    if not content:
        raise HTTPException(400, "That file is empty.")
    try:
        result = hooks.analyze(content, name)
    except Exception as exc:
        raise HTTPException(422, f"Could not analyze that report: {exc}")
    return {
        "source_filename": name,
        "style_notes": result["style_notes"],
        "sections": [{"title": s.title, "guidance": s.guidance} for s in result["sections"]],
    }


class SectionRow(BaseModel):
    title: str
    guidance: str = ""


class TemplateBody(BaseModel):
    name: str
    sections: list[SectionRow]
    style_notes: str = ""
    source_filename: Optional[str] = None


@router.put("/{payor}")
def save_template(payor: str, body: TemplateBody) -> dict:
    _known_payor(payor)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Give the template a name.")
    if len(name) > MAX_NAME or len(body.style_notes) > MAX_STYLE:
        raise HTTPException(422, "The name or writing style is too long.")
    sections = sections_from_rows([row.model_dump() for row in body.sections])
    if len(sections) < 2:
        raise HTTPException(422, "A template needs at least two sections.")
    store.save_template(payor, name, sections, body.style_notes.strip(), body.source_filename)
    return get_template(payor)


@router.delete("/{payor}")
def use_default(payor: str) -> dict:
    """Go back to the built-in layout (the saved template is kept)."""
    _known_payor(payor)
    store.clear_active_template(payor)
    return get_template(payor)
