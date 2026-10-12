import Dexie, { type Table } from "dexie";
import type {
  Assignment,
  Authorization,
  Client,
  Deadline,
  GeneratedReport,
  GoalDataPoint,
  ImportBatch,
  ImportProfile,
  MetaRow,
  ReportTemplate,
  ServiceType,
  Session,
  Settings,
  StaffMember,
  SupervisionOverride,
  WeekAction,
} from "./types";

export const DB_NAME = "caseload-tracker";

export class CaseloadDB extends Dexie {
  clients!: Table<Client, string>;
  authorizations!: Table<Authorization, string>;
  serviceTypes!: Table<ServiceType, string>;
  staff!: Table<StaffMember, string>;
  assignments!: Table<Assignment, string>;
  sessions!: Table<Session, string>;
  deadlines!: Table<Deadline, string>;
  importProfiles!: Table<ImportProfile, string>;
  importBatches!: Table<ImportBatch, string>;
  reportTemplates!: Table<ReportTemplate, string>;
  generatedReports!: Table<GeneratedReport, string>;
  goalDataPoints!: Table<GoalDataPoint, string>;
  supervisionOverrides!: Table<SupervisionOverride, string>;
  weekActions!: Table<WeekAction, string>;
  settings!: Table<Settings, string>;
  meta!: Table<MetaRow, string>;

  constructor(name = DB_NAME) {
    super(name);
    this.version(1).stores({
      clients: "id, &code, status",
      authorizations: "id, clientId, serviceTypeId, endDate",
      serviceTypes: "id, &code",
      staff: "id, role",
      assignments: "id, clientId, staffId",
      sessions: "id, clientId, staffId, date, status, importBatchId, supervisedStaffId",
      deadlines: "id, clientId, dueDate, status, authorizationId",
      importProfiles: "id, targetEntity",
      importBatches: "id, importedAt",
      reportTemplates: "id",
      generatedReports: "id, clientId, templateId, generatedAt",
      goalDataPoints: "id, clientId, goalName, date",
      supervisionOverrides: "id, [staffId+month]",
      weekActions: "id, weekStart, itemKey",
      settings: "id",
      meta: "key",
    });
  }
}

// Tables included in the data file. `meta` is per-browser state (file handle, timestamps).
export const DATA_TABLES = [
  "clients",
  "authorizations",
  "serviceTypes",
  "staff",
  "assignments",
  "sessions",
  "deadlines",
  "importProfiles",
  "importBatches",
  "reportTemplates",
  "generatedReports",
  "goalDataPoints",
  "supervisionOverrides",
  "weekActions",
  "settings",
] as const;

export type DataTableName = (typeof DATA_TABLES)[number];

export const db = new CaseloadDB();

type ChangeListener = () => void;
const listeners = new Set<ChangeListener>();

export function onDataChange(fn: ChangeListener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

let suppressed = 0;

// Writes made while suppressed (e.g. loading a data file) do not trigger autosave.
export async function withoutChangeEvents<T>(fn: () => Promise<T>): Promise<T> {
  suppressed++;
  try {
    return await fn();
  } finally {
    suppressed--;
  }
}

function emitChange() {
  if (suppressed > 0) return;
  for (const fn of listeners) fn();
}

for (const name of DATA_TABLES) {
  const table = db.table(name);
  table.hook("creating", function () {
    this.onsuccess = emitChange;
  });
  table.hook("updating", function () {
    this.onsuccess = emitChange;
  });
  table.hook("deleting", function () {
    this.onsuccess = emitChange;
  });
}
