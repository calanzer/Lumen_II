import type { Table } from "dexie";
import { db, type DataTableName } from "./db";
import { DEFAULT_SETTINGS } from "./defaults";
import type { BaseEntity, Settings } from "./types";

export function newId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

export function nowISO(): string {
  return new Date().toISOString();
}

type EntityTable = Exclude<DataTableName, "settings">;

function table<T extends BaseEntity>(name: EntityTable): Table<T, string> {
  return db.table(name) as Table<T, string>;
}

export type Draft<T extends BaseEntity> = Omit<T, "id" | "createdAt" | "updatedAt"> &
  Partial<Pick<T, "id">>;

export function stamp<T extends BaseEntity>(draft: Draft<T>): T {
  const now = nowISO();
  return { ...draft, id: draft.id ?? newId(), createdAt: now, updatedAt: now, deletedAt: null } as T;
}

export async function create<T extends BaseEntity>(name: EntityTable, draft: Draft<T>): Promise<T> {
  const row = stamp<T>(draft);
  await table<T>(name).add(row);
  return row;
}

// `manual` marks the changed fields so a later re-import does not overwrite them.
export async function update<T extends BaseEntity>(
  name: EntityTable,
  id: string,
  changes: Partial<T>,
  { manual = true }: { manual?: boolean } = {},
): Promise<void> {
  const t = table<T>(name);
  const existing = await t.get(id);
  if (!existing) throw new Error(`${name} ${id} not found`);
  const manualEdits = manual
    ? [...new Set([...(existing.manualEdits ?? []), ...Object.keys(changes)])]
    : existing.manualEdits;
  await t.put({ ...existing, ...changes, manualEdits, updatedAt: nowISO() });
}

export async function softDelete(name: EntityTable, id: string): Promise<void> {
  await table(name).update(id, { deletedAt: nowISO(), updatedAt: nowISO() });
}

export async function restore(name: EntityTable, id: string): Promise<void> {
  await table(name).update(id, { deletedAt: null, updatedAt: nowISO() });
}

export async function listLive<T extends BaseEntity>(name: EntityTable): Promise<T[]> {
  return (await table<T>(name).toArray()).filter((r) => !r.deletedAt);
}

export async function getSettings(): Promise<Settings> {
  const s = await db.settings.get("settings");
  return { ...DEFAULT_SETTINGS, ...s };
}

export async function saveSettings(changes: Partial<Settings>): Promise<void> {
  const current = await getSettings();
  await db.settings.put({ ...current, ...changes, id: "settings" });
}
