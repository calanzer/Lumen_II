"""The client roster: list, add, details with authorization periods, archive."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data import store
from pipeline import intake
from pipeline.exporter import list_available_payors

router = APIRouter(prefix="/api/clients", tags=["clients"])

MAX_NAME = 120
MAX_DIAGNOSIS_CODES = 20


def _days_until(end_iso: str, today: date) -> int:
    return (date.fromisoformat(end_iso) - today).days


def _period_json(period: dict, today: date) -> dict:
    return {
        "id": period["id"],
        "period_start": period["period_start"],
        "period_end": period["period_end"],
        "status": period["status"],
        "days_until_end": _days_until(period["period_end"], today),
        "uploaded_filename": period.get("uploaded_filename"),
        "has_data": bool(period.get("extracted_data")),
        "has_narrative": bool(period.get("narrative_data")),
        "exported_at": period.get("exported_at"),
    }


def _client_json(client: dict, periods: list[dict], today: date) -> dict:
    payors = list_available_payors()
    return {
        "id": client["id"],
        "display_name": client["display_name"],
        "client_identifier": client.get("client_identifier"),
        "payor": client["payor"],
        "payor_name": payors.get(client["payor"], {}).get("display_name", client["payor"]),
        "diagnosis_codes": client.get("diagnosis_codes") or [],
        "period_count": len(periods),
        # list_auth_periods is newest first, so this is the authorization to watch
        "latest_period": _period_json(periods[0], today) if periods else None,
    }


@router.get("")
def list_clients() -> list[dict]:
    today = date.today()
    return [
        _client_json(client, store.list_auth_periods(client["id"]), today)
        for client in store.list_clients(status="active")
    ]


class NewClient(BaseModel):
    display_name: str
    client_identifier: Optional[str] = None
    diagnosis_codes: list[str] = Field(default_factory=list)
    payor: str


@router.post("", status_code=201)
def create_client(body: NewClient) -> dict:
    name = body.display_name.strip()
    if not name:
        raise HTTPException(422, "Enter a name.")
    if len(name) > MAX_NAME:
        raise HTTPException(422, f"Keep the name under {MAX_NAME} characters.")
    if body.payor not in list_available_payors():
        raise HTTPException(422, "Choose a payor.")

    identifier = (body.client_identifier or "").strip() or None
    if identifier and intake.find_client(store.list_clients(), identifier):
        raise HTTPException(409, "A client with that ID already exists.")

    codes = [code.strip() for code in body.diagnosis_codes if code.strip()]
    if len(codes) > MAX_DIAGNOSIS_CODES:
        raise HTTPException(422, f"Enter at most {MAX_DIAGNOSIS_CODES} diagnosis codes.")

    client_id = store.create_client(
        display_name=name, client_identifier=identifier, diagnosis_codes=codes, payor=body.payor
    )
    return _client_json(store.get_client(client_id), [], date.today())


def _active_client(client_id: str) -> dict:
    client = store.get_client(client_id)
    if client is None or client.get("status") != "active":
        raise HTTPException(404, "Client not found.")
    return client


def _period_extras(period: dict) -> dict:
    """What the details screen shows for each period beyond the roster fields."""
    data = period.get("extracted_data_parsed")
    narrative = period.get("narrative_data_parsed")
    validation = period.get("validation_result_parsed")
    return {
        "notes": period.get("notes") or "",
        "extracted_at": period.get("extracted_at"),
        "validation": (
            {
                "score": validation["score"],
                "missing": len(validation.get("missing", [])),
                "warnings": len(validation.get("warnings", [])),
            }
            if validation
            else None
        ),
        "counts": (
            {
                "assessments": len(data.assessments),
                "skill_targets": len(data.skill_acquisition_targets),
                "behaviors": len(data.behavior_reduction_targets),
                "goals": len(data.treatment_goals),
                "hours_codes": len(data.hours_utilization),
            }
            if data
            else None
        ),
        "narrative": (
            {"confidence": narrative.overall_confidence, "flags": len(narrative.flags_for_bcba)} if narrative else None
        ),
    }


MAX_TREND_DOMAINS = 10


def _assessment_trends(periods: list[dict]) -> Optional[dict]:
    """VB-MAPP domain scores side by side across periods, oldest first (needs two or more)."""
    columns: list[str] = []
    scores: list[dict] = []
    for period in reversed(periods):  # list_auth_periods is newest first
        data = period.get("extracted_data_parsed")
        if not data:
            continue
        for assessment in data.assessments:
            if assessment.assessment_type.value == "VB-MAPP" and assessment.domain_scores:
                columns.append(period["period_start"][:7])
                scores.append(assessment.domain_scores)
    if len(scores) < 2:
        return None
    return {
        "columns": columns,
        "rows": [
            {"domain": domain, "values": [column.get(domain) for column in scores]}
            for domain in list(scores[0])[:MAX_TREND_DOMAINS]
        ],
    }


@router.get("/{client_id}")
def client_detail(client_id: str) -> dict:
    client = _active_client(client_id)
    today = date.today()
    periods = store.list_auth_periods(client_id)
    return {
        **_client_json(client, periods, today),
        "periods": [{**_period_json(p, today), **_period_extras(p)} for p in periods],
        "trends": _assessment_trends(periods),
    }


class NewPeriod(BaseModel):
    period_start: date
    period_end: date


@router.post("/{client_id}/periods", status_code=201)
def create_period(client_id: str, body: NewPeriod) -> dict:
    _active_client(client_id)
    if body.period_end <= body.period_start:
        raise HTTPException(422, "The period must end after it starts.")
    period_id = store.create_auth_period(client_id, body.period_start.isoformat(), body.period_end.isoformat())
    period = store.get_auth_period(period_id)
    return {**_period_json(period, date.today()), **_period_extras(period)}


@router.post("/{client_id}/archive")
def archive_client(client_id: str) -> dict:
    """Take a client off the active roster. Their records are kept."""
    _active_client(client_id)
    store.update_client(client_id, status="discharged")
    return {"ok": True}
