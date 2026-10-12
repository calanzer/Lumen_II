import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { DataFileError, parseDataFile, serializeTables } from "../../src/datafile/format";
import { generateDemoData } from "../../src/demo/demoData";

describe("data file format", () => {
  it("round-trips rows, including binary template files", async () => {
    const bytes = new Uint8Array(70_000).map((_, i) => i % 251);
    const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    const text = await serializeTables({
      clients: [{ id: "c1", code: "K7", customFields: { School: "North" } }],
      reportTemplates: [{ id: "t1", name: "Progress", fileBlob: blob, detectedTokens: ["client_code"] }],
    });
    const { tables } = parseDataFile(text);
    expect(tables.clients).toEqual([{ id: "c1", code: "K7", customFields: { School: "North" } }]);
    const restored = tables.reportTemplates![0].fileBlob as Blob;
    expect(restored.type).toBe(blob.type);
    expect(new Uint8Array(await restored.arrayBuffer())).toEqual(bytes);
    expect(tables.sessions).toEqual([]);
  });

  it("rejects files that are not data files, with a plain message", () => {
    expect(() => parseDataFile("not json")).toThrow(DataFileError);
    expect(() => parseDataFile(JSON.stringify({ hello: 1 }))).toThrow(/not a Caseload Tracker data file/);
    expect(() => parseDataFile(JSON.stringify({ format: "caseload-tracker-data", version: 99, tables: {} }))).toThrow(/newer version/);
    expect(() => parseDataFile(JSON.stringify({ encrypted: true }))).toThrow(/passphrase/);
  });
});

describe("demo data", () => {
  it("is deterministic for a given day and marks every row as demo", () => {
    const a = generateDemoData("2026-10-12", 7);
    const b = generateDemoData("2026-10-12", 7);
    expect(a.sessions.map((s) => [s.date, s.status])).toEqual(b.sessions.map((s) => [s.date, s.status]));
    const all = [...a.clients, ...a.sessions, ...a.authorizations, ...a.staff, ...a.assignments, ...a.goalDataPoints];
    expect(all.every((r) => r.demo === true)).toBe(true);
    expect(new Set(a.clients.map((c) => c.code)).size).toBe(a.clients.length);
  });

  it("references only ids that exist", () => {
    const d = generateDemoData("2026-10-12");
    const clientIds = new Set(d.clients.map((c) => c.id));
    const staffIds = new Set(d.staff.map((s) => s.id));
    const typeIds = new Set(d.serviceTypes.map((t) => t.id));
    for (const s of d.sessions) {
      expect(clientIds.has(s.clientId)).toBe(true);
      expect(staffIds.has(s.staffId!)).toBe(true);
      expect(typeIds.has(s.serviceTypeId)).toBe(true);
    }
  });
});
