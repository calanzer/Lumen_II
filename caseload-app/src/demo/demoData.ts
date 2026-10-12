import { DEFAULT_SERVICE_TYPES } from "../db/defaults";
import type {
  Assignment,
  Authorization,
  Client,
  GoalDataPoint,
  ServiceType,
  Session,
  SessionStatus,
  StaffMember,
} from "../db/types";
import { addDays, dayOfWeek, minutesToTime, timeToMinutes, todayISO } from "../lib/dates";

// All demo data is synthetic. Codes and initials are invented.

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface DemoDataset {
  serviceTypes: ServiceType[];
  staff: StaffMember[];
  clients: Client[];
  assignments: Assignment[];
  authorizations: Authorization[];
  sessions: Session[];
  goalDataPoints: GoalDataPoint[];
}

interface ClientPlan {
  code: string;
  location: Client["location"];
  // Days ago the current 6-month authorization started.
  startedDaysAgo: number;
  rbtHoursPerWeek: number;
  bcbaHoursPerWeek: number;
  // Fraction of planned sessions that actually happen; drives red/yellow/green.
  deliveryRate: number;
  // Authorized direct hours set too low, so delivered + scheduled exceeds it.
  overAuthorized?: boolean;
  rbts: number[];
  daysOfWeek: number[];
  startTime: string;
  tags: string[];
  school?: string;
}

const PLANS: ClientPlan[] = [
  { code: "K7", location: "home", startedDaysAgo: 120, rbtHoursPerWeek: 15, bcbaHoursPerWeek: 2, deliveryRate: 0.78, rbts: [0, 1], daysOfWeek: [1, 3, 5], startTime: "15:00", tags: ["new-goals"] },
  { code: "C3", location: "clinic", startedDaysAgo: 160, rbtHoursPerWeek: 20, bcbaHoursPerWeek: 2.5, deliveryRate: 0.97, rbts: [1, 2], daysOfWeek: [1, 2, 3, 4], startTime: "09:00", tags: [] },
  { code: "B2", location: "school", startedDaysAgo: 60, rbtHoursPerWeek: 10, bcbaHoursPerWeek: 1.5, deliveryRate: 0.9, rbts: [2], daysOfWeek: [2, 4], startTime: "12:30", tags: ["school-team"] },
  { code: "M4", location: "home", startedDaysAgo: 30, rbtHoursPerWeek: 12, bcbaHoursPerWeek: 2, deliveryRate: 0.97, overAuthorized: true, rbts: [3], daysOfWeek: [1, 3, 5], startTime: "16:00", tags: [] },
  { code: "T9", location: "clinic", startedDaysAgo: 90, rbtHoursPerWeek: 25, bcbaHoursPerWeek: 3, deliveryRate: 0.96, rbts: [0, 4], daysOfWeek: [1, 2, 3, 4, 5], startTime: "08:30", tags: [] },
  { code: "R5", location: "home", startedDaysAgo: 150, rbtHoursPerWeek: 8, bcbaHoursPerWeek: 1, deliveryRate: 0.88, rbts: [4], daysOfWeek: [2, 4], startTime: "17:00", tags: ["spanish"] },
  { code: "J1", location: "clinic", startedDaysAgo: 45, rbtHoursPerWeek: 18, bcbaHoursPerWeek: 2, deliveryRate: 0.99, rbts: [5, 3], daysOfWeek: [1, 2, 4, 5], startTime: "13:00", tags: [] },
  { code: "A8", location: "home", startedDaysAgo: 170, rbtHoursPerWeek: 10, bcbaHoursPerWeek: 1.5, deliveryRate: 0.93, rbts: [5], daysOfWeek: [1, 4], startTime: "15:30", tags: [] },
  { code: "L6", location: "school", startedDaysAgo: 15, rbtHoursPerWeek: 10, bcbaHoursPerWeek: 2, deliveryRate: 0.8, rbts: [2, 4], daysOfWeek: [3, 5], startTime: "10:00", tags: ["new-client"] },
];

const RBTS = ["M.R.", "J.T.", "A.P.", "S.K.", "D.L.", "N.V."];

function stamp<T>(row: T, id: string, now: string): T & { id: string; createdAt: string; updatedAt: string; deletedAt: null; demo: true } {
  return { ...row, id, createdAt: now, updatedAt: now, deletedAt: null, demo: true };
}

export function generateDemoData(today = todayISO(), seed = 42): DemoDataset {
  const rand = mulberry32(seed);
  const now = new Date().toISOString();
  let n = 0;
  const id = (prefix: string) => `demo-${prefix}-${++n}`;

  const serviceTypes: ServiceType[] = DEFAULT_SERVICE_TYPES.map((s) => stamp({ ...s }, id("st"), now));
  const [direct, protocol, parent] = serviceTypes;

  const bcba: StaffMember = stamp({ displayName: "Me (BCBA)", role: "BCBA", targetWeeklyHours: 40, active: true }, id("staff"), now);
  const rbts: StaffMember[] = RBTS.map((name, i) =>
    stamp({ displayName: name, role: "RBT" as const, targetWeeklyHours: [30, 25, 28, 20, 32, 24][i], active: true }, id("staff"), now),
  );

  const clients: Client[] = [];
  const assignments: Assignment[] = [];
  const authorizations: Authorization[] = [];
  const sessions: Session[] = [];
  const goalDataPoints: GoalDataPoint[] = [];

  const addSession = (s: Omit<Session, "id" | "createdAt" | "updatedAt">) => sessions.push(stamp(s, id("ses"), now));

  for (const plan of PLANS) {
    const start = addDays(today, -plan.startedDaysAgo);
    const end = addDays(start, 181);
    const client: Client = stamp(
      {
        code: plan.code,
        status: "active" as const,
        location: plan.location,
        notes: "",
        tags: plan.tags,
        customFields: { "Funding source": rand() < 0.5 ? "Commercial" : "Medicaid", "Intake month": start.slice(0, 7) },
      },
      id("client"),
      now,
    );
    clients.push(client);

    for (const ri of plan.rbts) {
      assignments.push(stamp({ clientId: client.id, staffId: rbts[ri].id, startDate: start, endDate: null }, id("asg"), now));
    }

    const weeks = 26;
    const payer = rand() < 0.5 ? "Synthetic Health Plan A" : "Synthetic Health Plan B";
    authorizations.push(
      stamp({ clientId: client.id, serviceTypeId: direct.id, amount: plan.overAuthorized ? 70 : plan.rbtHoursPerWeek * weeks, amountUnit: "hours" as const, startDate: start, endDate: end, payer, notes: "" }, id("auth"), now),
      stamp({ clientId: client.id, serviceTypeId: protocol.id, amount: plan.bcbaHoursPerWeek * weeks * 4, amountUnit: "units" as const, startDate: start, endDate: end, payer, notes: "" }, id("auth"), now),
      stamp({ clientId: client.id, serviceTypeId: parent.id, amount: 24, amountUnit: "hours" as const, startDate: start, endDate: end, payer, notes: "" }, id("auth"), now),
    );

    const sessionMinutes = Math.round((plan.rbtHoursPerWeek * 60) / plan.daysOfWeek.length / 15) * 15;
    const startMin = timeToMinutes(plan.startTime);
    const horizon = addDays(today, 21);
    let week = 0;
    for (let d = start; d <= horizon && d <= end; d = addDays(d, 1)) {
      const dow = dayOfWeek(d);
      if (dow === 1) week++;
      if (!plan.daysOfWeek.includes(dow)) continue;
      const future = d > today;
      const rbt = rbts[plan.rbts[(week + dow) % plan.rbts.length]];
      const status = future ? "scheduled" : pickStatus(rand, plan.deliveryRate);
      const cancelledBy = status === "cancelled" ? (["client", "staff", "provider"] as const)[Math.floor(rand() * 3)] : status === "no-show" ? ("client" as const) : null;
      addSession({
        clientId: client.id, staffId: rbt.id, serviceTypeId: direct.id, date: d,
        startTime: plan.startTime, endTime: minutesToTime(startMin + sessionMinutes), durationMinutes: sessionMinutes,
        status, cancelledBy, cancelNoticeHours: cancelledBy ? Math.floor(rand() * 48) : null,
        supervisedStaffId: null, observation: false, source: "manual", importBatchId: null,
      });

      // BCBA joins the first session day each week, overlapping the technician's session.
      const firstDay = dow === plan.daysOfWeek[0];
      if (firstDay) {
        const bcbaMin = Math.min(sessionMinutes, Math.round((plan.bcbaHoursPerWeek * 60) / 15) * 15);
        const skipped = !future && plan.code === "L6" && rand() < 0.7;
        if (!skipped) {
          const bStatus: SessionStatus = future ? "scheduled" : status === "completed" && rand() < Math.min(1, plan.deliveryRate + 0.05) ? "completed" : status === "completed" ? "cancelled" : status;
          addSession({
            clientId: client.id, staffId: bcba.id, serviceTypeId: protocol.id, date: d,
            startTime: minutesToTime(startMin + 30), endTime: minutesToTime(startMin + 30 + bcbaMin), durationMinutes: bcbaMin,
            status: bStatus, cancelledBy: bStatus === "cancelled" ? "provider" : bStatus === "no-show" ? "client" : null, cancelNoticeHours: null,
            supervisedStaffId: week % 3 === 0 ? rbt.id : null, observation: week % 4 === 0, source: "manual", importBatchId: null,
          });
        }
      }
      // Parent training every other week on the last session day.
      if (dow === plan.daysOfWeek[plan.daysOfWeek.length - 1] && week % 2 === 0) {
        addSession({
          clientId: client.id, staffId: bcba.id, serviceTypeId: parent.id, date: d,
          startTime: minutesToTime(startMin + sessionMinutes), endTime: minutesToTime(startMin + sessionMinutes + 60), durationMinutes: 60,
          status: future ? "scheduled" : pickStatus(rand, 0.92), cancelledBy: null, cancelNoticeHours: null,
          supervisedStaffId: null, observation: false, source: "manual", importBatchId: null,
        });
      }
    }

    // Goal data for the first three clients, weekly probes trending upward.
    if (clients.length <= 3) {
      const goals = ["Mands for items", "Follows 2-step instructions", "Tolerates transitions"];
      goals.forEach((goal, gi) => {
        const baseline = 15 + gi * 10 + Math.floor(rand() * 10);
        for (let w = 0; w < Math.min(20, Math.floor(plan.startedDaysAgo / 7)); w++) {
          const value = Math.min(100, Math.round(baseline + w * (2 + gi) + (rand() - 0.5) * 8));
          goalDataPoints.push(
            stamp({ clientId: client.id, goalName: goal, date: addDays(start, w * 7 + 2), measure: "percent correct", value }, id("goal"), now),
          );
        }
      });
    }
  }

  for (const s of sessions) {
    if (s.status === "no-show" && !s.cancelledBy) s.cancelledBy = "client";
  }

  return { serviceTypes, staff: [bcba, ...rbts], clients, assignments, authorizations, sessions, goalDataPoints };
}

function pickStatus(rand: () => number, deliveryRate: number): SessionStatus {
  const r = rand();
  const completed = Math.min(0.97, deliveryRate);
  if (r < completed) return "completed";
  if (r < completed + (1 - completed) * 0.75) return "cancelled";
  return "no-show";
}
