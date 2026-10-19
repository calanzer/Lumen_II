# Caseload Tracker + Report Writer: v1 Spec

## 1. Summary

A local-first web app for a single BCBA (Board Certified Behavior Analyst). It runs in her browser, stores everything on her laptop, and makes no network requests.

Two modules:

- **Caseload Tracker**: shows whether she is seeing every client and supervising every technician enough, and what to do this week to stay on pace.
- **Report Writer**: takes a Word report template plus session data and produces a Word report with everything computable filled in and everything that needs her judgment left as yellow-highlighted placeholders.

This replaces a personal spreadsheet she maintains today because her employer's practice management system does not answer "am I seeing everyone enough?"

## 2. User and context

- One user: a BCBA employed by an ABA therapy provider. Non-technical. Works on a laptop in Chrome or Edge.
- Assumed caseload: 8 to 20 clients, 5 to 15 technicians (RBTs). Confirm with her.
- Her employer uses a practice management system that can export reports as CSV or XLSX. This app never connects to that system. Data arrives by file import or manual entry.

### Glossary

| Term | Meaning |
|---|---|
| BCBA | Supervising clinician. The user. |
| RBT | Registered Behavior Technician. Delivers most direct therapy, supervised by the BCBA. |
| Authorization | An insurer's approval of a number of hours or units per service type for one client over a date range. |
| Service type | Billing category for a session. Common CPT codes: 97153 (direct therapy by technician), 97155 (BCBA protocol modification, often used for supervision), 97156 (parent training), 97151 (assessment). Must be configurable. |
| Unit | Billing increment, usually 15 minutes. Authorizations may be stated in units or hours. |
| Utilization | Delivered hours divided by authorized hours. |
| Reassessment | Periodic report the BCBA writes to renew an authorization. |

## 3. Hard constraints

1. **No network.** After the app loads, it makes zero outbound requests. Enforce with a Content Security Policy (`connect-src 'none'`). Bundle every asset: no CDNs, web fonts, analytics, or error reporting.
2. **Local storage only.** Working data lives in IndexedDB. Call `navigator.storage.persist()` on first run.
3. **Data file.** She can save all data to a single file on disk and open it again (like a spreadsheet file). Where the File System Access API is available, autosave to the chosen file. Otherwise provide Export and Import buttons. Show "last saved" time and remind her if no backup has been made in 7 days.
4. **Works offline**, fully.
5. **One-click start.** She must be able to launch it without a terminal or developer tools. Options, in order of preference; test before choosing and document the choice:
   - A single self-contained `index.html` she double-clicks. Verify IndexedDB persistence and file pickers work from `file://` in current Chrome and Edge.
   - An installable PWA served from a static host, fully offline after first load.
   - A small double-click launcher that serves the build on `localhost`.
6. **No AI or LLM calls in v1.** Sending client data to a cloud model would break constraint 1. All import mapping and report generation is deterministic.
7. **Data minimization.** Clients are identified by a code she chooses, not by name. On import, let her exclude columns, and warn when a column looks like a full name, date of birth, address, or member ID.

## 4. Data model

All entities have `id`, `createdAt`, `updatedAt`. Soft-delete with undo.

- **Client**: `code` (unique, required), `status` (active, paused, discharged), `location` (home, clinic, school, other), `notes`, `tags[]`, `customFields{}`.
- **Authorization**: `clientId`, `serviceTypeId`, `amount`, `amountUnit` (hours or units), `startDate`, `endDate`, `payer` (free text), `notes`.
- **ServiceType**: `code` (e.g. 97153), `label`, `minutesPerUnit` (default 15), `countsAsRbtDirect` (bool), `countsAsSupervision` (bool), `deliveredBy` (BCBA, RBT, either).
- **StaffMember**: `displayName` or code, `role` (BCBA, RBT, other), `targetWeeklyHours`, `active`.
- **Assignment**: `clientId`, `staffId`, `startDate`, `endDate`. Which technicians work with which clients.
- **Session**: `clientId`, `staffId`, `serviceTypeId`, `date`, `startTime`, `endTime`, `durationMinutes`, `status` (scheduled, completed, cancelled, no-show), `cancelledBy` (client, staff, provider, unknown), `cancelNoticeHours`, `supervisedStaffId` (optional), `observation` (bool), `source` (import or manual), `importBatchId`.
- **Deadline**: `clientId` (optional), `type` (auth expiry, reassessment due, custom), `dueDate`, `status` (open, done), `notes`. Auth expiry deadlines are generated automatically from authorizations.
- **ImportProfile**: saved column mapping for a given export layout: `name`, `targetEntity`, `columnMap{}`, `valueMaps{}` (e.g. status text to status enum), `dateFormat`.
- **ImportBatch**: `fileName`, `importedAt`, `profileId`, row counts (added, updated, skipped). Supports undo of a whole batch.
- **ReportTemplate**: `name`, `fileBlob` (.docx), `detectedTokens[]`.
- **GeneratedReport**: `templateId`, `clientId`, `periodStart`, `periodEnd`, `generatedAt`, `placeholderCount`, `fileBlob`.
- **GoalDataPoint** (optional, for reports): `clientId`, `goalName`, `date`, `measure`, `value`.
- **Settings**: BCBA name and credential, pacing thresholds, supervision rules, week start day, default report period.

**Custom fields are required.** Her existing spreadsheet is the source of truth for what she tracks. Any column in it that this model lacks must be representable as a custom field on Client, shown in the caseload table, sortable and filterable.

## 5. Module A: Caseload Tracker

### A1. Import

- Accept CSV and XLSX. Target entities: sessions, authorizations, clients, staff, goal data.
- Mapping screen: show the first 20 rows, let her map each column to a field or mark it "ignore". Pre-fill guesses with header-name heuristics (no AI).
- Map values as well as columns (e.g. "Cancelled - Client" to status cancelled, cancelledBy client).
- Save the mapping as an ImportProfile and auto-apply it when the same headers appear again.
- Re-importing must not duplicate. Match sessions on client + staff + date + start time + service type, and update status and duration when they change.
- Show a preview summary (added, updated, skipped, errors with row numbers) before committing. Each batch can be undone.
- One-time import of her existing tracker spreadsheet, mapping unknown columns to custom fields.

### A2. Caseload board (home screen)

One row per active client and authorized service type. Columns:

- Client code, service type, authorization period
- Authorized, delivered, remaining (hours; toggle to units)
- **Pace**: delivered divided by expected-to-date, where expected-to-date = authorized x (days elapsed / days in period)
- **Needed per week** to finish on time: remaining / weeks remaining
- **Projected utilization** at period end: (delivered + scheduled future) / authorized
- Days since the BCBA last saw the client
- Status chip

Status rules (thresholds configurable in Settings):

- Green: pace at or above 95%
- Yellow: 85% to 95%
- Red: below 85%
- Over: delivered + scheduled exceeds authorized. This must be visually distinct, since over-delivery is unbillable.
- Not seen: no completed BCBA session in more than N days (default 14)

Status must never rely on color alone: include an icon and text label. Sort and filter by any column; default sort is worst status first. A summary strip at the top shows counts by status and total hours behind.

### A3. Client detail

- All authorizations with a progress bar per service type
- Session history (filterable), with cancellations marked
- Assigned technicians
- Deadlines, notes, custom fields
- A "Generate report" shortcut into Module B

### A4. Supervision tracker

Per technician, per calendar month:

- Direct hours: completed sessions with `countsAsRbtDirect`
- Supervised hours: time the BCBA supervised that technician. Derive it two ways and let her override:
  1. Explicit: a session with `supervisedStaffId` set.
  2. Inferred: a BCBA session with `countsAsSupervision` that overlaps in time with that technician's session for the same client. Count the overlap duration.
- Supervision percent = supervised / direct. Target default 5%, configurable.
- Contacts this month (default minimum 2) and observations (default minimum 1), with manual checkboxes when the data cannot show it.
- **Projection**: given the technician's scheduled direct hours for the rest of the month, how many more supervision hours are needed, and by when.
- Status chip using the same green, yellow, red convention.

Supervision rules vary by credentialing body, insurer, and employer. Every number here is a setting with a sensible default, never a hard-coded rule.

### A5. Deadlines

- A list sorted by due date with windows at 30, 14, and 7 days and overdue.
- Auto-generated: authorization expiry, plus a reassessment-due deadline N days before expiry (default 30, configurable per payer).
- Custom deadlines she adds herself. Mark done, snooze, add notes.

### A6. This Week

The screen she opens on Monday. A prioritized, plain-language action list computed from A2, A4, and A5. Examples:

- "K7 is 3.5 hours behind on 97155. Add about 1.25 hours a week for the next 6 weeks."
- "RBT M.R. needs 1.5 more supervision hours by Oct 31. Overlap opportunities: Tue 3 to 5 pm with K7, Thu 4 to 6 pm with C3." (taken from that technician's scheduled sessions)
- "Authorization for C3 expires in 21 days. Reassessment report not started."
- "B2 not seen in 19 days."

Each item links to the relevant detail screen and can be checked off or dismissed for the week. Include a read-only week calendar of her scheduled sessions so she can see open time.

### A7. Manual entry

Full create, edit, and delete for every entity, plus a quick-add session form (client, service type, date, start, duration, status) usable in under 10 seconds. Imported records are editable; manual edits survive re-import unless she chooses to overwrite.

### A8. Cancellations

A log of cancelled and no-show sessions with filters, plus simple rollups: rate by client, by weekday, by who cancelled, and hours lost this month. Mark a cancellation as "made up" by linking it to a later session.

### A9. Backup, export, delete

- Save or open the full data file (see constraint 3). Optional passphrase encryption using WebCrypto (AES-GCM with a PBKDF2-derived key).
- Export any table view to CSV or XLSX.
- A "Delete all data" action with typed confirmation.

## 6. Module B: Report Writer

### B1. Inputs

1. **Template**: a `.docx` file she uploads, normally her employer's or an insurer's progress or reassessment report format. Stored in the template library.
2. **Session data**: from the app database for the chosen client and period. She may also import a fresh export on the spot.
3. **Goal data** (optional): CSV or XLSX in long format (date, goal, measure, value), imported through the same mapping flow.
4. **Parameters**: client, period start and end, report date.

### B2. Template tokens

Templates are ordinary Word documents with tokens in the text. Formatting around a token is preserved.

- `{{token_name}}`: replaced with a computed value.
- `{{TODO: instruction text}}`: always becomes a yellow-highlighted placeholder containing the instruction text. This is how the template author marks sections that need clinical judgment.
- Table and loop tokens for repeating rows, using the syntax of the chosen docx library. Document the syntax in the user guide.
- Chart tokens insert a PNG rendered locally.

**The highlight rule**, which is the core requirement:

- Any `TODO` token becomes yellow-highlighted text.
- Any token the app cannot fill (unknown name, or no data for it) becomes yellow-highlighted text reading `[MISSING: token_name]`. Generation never fails because of a missing value and never silently leaves a blank.
- Use true Word highlighting (`w:highlight` with value `yellow`) so she can clear it with Word's highlighter. Do not use shading or colored text.
- Auto-filled values are not highlighted by default. Provide a setting, "mark auto-filled values", that highlights them in a different color (e.g. cyan) for reviewing.
- Where data exists that would help her write a narrative section, include it inside the placeholder. Example: `[SUMMARIZE PROGRESS. Goal 2: baseline 20%, current 65%, 14 sessions]`, highlighted yellow.

### B3. Token catalog (minimum)

- Identity: `client_code`, `report_date`, `period_start`, `period_end`, `bcba_name`, `bcba_credential`
- Authorization, per service type and total: authorized, delivered, remaining, utilization percent
- Sessions: counts scheduled, completed, cancelled, no-show; attendance rate; cancellation rate; cancellations by who cancelled; first and last session dates
- Tables: sessions by month, hours by service type, hours by staff member, cancellation list
- Supervision: supervision hours and percent in period, parent training hours
- Staff: list of assigned technicians
- Goals, when goal data exists: table of goal, baseline (first N data points), current (last N), change, session count; one line chart per goal
- Any client custom field: `{{custom.field_name}}`

### B4. Flow

1. Choose client, period, and template.
2. Preview screen: rendered report on the left; on the right, a list of every yellow placeholder (with jump links) and a count, e.g. "12 placeholders to complete".
3. Download as `.docx`. File name: `{client_code}_{template_name}_{period_end}.docx`. Never overwrite an earlier output; keep generated reports in history.
4. She finishes the report in Word. The app does not need to edit report text in v1.

### B5. Template manager

- Upload, rename, delete templates.
- On upload, list detected tokens and flag unknown ones with suggestions ("did you mean `period_start`?").
- Ship one sample template and a token reference page so she can adapt her own document.
- "Test with sample data" generates from synthetic data.

## 7. UX requirements

- Navigation: This Week, Caseload, Staff and Supervision, Deadlines, Cancellations, Reports, Import, Settings.
- First run: a short wizard (BCBA name and credential, service types, thresholds) and an option to load synthetic demo data that can be cleared in one click.
- Desktop layout first; must remain usable at 1280px wide. No mobile layout in v1.
- Every calculated number has a tooltip or "how is this calculated" link showing the formula and inputs.
- Print-friendly views for Caseload and This Week.
- Undo for deletes and imports. Confirm destructive actions.
- Meets WCAG AA contrast; fully keyboard navigable.

## 8. Technical suggestions

The agent may change these with a stated reason.

- TypeScript, React, Vite. IndexedDB through a wrapper such as Dexie.
- CSV and XLSX parsing in the browser. DOCX templating in the browser; check that the chosen library preserves run formatting and supports loops and images, and add an XML post-processing step for highlights if it cannot emit them.
- Charts rendered to canvas and exported as PNG for embedding.
- All calculation logic in pure functions, separate from UI, with unit tests.
- Pin dependencies, confirm licenses permit commercial use, and verify the production build makes no network requests (automated test that fails on any request).

## 9. Privacy and security notes

- Display a short, plain notice on first run: data stays on this device; use client codes, not names; keep the laptop's disk encryption on; check employer policy before entering client information.
- No telemetry, crash reporting, or update checks.
- This spec is not legal advice. Before real client data is entered, the user should confirm with her employer that a local tool is permitted, as she presumably has for her current spreadsheet.

## 10. Non-goals for v1

- Billing, claims, clinical data collection, session notes
- Writing anything back to the practice management system
- Multiple users, sync, or cloud storage
- Automated scheduling or sending messages to families
- AI-written narrative text
- In-app editing of report body text

## 11. Acceptance criteria

1. With the network disabled, every feature works, and an automated test confirms zero outbound requests.
2. Closing and reopening the browser preserves all data. Saving to a file and opening it in a fresh browser profile restores everything.
3. Importing the same export twice produces no duplicates. Undoing an import restores the prior state exactly.
4. For a fixture with known values, pace, needed-per-week, projected utilization, and supervision percent match hand-calculated results, including edge cases: authorization starting mid-month, period already ended, zero delivered hours, units versus hours, sessions spanning midnight, overlapping authorizations for the same service type.
5. Inferred supervision overlap is computed correctly for partial overlaps, and manual overrides take precedence.
6. This Week lists an item for every red or yellow status, every deadline inside its window, and every client past the not-seen threshold.
7. Generating a report from the sample template yields a valid `.docx` that opens in Word without repair prompts, preserves template formatting, fills all catalog tokens that have data, and renders every `TODO` and missing token as yellow-highlighted text.
8. The placeholder count in the preview equals the number of highlighted placeholders in the file.
9. A template containing an unknown token still generates, with that token shown as `[MISSING: ...]` in yellow.
10. A non-technical user can launch the app with one double-click by following a one-page guide.

All fixtures and demo data must be synthetic. Never commit real client data.

## 12. Assumptions to confirm with the BCBA

These were decided without her input. Each could change the build.

1. Report templates are Word documents, and she finishes reports in Word.
2. Her practice system can export sessions and authorizations to CSV or XLSX, and she is permitted to export them.
3. Authorizations are tracked per service type over a date range, in hours or 15-minute units.
4. "Seeing a client enough" means meeting authorized BCBA hours per client plus supervision minimums per technician. If she uses a different rule, A2 and A4 change.
5. How she currently knows which technician a supervision session covered (explicit field, overlap, or memory).
6. Whether goal or behavior data is available as an export, and in what shape. Without it, goal sections of reports stay as placeholders.
7. Which report types she writes (progress, reassessment, discharge) and how often.
8. The exact columns of her current spreadsheet. Get a copy with client details removed before starting M3.

## 13. Milestones

1. **M1**: app shell, data model, IndexedDB, save and open data file, demo data, no-network test.
2. **M2**: import with mapping, profiles, dedupe, undo. Manual entry for all entities.
3. **M3**: Caseload board and client detail with pacing calculations and tests.
4. **M4**: Supervision tracker, deadlines, This Week, cancellations.
5. **M5**: Report Writer: template manager, token engine, highlight rule, preview, download.
6. **M6**: packaging for one-click start, user guide, accessibility pass, encryption option.
