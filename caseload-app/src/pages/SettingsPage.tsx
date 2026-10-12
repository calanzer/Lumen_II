import { useLiveQuery } from "dexie-react-hooks";
import { useEffect, useState } from "react";
import { Confirm } from "../components/Confirm";
import { useOpenDataFile, useSync } from "../components/DataFile";
import { ServiceTypesEditor, ThresholdFields, type EditableServiceType } from "../components/SettingsFields";
import { toast } from "../components/Toasts";
import { deleteAllData, exportDownload, saveToNewFile, unlinkFile } from "../datafile/fileSync";
import { db } from "../db/db";
import { getSettings, saveSettings } from "../db/repo";
import { saveServiceTypes, validateServiceTypes } from "../db/serviceTypes";
import type { Settings } from "../db/types";
import { clearDemoData, hasDemoData, loadDemoData } from "../demo/loadDemo";
import { PrivacyNotice } from "./FirstRun";

export function SettingsPage() {
  const stored = useLiveQuery(() => getSettings(), []);
  const storedTypes = useLiveQuery(() => db.serviceTypes.toArray().then((r) => r.filter((t) => !t.deletedAt)), []);
  const demoLoaded = useLiveQuery(() => hasDemoData(), [], false);
  const sync = useSync();
  const opener = useOpenDataFile();

  const [draft, setDraft] = useState<Settings | null>(null);
  const [types, setTypes] = useState<EditableServiceType[] | null>(null);
  const [newField, setNewField] = useState("");
  const [confirm, setConfirm] = useState<"delete-all" | "clear-demo" | null>(null);
  const [typeError, setTypeError] = useState<string | null>(null);

  useEffect(() => {
    if (stored && !draft) setDraft(stored);
  }, [stored, draft]);
  useEffect(() => {
    if (storedTypes && !types) setTypes(storedTypes.map(({ createdAt: _c, updatedAt: _u, deletedAt: _d, manualEdits: _m, demo: _demo, ...t }) => t));
  }, [storedTypes, types]);

  if (!draft || !types || !stored) return null;

  const settingsDirty = JSON.stringify(draft) !== JSON.stringify(stored);

  async function saveDraft() {
    if (!draft) return;
    if (draft.paceYellowAt > draft.paceGreenAt) return toast("The yellow threshold must be at or below the green threshold.");
    await saveSettings({ ...draft, customFieldNames: stored!.customFieldNames });
    toast("Settings saved.");
  }

  async function addCustomField() {
    const name = newField.trim();
    if (!name) return;
    if (stored!.customFieldNames.includes(name)) return toast(`There is already a field called ${name}.`);
    await saveSettings({ customFieldNames: [...stored!.customFieldNames, name] });
    setNewField("");
  }

  async function removeCustomField(name: string) {
    const previous = stored!.customFieldNames;
    await saveSettings({ customFieldNames: previous.filter((n) => n !== name) });
    toast(`Removed the ${name} column. Values stay on each client.`, () => saveSettings({ customFieldNames: previous }));
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Every threshold here drives the status colors and This Week list.</p>
        </div>
      </div>

      <section className="card" aria-labelledby="s-about">
        <h2 id="s-about">About you</h2>
        <div className="grid-2">
          <div className="field">
            <label htmlFor="set-name">Your name</label>
            <input id="set-name" type="text" value={draft.bcbaName} onChange={(e) => setDraft({ ...draft, bcbaName: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="set-cred">Credential</label>
            <input id="set-cred" type="text" value={draft.bcbaCredential} onChange={(e) => setDraft({ ...draft, bcbaCredential: e.target.value })} />
          </div>
        </div>
        <h2 style={{ marginTop: 8 }}>Thresholds</h2>
        <ThresholdFields value={draft} onChange={(p) => setDraft({ ...draft, ...p })} />
        <div className="row">
          <button className="btn btn-primary" disabled={!settingsDirty} onClick={() => void saveDraft()}>
            Save settings
          </button>
          {settingsDirty && (
            <button className="btn" onClick={() => setDraft(stored)}>
              Discard changes
            </button>
          )}
        </div>
      </section>

      <section className="card" aria-labelledby="s-types">
        <h2 id="s-types">Service types</h2>
        <ServiceTypesEditor value={types} onChange={setTypes} />
        {typeError && (
          <p className="error-text" role="alert">
            {typeError}
          </p>
        )}
        <div className="row" style={{ marginTop: 12 }}>
          <button
            className="btn btn-primary"
            onClick={async () => {
              const err = validateServiceTypes(types);
              setTypeError(err);
              if (err) return;
              await saveServiceTypes(types);
              setTypes(null);
              toast("Service types saved.");
            }}
          >
            Save service types
          </button>
        </div>
      </section>

      <section className="card" aria-labelledby="s-fields">
        <h2 id="s-fields">Custom client fields</h2>
        <p className="muted">Columns from your own tracker that the app does not have built in. They appear on the caseload board and can be sorted and filtered.</p>
        {stored.customFieldNames.length > 0 ? (
          <ul>
            {stored.customFieldNames.map((n) => (
              <li key={n} className="row" style={{ marginBottom: 4 }}>
                <span>{n}</span>
                <button className="btn-link" onClick={() => void removeCustomField(n)} aria-label={`Remove field ${n}`}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted small">No custom fields yet. Importing your tracker spreadsheet can add them for you.</p>
        )}
        <div className="row">
          <label htmlFor="new-field" className="sr-only">
            New field name
          </label>
          <input id="new-field" type="text" placeholder="Field name" value={newField} onChange={(e) => setNewField(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void addCustomField()} />
          <button className="btn" onClick={() => void addCustomField()}>
            Add field
          </button>
        </div>
      </section>

      <section className="card" aria-labelledby="s-data">
        <h2 id="s-data">Your data file</h2>
        <p>
          Everything is stored in this browser on this computer.
          {sync.link === "linked" && sync.fileName ? (
            <>
              {" "}Changes are saved automatically to <strong>{sync.fileName}</strong>.
            </>
          ) : (
            " Save it to a file to keep a backup you can open again on any computer."
          )}
        </p>
        <div className="row">
          {sync.supportsFileLink && (
            <button className="btn btn-primary" onClick={() => void saveToNewFile()}>
              {sync.link === "linked" ? "Save to a different file…" : "Save to file…"}
            </button>
          )}
          <button className="btn" onClick={opener.open}>
            Open file…
          </button>
          <button className="btn" onClick={() => void exportDownload().then(() => toast("Backup copy downloaded."))}>
            Download a copy
          </button>
          {sync.link !== "none" && (
            <button className="btn" onClick={() => void unlinkFile()}>
              Stop autosaving to {sync.fileName}
            </button>
          )}
        </div>
        {opener.element}
      </section>

      <section className="card" aria-labelledby="s-demo">
        <h2 id="s-demo">Demo data</h2>
        {demoLoaded ? (
          <>
            <p>Demo data is loaded. It is made up and marked so it can be removed without touching anything you entered.</p>
            <button className="btn btn-danger" onClick={() => setConfirm("clear-demo")}>
              Clear demo data
            </button>
          </>
        ) : (
          <>
            <p className="muted">Load made-up clients, technicians and sessions to explore the app.</p>
            <button className="btn" onClick={() => void loadDemoData().then(() => toast("Demo data loaded."))}>
              Load demo data
            </button>
          </>
        )}
      </section>

      <section className="card" aria-labelledby="s-privacy">
        <h2 id="s-privacy">Privacy</h2>
        <PrivacyNotice />
      </section>

      <section className="card" aria-labelledby="s-danger">
        <h2 id="s-danger">Delete all data</h2>
        <p>Removes every client, session, template and setting from this browser. Data files you saved stay on disk.</p>
        <button className="btn btn-danger" onClick={() => setConfirm("delete-all")}>
          Delete all data…
        </button>
      </section>

      {confirm === "clear-demo" && (
        <Confirm
          title="Clear demo data?"
          body={<p>This removes all made-up demo records. Anything you entered yourself stays.</p>}
          confirmLabel="Clear demo data"
          danger
          onCancel={() => setConfirm(null)}
          onConfirm={async () => {
            await clearDemoData();
            setConfirm(null);
            setTypes(null);
            toast("Demo data cleared.");
          }}
        />
      )}
      {confirm === "delete-all" && (
        <Confirm
          title="Delete all data?"
          body={
            <p>
              This permanently removes everything stored in this browser. It cannot be undone here. If you want a copy, download one first.
            </p>
          }
          confirmLabel="Delete everything"
          danger
          typedConfirmation="DELETE"
          onCancel={() => setConfirm(null)}
          onConfirm={async () => {
            await deleteAllData();
            window.location.hash = "";
            window.location.reload();
          }}
        />
      )}
    </>
  );
}
