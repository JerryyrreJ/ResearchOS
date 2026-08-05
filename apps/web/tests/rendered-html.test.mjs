import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
}

test("server-renders the branded ResearchOS entry", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>ResearchOS — Evidence becomes structure<\/title>/i);
  assert.match(html, /Evidence/);
  assert.match(html, /becomes/);
  assert.match(html, /structure\./);
  assert.match(html, /进入你的研究空间/);
  assert.match(html, /使用 ChatGPT 账号继续/);
  assert.match(html, /不会采集或保存密码/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("preserves frozen evidence semantics in the UI", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /ASSOCIATIONAL/);
  assert.match(page, /cannot support causal wording/i);
  assert.match(page, /contains no real empirical conclusion/i);
  assert.match(page, /EVIDENCE_DEMO_001/);
  assert.match(page, /THESIS_VER_002/);
  assert.match(page, /FIXTURE MODE/);
  assert.match(page, /CLAIM_LANG001/);
});

test("ships Simplified Chinese, Traditional Chinese, and English UI catalogs", async () => {
  const catalog = await readFile(new URL("../app/i18n.ts", import.meta.url), "utf8");
  assert.match(catalog, /"zh-CN"/);
  assert.match(catalog, /"zh-TW"/);
  assert.match(catalog, /\ben:\s*\{/);
  assert.match(catalog, /進入你的研究空間/);
  assert.match(catalog, /Enter your research workspace/);
});

test("defines phone, tablet, and desktop adaptive behavior", async () => {
  const [page, css, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);
  assert.match(packageJson, /@radix-ui\/react-dialog/);
  assert.match(page, /InspectorDrawer/);
  assert.match(css, /--breakpoint-phone/);
  assert.match(css, /--breakpoint-tablet/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /drawer-content/);
});

test("provides token-driven themes, accessibility preferences, and an honest extension catalog", async () => {
  const [page, css, favicon] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../public/favicon.svg", import.meta.url), "utf8"),
  ]);
  assert.match(page, /Extension Center/);
  assert.match(page, /Only MacroTrace is active/);
  assert.match(page, /prefers-color-scheme: dark/);
  assert.match(page, /High contrast/);
  assert.match(css, /data-theme="dark"/);
  assert.match(css, /data-reduced-motion="true"/);
  assert.match(favicon, /#183F37/i);
  assert.match(page, /researchos-mark/);
  assert.match(favicon, /circle cx="23" cy="16"/);
});

test("exposes honest delivery modes and visible asynchronous failure states", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  for (const label of ["FIXTURE MODE", "OFFLINE REPLAY", "REAL API", "Run queued", "Partial evidence available", "Model run failed", "Run cancelled", "Permission blocked", "Model timeout", "Unsupported backend state"]) {
    assert.match(page, new RegExp(label, "i"));
  }
  assert.match(page, /last successful result is marked stale and is not reused/i);
  assert.match(page, /Waiting for producer APIs/);
  assert.match(page, /QRCodeSVG/);
});

test("serves a non-cached web health endpoint", async () => {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("health-test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  const response = await worker.fetch(new Request("http://localhost/health"), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { status: "ok", service: "researchos-web", mode: "fixture", contract: "0.1.0-frozen" });
});
