# Lumen ABA: design and framework

Status: decided and built. Every screen is in the new interface and the Streamlit app has been removed.

## Decision

The interface is a **React single-page app on shadcn/ui, Radix UI and Tailwind CSS v4**, served by a **Python (FastAPI) API** that wraps the existing pipeline. The earlier Streamlit app has been retired (it's in git history).

Why the change was made: the research on what BCBAs need (`reports/BCBA software needs research.md`) puts a source-linked review step at the top of the list: each extracted value shown next to where it came from in the original report. Streamlit can't do that well, nor sortable tables with row events, proper dialogs, or a layout that holds up on narrow screens. React with a real component system can.

What did not change: all of the extraction, drafting, cross-checking and intake logic (`pipeline/`, `schemas/`, `data/`) is untouched and keeps its tests. Only the screens are rebuilt.

## How the pieces fit

```
Browser (Vite SPA, web/)  --/api, session cookie-->  FastAPI (api/)  -->  pipeline/  -->  SQLite
                                                       |                    |
                                                  login, jobs          Claude API
```

- **Development:** the Vite dev server (`:5173`) proxies `/api` to uvicorn (`:8000`), so the browser sees one origin and no CORS is needed.
- **Production:** `uvicorn api.main:app` also serves the built frontend from `web/dist`, with the app's own routes falling back to `index.html`. One process, one deployment.
- **Long work runs as jobs.** A real import takes one to two minutes, so `POST /api/imports` returns immediately and the browser polls the job through these stages: `reading` → `needs_answers` (only when the report leaves something out) → `setting_up` → `drafting` → `checking` → `done`, or `error`. The frontend remembers the job id in `sessionStorage`, so a page refresh resumes the import instead of losing it.

## Stack

| Layer | Choice | Version | Notes |
|---|---|---|---|
| Build | Vite + `@vitejs/plugin-react` | 8.3 / 6.1 | Static output the API serves. No Node server in production. |
| UI | React, TypeScript | 19.3 / 6.0 | Strict compiler options (`noUnusedLocals`, `erasableSyntaxOnly`). |
| Components | shadcn/ui, preset `radix-vega`, base color neutral, CSS variables | CLI 4.22 | Source is copied into `src/components/ui/`, not imported from a package. |
| Primitives | Radix UI (`radix-ui` unified package) | 1.8 | Dialog, Select, Popover, Tabs, Dropdown. |
| Styling | Tailwind CSS v4, theme in `src/index.css` | 4.3 | `class-variance-authority`, `tw-animate-css`, `cn` helper. |
| Icons / font | lucide-react, Inter (self-hosted via `@fontsource-variable/inter`) | 1.59 / 5.3 | No external font request. |
| Charts | Recharts | 3.10 | Installed; first used on the Review screen (baseline vs current graphs). |
| Dates | react-day-picker + date-fns | 10.0 / 4.4 | Behind the shadcn `Calendar`; `DatePicker` wraps it with Popover. |
| Routing | react-router | 7.18 | Client-side routes under one auth guard. |
| Tests | Vitest, Testing Library, jsdom | 5.0 | Plus pytest for the API and pipeline. |
| Lint | oxlint | 1.89 | shadcn's generated files are excluded. |
| API | FastAPI, uvicorn, Starlette sessions | 0.150 / 0.54 / 1.9 | Signed cookie session. |

Where this differs from the reference stack description we started from:

- shadcn's CLI no longer ships a style called "new-york"; its equivalent classic look is the **`radix-vega`** preset, which is what `components.json` records.
- Radix now ships as one `radix-ui` package rather than many `@radix-ui/react-*` packages. Same primitives.
- **Not adopted yet:** `react-big-calendar` and `moment`. They are for a session calendar, which this product doesn't have. Add them if a sessions view is built.
- **Added beyond the reference list:** `alert` (error and warning banners), `react-router`, `lucide-react`.
- **TanStack Table is not used.** The first plan was to adopt it for the Clients table, and it was installed and then removed: version 9 needs every feature and row model registered by hand, which is a lot of machinery for a roster of a few dozen rows. Sorting and searching are small pure functions in `src/lib/clients.ts` with their own tests, over shadcn's `Table`, which is what the reference stack does too. Revisit if a table needs pagination, virtualization or column features.

## Design tokens

Defined once in `src/index.css`. Components use token classes (`bg-primary`, `text-muted-foreground`, `border-success`), never raw hex values, so the theme can change in one place.

| Token | Light | Role |
|---|---|---|
| `primary` | `#0B7285` teal | Main actions, links, focus accents, brand mark |
| `foreground` | `#1A2B3C` navy | Body text and headings |
| `secondary`, `muted` | `#F0F7F9` | Quiet backgrounds |
| `accent` | `#E6F4F7` | Hover and selected states |
| `muted-foreground` | `#5B6B7B` | Secondary text |
| `border`, `input` | `#DCE5EA` | Borders |
| `success` | `#059669` | Complete, healthy |
| `warning` | `#D97706` | Needs a look |
| `destructive` | `#DC2626` | Errors, blocking problems |
| `chart-1` to `chart-5` | teal, slate, amber, violet, emerald | Recharts series |

Dark mode: the dark values are defined (`.dark` class) but there is no toggle yet. Radius is `0.625rem`. Cards, tables and form controls come from shadcn unchanged.

## Component rules

1. **Reach for shadcn first.** Cards for panels, `Table` for lists, `Dialog` for modals, `Tabs` for alternate views of the same data, `Select` for choices, `Popover` + `Calendar` for dates, `Badge` for status, `Progress` for job progress, `Skeleton` for loading, `Alert` for banners.
2. **Add components with the CLI** (`npx shadcn@latest add <name>`) so they stay upgradeable. Don't hand-edit `src/components/ui/`; compose around it. App-specific components live in `src/components/`.
3. **Never present a missing value as a real one.** An unknown number is "Not stated" or an empty field, never `0`. A failed check is "n/a" with a visible reason, never zero problems. (This is the lesson of the Streamlit Review page, which turned missing values into `0`.)
4. **Show errors where the user is looking,** with the server's reason, and clear them once the user starts fixing the field.
   A server that can't be reached (no answer, or a 502/503/504 from a proxy) is its own screen with a retry, never the login form, and never the browser's raw "Failed to fetch".
5. **Everything is operable by keyboard and named for screen readers.** Inputs have labels, metric tiles are `role="group"` with a name, the dropzone is a real labelled file input, date buttons announce their date.
6. **Layout is mobile-first:** the sidebar becomes a top bar with a menu below `md`; grids reflow rather than overflow.

## Screens (and what each replaced in the Streamlit app)

| Was (Streamlit) | Screen | Status | Built with |
|---|---|---|---|
| Login | `/login` | Built | Card, Input, Label, Alert |
| Import (drop a file, everything runs) | `/import` | **Built, end to end** | Dropzone (labelled file input), Progress, Select, Calendar in Popover, Tabs, Badge, Alert |
| Clients, Client Detail (table, details, Add client modal) | `/clients` | **Built** | shadcn `Table` with sortable headers, `Dialog` (add, details, archive confirm), `DropdownMenu` row actions, `Badge` deadline indicators. Sorted most-urgent authorization first; search across name, ID, diagnosis and payor; double-click or Enter opens details. Details: periods (`Accordion`) with status, completeness, extracted counts, narrative confidence, notes, links to Review / Generate / Export; new period; VB-MAPP trends table. |
| Review data | `/periods/:id/review` | **Built** (parity). Source-linked two-pane view still to do (see below). | Card per section (nine, as before), `Accordion` items with add / remove, native date boxes, `Checkbox`, `Select`, `Progress`. Blank stays blank (never 0). Autosave 0.8 s after the last edit with a visible save state, "Save now", leave-page warning, raw JSON editor. The server re-checks everything on save and refuses bad values with a reason. |
| Generate | `/periods/:id/generate` | **Built** (parity) | Progress since prior authorization, incomplete-data and stale warnings, background job with progress and cross-check result (including "could not run"), side-by-side source data and editable text per section with word-count hints, flags, autosave. Regenerating asks first, and drops pending edits so a late save can't overwrite the new draft. |
| Export | `/periods/:id/export` | **Built** (parity) | Summary cards, payor choice (fixed for template-driven narratives), sign-off checkbox the server also requires, Word download, mark as submitted. |
| Templates | `/templates` | **Built** (parity) | Per payor: current template or built-in default, reset, analyze a past report, editable sections (rename, describe, reorder, add, delete), style notes, name, save, discard. One draft kept per payor while you switch. |

The sidebar's Review, Generate and Export links open that step for the period you worked on last (remembered in the browser), or ask you to choose a client.

Screens not rebuilt yet show a "Not in the new interface yet" card with a link to the current app. Both apps read and write the same database, so work carries across.

Migration order: Review, Generate, Export, Templates (Import and Clients are done). Then retire Streamlit and move `caseload-app` onto the same component system.

## API

All routes except `/api/health` and `/api/auth/login` require a signed-in session.

| Route | Purpose |
|---|---|
| `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` | Session. 5 failed attempts per username locks it for 5 minutes. |
| `GET /api/payors` | The payor list. |
| `GET /api/clients`, `POST /api/clients` | The active roster, each with their latest authorization period (days left, status); add a client. Duplicate client IDs are refused however they're written. |
| `GET /api/clients/{id}` | One client with every authorization period, newest first (summaries only, no report contents). |
| `POST /api/clients/{id}/archive` | Take a client off the active roster. Nothing is deleted. |
| `POST /api/clients/{id}/periods` | Add an authorization period (end must be after start). |
| `GET /api/periods/{id}` | Everything a period screen needs: client, extracted data, completeness, narrative (sections with their source data, stale flag), active template, prior-period comparison. |
| `PATCH /api/periods/{id}` | BCBA notes. |
| `PUT /api/periods/{id}/data` | Save edited data. Fully re-validated; refused with a reason if a value is impossible. Returns the new completeness and whether the narrative is now stale. |
| `PUT /api/periods/{id}/narrative` | Save narrative edits by section key. Unknown keys refuse the whole request. |
| `POST /api/periods/{id}/generate`, `GET …/generate` | Write the narrative in the background and follow it (`drafting`, `checking`, `done`, `error`; cross-check result or why it couldn't run). One at a time per period. A failed draft leaves the previous one untouched. |
| `POST /api/periods/{id}/export` | Build the Word document (requires `confirmed: true`). Marks the period exported. Filename is sanitized. |
| `POST /api/periods/{id}/submitted` | Mark submitted; only after export. |
| `GET/PUT/DELETE /api/templates/{payor}`, `POST /api/templates/analyze` | Template library: read, save, go back to the built-in layout, analyze a past report (nothing is stored from the upload). |
| `POST /api/imports` (multipart `file`) | Start an import. PDF or `.docx`, 50 MB max. Returns the job. |
| `GET /api/imports/{id}` | Job state: `stage`, `questions`, `error`, `result`. |
| `POST /api/imports/{id}/answers` | Supply what the report left out (client, payor, period). Refused with a reason if incomplete. |

Types the frontend uses are in `web/src/lib/types.ts` and mirror these responses. If they drift, generate them from `/openapi.json`.

## Security notes

- Session in a signed cookie, `SameSite=Lax`, which stops other sites from making the browser send it on cross-site POSTs (uploads and answers). Set `ABA_HTTPS_ONLY=1` behind HTTPS so the cookie is Secure.
- Unknown usernames take as long to reject as wrong passwords; failures are rate-limited per username.
- A job belongs to the user who started it; others get a 404.
- **Skipping sign-in locally (opt-in).** Set `ABA_LOCAL_NO_LOGIN=1` and a request is treated as signed in as "Local tester" (marked `local: true`, shown as a **Local** badge in the sidebar) only if *all* of these hold: the connection comes from a loopback address; the `Host` header is `localhost`, `127.0.0.1` or `::1` (stops DNS rebinding); there are no proxy headers (`X-Forwarded-*`, `X-Real-IP`, `Forwarded`); the browser does not report `Sec-Fetch-Site: cross-site`; and any `Origin` header is itself loopback. The last two matter because any website you visit can make your browser send requests to `localhost`, so a plain "is it local" check would let another page archive your clients. Each condition has a test that fails without it. A real session still takes priority, and the flag is off unless set, so a deployed copy is unaffected.
- Uploaded bytes are dropped from memory once the report has been read.
- **Not yet addressed:** the app has no audit log, no per-user roles, the lockout counter and the jobs are in memory (a restart clears them), and nothing here is a HIPAA compliance claim. See the gap list in the project notes before handling real client data.

## Running it

```bash
# API (from aba-auth-agent/)
.venv/bin/uvicorn api.main:app --port 8000

# Frontend, in development (from aba-auth-agent/web/)
npm install
npm run dev            # http://localhost:5173, proxies /api to :8000

# Production-style: build, then the API serves it
npm run build
.venv/bin/uvicorn api.main:app --port 8000      # http://localhost:8000
```

| Setting | Effect |
|---|---|
| `ABA_DB_PATH` | Use a different SQLite file (for tests and demos). |
| `ABA_AUTH_CONFIG` | Use a different login file than `config/auth_config.yaml`. |
| `ABA_HTTPS_ONLY` | Mark the session cookie Secure. |
| `ABA_LOCAL_NO_LOGIN` | Skip sign-in for plain same-machine requests (see Security notes). The `lumen-api` run configuration sets it. |
| `ANTHROPIC_API_KEY` | In `.env`; used by the pipeline. |

## Quality gates

Run all four before merging UI work:

```bash
.venv/bin/python -m pytest -q tests         # API, pipeline, pages
cd web && npm test                           # components, hooks, app flow
cd web && npm run typecheck && npx oxlint    # types and lint
cd web && npm run build                      # production build
```

Tests that guard a bug fix should be shown to fail without the fix. Twice during this build a test passed for the wrong reason (an assertion that could never fail), which only showed up by removing the fix and rerunning.

## Open decisions

1. **Keep the uploaded report?** The source-linked review needs the original file to display beside the data, but today it is dropped after extraction. Keeping it means storing PHI, which needs encryption at rest, retention rules and access control first.
2. **Background jobs.** Jobs live in memory in one process. A restart loses in-flight imports; several workers would not share them. A small queue (or a table in SQLite) is the next step if that matters.
3. **Batch import.** The Import screen takes one file at a time; the worklist model (drop many, review by due date) is the natural next step.
4. **SQLite and threads.** `data/store.py` lets only one thread hold a database connection at a time. SQLite 3.51.0 (the version some current Macs ship with Python) deadlocks inside the library when threads open and close connections to one file together, which froze the API the first time the browser asked for several things at once. The lock costs nothing noticeable here; a real database server would replace it if the app outgrows one machine.
5. **Source-linked review.** Parity is done, but the research's top recommendation for Review (each value shown beside the passage of the report it came from) still depends on decision 1.
