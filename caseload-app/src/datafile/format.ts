import { DATA_TABLES, type DataTableName } from "../db/db";

export const DATA_FORMAT = "caseload-tracker-data";
export const DATA_VERSION = 1;
export const DATA_FILE_EXTENSION = ".caseload.json";

export type TableDump = Partial<Record<DataTableName, Record<string, unknown>[]>>;

export interface DataFile {
  format: typeof DATA_FORMAT;
  version: number;
  savedAt: string;
  tables: TableDump;
}

interface EncodedBlob {
  __blob: string;
  type: string;
}

function bytesToBase64(bytes: Uint8Array): string {
  let s = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    s += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(s);
}

function base64ToBytes(b64: string): Uint8Array {
  const s = atob(b64);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

function isEncodedBlob(v: unknown): v is EncodedBlob {
  return typeof v === "object" && v !== null && typeof (v as EncodedBlob).__blob === "string";
}

async function encodeRow(row: Record<string, unknown>): Promise<Record<string, unknown>> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) {
    if (v instanceof Blob) {
      out[k] = { __blob: bytesToBase64(new Uint8Array(await v.arrayBuffer())), type: v.type };
    } else {
      out[k] = v;
    }
  }
  return out;
}

function decodeRow(row: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) {
    out[k] = isEncodedBlob(v) ? new Blob([base64ToBytes(v.__blob)], { type: v.type }) : v;
  }
  return out;
}

export async function serializeTables(tables: TableDump, savedAt = new Date().toISOString()): Promise<string> {
  const encoded: TableDump = {};
  for (const name of DATA_TABLES) {
    const rows = tables[name] ?? [];
    encoded[name] = await Promise.all(rows.map(encodeRow));
  }
  const file: DataFile = { format: DATA_FORMAT, version: DATA_VERSION, savedAt, tables: encoded };
  return JSON.stringify(file);
}

export class DataFileError extends Error {}

export function parseDataFile(text: string): { savedAt: string; tables: TableDump } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new DataFileError("This file is not a Caseload Tracker data file (it could not be read as data).");
  }
  const file = parsed as Partial<DataFile> & { encrypted?: boolean };
  if (file.encrypted) {
    throw new DataFileError("This data file is encrypted. Enter its passphrase to open it.");
  }
  if (file.format !== DATA_FORMAT || typeof file.tables !== "object" || file.tables === null) {
    throw new DataFileError("This file is not a Caseload Tracker data file.");
  }
  if (typeof file.version !== "number" || file.version > DATA_VERSION) {
    throw new DataFileError("This data file was made by a newer version of the app.");
  }
  const tables: TableDump = {};
  for (const name of DATA_TABLES) {
    const rows = (file.tables as TableDump)[name];
    tables[name] = Array.isArray(rows) ? rows.map(decodeRow) : [];
  }
  return { savedAt: file.savedAt ?? "", tables };
}
