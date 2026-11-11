# Streamlit → React parity checklist

Status: complete, and the Streamlit app has been removed. Kept as a record of what was carried over.

Goal was: every workflow of the old Streamlit app works in the new React interface. `[x]` means built **and** covered by a test that fails when the behavior is
removed (checked by breaking each one on purpose). "Replaced" means the old workflow is
intentionally done differently, with the reason.

Also checked by hand in the browser on a throwaway database: Review autosave (blank saved as
unknown), Generate with the real model (background job, cross-check, draft saved, not stale),
Export (real Word file, period marked exported), template analysis of a fictional past report,
and every new screen at phone width (no sideways scrolling).

## Import / Upload (`0_Import.py`, `3_Upload.py`)
- [x] Drop a PDF/DOCX → extract, match/create client + period, draft, cross-check
- [x] Ask only for what the report left out (client, payor, period)
- [x] Result links straight to Review and to the draft
- replaced: manual "select client / period, then Extract" — the import does it from the report

## Clients (`1_Clients.py`)
- [x] Table, search/sort, deadline badges, add client, archive, double-click for details

## Client details (`2_Client_Detail.py`)
- [x] Header: name, client ID, diagnosis codes, payor
- [x] Create a new authorization period (dates prefilled, end must be after start)
- [x] Period list with status, deadline, source file, extracted/exported dates
- [x] Completeness, missing and warning counts; counts of assessments/targets/behaviors/goals/hours
- [x] Narrative confidence and flag count
- [x] BCBA notes per period (save only when changed, errors shown)
- [x] Per-period actions: Review data · Generate · Export, each shown only when it applies
- [x] VB-MAPP trend table across periods
- dropped: client "Status" tile (the roster is active clients only; archived ones are hidden)

## Review data (`4_Review_Data.py`)
- [x] Completeness banner, missing fields, warnings
- [x] 1 Demographics · 2 Assessments (incl. domain scores, previous score/date) · 3 Skill targets · 4 Behavior targets (incl. reduction %) · 5 Hours (auto utilization, low-utilization explanation) · 6 Treatment goals (rationale required when modified/discontinued) · 7 Caregiver · 8 Discharge · 9 Requested hours + justification
- [x] Add and remove items; other items keep their open/closed state
- [x] Unknown stays unknown: a cleared box is saved as empty, never 0; half-typed numbers aren't rewritten; out-of-range values explained
- [x] Autosave with visible state, Save now, saved on leaving the page, warning before closing the tab with unsaved edits
- [x] A refused save keeps the edits and says why
- [x] Server re-validates every save and returns the new completeness and whether the draft is now stale
- [x] Confidence notes and missing-fields lists
- [x] Raw JSON editor (invalid JSON explained; applied JSON is saved and validated)
- [x] Continue to Generate

## Generate (`5_Generate.py`)
- [x] Progress since prior authorization (mastered delta, target counts, behavior trends)
- [x] Incomplete-data warning
- [x] Button names the payor and says which layout (template or built-in)
- [x] Runs in the background with progress; survives leaving the page; one at a time per period
- [x] Cross-check result shown, including "could not run" (never shown as "no discrepancies")
- [x] A failed draft leaves the previous one untouched and says so
- [x] Stale-draft warning
- [x] Per-section side-by-side: source data left, editable text right
- [x] Word-count hints (<50, >400), needs-review badge and note, flags list
- [x] Autosave + Save all edits
- [x] Regenerating asks first, and pending edits can't overwrite the new draft
- [x] Continue to Export

## Export (`6_Export.py`)
- [x] Stale warning; confidence / flags / sections-needing-review summary
- [x] Payor choice (fixed for template-driven narratives, enforced by the server)
- [x] Accuracy confirmation gates the export (server requires it too)
- [x] Download .docx (filename sanitized), period marked exported
- [x] Mark as submitted — only after exported

## Templates (`7_Templates.py`)
- [x] Per payor: current template (name, sections, style) or built-in default; reset to default
- [x] Upload past report → analyze → editable sections (rename, describe, reorder, add, delete), style notes, name → save
- [x] Discard draft; "at least two sections" and name validation (client and server)
- [x] A separate in-progress draft per payor

## Cross-cutting
- [x] Every screen reachable from the sidebar and from client details; period screens have addresses (`/periods/:id/review|generate|export`)
- [x] Sidebar Review / Generate / Export open the period worked on last, or ask to choose a client
- [x] Errors in plain words, including "can't reach the server"
- [x] Phone layout: no horizontal scrolling on any new screen
- [x] Database access no longer freezes when the browser makes several requests at once (SQLite 3.51.0 deadlock, found while testing)

## Not carried over, on purpose
- Streamlit's Dashboard page (removed earlier at your request)
- The separate Upload page (the import flow replaces it)

## Still open (not parity)
- Source-linked review (value shown beside the passage of the report it came from) needs the uploaded file kept — see Open decisions in `DESIGN.md`
- No code splitting yet: the app is one 500 kB+ file, fine on a local network
