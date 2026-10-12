import { useLiveQuery } from "dexie-react-hooks";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { db } from "../db/db";
import {
  backupOverdue,
  BACKUP_REMINDER_DAYS,
  exportDownload,
  getSyncState,
  importFromFile,
  openFromPicker,
  reconnectFile,
  saveToNewFile,
  subscribeSync,
} from "../datafile/fileSync";
import { DATA_FILE_EXTENSION } from "../datafile/format";
import { Confirm } from "./Confirm";
import { toast } from "./Toasts";

export function useSync() {
  return useSyncExternalStore(subscribeSync, getSyncState);
}

function useNow(intervalMs = 30_000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

export function relativeTime(iso: string, now = Date.now()): string {
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (s < 45) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} hr ago`;
  const d = Math.round(h / 24);
  return `${d} day${d === 1 ? "" : "s"} ago`;
}

export function useOpenDataFile() {
  const sync = useSync();
  const inputRef = useRef<HTMLInputElement>(null);
  const [confirming, setConfirming] = useState(false);

  async function afterOpen(ok: boolean) {
    if (ok) toast("Data file opened.");
  }

  const element = (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={`${DATA_FILE_EXTENSION},.json,application/json`}
        hidden
        data-testid="open-file-input"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (!file) return;
          try {
            await importFromFile(file);
            await afterOpen(true);
          } catch (err) {
            toast((err as Error).message);
          }
        }}
      />
      {confirming && (
        <Confirm
          title="Open a data file?"
          body={<p>Opening a data file replaces everything currently in this browser with the file's contents. Save first if you have changes you want to keep.</p>}
          confirmLabel="Choose file…"
          onCancel={() => setConfirming(false)}
          onConfirm={async () => {
            setConfirming(false);
            if (sync.supportsFileLink) {
              try {
                await afterOpen(await openFromPicker());
              } catch (err) {
                toast((err as Error).message);
              }
            } else {
              inputRef.current?.click();
            }
          }}
        />
      )}
    </>
  );
  return { element, open: () => setConfirming(true) };
}

export function DataFileBar() {
  const sync = useSync();
  const now = useNow();
  const opener = useOpenDataFile();

  let status: string;
  if (sync.saving) status = "Saving…";
  else if (sync.link === "linked" && sync.fileName) {
    status = `Autosaving to ${sync.fileName}` + (sync.lastSavedAt ? ` · saved ${relativeTime(sync.lastSavedAt, now)}` : "");
  } else if (sync.lastSavedAt) status = `Last saved ${relativeTime(sync.lastSavedAt, now)}`;
  else status = "Not saved to a file yet";

  return (
    <div className="row">
      <span className="save-status" data-testid="save-status" aria-live="polite">
        {status}
        {sync.dirty && sync.link !== "linked" ? " · unsaved changes" : ""}
      </span>
      {sync.supportsFileLink && sync.link === "none" && (
        <button className="btn btn-primary" onClick={() => void saveToNewFile()}>
          Save to file…
        </button>
      )}
      <button className="btn" onClick={opener.open}>
        Open file…
      </button>
      <button className="btn" onClick={() => void exportDownload().then(() => toast("Backup copy downloaded."))}>
        {sync.supportsFileLink ? "Download a copy" : "Save (download)"}
      </button>
      {opener.element}
    </div>
  );
}

export function DataBanners() {
  const sync = useSync();
  const now = useNow(60_000);
  const clientCount = useLiveQuery(() => db.clients.count(), [], 0);
  const [persisted, setPersisted] = useState<boolean | null>(null);

  useEffect(() => {
    navigator.storage?.persisted?.().then(setPersisted).catch(() => setPersisted(null));
  }, []);

  return (
    <>
      {sync.link === "needs-permission" && (
        <div className="banner banner-warn" role="alert">
          <span>
            Autosave to <strong>{sync.fileName}</strong> is paused. Your browser asks for permission again after it restarts.
          </span>
          <button className="btn" onClick={() => void reconnectFile()}>
            Resume autosave
          </button>
        </div>
      )}
      {sync.error && (
        <div className="banner banner-danger" role="alert">
          <span>{sync.error}</span>
          <button className="btn" onClick={() => void saveToNewFile()}>
            Save to a different file…
          </button>
        </div>
      )}
      {clientCount > 0 && sync.link !== "linked" && backupOverdue(sync, now) && (
        <div className="banner banner-warn" data-testid="backup-reminder">
          <span>
            {sync.lastSavedAt
              ? `You have not saved a backup in more than ${BACKUP_REMINDER_DAYS} days.`
              : "Your data is only in this browser. Save it to a file so you have a backup."}
          </span>
          <button className="btn" onClick={() => void (sync.supportsFileLink ? saveToNewFile() : exportDownload())}>
            Save now
          </button>
        </div>
      )}
      {persisted === false && clientCount > 0 && (
        <div className="banner banner-info small">
          The browser has not promised to keep this data permanently. Keep saving to a file as your backup.
        </div>
      )}
    </>
  );
}
