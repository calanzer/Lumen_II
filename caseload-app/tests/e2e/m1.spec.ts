import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { APP_URL, completeFirstRun, forceDownloadFallback, launchProfile, newProfileDir } from "./helpers";

const NAV = ["This Week", "Caseload", "Staff and Supervision", "Deadlines", "Cancellations", "Reports", "Import", "Settings"];

// Row counts per object store, read straight from IndexedDB.
async function tableCounts(page: Page): Promise<Record<string, number>> {
  return page.evaluate(
    () =>
      new Promise<Record<string, number>>((resolve, reject) => {
        const req = indexedDB.open("caseload-tracker");
        req.onerror = () => reject(req.error);
        req.onsuccess = () => {
          const idb = req.result;
          const names = Array.from(idb.objectStoreNames).filter((n) => n !== "meta");
          const tx = idb.transaction(names);
          const out: Record<string, number> = {};
          for (const n of names) {
            const c = tx.objectStore(n).count();
            c.onsuccess = () => (out[n] = c.result);
          }
          tx.oncomplete = () => resolve(out);
        };
      }),
  );
}

test("works offline and makes zero network requests", async () => {
  const { context, page, watch } = await launchProfile(newProfileDir(), { offline: true });
  await page.goto(APP_URL);
  await completeFirstRun(page, { demo: true });
  for (const label of NAV) {
    await page.getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: label })).toBeVisible();
  }
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download a copy" }).first().click();
  await download;

  // Prove the CSP actually blocks connections, not just that the app happens not to make any.
  const violated = await page.evaluate(async () => {
    const seen = new Promise<string>((res) =>
      document.addEventListener("securitypolicyviolation", (e) => res(e.effectiveDirective), { once: true }),
    );
    await fetch("https://example.com/").catch(() => null);
    return seen;
  });
  expect(violated).toBe("connect-src");
  expect(watch.external).toEqual([]);
  expect(watch.cspViolations.filter((v) => !v.includes("example.com"))).toEqual([]);
  await context.close();
});

test("data survives closing and reopening the browser", async () => {
  const dir = newProfileDir();
  let { context, page } = await launchProfile(dir);
  await page.goto(APP_URL);
  await completeFirstRun(page, { demo: true });
  const before = await tableCounts(page);
  expect(before.clients).toBeGreaterThan(0);
  expect(before.sessions).toBeGreaterThan(0);
  await context.close();

  ({ context, page } = await launchProfile(dir));
  await page.goto(APP_URL);
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  expect(await tableCounts(page)).toEqual(before);
  await page.getByRole("link", { name: "Settings" }).click();
  await expect(page.getByLabel("Your name")).toHaveValue("Test BCBA");
  await context.close();
});

test("a saved data file restores everything in a fresh browser profile", async () => {
  const first = await launchProfile(newProfileDir());
  await forceDownloadFallback(first.context);
  await first.page.goto(APP_URL);
  await completeFirstRun(first.page, { demo: true });
  const before = await tableCounts(first.page);
  await expect(first.page.getByTestId("backup-reminder")).toBeVisible();
  const dl = first.page.waitForEvent("download");
  await first.page.getByRole("button", { name: "Save (download)" }).click();
  const filePath = path.join(newProfileDir(), "backup.caseload.json");
  await (await dl).saveAs(filePath);
  await expect(first.page.getByTestId("backup-reminder")).toBeHidden();
  await expect(first.page.getByTestId("save-status")).toContainText("Last saved just now");
  const text = readFileSync(filePath, "utf8");
  expect(JSON.parse(text).format).toBe("caseload-tracker-data");
  await first.context.close();

  const second = await launchProfile(newProfileDir());
  await forceDownloadFallback(second.context);
  await second.page.goto(APP_URL);
  await second.page.getByRole("button", { name: "I already have a data file…" }).click();
  const chooser = second.page.waitForEvent("filechooser");
  await second.page.getByRole("button", { name: "Choose file…" }).click();
  await (await chooser).setFiles(filePath);
  await expect(second.page.getByRole("navigation", { name: "Main" })).toBeVisible();
  expect(await tableCounts(second.page)).toEqual(before);
  await second.context.close();
});

test("autosaves to the chosen file after each change", async () => {
  const { context, page } = await launchProfile(newProfileDir());
  // A stand-in for a real file handle; the native picker cannot be driven headlessly.
  await context.addInitScript(() => {
    const w = window as unknown as { __writes: string[]; showSaveFilePicker: unknown };
    w.__writes = [];
    w.showSaveFilePicker = async () => ({
      name: "my-caseload.caseload.json",
      queryPermission: async () => "granted",
      requestPermission: async () => "granted",
      getFile: async () => new File([w.__writes.at(-1) ?? ""], "my-caseload.caseload.json"),
      createWritable: async () => {
        let buf = "";
        return {
          write: async (d: string) => void (buf += d),
          close: async () => void w.__writes.push(buf),
        };
      },
    });
  });
  await page.goto(APP_URL);
  await completeFirstRun(page, { demo: false });
  await page.getByRole("button", { name: "Save to file…" }).first().click();
  await expect(page.getByTestId("save-status")).toContainText("Autosaving to my-caseload.caseload.json");
  const writes = () => page.evaluate(() => (window as unknown as { __writes: string[] }).__writes);
  expect((await writes()).length).toBe(1);

  await page.getByRole("link", { name: "Settings" }).click();
  await page.getByPlaceholder("Field name").fill("School district");
  await page.getByRole("button", { name: "Add field" }).click();
  await expect.poll(async () => (await writes()).length, { timeout: 5000 }).toBeGreaterThan(1);
  const last = JSON.parse((await writes()).at(-1)!);
  expect(last.tables.settings[0].customFieldNames).toContain("School district");
  await context.close();
});

test("clear demo data removes only demo records, delete all data needs typed confirmation", async () => {
  const { context, page } = await launchProfile(newProfileDir());
  await page.goto(APP_URL);
  await completeFirstRun(page, { demo: true });
  await page.getByRole("link", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Clear demo data" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Clear demo data" }).click();
  await expect(page.getByRole("button", { name: "Load demo data" })).toBeVisible();
  const counts = await tableCounts(page);
  expect(counts.clients).toBe(0);
  expect(counts.sessions).toBe(0);
  expect(counts.serviceTypes).toBe(4);

  await page.getByRole("button", { name: "Delete all data…" }).click();
  const confirm = page.getByRole("dialog").getByRole("button", { name: "Delete everything" });
  await expect(confirm).toBeDisabled();
  await page.getByLabel("Type DELETE to confirm").fill("DELETE");
  await confirm.click();
  await expect(page.getByRole("button", { name: "I understand, continue" })).toBeVisible();
  expect((await tableCounts(page)).serviceTypes).toBe(0);
  await context.close();
});
