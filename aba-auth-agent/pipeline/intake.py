"""Turn a dropped-in progress report into a client, an authorization period and a draft.

The goal is that a BCBA drops a file and nothing else needs clicking. This module reads
the payor, client and period from the extracted report, matches or creates the records,
and says what (if anything) is still missing, so the page only ever asks about the
things it genuinely could not read.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from data import store
from pipeline.exporter import list_available_payors
from pipeline.validator import validate_completeness
from schemas.clinical_data import ExtractedClinicalData

# Words that identify a payor in report text, keyed by the registry in pipeline.exporter.
# Longer phrases first within a payor; payors are checked in this order.
PAYOR_ALIASES: dict[str, tuple[str, ...]] = {
    "blue_shield_ca": ("blue shield",),
    "medi_cal": ("medi cal", "medicaid"),
    "anthem_blue_cross_ca": ("anthem", "elevance", "blue cross"),
    "aetna": ("aetna", "evernorth"),
    "optum": ("optum", "unitedhealthcare", "united healthcare", "uhc"),
}

DEFAULT_PERIOD_DAYS = 182

# What the page has to ask for when the report doesn't say
ASK_CLIENT = "client"
ASK_PAYOR = "payor"
ASK_PERIOD = "period"


def detect_payor_key(text: Optional[str]) -> Optional[str]:
    """The registry key for a payor named in free text, or None if unrecognized."""
    if not text:
        return None
    normalized = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "
    for key, aliases in PAYOR_ALIASES.items():
        if any(f" {alias} " in normalized for alias in aliases):
            return key
    return None


def _norm_id(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def find_client(clients: list[dict], identifier: Optional[str]) -> Optional[dict]:
    """The existing client whose practice ID (or display name) equals the report's client ID."""
    wanted = _norm_id(identifier)
    if not wanted:
        return None
    for client in clients:
        if wanted in (_norm_id(client.get("client_identifier")), _norm_id(client.get("display_name"))):
            return client
    return None


def find_period(periods: list[dict], start: date, end: date) -> Optional[dict]:
    """An existing period with exactly these dates."""
    for period in periods:
        if str(period["period_start"]) == start.isoformat() and str(period["period_end"]) == end.isoformat():
            return period
    return None


@dataclass
class ImportPlan:
    """What the report told us, and what is still unknown."""
    client: Optional[dict] = None  # existing client matched by the report's client ID
    client_identifier: Optional[str] = None  # the ID as written in the report
    payor_key: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    questions: list[str] = field(default_factory=list)  # ASK_* values still needed
    notes: list[str] = field(default_factory=list)  # decisions worth telling the BCBA about


def build_plan(data: ExtractedClinicalData, clients: list[dict]) -> ImportPlan:
    """Decide client, payor and period from the extracted report."""
    plan = ImportPlan()
    info = data.client

    # Client
    plan.client_identifier = (info.client_id or "").strip() or None
    plan.client = find_client(clients, plan.client_identifier)
    if plan.client is None and not plan.client_identifier:
        plan.questions.append(ASK_CLIENT)

    # Payor: an existing client keeps theirs; otherwise read it from the report
    if plan.client is not None:
        plan.payor_key = plan.client.get("payor")
    else:
        plan.payor_key = detect_payor_key(info.payor_name)
        if plan.payor_key is None:
            plan.questions.append(ASK_PAYOR)
        elif plan.client_identifier:
            plan.notes.append(f"Payor read from the report: {info.payor_name}.")

    # Period: the authorization period, else the period the report covers
    if info.auth_period_start and info.auth_period_end:
        plan.period_start, plan.period_end = info.auth_period_start, info.auth_period_end
    elif info.report_period_start and info.report_period_end:
        plan.period_start, plan.period_end = info.report_period_start, info.report_period_end
        plan.notes.append(
            "The report doesn't state an authorization period, so the period it covers "
            f"({plan.period_start:%m/%d/%Y} to {plan.period_end:%m/%d/%Y}) was used."
        )
    else:
        plan.questions.append(ASK_PERIOD)
    return plan


@dataclass
class Answers:
    """The BCBA's replies to whatever the plan could not read."""
    existing_client_id: Optional[str] = None  # chose an existing client
    new_identifier: Optional[str] = None  # or typed a new client's ID
    payor_key: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


@dataclass
class ImportResult:
    client_id: str
    period_id: str
    client_created: bool
    period_reused: bool
    payor_key: str
    data: ExtractedClinicalData  # the report's data plus anything the BCBA told us
    validation: dict
    notes: list[str] = field(default_factory=list)


def _without_answered(missing_fields: list[str], data: ExtractedClinicalData) -> list[str]:
    """Drop 'missing' notes for client fields that now have a value."""
    info = data.client
    answered = {
        "client_id": bool(info.client_id),
        "client id": bool(info.client_id),
        "payor": bool(info.payor_name),
        "auth_period": bool(info.auth_period_start and info.auth_period_end),
        "auth period": bool(info.auth_period_start and info.auth_period_end),
        "authorization period": bool(info.auth_period_start and info.auth_period_end),
    }
    kept = []
    for note in missing_fields:
        lowered = note.lower()
        if any(done and token in lowered for token, done in answered.items()):
            continue
        kept.append(note)
    return kept


def default_period(today: Optional[date] = None) -> tuple[date, date]:
    start = today or date.today()
    return start, start + timedelta(days=DEFAULT_PERIOD_DAYS)


def apply_import(
    plan: ImportPlan,
    data: ExtractedClinicalData,
    filename: str,
    validation: dict,
    answers: Optional[Answers] = None,
) -> ImportResult:
    """Create or match the client and period, and save the extraction onto the period."""
    answers = answers or Answers()
    notes = list(plan.notes)

    # Client
    client = plan.client
    if client is None and answers.existing_client_id:
        client = store.get_client(answers.existing_client_id)
    created = False
    if client is None:
        identifier = plan.client_identifier or (answers.new_identifier or "").strip()
        if not identifier:
            raise ValueError("A client ID is needed to create the client.")
        payor_key = plan.payor_key or answers.payor_key
        if payor_key is None:
            raise ValueError("A payor is needed to create the client.")
        client_id = store.create_client(
            display_name=identifier,
            client_identifier=identifier,
            diagnosis_codes=list(data.client.diagnosis_codes),
            payor=payor_key,
        )
        created = True
        notes.append(f"New client created: {identifier}. You can rename them on the Clients page.")
    else:
        client_id = client["id"]
        payor_key = client.get("payor") or plan.payor_key or "anthem_blue_cross_ca"

    # Period
    start = plan.period_start or answers.period_start
    end = plan.period_end or answers.period_end
    if start is None or end is None:
        raise ValueError("Authorization period dates are needed.")
    existing = find_period(store.list_auth_periods(client_id), start, end)
    if existing:
        period_id = existing["id"]
        notes.append("This period already existed, so its data was replaced with this report.")
    else:
        period_id = store.create_auth_period(client_id, start.isoformat(), end.isoformat())

    # What the BCBA told us belongs in the data too, so the draft, the export header and the
    # completeness check all see it. Only explicit answers fill the authorization period:
    # a period borrowed from the report's own dates is not an authorization period.
    data = data.model_copy(deep=True)
    identifier = (client or {}).get("client_identifier") or plan.client_identifier or (answers.new_identifier or "").strip()
    if not data.client.client_id and identifier:
        data.client.client_id = identifier
    if not data.client.payor_name and answers.payor_key:
        data.client.payor_name = list_available_payors().get(answers.payor_key, {}).get("display_name")
    if answers.period_start and answers.period_end and not (data.client.auth_period_start and data.client.auth_period_end):
        data.client.auth_period_start, data.client.auth_period_end = answers.period_start, answers.period_end
    data.missing_fields = _without_answered(data.missing_fields, data)
    validation = validate_completeness(data)

    store.save_extraction(period_id, data, filename, validation)
    return ImportResult(
        client_id=client_id,
        period_id=period_id,
        client_created=created,
        period_reused=existing is not None,
        payor_key=payor_key,
        data=data,
        validation=validation,
        notes=notes,
    )


# -- Narrative drafting ----------------------------------------------

def source_hash(data: ExtractedClinicalData) -> str:
    """Fingerprint of the data a narrative was written from, to spot a stale draft."""
    return hashlib.sha256(data.model_dump_json().encode()).hexdigest()[:16]


def is_stale(narrative, data: ExtractedClinicalData) -> bool:
    """True if the data changed since this narrative was drafted."""
    recorded = getattr(narrative, "source_hash", None)
    return bool(recorded) and recorded != source_hash(data)


def draft_narrative(data: ExtractedClinicalData, payor_key: str):
    """Draft the narrative the way the Generate page would: the practice's template for
    this payor if there is one, else the built-in layout."""
    from pipeline.generator import generate_custom_narrative, generate_narrative

    payor_name = list_available_payors().get(payor_key, {}).get("display_name", payor_key)
    template = store.get_active_template(payor_key)
    if template:
        narrative = generate_custom_narrative(data, template, payor_name, payor_key)
    else:
        narrative = generate_narrative(data, payor_name)
    narrative.source_hash = source_hash(data)
    return narrative
