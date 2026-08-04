import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
}

test("server-renders the ResearchOS thesis workspace", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>ResearchOS — Evidence becomes structure<\/title>/i);
  assert.match(html, /Thesis Build/);
  assert.match(html, /BUILD FAILED/);
  assert.match(html, /FIXTURE MODE/);
  assert.match(html, /CLAIM_LANG001/);
  assert.match(html, /Compile thesis/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("preserves frozen evidence semantics in the UI", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /ASSOCIATIONAL/);
  assert.match(page, /cannot support causal wording/i);
  assert.match(page, /contains no real empirical conclusion/i);
  assert.match(page, /EVIDENCE_DEMO_001/);
  assert.match(page, /THESIS_VER_002/);
});
