import { db, DATA_TABLES } from "../db/db";
import { getSettings, saveSettings } from "../db/repo";
import type { BaseEntity } from "../db/types";
import { generateDemoData } from "./demoData";

export async function loadDemoData(): Promise<void> {
  const demo = generateDemoData();
  const existingTypes = await db.serviceTypes.toArray();
  const typeIdMap = new Map<string, string>();
  const newTypes = demo.serviceTypes.filter((t) => {
    const match = existingTypes.find((e) => e.code === t.code && !e.deletedAt);
    if (match) typeIdMap.set(t.id, match.id);
    return !match;
  });
  const mapType = <T extends { serviceTypeId: string }>(r: T): T => ({
    ...r,
    serviceTypeId: typeIdMap.get(r.serviceTypeId) ?? r.serviceTypeId,
  });

  const settings = await getSettings();
  const customFieldNames = [
    ...new Set([...settings.customFieldNames, ...demo.clients.flatMap((c) => Object.keys(c.customFields))]),
  ];

  await db.transaction("rw", [db.serviceTypes, db.staff, db.clients, db.assignments, db.authorizations, db.sessions, db.goalDataPoints, db.settings], async () => {
    await db.serviceTypes.bulkAdd(newTypes);
    await db.staff.bulkAdd(demo.staff);
    await db.clients.bulkAdd(demo.clients);
    await db.assignments.bulkAdd(demo.assignments);
    await db.authorizations.bulkAdd(demo.authorizations.map(mapType));
    await db.sessions.bulkAdd(demo.sessions.map(mapType));
    await db.goalDataPoints.bulkAdd(demo.goalDataPoints);
    await saveSettings({ customFieldNames });
  });
}

export async function hasDemoData(): Promise<boolean> {
  return (await db.clients.filter((c) => !!c.demo).count()) > 0;
}

export async function clearDemoData(): Promise<void> {
  const tables = DATA_TABLES.filter((n) => n !== "settings").map((n) => db.table(n));
  await db.transaction("rw", tables, async () => {
    for (const t of tables) {
      const ids = (await t.toArray()).filter((r: BaseEntity) => r.demo).map((r: BaseEntity) => r.id);
      if (ids.length) await t.bulkDelete(ids);
    }
  });
}
