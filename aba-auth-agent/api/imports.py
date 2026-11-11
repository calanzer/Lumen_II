"""Import jobs: drop a report, the pipeline does the rest.

A real import takes a minute or two (read the report, draft the narrative, check the
numbers), so it runs in a background thread and the client polls the job. Stages:

    reading -> needs_answers (only if the report left something out) -> setting_up
            -> drafting -> checking -> done        (or error at any point)

Jobs live in memory: a restart forgets in-flight imports, but anything already imported is
saved in the database.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import date
from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from api.auth import require_user
from data import store
from pipeline import intake
from pipeline.exporter import list_available_payors
from pipeline.validator import validate_completeness
from schemas.narrative import get_sections

router = APIRouter(prefix="/api/imports", tags=["imports"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_SUFFIXES = (".pdf", ".docx")


def _extract(file_bytes: bytes, filename: str):
    from pipeline.extractor import extract_clinical_data

    return extract_clinical_data(file_bytes, filename)


def _check(narrative, data):
    from pipeline.generator import validate_narrative_against_source

    return validate_narrative_against_source(narrative, data)


# The three model-backed steps, swappable so tests don't call the API
hooks = SimpleNamespace(extract=_extract, draft=intake.draft_narrative, check=_check)


@dataclass
class Job:
    id: str
    owner: str
    filename: str
    file_bytes: bytes = field(repr=False, default=b"")
    stage: str = "reading"
    error: Optional[str] = None
    questions: list[str] = field(default_factory=list)
    result: Optional[dict] = None
    # working state, never sent to the client
    data: object = field(repr=False, default=None)
    validation: dict = field(repr=False, default_factory=dict)
    plan: object = field(repr=False, default=None)
    answers: object = field(repr=False, default=None)


JOBS: dict[str, Job] = {}


def start_job(owner: str, file_bytes: bytes, filename: str) -> Job:
    job = Job(id=uuid.uuid4().hex, owner=owner, filename=filename, file_bytes=file_bytes)
    JOBS[job.id] = job
    threading.Thread(target=_read_and_plan, args=(job,), daemon=True).start()
    return job


def _read_and_plan(job: Job) -> None:
    try:
        job.data = hooks.extract(job.file_bytes, job.filename)
        job.validation = validate_completeness(job.data)
        job.plan = intake.build_plan(job.data, store.list_clients())
        job.file_bytes = b""  # not needed again, and not worth keeping in memory
        if job.plan.questions:
            job.questions = list(job.plan.questions)
            job.stage = "needs_answers"
            return
        _finish(job)
    except Exception as exc:  # shown to the BCBA, so keep the message
        job.stage, job.error = "error", str(exc)


def _finish(job: Job) -> None:
    try:
        job.stage = "setting_up"
        imported = intake.apply_import(job.plan, job.data, job.filename, job.validation, job.answers)

        narrative, draft_error = None, None
        job.stage = "drafting"
        try:
            narrative = hooks.draft(imported.data, imported.payor_key)
            store.save_narrative(imported.period_id, narrative)
        except Exception as exc:
            draft_error = str(exc)

        discrepancies, check_error = None, None
        if narrative is not None:
            job.stage = "checking"
            try:
                discrepancies = hooks.check(narrative, imported.data)
            except Exception as exc:
                check_error = str(exc)

        job.result = _summary(job, imported, narrative, draft_error, discrepancies, check_error)
        job.stage = "done"
    except Exception as exc:
        job.stage, job.error = "error", str(exc)


def _summary(job, imported, narrative, draft_error, discrepancies, check_error) -> dict:
    client = store.get_client(imported.client_id)
    payor = list_available_payors().get(imported.payor_key, {})
    plan = job.plan
    period = store.get_auth_period(imported.period_id)

    draft = None
    if narrative is not None:
        sections = get_sections(narrative)
        draft = {
            "section_count": len(sections),
            "sections_needing_review": sum(1 for _, _, section in sections if section.requires_review),
            "flags": list(narrative.flags_for_bcba),
            "used_custom_template": store.get_active_template(imported.payor_key) is not None,
        }

    return {
        "client_id": imported.client_id,
        "period_id": imported.period_id,
        "client": {"display_name": client["display_name"], "identifier": client.get("client_identifier")},
        "client_created": imported.client_created,
        "payor": {"key": imported.payor_key, "name": payor.get("display_name", imported.payor_key)},
        "period": {"start": period["period_start"], "end": period["period_end"]},
        "notes": imported.notes,
        "completeness": imported.validation.get("score", 0),
        "missing": [item["description"] for item in imported.validation.get("missing", [])],
        "warnings": imported.validation.get("warnings", []),
        "draft": draft,
        "draft_error": draft_error,
        # None means the automatic number check could not run
        "discrepancies": discrepancies,
        "check_error": check_error,
    }


class AnswersBody(BaseModel):
    existing_client_id: Optional[str] = None
    new_identifier: Optional[str] = None
    payor_key: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


def _validated_answers(job: Job, body: AnswersBody) -> intake.Answers:
    """Check the reply covers every question the job asked, or say what's missing."""
    creating_client = job.plan.client is None
    if intake.ASK_CLIENT in job.questions:
        if body.existing_client_id:
            if store.get_client(body.existing_client_id) is None:
                raise ValueError("That client doesn't exist.")
            creating_client = False
        elif not (body.new_identifier or "").strip():
            raise ValueError("Choose a client or enter a new client ID.")
    if intake.ASK_PAYOR in job.questions and creating_client:
        if body.payor_key not in list_available_payors():
            raise ValueError("Choose a payor.")
    if intake.ASK_PERIOD in job.questions:
        if not (body.period_start and body.period_end):
            raise ValueError("Enter the authorization period dates.")
        if body.period_end <= body.period_start:
            raise ValueError("The period must end after it starts.")
    return intake.Answers(**body.model_dump())


def _owned_job(job_id: str, user: dict) -> Job:
    job = JOBS.get(job_id)
    if job is None or job.owner != user["username"]:
        raise HTTPException(404, "Import not found.")
    return job


def job_json(job: Job) -> dict:
    return {
        "id": job.id,
        "filename": job.filename,
        "stage": job.stage,
        "questions": job.questions,
        "error": job.error,
        "result": job.result,
    }


@router.post("", status_code=202)
async def create_import(file: UploadFile, user: dict = Depends(require_user)) -> dict:
    name = file.filename or ""
    if not name.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(415, "Upload a PDF or Word (.docx) report.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "That file is larger than 50 MB.")
    if not content:
        raise HTTPException(400, "That file is empty.")
    return job_json(start_job(user["username"], content, name))


@router.get("/{job_id}")
def get_import(job_id: str, user: dict = Depends(require_user)) -> dict:
    return job_json(_owned_job(job_id, user))


@router.post("/{job_id}/answers", status_code=202)
def answer_questions(job_id: str, body: AnswersBody, user: dict = Depends(require_user)) -> dict:
    job = _owned_job(job_id, user)
    if job.stage != "needs_answers":
        raise HTTPException(409, "This import isn't waiting for answers.")
    try:
        job.answers = _validated_answers(job, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    job.stage = "setting_up"
    threading.Thread(target=_finish, args=(job,), daemon=True).start()
    return job_json(job)
