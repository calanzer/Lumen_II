import { useState } from "react";
import { requestPersistentStorage } from "../datafile/fileSync";
import { DEFAULT_SERVICE_TYPES, DEFAULT_SETTINGS } from "../db/defaults";
import { saveSettings } from "../db/repo";
import { saveServiceTypes, validateServiceTypes } from "../db/serviceTypes";
import type { Settings } from "../db/types";
import { loadDemoData } from "../demo/loadDemo";
import { ServiceTypesEditor, ThresholdFields, type EditableServiceType } from "../components/SettingsFields";
import { useOpenDataFile } from "../components/DataFile";

export function PrivacyNotice() {
  return (
    <ul>
      <li>
        <strong>Your data stays on this computer.</strong> The app makes no internet connections. Nothing is uploaded anywhere.
      </li>
      <li>
        <strong>Use client codes, not names.</strong> Pick a short code for each client (like K7). Avoid names, birth dates, addresses and member IDs.
      </li>
      <li>
        <strong>Keep your laptop's disk encryption turned on</strong> (BitLocker on Windows, FileVault on Mac), and save backups only to places your employer allows.
      </li>
      <li>
        <strong>Check your employer's policy</strong> before entering real client information into any tool, including this one.
      </li>
    </ul>
  );
}

const STEPS = ["Welcome", "About you", "Service types", "Thresholds", "Get started"];

export function FirstRun() {
  const [step, setStep] = useState(0);
  const [settings, setSettings] = useState<Settings>({ ...DEFAULT_SETTINGS });
  const [types, setTypes] = useState<EditableServiceType[]>(DEFAULT_SERVICE_TYPES.map((t) => ({ ...t })));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const opener = useOpenDataFile();

  function next() {
    setError(null);
    if (step === 1 && !settings.bcbaName.trim()) return setError("Enter your name as it should appear on reports.");
    if (step === 2) {
      const err = validateServiceTypes(types);
      if (err) return setError(err);
    }
    if (step === 3 && settings.paceYellowAt > settings.paceGreenAt) return setError("The yellow threshold must be at or below the green threshold.");
    setStep(step + 1);
  }

  async function finish(withDemo: boolean) {
    setBusy(true);
    try {
      await requestPersistentStorage();
      await saveServiceTypes(types);
      await saveSettings({ ...settings, bcbaName: settings.bcbaName.trim(), firstRunComplete: false });
      if (withDemo) await loadDemoData();
      await saveSettings({ firstRunComplete: true });
      window.location.hash = withDemo ? "#/caseload" : "#/settings";
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="content" style={{ maxWidth: 980, margin: "0 auto" }} aria-labelledby="wizard-title">
      <div className="card" style={{ marginTop: 24 }}>
        <div className="steps" aria-hidden="true">
          {STEPS.map((s, i) => (
            <span key={s} className={i <= step ? "done" : ""} />
          ))}
        </div>
        <p className="muted small">
          Step {step + 1} of {STEPS.length}: {STEPS[step]}
        </p>

        {step === 0 && (
          <>
            <h1 id="wizard-title">Welcome to Caseload Tracker</h1>
            <p>A few minutes of setup, then you can see at a glance whether every client and technician is on pace.</p>
            <h2>Before you start</h2>
            <PrivacyNotice />
          </>
        )}

        {step === 1 && (
          <>
            <h1 id="wizard-title">About you</h1>
            <p className="muted">Used on generated reports.</p>
            <div className="field">
              <label htmlFor="bcba-name">Your name</label>
              <input id="bcba-name" type="text" value={settings.bcbaName} onChange={(e) => setSettings({ ...settings, bcbaName: e.target.value })} autoFocus />
            </div>
            <div className="field">
              <label htmlFor="bcba-cred">Credential</label>
              <input id="bcba-cred" type="text" value={settings.bcbaCredential} onChange={(e) => setSettings({ ...settings, bcbaCredential: e.target.value })} />
              <span className="hint">For example: BCBA, BCBA-D, LBA</span>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h1 id="wizard-title">Service types</h1>
            <p className="muted">
              The billing codes your sessions and authorizations use. These are common defaults; edit them to match your payers. You can change them later in Settings.
            </p>
            <ServiceTypesEditor value={types} onChange={setTypes} />
          </>
        )}

        {step === 3 && (
          <>
            <h1 id="wizard-title">Thresholds</h1>
            <p className="muted">Sensible defaults are filled in. Every number can be changed later in Settings.</p>
            <ThresholdFields value={settings} onChange={(p) => setSettings({ ...settings, ...p })} />
          </>
        )}

        {step === 4 && (
          <>
            <h1 id="wizard-title">Get started</h1>
            <p>Choose how to begin. Demo data is made up and can be removed in one click from Settings.</p>
            <div className="grid-2">
              <div className="card">
                <h2>Start empty</h2>
                <p className="muted">Import your practice system exports or your existing tracker spreadsheet.</p>
                <button className="btn btn-primary" disabled={busy} onClick={() => void finish(false)}>
                  Start with an empty caseload
                </button>
              </div>
              <div className="card">
                <h2>Explore with demo data</h2>
                <p className="muted">Nine made-up clients and six technicians, so you can see how everything works first.</p>
                <button className="btn" disabled={busy} onClick={() => void finish(true)}>
                  Load demo data
                </button>
              </div>
            </div>
          </>
        )}

        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}

        <div className="modal-actions" style={{ justifyContent: "space-between" }}>
          <div>
            {step === 0 && (
              <button className="btn" onClick={opener.open}>
                I already have a data file…
              </button>
            )}
            {step > 0 && (
              <button className="btn" onClick={() => setStep(step - 1)} disabled={busy}>
                Back
              </button>
            )}
          </div>
          {step < STEPS.length - 1 && (
            <button className="btn btn-primary" onClick={next}>
              {step === 0 ? "I understand, continue" : "Continue"}
            </button>
          )}
        </div>
      </div>
      {opener.element}
    </main>
  );
}
