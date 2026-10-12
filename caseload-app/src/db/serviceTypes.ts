import { db } from "./db";
import { create, softDelete, update } from "./repo";
import type { ServiceType } from "./types";
import type { EditableServiceType } from "../components/SettingsFields";

export function validateServiceTypes(rows: EditableServiceType[]): string | null {
  if (!rows.length) return "Add at least one service type.";
  const codes = rows.map((r) => r.code.trim());
  if (codes.some((c) => !c)) return "Every service type needs a code.";
  const dup = codes.find((c, i) => codes.indexOf(c) !== i);
  if (dup) return `The code ${dup} is listed twice.`;
  if (rows.some((r) => !(r.minutesPerUnit > 0))) return "Minutes per unit must be more than zero.";
  return null;
}

// Removed types are soft-deleted so existing sessions and authorizations keep their label.
export async function saveServiceTypes(rows: EditableServiceType[]): Promise<void> {
  const existing = (await db.serviceTypes.toArray()).filter((s) => !s.deletedAt);
  const keep = new Set(rows.map((r) => r.id).filter(Boolean));
  for (const old of existing) {
    if (!keep.has(old.id)) await softDelete("serviceTypes", old.id);
  }
  for (const r of rows) {
    const { id, ...fields } = r;
    const clean = { ...fields, code: fields.code.trim(), label: fields.label.trim() };
    if (id) await update<ServiceType>("serviceTypes", id, clean, { manual: false });
    else {
      const revived = (await db.serviceTypes.where("code").equals(clean.code).first());
      if (revived) await update<ServiceType>("serviceTypes", revived.id, { ...clean, deletedAt: null }, { manual: false });
      else await create<ServiceType>("serviceTypes", clean);
    }
  }
}
