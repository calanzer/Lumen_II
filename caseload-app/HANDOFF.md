# Caseload Tracker: handoff notes

The product spec is `SPEC.md` in this folder. Build against it milestone by milestone (section 13).

## Status

| Milestone | Status |
|---|---|
| M1: app shell, data model, IndexedDB, data file, demo data, no-network test | Done |
| M2: import with mapping, profiles, dedupe, undo; manual entry | Next |
| M3: caseload board, client detail, pacing calculations | Not started |
| M4: supervision, deadlines, This Week, cancellations | Not started |
| M5: Report Writer | Not started |
| M6: packaging, user guide, accessibility, encryption | Not started |

Only Settings and the data-file controls work in the UI. Other screens render "This screen is not built yet".

## Running

```bash
npm install
npm run dev          # http://localhost:5173 (no CSP in dev; Vite needs HMR)
npm run build        # dist/index.html, single self-contained file
npm test             # unit tests (vitest)
npx playwright install chromium   # first time only
npm run test:e2e     # browser tests; run `npm run build` first, they load dist/index.html
```

## Decisions made

- **Launch method:** a single self-contained `dist/index.html` opened by double-click (`file://`). Verified in Chromium: IndexedDB persists across browser restarts, `file://` is a secure context (WebCrypto, `crypto.randomUUID` available), File System Access pickers exist. Real Chrome and Edge still need a manual check.
- **No network:** `vite.config.ts` injects a CSP at build time with `connect-src 'none'` and inline scripts allowed by sha256 hash. The e2e test asserts zero non-`file:` requests, zero page errors, and that a deliberate `fetch` triggers a `connect-src` violation.
- **Stack:** React 18, TypeScript, Vite 5, Dexie 4 (IndexedDB). Dependencies are pinned exactly.
- **Data model:** `src/db/types.ts` follows spec section 4, plus two additions: `SupervisionOverride` (A4 manual overrides) and `WeekAction` (A6 check-off state). Soft delete via `deletedAt`; `manualEdits` lists fields the user changed by hand so re-import can leave them alone.
- **Data file:** JSON (`.caseload.json`) holding every table except `meta`; Blobs are base64-encoded (`src/datafile/format.ts`). Autosave uses the File System Access API where available, otherwise Download/Open. The encrypted envelope (`encrypted: true`) is reserved for M6.
- **Change tracking:** Dexie hooks in `src/db/db.ts` emit change events that drive autosave. Writes made inside those hooks must not touch tables outside the current transaction; the dirty flag is written via `setTimeout` for that reason.
- **Demo data:** `src/demo/demoData.ts`, seeded and synthetic, every row has `demo: true`. Includes red, yellow, over-authorized and not-seen cases.

## Known caveats

- Chrome gives every local HTML file the same origin, so another HTML file opened from disk could read this app's IndexedDB. Mention in the user guide (M6).
- The native save/open pickers cannot be driven headlessly. The autosave e2e test uses a stand-in file handle; check the real picker by hand.
- Spec section 12 lists assumptions to confirm with the BCBA. #8 (a de-identified copy of her current spreadsheet) matters before M3.

## Unrelated code in this repo

`../aba-auth-agent/` is the earlier Streamlit reauthorization app. The caseload app does not use it.
