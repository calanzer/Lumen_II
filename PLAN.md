# Multi-Client BCBA Workflow Redesign

## Problem
The current app is a linear single-session wizard (Upload → Review → Generate → Export).
A real BCBA manages 15-30+ clients, each with 6-month auth periods, and needs to:
- See which clients need reauth soon
- Upload reports across multiple days
- Resume work-in-progress
- Compare current period to prior periods
- Process multiple clients per week

## Design

### Database (SQLite via `data/store.py`)

```sql
-- Clients the BCBA manages
CREATE TABLE clients (
    id TEXT PRIMARY KEY,           -- UUID
    client_identifier TEXT,        -- e.g. "CR-2024-0847" (their practice ID)
    display_name TEXT NOT NULL,    -- e.g. "Martinez, A." (de-identified)
    diagnosis_codes TEXT,          -- JSON array: ["F84.0", "F80.2"]
    date_of_birth TEXT,            -- for age calc (optional)
    payor TEXT DEFAULT 'anthem_blue_cross_ca',
    status TEXT DEFAULT 'active',  -- active | discharged | on_hold
    created_at TEXT,
    updated_at TEXT
);

-- One row per authorization period per client
CREATE TABLE auth_periods (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    period_start TEXT NOT NULL,    -- YYYY-MM-DD
    period_end TEXT NOT NULL,
    status TEXT DEFAULT 'draft',   -- draft | in_progress | generated | exported | submitted
    -- Stored as JSON blobs (the Pydantic models serialized)
    extracted_data TEXT,           -- ExtractedClinicalData JSON
    narrative_data TEXT,           -- AnthemReauthNarrative JSON
    validation_result TEXT,        -- validate_completeness() result JSON
    -- Tracking
    uploaded_filename TEXT,
    uploaded_at TEXT,
    extracted_at TEXT,
    generated_at TEXT,
    exported_at TEXT,
    notes TEXT,                    -- BCBA freeform notes
    created_at TEXT,
    updated_at TEXT
);
```

### New Page Structure

```
app.py                    → Dashboard (home page, no more login-only landing)
pages/
  1_Clients.py            → Client list + add/edit clients
  2_Client_Detail.py      → Single client: auth period history, trends
  3_Upload.py             → Upload report for selected client/period
  4_Review_Data.py        → Edit extracted data (existing, now loads from DB)
  5_Generate.py           → Generate narrative (existing, now with prior period comparison)
  6_Export.py             → Export (existing, saves to DB on export)
```

### Data Flow

1. **Dashboard (app.py)**: Query all clients + their latest auth_period. Show table:
   - Client name | Payor | Auth expires | Status | Last updated | Action button
   - Sort by auth expiration (soonest first)
   - Color code: red (<14 days), yellow (<30 days), green (>30 days)
   - "New Client" button

2. **Clients page**: CRUD for clients. Minimal: name, dx codes, payor.

3. **Client Detail page**: Selected client's history.
   - All auth periods in reverse chronological order
   - For each: status badge, dates, quick actions (resume, view, export)
   - Assessment score trends across periods (if multiple exist)
   - "+ New Auth Period" button → goes to Upload

4. **Upload page**: Now scoped to a specific client + auth period.
   - Select existing client (or create new)
   - Upload document → extract → save extraction to auth_periods.extracted_data
   - Auto-advances to Review

5. **Review page**: Loads from DB instead of session state.
   - "Save" writes back to auth_periods.extracted_data
   - Can close browser and come back

6. **Generate page**: Loads from DB.
   - If prior auth period exists, shows prior assessment scores for comparison
   - Saves narrative to auth_periods.narrative_data
   - Updates status to "generated"

7. **Export page**: Loads from DB.
   - Saves exported_at timestamp
   - Updates status to "exported"

### Session State → DB Migration

All `st.session_state.clinical_data` / `st.session_state.narrative` usage
gets replaced with DB reads/writes via a `data/store.py` module:

```python
# data/store.py - Key functions
def init_db()
def create_client(name, dx_codes, payor) -> client_id
def list_clients() -> list[dict]
def get_client(client_id) -> dict
def create_auth_period(client_id, start, end) -> period_id
def list_auth_periods(client_id) -> list[dict]
def get_auth_period(period_id) -> dict
def save_extraction(period_id, clinical_data, filename)
def save_narrative(period_id, narrative)
def save_export(period_id)
def get_dashboard_data() -> list[dict]  # clients + latest period joined
```

### What stays the same
- All pipeline/ code (extractor, generator, validator, exporter, classifier)
- All schemas/ (clinical_data.py, narrative.py)
- All prompts/
- All templates/
- All tests/ (add new DB tests)
- Authentication (streamlit-authenticator)

### Implementation Order
1. Create data/store.py with SQLite operations
2. Rewrite app.py as dashboard
3. Create pages/1_Clients.py
4. Create pages/2_Client_Detail.py
5. Update pages/3_Upload.py to use DB
6. Update pages/4_Review_Data.py to use DB
7. Update pages/5_Generate.py to use DB + prior period comparison
8. Update pages/6_Export.py to use DB
9. Add tests for store.py
10. Run full test suite, push
