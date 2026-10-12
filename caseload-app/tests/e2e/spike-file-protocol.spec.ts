import { expect, test } from "@playwright/test";
import { APP_URL, launchProfile, newProfileDir } from "./helpers";

// Checks the capabilities the single-file, double-click launch depends on.
test("file:// origin supports IndexedDB persistence, secure context and file pickers", async () => {
  const dir = newProfileDir();
  let { context, page } = await launchProfile(dir);
  await page.goto(APP_URL);
  const caps = await page.evaluate(async () => {
    const req = indexedDB.open("spike", 1);
    await new Promise<void>((res, rej) => {
      req.onupgradeneeded = () => req.result.createObjectStore("s");
      req.onsuccess = () => {
        const tx = req.result.transaction("s", "readwrite");
        tx.objectStore("s").put("kept", "k");
        tx.oncomplete = () => res();
      };
      req.onerror = () => rej(req.error);
    });
    return {
      origin: location.origin,
      secure: window.isSecureContext,
      randomUUID: typeof crypto.randomUUID,
      subtle: typeof crypto.subtle,
      savePicker: typeof (window as unknown as Record<string, unknown>).showSaveFilePicker,
      openPicker: typeof (window as unknown as Record<string, unknown>).showOpenFilePicker,
      persist: typeof navigator.storage?.persist,
    };
  });
  console.log("file:// capabilities", caps);
  expect(caps.secure).toBe(true);
  expect(caps.subtle).toBe("object");
  expect(caps.savePicker).toBe("function");
  await context.close();

  ({ context, page } = await launchProfile(dir));
  await page.goto(APP_URL);
  const value = await page.evaluate(
    () =>
      new Promise((res) => {
        const req = indexedDB.open("spike", 1);
        req.onsuccess = () => {
          const g = req.result.transaction("s").objectStore("s").get("k");
          g.onsuccess = () => res(g.result);
        };
      }),
  );
  expect(value).toBe("kept");
  await context.close();
});
