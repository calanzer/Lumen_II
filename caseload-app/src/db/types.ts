export type ID = string;
export type ISODate = string; // YYYY-MM-DD
export type ISODateTime = string;
export type HHMM = string; // 24h "HH:MM"

export interface BaseEntity {
  id: ID;
  createdAt: ISODateTime;
  updatedAt: ISODateTime;
  deletedAt?: ISODateTime | null;
  demo?: boolean;
  // Fields the user changed by hand; re-import leaves these alone unless she chooses to overwrite.
  manualEdits?: string[];
}

export type ClientStatus = "active" | "paused" | "discharged";
export type ClientLocation = "home" | "clinic" | "school" | "other";

export interface Client extends BaseEntity {
  code: string;
  status: ClientStatus;
  location: ClientLocation;
  notes: string;
  tags: string[];
  customFields: Record<string, string>;
}

export type AmountUnit = "hours" | "units";

export interface Authorization extends BaseEntity {
  clientId: ID;
  serviceTypeId: ID;
  amount: number;
  amountUnit: AmountUnit;
  startDate: ISODate;
  endDate: ISODate;
  payer: string;
  notes: string;
}

export type DeliveredBy = "BCBA" | "RBT" | "either";

export interface ServiceType extends BaseEntity {
  code: string;
  label: string;
  minutesPerUnit: number;
  countsAsRbtDirect: boolean;
  countsAsSupervision: boolean;
  deliveredBy: DeliveredBy;
}

export type StaffRole = "BCBA" | "RBT" | "other";

export interface StaffMember extends BaseEntity {
  displayName: string;
  role: StaffRole;
  targetWeeklyHours: number | null;
  active: boolean;
}

export interface Assignment extends BaseEntity {
  clientId: ID;
  staffId: ID;
  startDate: ISODate;
  endDate: ISODate | null;
}

export type SessionStatus = "scheduled" | "completed" | "cancelled" | "no-show";
export type CancelledBy = "client" | "staff" | "provider" | "unknown";

export interface Session extends BaseEntity {
  clientId: ID;
  staffId: ID | null;
  serviceTypeId: ID;
  date: ISODate;
  startTime: HHMM | null;
  endTime: HHMM | null;
  durationMinutes: number;
  status: SessionStatus;
  cancelledBy: CancelledBy | null;
  cancelNoticeHours: number | null;
  supervisedStaffId: ID | null;
  observation: boolean;
  source: "import" | "manual";
  importBatchId: ID | null;
  madeUpBySessionId?: ID | null;
}

export type DeadlineType = "auth-expiry" | "reassessment-due" | "custom";

export interface Deadline extends BaseEntity {
  clientId: ID | null;
  type: DeadlineType;
  dueDate: ISODate;
  status: "open" | "done";
  notes: string;
  title?: string;
  snoozedUntil?: ISODate | null;
  // Set on auto-generated deadlines so they can be regenerated when the authorization changes.
  authorizationId?: ID | null;
}

export type ImportTarget = "sessions" | "authorizations" | "clients" | "staff" | "goals";

export interface ImportProfile extends BaseEntity {
  name: string;
  targetEntity: ImportTarget;
  headers: string[];
  columnMap: Record<string, string>;
  valueMaps: Record<string, Record<string, string>>;
  dateFormat: string;
}

export interface ImportBatch extends BaseEntity {
  fileName: string;
  importedAt: ISODateTime;
  profileId: ID | null;
  targetEntity: ImportTarget;
  added: number;
  updated: number;
  skipped: number;
  undoneAt?: ISODateTime | null;
  // Prior versions of rows the batch updated, so undo restores them exactly.
  previous: Record<string, unknown>[];
}

export interface ReportTemplate extends BaseEntity {
  name: string;
  fileBlob: Blob;
  detectedTokens: string[];
}

export interface GeneratedReport extends BaseEntity {
  templateId: ID;
  clientId: ID;
  periodStart: ISODate;
  periodEnd: ISODate;
  generatedAt: ISODateTime;
  placeholderCount: number;
  fileName: string;
  fileBlob: Blob;
}

export interface GoalDataPoint extends BaseEntity {
  clientId: ID;
  goalName: string;
  date: ISODate;
  measure: string;
  value: number;
}

// Per technician per month (YYYY-MM). Null fields fall back to what the session data shows.
export interface SupervisionOverride extends BaseEntity {
  staffId: ID;
  month: string;
  supervisedMinutes: number | null;
  contactsMet: boolean | null;
  observationMet: boolean | null;
}

// Check-off / dismiss state for This Week items, keyed by the item's stable key.
export interface WeekAction extends BaseEntity {
  weekStart: ISODate;
  itemKey: string;
  state: "done" | "dismissed";
}

export interface Settings {
  id: "settings";
  bcbaName: string;
  bcbaCredential: string;
  paceGreenAt: number;
  paceYellowAt: number;
  notSeenDays: number;
  supervisionTargetPercent: number;
  minContactsPerMonth: number;
  minObservationsPerMonth: number;
  reassessmentLeadDays: number;
  reassessmentLeadDaysByPayer: Record<string, number>;
  weekStartsOn: 0 | 1;
  defaultReportPeriodDays: number;
  markAutoFilledValues: boolean;
  customFieldNames: string[];
  firstRunComplete: boolean;
}

export interface MetaRow {
  key: string;
  value: unknown;
}
