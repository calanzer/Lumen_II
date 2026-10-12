import type { ServiceType, Settings } from "./types";

export const DEFAULT_SETTINGS: Settings = {
  id: "settings",
  bcbaName: "",
  bcbaCredential: "BCBA",
  paceGreenAt: 0.95,
  paceYellowAt: 0.85,
  notSeenDays: 14,
  supervisionTargetPercent: 5,
  minContactsPerMonth: 2,
  minObservationsPerMonth: 1,
  reassessmentLeadDays: 30,
  reassessmentLeadDaysByPayer: {},
  weekStartsOn: 1,
  defaultReportPeriodDays: 180,
  markAutoFilledValues: false,
  customFieldNames: [],
  firstRunComplete: false,
};

export type ServiceTypeDraft = Omit<ServiceType, "id" | "createdAt" | "updatedAt">;

export const DEFAULT_SERVICE_TYPES: ServiceTypeDraft[] = [
  {
    code: "97153",
    label: "Direct therapy (technician)",
    minutesPerUnit: 15,
    countsAsRbtDirect: true,
    countsAsSupervision: false,
    deliveredBy: "RBT",
  },
  {
    code: "97155",
    label: "Protocol modification (BCBA)",
    minutesPerUnit: 15,
    countsAsRbtDirect: false,
    countsAsSupervision: true,
    deliveredBy: "BCBA",
  },
  {
    code: "97156",
    label: "Parent / caregiver training",
    minutesPerUnit: 15,
    countsAsRbtDirect: false,
    countsAsSupervision: false,
    deliveredBy: "BCBA",
  },
  {
    code: "97151",
    label: "Assessment",
    minutesPerUnit: 15,
    countsAsRbtDirect: false,
    countsAsSupervision: false,
    deliveredBy: "BCBA",
  },
];
