"""One authorization period: its extracted data, narrative, notes and Word export.

This is what the Review, Generate and Export screens work with. Generating a narrative takes
a minute, so it runs in a background thread and the screen polls the period's generation job.
"""

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from api import imports
from data import store
from pipeline import intake
from pipeline.exporter import export_to_docx, list_available_payors
from pipeline.section_sources import source_for_section
from pipeline.validator import validate_completeness
from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import CustomNarrative, Narrative, get_sections

router = APIRouter(prefix="/api/periods", tags=["periods"])

MAX_NOTES = 5000
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ── helpers ──────────────────────────────────────────────────────────

def _period_or_404(period_id: str) -> dict:
    period = store.get_auth_period(period_id)
    if period is None:
        raise HTTPException(404, "Authorization period not found.")
    client = store.get_client(period["client_id"])
    if client is None:
        raise HTTPException(404, "Authorization period not found.")
    period["_client"] = client
    return period


def _need_data(period: dict) -> ExtractedClinicalData:
    data = period.get("extracted_data_parsed")
    if data is None:
        raise HTTPException(409, "No report has been imported for this period yet.")
    return data


def _need_narrative(period: dict) -> Narrative:
    narrative = period.get("narrative_data_parsed")
    if narrative is None:
        raise HTTPException(409, "No narrative has been generated for this period yet.")
    return narrative


def narrative_json(narrative: Narrative, data: ExtractedClinicalData) -> dict:
    return {
        "kind": "custom" if isinstance(narrative, CustomNarrative) else "default",
        "payor_key": getattr(narrative, "payor_key", "") or None,
        "template_name": getattr(narrative, "template_name", "") or None,
        "overall_confidence": narrative.overall_confidence,
        "flags": list(narrative.flags_for_bcba),
        "stale": intake.is_stale(narrative, data),
        "sections": [
            {
                "key": key,
                "title": title,
                "content": section.content,
                "requires_review": section.requires_review,
                "review_note": section.review_note,
                "source": source_for_section(narrative, key, section, data),
            }
            for key, title, section in get_sections(narrative)
        ],
    }


def comparison_json(period: dict, data: ExtractedClinicalData) -> Optional[dict]:
    """Progress since the authorization before this one, if that one has data."""
    prior = store.get_prior_period(period["client_id"], period["id"])
    if not prior or not prior.get("extracted_data_parsed"):
        return None
    before: ExtractedClinicalData = prior["extracted_data_parsed"]

    earlier = {b.behavior_name: b for b in before.behavior_reduction_targets}
    changes = []
    for b in data.behavior_reduction_targets:
        old = earlier.get(b.behavior_name)
        if old and old.current_value is not None and b.current_value is not None and old.current_value > 0:
            changes.append(
                {
                    "name": b.behavior_name,
                    "prior": old.current_value,
                    "current": b.current_value,
                    "unit": b.unit,
                    "percent_change": (b.current_value - old.current_value) / old.current_value * 100,
                }
            )
    return {
        "prior_start": prior["period_start"],
        "prior_end": prior["period_end"],
        "skills_mastered_prior": sum(1 for t in before.skill_acquisition_targets if t.is_mastered),
        "skills_mastered": sum(1 for t in data.skill_acquisition_targets if t.is_mastered),
        "skill_targets": len(data.skill_acquisition_targets),
        "behavior_targets": len(data.behavior_reduction_targets),
        "behavior_changes": changes,
    }


def period_detail(period: dict) -> dict:
    client = period["_client"]
    payors = list_available_payors()
    data: Optional[ExtractedClinicalData] = period.get("extracted_data_parsed")
    narrative: Optional[Narrative] = period.get("narrative_data_parsed")
    template = store.get_active_template(client["payor"])
    return {
        "id": period["id"],
        "period_start": period["period_start"],
        "period_end": period["period_end"],
        "status": period["status"],
        "notes": period.get("notes") or "",
        "uploaded_filename": period.get("uploaded_filename"),
        "extracted_at": period.get("extracted_at"),
        "generated_at": period.get("generated_at"),
        "exported_at": period.get("exported_at"),
        "client": {
            "id": client["id"],
            "display_name": client["display_name"],
            "client_identifier": client.get("client_identifier"),
            "payor": client["payor"],
            "payor_name": payors.get(client["payor"], {}).get("display_name", client["payor"]),
        },
        "data": data.model_dump(mode="json") if data else None,
        "validation": period.get("validation_result_parsed"),
        "narrative": narrative_json(narrative, data) if narrative and data else None,
        "template": {"name": template.name, "section_count": len(template.sections)} if template else None,
        "comparison": comparison_json(period, data) if data else None,
    }


def _readable_errors(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:3]:
        where = ".".join(str(p) for p in error["loc"]) or "data"
        parts.append(f"{where}: {error['msg']}")
    return "; ".join(parts)


# ── read / small updates ─────────────────────────────────────────────

@router.get("/{period_id}")
def get_period(period_id: str) -> dict:
    return period_detail(_period_or_404(period_id))


class PeriodUpdate(BaseModel):
    notes: str


@router.patch("/{period_id}")
def update_period(period_id: str, body: PeriodUpdate) -> dict:
    _period_or_404(period_id)
    if len(body.notes) > MAX_NOTES:
        raise HTTPException(422, f"Keep notes under {MAX_NOTES} characters.")
    store.update_period_notes(period_id, body.notes)
    return {"notes": body.notes}


# ── extracted data (Review) ──────────────────────────────────────────

@router.put("/{period_id}/data")
def save_data(period_id: str, body: dict[str, Any]) -> dict:
    """Save the BCBA's edits. The whole record is re-checked, so bad values are refused with a reason."""
    period = _period_or_404(period_id)
    _need_data(period)
    try:
        updated = ExtractedClinicalData.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(422, _readable_errors(exc))
    validation = validate_completeness(updated)
    store.save_clinical_data(period_id, updated, validation)
    narrative = period.get("narrative_data_parsed")
    return {
        "data": updated.model_dump(mode="json"),
        "validation": validation,
        "narrative_stale": bool(narrative) and intake.is_stale(narrative, updated),
    }


# ── narrative (Generate) ─────────────────────────────────────────────

class SectionEdit(BaseModel):
    key: str
    content: str


class NarrativeEdit(BaseModel):
    sections: list[SectionEdit]


@router.put("/{period_id}/narrative")
def save_narrative_edits(period_id: str, body: NarrativeEdit) -> dict:
    period = _period_or_404(period_id)
    data = _need_data(period)
    narrative = _need_narrative(period)
    by_key = {key: section for key, _, section in get_sections(narrative)}
    for edit in body.sections:
        if edit.key not in by_key:
            raise HTTPException(422, f"This narrative has no section “{edit.key}”.")
    for edit in body.sections:
        by_key[edit.key].content = edit.content
    store.save_narrative(period_id, narrative)
    return narrative_json(narrative, data)


@dataclass
class GenerationJob:
    period_id: str
    stage: str = "drafting"  # drafting -> checking -> done | error
    error: Optional[str] = None
    discrepancies: Optional[list[str]] = None
    check_error: Optional[str] = None
    narrative_ready: bool = field(default=False)


GENERATIONS: dict[str, GenerationJob] = {}


def _generate(job: GenerationJob, data: ExtractedClinicalData, payor_key: str) -> None:
    try:
        narrative = imports.hooks.draft(data, payor_key)
        store.save_narrative(job.period_id, narrative)
        job.narrative_ready = True
    except Exception as exc:  # shown to the BCBA; the previous draft (if any) is untouched
        job.stage, job.error = "error", str(exc)
        return
    job.stage = "checking"
    try:
        job.discrepancies = imports.hooks.check(narrative, data)
    except Exception as exc:
        job.check_error = str(exc)
    job.stage = "done"


def generation_json(job: Optional[GenerationJob]) -> dict:
    if job is None:
        return {"stage": "idle", "error": None, "discrepancies": None, "check_error": None}
    return {
        "stage": job.stage,
        "error": job.error,
        "discrepancies": job.discrepancies,
        "check_error": job.check_error,
    }


@router.post("/{period_id}/generate", status_code=202)
def start_generation(period_id: str) -> dict:
    period = _period_or_404(period_id)
    data = _need_data(period)
    running = GENERATIONS.get(period_id)
    if running and running.stage in ("drafting", "checking"):
        raise HTTPException(409, "A narrative is already being written for this period.")
    job = GenerationJob(period_id=period_id)
    GENERATIONS[period_id] = job
    threading.Thread(target=_generate, args=(job, data, period["_client"]["payor"]), daemon=True).start()
    return generation_json(job)


@router.get("/{period_id}/generate")
def generation_status(period_id: str) -> dict:
    _period_or_404(period_id)
    return generation_json(GENERATIONS.get(period_id))


# ── export ───────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    confirmed: bool = False
    payor_key: Optional[str] = None


def _filename(payor_key: str, data: ExtractedClinicalData) -> str:
    def clean(text: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "x"

    client_ref = clean(data.client.client_id or "client")
    end = clean(str(data.client.auth_period_end or "draft"))
    return f"reauth_{clean(payor_key.replace('_', '-'))}_{client_ref}_{end}.docx"


@router.post("/{period_id}/export")
def export_period(period_id: str, body: ExportRequest) -> Response:
    period = _period_or_404(period_id)
    data = _need_data(period)
    narrative = _need_narrative(period)
    if not body.confirmed:
        raise HTTPException(422, "Confirm that you've reviewed every section before exporting.")

    payors = list_available_payors()
    if isinstance(narrative, CustomNarrative):
        # a template-driven narrative carries its own payor and layout
        payor_key = narrative.payor_key or period["_client"]["payor"]
    else:
        payor_key = body.payor_key or period["_client"]["payor"]
    if payor_key not in payors:
        raise HTTPException(422, "Choose a payor.")

    try:
        content = export_to_docx(data, narrative, payor_key=payor_key)
    except Exception as exc:
        raise HTTPException(500, f"The Word document couldn't be built: {exc}")
    store.save_export(period_id)
    return Response(
        content,
        media_type=DOCX_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{_filename(payor_key, data)}"'},
    )


@router.post("/{period_id}/submitted")
def mark_submitted(period_id: str) -> dict:
    period = _period_or_404(period_id)
    if period["status"] != "exported":
        raise HTTPException(409, "Export the document before marking it submitted.")
    store.mark_submitted(period_id)
    return {"status": "submitted"}
