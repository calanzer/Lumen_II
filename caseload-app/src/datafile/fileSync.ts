import { db, DATA_TABLES, onDataChange, withoutChangeEvents } from "../db/db";
import { DATA_FILE_EXTENSION, parseDataFile, serializeTables, type TableDump } from "./format";

// Minimal File System Access API typings (Chromium only; not in TS's DOM lib).
interface FsWritable {
  write(data: string): Promise<void>;
  close(): Promise<void>;
}
interface FsFileHandle {
  name: string;
  getFile(): Promise<File>;
  createWritable(): Promise<FsWritable>;
  queryPermission(opts: { mode: "readwrite" }): Promise<PermissionState>;
  requestPermission(opts: { mode: "readwrite" }): Promise<PermissionState>;
}
type PickerOpts = {
  suggestedName?: string;
  types?: { description: string; accept: Record<string, string[]> }[];
  excludeAcceptAllOption?: boolean;
};
type FsWindow = Window & {
  showSaveFilePicker?: (o?: PickerOpts) => Promise<FsFileHandle>;
  showOpenFilePicker?: (o?: PickerOpts & { multiple?: boolean }) => Promise<FsFileHandle[]>;
};

const fsWindow = window as FsWindow;
const PICKER_TYPES = [
  { description: "Caseload Tracker data", accept: { "application/json": [DATA_FILE_EXTENSION, ".json"] } },
];

export const BACKUP_REMINDER_DAYS = 7;

export type LinkState = "none" | "linked" | "needs-permission";

export interface SyncState {
  supportsFileLink: boolean;
  link: LinkState;
  fileName: string | null;
  lastSavedAt: string | null;
  dirty: boolean;
  saving: boolean;
  error: string | null;
}

let state: SyncState = {
  supportsFileLink: typeof fsWindow.showSaveFilePicker === "function",
  link: "none",
  fileName: null,
  lastSavedAt: null,
  dirty: false,
  saving: false,
  error: null,
};
let handle: FsFileHandle | null = null;
const subscribers = new Set<() => void>();
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function set(patch: Partial<SyncState>) {
  state = { ...state, ...patch };
  for (const fn of subscribers) fn();
}

export function subscribeSync(fn: () => void): () => void {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

export function getSyncState(): SyncState {
  return state;
}

async function setMeta(key: string, value: unknown) {
  await db.meta.put({ key, value });
}

// If the handle cannot be stored, autosave still works until the browser closes.
async function rememberHandle(h: FsFileHandle) {
  try {
    await setMeta("fileHandle", h);
  } catch {
    /* handle not storable in this browser */
  }
}

async function getMeta<T>(key: string): Promise<T | undefined> {
  return (await db.meta.get(key))?.value as T | undefined;
}

export async function dumpDatabase(): Promise<TableDump> {
  const out: TableDump = {};
  for (const name of DATA_TABLES) {
    out[name] = (await db.table(name).toArray()) as Record<string, unknown>[];
  }
  return out;
}

export async function replaceDatabase(tables: TableDump): Promise<void> {
  await withoutChangeEvents(() =>
    db.transaction("rw", DATA_TABLES.map((n) => db.table(n)), async () => {
      for (const name of DATA_TABLES) {
        const t = db.table(name);
        await t.clear();
        const rows = tables[name] ?? [];
        if (rows.length) await t.bulkPut(rows);
      }
    }),
  );
}

async function markSaved(fileName: string | null) {
  const at = new Date().toISOString();
  await setMeta("lastSavedAt", at);
  await setMeta("dirty", false);
  set({ lastSavedAt: at, dirty: false, saving: false, error: null, fileName: fileName ?? state.fileName });
}

async function writeHandle(h: FsFileHandle) {
  set({ saving: true });
  try {
    const text = await serializeTables(await dumpDatabase());
    const w = await h.createWritable();
    await w.write(text);
    await w.close();
    await markSaved(h.name);
  } catch (e) {
    set({ saving: false, error: `Could not save to ${h.name}: ${(e as Error).message}` });
  }
}

function scheduleAutosave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveTimer = null;
    if (handle && state.link === "linked") void writeHandle(handle);
  }, 1500);
}

export async function initSync(): Promise<void> {
  const [h, lastSavedAt, dirty] = await Promise.all([
    getMeta<FsFileHandle>("fileHandle"),
    getMeta<string>("lastSavedAt"),
    getMeta<boolean>("dirty"),
  ]);
  set({ lastSavedAt: lastSavedAt ?? null, dirty: !!dirty });
  if (h && state.supportsFileLink) {
    handle = h;
    let perm: PermissionState = "prompt";
    try {
      perm = await h.queryPermission({ mode: "readwrite" });
    } catch {
      perm = "prompt";
    }
    set({ fileName: h.name, link: perm === "granted" ? "linked" : "needs-permission" });
    if (perm === "granted" && state.dirty) scheduleAutosave();
  }
  onDataChange(() => {
    // Deferred: changes fire inside other tables' transactions, which do not include `meta`.
    if (!state.dirty) setTimeout(() => void setMeta("dirty", true).catch(() => null), 0);
    set({ dirty: true });
    scheduleAutosave();
  });
}

function isAbort(e: unknown) {
  return e instanceof DOMException && e.name === "AbortError";
}

export async function saveToNewFile(): Promise<void> {
  if (!fsWindow.showSaveFilePicker) return exportDownload();
  try {
    const h = await fsWindow.showSaveFilePicker({
      suggestedName: `caseload-data${DATA_FILE_EXTENSION}`,
      types: PICKER_TYPES,
    });
    handle = h;
    await rememberHandle(h);
    set({ link: "linked", fileName: h.name });
    await writeHandle(h);
  } catch (e) {
    if (!isAbort(e)) set({ error: (e as Error).message });
  }
}

export async function reconnectFile(): Promise<void> {
  if (!handle) return;
  const perm = await handle.requestPermission({ mode: "readwrite" });
  if (perm === "granted") {
    set({ link: "linked" });
    if (state.dirty) await writeHandle(handle);
  }
}

export async function unlinkFile(): Promise<void> {
  handle = null;
  await db.meta.delete("fileHandle");
  set({ link: "none", fileName: null });
}

async function loadText(text: string) {
  const { tables } = parseDataFile(text);
  await replaceDatabase(tables);
}

// Replaces all data in the browser with the file's contents. Callers confirm first.
export async function openFromPicker(): Promise<boolean> {
  if (!fsWindow.showOpenFilePicker) return false;
  try {
    const [h] = await fsWindow.showOpenFilePicker({ types: PICKER_TYPES, multiple: false });
    await loadText(await (await h.getFile()).text());
    handle = h;
    await rememberHandle(h);
    let perm: PermissionState = "prompt";
    try {
      perm = await h.requestPermission({ mode: "readwrite" });
    } catch {
      perm = "denied";
    }
    set({ fileName: h.name, link: perm === "granted" ? "linked" : "needs-permission" });
    await markSaved(h.name);
    return true;
  } catch (e) {
    if (isAbort(e)) return false;
    set({ error: (e as Error).message });
    throw e;
  }
}

export async function importFromFile(file: File): Promise<void> {
  await loadText(await file.text());
  await markSaved(null);
}

export async function exportDownload(): Promise<void> {
  const text = await serializeTables(await dumpDatabase());
  const stamp = new Date().toISOString().slice(0, 10);
  downloadBlob(new Blob([text], { type: "application/json" }), `caseload-data-${stamp}${DATA_FILE_EXTENSION}`);
  await markSaved(null);
}

export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export async function deleteAllData(): Promise<void> {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = null;
  handle = null;
  await replaceDatabase({});
  await db.meta.clear();
  set({ link: "none", fileName: null, lastSavedAt: null, dirty: false, error: null });
}

export function backupOverdue(s: SyncState, now = Date.now()): boolean {
  if (!s.lastSavedAt) return true;
  return now - Date.parse(s.lastSavedAt) > BACKUP_REMINDER_DAYS * 86_400_000;
}

export async function requestPersistentStorage(): Promise<boolean | null> {
  if (!navigator.storage?.persist) return null;
  if (await navigator.storage.persisted()) return true;
  return navigator.storage.persist();
}
