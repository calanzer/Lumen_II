import { createHash } from "node:crypto";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// Inlined scripts are allowed by hash, not 'unsafe-inline'. connect-src 'none'
// blocks fetch/XHR/WebSocket so the built app cannot send data anywhere.
function contentSecurityPolicy(): Plugin {
  return {
    name: "offline-csp",
    apply: "build",
    enforce: "post",
    generateBundle(_options, bundle) {
      for (const file of Object.values(bundle)) {
        if (file.type !== "asset" || !file.fileName.endsWith(".html")) continue;
        const html = String(file.source);
        const hashes = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
          .map((m) => m[1])
          .filter((body) => body.length > 0)
          .map((body) => `'sha256-${createHash("sha256").update(body).digest("base64")}'`);
        const csp = [
          "default-src 'none'",
          `script-src ${hashes.join(" ")}`,
          "style-src 'unsafe-inline'",
          "img-src data: blob:",
          "font-src data:",
          "connect-src 'none'",
          "form-action 'none'",
          "base-uri 'none'",
        ].join("; ");
        file.source = html.replace(
          "<head>",
          `<head>\n    <meta http-equiv="Content-Security-Policy" content="${csp}" />`,
        );
      }
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [react(), viteSingleFile({ removeViteModuleLoader: true }), contentSecurityPolicy()],
  build: { target: "es2022", assetsInlineLimit: 100_000_000, chunkSizeWarningLimit: 10_000 },
  test: {
    include: ["tests/unit/**/*.test.ts"],
    environment: "node",
  },
});
