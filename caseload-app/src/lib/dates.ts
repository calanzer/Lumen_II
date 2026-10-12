import type { HHMM, ISODate } from "../db/types";

const DAY_MS = 86_400_000;

// Calendar dates are handled as UTC midnights so DST never shifts a day.
export function parseISODate(d: ISODate): number {
  const [y, m, day] = d.split("-").map(Number);
  return Date.UTC(y, m - 1, day);
}

export function formatISODate(ms: number): ISODate {
  return new Date(ms).toISOString().slice(0, 10);
}

export function todayISO(now = new Date()): ISODate {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDays(d: ISODate, n: number): ISODate {
  return formatISODate(parseISODate(d) + n * DAY_MS);
}

// Whole days from a to b (b - a).
export function diffDays(a: ISODate, b: ISODate): number {
  return Math.round((parseISODate(b) - parseISODate(a)) / DAY_MS);
}

export function dayOfWeek(d: ISODate): number {
  return new Date(parseISODate(d)).getUTCDay();
}

export function startOfWeek(d: ISODate, weekStartsOn: 0 | 1): ISODate {
  const offset = (dayOfWeek(d) - weekStartsOn + 7) % 7;
  return addDays(d, -offset);
}

export function monthKey(d: ISODate): string {
  return d.slice(0, 7);
}

export function timeToMinutes(t: HHMM): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

export function minutesToTime(min: number): HHMM {
  const m = ((min % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatShortDate(d: ISODate): string {
  const [y, m, day] = d.split("-").map(Number);
  return `${MONTHS[m - 1]} ${day}, ${y}`;
}
