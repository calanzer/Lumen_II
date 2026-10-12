import { chromium, type BrowserContext, type Page } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const APP_URL = pathToFileURL(path.resolve("dist/index.html")).href;

export function newProfileDir(): string {
  return mkdtempSync(path.join(tmpdir(), "caseload-profile-"));
}

export interface NetworkWatch {
  external: string[];
  cspViolations: string[];
}

// Records every request that is not to the local file, plus any CSP violation the page reports.
export function watchNetwork(context: BrowserContext): NetworkWatch {
  const watch: NetworkWatch = { external: [], cspViolations: [] };
  context.on("request", (req) => {
    const url = req.url();
    if (!/^(file|data|blob|about):/.test(url)) watch.external.push(url);
  });
  context.on("console", (msg) => {
    if (/Content Security Policy/i.test(msg.text())) watch.cspViolations.push(msg.text());
  });
  return watch;
}

export async function launchProfile(dir: string, opts: { offline?: boolean } = {}) {
  const context = await chromium.launchPersistentContext(dir, {
    viewport: { width: 1280, height: 900 },
    acceptDownloads: true,
    offline: opts.offline ?? true,
  });
  const watch = watchNetwork(context);
  const page = context.pages()[0] ?? (await context.newPage());
  return { context, page, watch };
}

// Removes the File System Access API so the app uses its Export/Import fallback.
export async function forceDownloadFallback(context: BrowserContext) {
  await context.addInitScript(() => {
    delete (window as unknown as Record<string, unknown>).showSaveFilePicker;
    delete (window as unknown as Record<string, unknown>).showOpenFilePicker;
  });
}

export async function completeFirstRun(page: Page, { demo }: { demo: boolean }) {
  await page.getByRole("button", { name: "I understand, continue" }).click();
  await page.getByLabel("Your name").fill("Test BCBA");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: demo ? "Load demo data" : "Start with an empty caseload" }).click();
  await page.getByRole("navigation", { name: "Main" }).waitFor();
}
