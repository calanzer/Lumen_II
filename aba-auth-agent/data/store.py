"""SQLite persistence layer for multi-client ABA reauthorization workflow.

Stores clients, auth periods, extracted clinical data, and generated narratives.
All JSON-serialized Pydantic models are stored as TEXT columns.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import AnthemReauthNarrative

DB_PATH = Path(__file__).parent / "aba_auth.db"


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def get_db():
    """Context manager for database connections with WAL mode."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                client_identifier TEXT,
                display_name TEXT NOT NULL,
                diagnosis_codes TEXT DEFAULT '[]',
                date_of_birth TEXT,
                payor TEXT DEFAULT 'anthem_blue_cross_ca',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_periods (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                extracted_data TEXT,
                narrative_data TEXT,
                validation_result TEXT,
                uploaded_filename TEXT,
                uploaded_at TEXT,
                extracted_at TEXT,
                generated_at TEXT,
                exported_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_auth_periods_client
                ON auth_periods(client_id);
            CREATE INDEX IF NOT EXISTS idx_auth_periods_status
                ON auth_periods(status);
            CREATE INDEX IF NOT EXISTS idx_clients_status
                ON clients(status);
        """)


# ── Client CRUD ──────────────────────────────────────────────────────

def create_client(
    display_name: str,
    client_identifier: Optional[str] = None,
    diagnosis_codes: Optional[list[str]] = None,
    payor: str = "anthem_blue_cross_ca",
) -> str:
    """Create a new client. Returns client ID."""
    client_id = _new_id()
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO clients (id, client_identifier, display_name, diagnosis_codes, payor, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (client_id, client_identifier, display_name, json.dumps(diagnosis_codes or []), payor, now, now),
        )
    return client_id


def update_client(client_id: str, **kwargs):
    """Update client fields. Pass field=value pairs."""
    allowed = {"display_name", "client_identifier", "diagnosis_codes", "date_of_birth", "payor", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    if "diagnosis_codes" in updates and isinstance(updates["diagnosis_codes"], list):
        updates["diagnosis_codes"] = json.dumps(updates["diagnosis_codes"])
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [client_id]
    with get_db() as conn:
        conn.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", values)


def get_client(client_id: str) -> Optional[dict]:
    """Get a single client by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["diagnosis_codes"] = json.loads(d["diagnosis_codes"]) if d["diagnosis_codes"] else []
    return d


def list_clients(status: str = "active") -> list[dict]:
    """List all clients with the given status."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM clients WHERE status = ? ORDER BY display_name", (status,)
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["diagnosis_codes"] = json.loads(d["diagnosis_codes"]) if d["diagnosis_codes"] else []
        result.append(d)
    return result


def delete_client(client_id: str):
    """Delete a client and all their auth periods."""
    with get_db() as conn:
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))


# ── Auth Period CRUD ─────────────────────────────────────────────────

def create_auth_period(
    client_id: str,
    period_start: str,
    period_end: str,
) -> str:
    """Create a new auth period for a client. Returns period ID."""
    period_id = _new_id()
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO auth_periods (id, client_id, period_start, period_end, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'draft', ?, ?)""",
            (period_id, client_id, period_start, period_end, now, now),
        )
    return period_id


def get_auth_period(period_id: str) -> Optional[dict]:
    """Get a single auth period by ID, with deserialized JSON fields."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM auth_periods WHERE id = ?", (period_id,)).fetchone()
    if row is None:
        return None
    return _deserialize_period(dict(row))


def list_auth_periods(client_id: str) -> list[dict]:
    """List all auth periods for a client, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM auth_periods WHERE client_id = ? ORDER BY period_end DESC",
            (client_id,),
        ).fetchall()
    return [_deserialize_period(dict(row)) for row in rows]


def get_prior_period(client_id: str, current_period_id: str) -> Optional[dict]:
    """Get the auth period immediately before the current one (for comparison)."""
    current = get_auth_period(current_period_id)
    if not current:
        return None
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM auth_periods
               WHERE client_id = ? AND id != ? AND period_end <= ?
               ORDER BY period_end DESC LIMIT 1""",
            (client_id, current_period_id, current["period_start"]),
        ).fetchone()
    if row is None:
        return None
    return _deserialize_period(dict(row))


def _deserialize_period(d: dict) -> dict:
    """Deserialize JSON fields in an auth_period row."""
    if d.get("extracted_data"):
        try:
            d["extracted_data_parsed"] = ExtractedClinicalData.model_validate_json(d["extracted_data"])
        except Exception:
            d["extracted_data_parsed"] = None
    else:
        d["extracted_data_parsed"] = None

    if d.get("narrative_data"):
        try:
            d["narrative_data_parsed"] = AnthemReauthNarrative.model_validate_json(d["narrative_data"])
        except Exception:
            d["narrative_data_parsed"] = None
    else:
        d["narrative_data_parsed"] = None

    if d.get("validation_result"):
        try:
            d["validation_result_parsed"] = json.loads(d["validation_result"])
        except Exception:
            d["validation_result_parsed"] = None
    else:
        d["validation_result_parsed"] = None

    return d


# ── Save pipeline outputs ────────────────────────────────────────────

def save_extraction(
    period_id: str,
    clinical_data: ExtractedClinicalData,
    filename: str,
    validation_result: Optional[dict] = None,
):
    """Save extracted clinical data to an auth period."""
    now = _now()
    with get_db() as conn:
        conn.execute(
            """UPDATE auth_periods
               SET extracted_data = ?, validation_result = ?,
                   uploaded_filename = ?, extracted_at = ?,
                   status = CASE WHEN status = 'draft' THEN 'in_progress' ELSE status END,
                   updated_at = ?
               WHERE id = ?""",
            (
                clinical_data.model_dump_json(),
                json.dumps(validation_result) if validation_result else None,
                filename,
                now,
                now,
                period_id,
            ),
        )


def save_clinical_data(period_id: str, clinical_data: ExtractedClinicalData, validation_result: Optional[dict] = None):
    """Save edited clinical data (from Review page)."""
    now = _now()
    with get_db() as conn:
        conn.execute(
            """UPDATE auth_periods
               SET extracted_data = ?, validation_result = ?, updated_at = ?
               WHERE id = ?""",
            (
                clinical_data.model_dump_json(),
                json.dumps(validation_result) if validation_result else None,
                now,
                period_id,
            ),
        )


def save_narrative(period_id: str, narrative: AnthemReauthNarrative):
    """Save generated/edited narrative."""
    now = _now()
    with get_db() as conn:
        conn.execute(
            """UPDATE auth_periods
               SET narrative_data = ?, generated_at = ?,
                   status = 'generated', updated_at = ?
               WHERE id = ?""",
            (narrative.model_dump_json(), now, now, period_id),
        )


def save_export(period_id: str):
    """Mark an auth period as exported."""
    now = _now()
    with get_db() as conn:
        conn.execute(
            """UPDATE auth_periods
               SET exported_at = ?, status = 'exported', updated_at = ?
               WHERE id = ?""",
            (now, now, period_id),
        )


def update_period_notes(period_id: str, notes: str):
    """Save BCBA notes on an auth period."""
    with get_db() as conn:
        conn.execute(
            "UPDATE auth_periods SET notes = ?, updated_at = ? WHERE id = ?",
            (notes, _now(), period_id),
        )


# ── Dashboard query ──────────────────────────────────────────────────

def get_dashboard_data() -> list[dict]:
    """
    Get all active clients with their most recent auth period info.
    Returns list sorted by auth expiration (soonest first).
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                c.id AS client_id,
                c.display_name,
                c.client_identifier,
                c.diagnosis_codes,
                c.payor,
                ap.id AS period_id,
                ap.period_start,
                ap.period_end,
                ap.status AS period_status,
                ap.updated_at AS period_updated,
                ap.uploaded_filename
            FROM clients c
            LEFT JOIN auth_periods ap ON ap.id = (
                SELECT id FROM auth_periods
                WHERE client_id = c.id
                ORDER BY period_end DESC
                LIMIT 1
            )
            WHERE c.status = 'active'
            ORDER BY
                CASE WHEN ap.period_end IS NULL THEN '9999-12-31' ELSE ap.period_end END ASC,
                c.display_name ASC
        """).fetchall()

    result = []
    today = date.today().isoformat()
    for row in rows:
        d = dict(row)
        d["diagnosis_codes"] = json.loads(d["diagnosis_codes"]) if d["diagnosis_codes"] else []

        # Calculate urgency
        if d["period_end"]:
            days_remaining = (date.fromisoformat(d["period_end"]) - date.today()).days
            d["days_until_expiry"] = days_remaining
            if days_remaining < 0:
                d["urgency"] = "expired"
            elif days_remaining <= 14:
                d["urgency"] = "critical"
            elif days_remaining <= 30:
                d["urgency"] = "soon"
            else:
                d["urgency"] = "ok"
        else:
            d["days_until_expiry"] = None
            d["urgency"] = "no_period"

        result.append(d)

    return result


# Auto-initialize on import
init_db()
