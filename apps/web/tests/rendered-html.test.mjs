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
  assert.match(page, /contains no real empirical\s+conclusion/i);
  assert.match(page, /EVIDENCE_DEMO_001/);
  assert.match(page, /THESIS_VER_002/);
  assert.match(page, /FIXTURE MODE/);
  assert.match(page, /CLAIM_LANG001/);
});

test("ships Simplified Chinese, Traditional Chinese, and English UI catalogs", async () => {
  const [catalog, page, workspace, css] = await Promise.all([
    readFile(new URL("../app/i18n.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(catalog, /"zh-CN"/);
  assert.match(catalog, /"zh-TW"/);
  assert.match(catalog, /\ben:\s*\{/);
  assert.match(catalog, /進入你的研究空間/);
  assert.match(catalog, /Enter your research workspace/);
  assert.match(page, /<RealWorkspace\s+locale=\{locale\}/);
  assert.match(workspace, /Relationship network/);
  assert.match(workspace, /關係網路/);
  assert.match(page, /InterfaceLanguageBridge/);
  const bridge = await readFile(new URL("../app/interface-language.tsx", import.meta.url), "utf8");
  assert.match(bridge, /MutationObserver/);
  assert.match(bridge, /端到端研究編譯/);
  assert.match(bridge, /End-to-end research compilation/);
  assert.match(css, /--font-ui/);
  assert.match(css, /PingFang SC/);
  assert.match(css, /PingFang TC/);
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
  assert.match(css, /ResearchOS Archive Instrument/);
  assert.match(css, /--surface:#fcfbf7/);
  assert.match(css, /background:#17221f/);
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
  assert.match(page, /Integrated producer APIs/);
  const flow = await readFile(new URL("../app/live-research-flow.tsx", import.meta.url), "utf8");
  for (const operation of ["createThesis", "compileThesis", "runMacroTrace", "verifyThesis", "getVersionDiff"]) {
    assert.match(flow, new RegExp(operation));
  }
  assert.match(page, /QRCodeSVG/);
});

test("wires visible controls to navigation, feedback, export, and live workspace states", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  for (const behavior of ["handleShellClick", "runPrimaryFlow", "downloadDiff", "Workspace link copied", "policyNotice", "inspectorVisible"]) {
    assert.match(page, new RegExp(behavior));
  }
  assert.doesNotMatch(workspace, /<button disabled>Relations/);
  assert.match(workspace, /setWorkspaceTab\("relations"\)/);
  assert.match(workspace, /setWorkspaceTab\("conflicts"\)/);
  assert.match(css, /action-toast/);
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

test("connects deployed UI to same-origin durable APIs and creates real theses", async () => {
  const [page, flow, client, worker, hosting] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/live-research-flow.tsx", import.meta.url), "utf8"),
    readFile(new URL("../lib/api-client.ts", import.meta.url), "utf8"),
    readFile(new URL("../worker/researchos-api.ts", import.meta.url), "utf8"),
    readFile(new URL("../../../.openai/hosting.json", import.meta.url), "utf8"),
  ]);
  assert.match(client, /window\.location\.origin.*\/api\/v1/);
  assert.match(page, /newThesisOpen/);
  assert.match(page, /createThesis\(\s*buildThesisPayload/);
  assert.match(page, /thesisId=\{activeThesis/);
  assert.match(flow, /buildThesisPayload/);
  for (const route of ["/workspaces", "/theses", "/tool-runs/macrotrace", "/verify", "thesis-versions"]) assert.match(worker, new RegExp(route.replaceAll("/", "\\/")));
  for (const method of ["getBatch", "listObjectVersions", "getAssetVersion", "getThesis", "getToolRun", "getJobEvents"]) assert.match(client, new RegExp(method));
  for (const route of ["ingest-batches", "object_id", "asset-versions", "jobs", "text/event-stream"]) assert.match(worker, new RegExp(route));
  assert.match(flow, /getJobEvents/);
  assert.match(flow, /getToolRun/);
  assert.match(worker, /env\.DB/);
  assert.match(worker, /env\.UPLOADS\.put/);
  assert.match(worker, /INSERT INTO assets VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?\)/);
  assert.doesNotMatch(worker, /INSERT INTO assets VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?\)/);
  assert.match(hosting, /"d1"\s*:\s*"DB"/);
  assert.match(hosting, /"r2"\s*:\s*"UPLOADS"/);
});

test("supports workspace-wide drag upload and a collapsible functional sidebar", async () => {
  const [page, workspace, css] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(page, /sidebarCollapsed/);
  assert.match(page, /Collapse sidebar/);
  assert.match(page, /sidebar-collapsed/);
  assert.match(workspace, /onWorkspaceDragEnter/);
  assert.match(workspace, /workspace-drop-overlay/);
  assert.match(workspace, /acceptFiles\(Array\.from\(event\.dataTransfer\.files\)\)/);
  assert.match(css, /\.app-shell\.sidebar-collapsed/);
  assert.match(css, /\.workspace-drop-overlay/);
});

test("makes the shared knowledge library the primary product workflow", async () => {
  const [page, workspace, css] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(page, /useState<View>\("workspace"\)/);
  assert.match(page, /知识库/);
  assert.match(page, /团队文件，共享有序/);
  assert.match(page, /researchos:choose-files/);
  assert.match(workspace, /拖入文件/);
  assert.doesNotMatch(workspace, /把团队文件放到同一个地方|共享资料库/);
  assert.match(workspace, /categoryFor/);
  assert.match(workspace, /基础分析/);
  assert.match(workspace, /versions: \["版本", "版本", "Versions"\]/);
  assert.match(workspace, /关系网络/);
  assert.match(workspace, /查看完整版本链/);
  assert.match(workspace, /同一知识库/);
  assert.match(workspace, /NEW_VERSION_OF/);
  assert.match(workspace, /仅展示后端确认的确定性版本关系/);
  assert.match(workspace, /researchos:new-thesis/);
  assert.match(css, /\.knowledge-library/);
  assert.match(css, /\.quick-analysis/);
  assert.match(css, /\.lineage-chain/);
  assert.match(css, /\.knowledge-network/);
  assert.match(css, /\.network-node/);
});

test("integrates the original Evidence Archivist as a restrained product mascot", async () => {
  const [page, workspace, css, mascot] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../public/brand/evidence-archivist.png", import.meta.url)),
  ]);
  assert.match(page, /archivist-login/);
  assert.match(workspace, /交给证据档案员/);
  assert.match(workspace, /档案员正在等待第一份资料/);
  assert.match(css, /\.archivist-login/);
  assert.ok(mascot.byteLength > 100_000);
  assert.equal(mascot.subarray(1, 4).toString(), "PNG");
});

test("explains backend deduplication and version outcomes in the upload UI", async () => {
  const [workspace, css] = await Promise.all([
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(workspace, /EXACT_DUPLICATE/);
  assert.match(workspace, /重复文件 · 已跳过/);
  assert.match(workspace, /已建立新版本/);
  assert.match(workspace, /内容哈希完全相同/);
  assert.match(workspace, /没有创建副本或占用额外存储/);
  assert.match(css, /\.result-duplicate/);
  assert.match(css, /\.result-version/);
});

test("uses the Cobalt Protocol visual system across light, dark, and login surfaces", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /ResearchOS Cobalt Protocol/);
  assert.match(css, /--accent:#2f5bff/);
  assert.match(css, /--surface:#141d31/);
  assert.match(css, /grid-template-columns:minmax\(390px,42%\)/);
  assert.match(css, /\.archivist-login\{display:none\}/);
  assert.match(css, /background-size:32px 32px/);
});
