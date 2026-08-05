import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
}

test("server-renders the Chinese ResearchOS entry", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>ResearchOS — 让证据形成结构<\/title>/i);
  assert.match(html, /让证据/);
  assert.match(html, /进入你的研究空间/);
  assert.match(html, /使用 ChatGPT 账号继续/);
  assert.match(html, /不会采集或保存密码/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("makes the financial research assistant the first product workflow", async () => {
  const [page, workspace] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(page, /id: "workspace"[^\n]+label: "研究助手"/);
  assert.match(page, /id: "report-update"[^\n]+label: "研究出品"/);
  assert.match(page, /useState<View>\("workspace"\)/);
  for (const label of ["公开资料", "市场数据", "内部资料", "研究结论（初稿）", "开始实证检验", "形成周报页面"]) assert.match(workspace, new RegExp(label));
  for (const obsolete of ["流程样例", "AI 排版", "公开搜索智能体", "数据与 MacroTrace 智能体", "生成可视化报告"]) assert.doesNotMatch(`${page}\n${workspace}`, new RegExp(obsolete));
});

test("ships a publication-grade weekly report instead of a dashboard mockup", async () => {
  const output = await readFile(new URL("../app/research-output-studio.tsx", import.meta.url), "utf8");
  for (const feature of ["全球主要市场表现", "单位：%，国债收益率变动为 bp", "professional-bar-chart", "中美港主要行业估值对比", "professional-line-chart", "数据截止日期", "研究结论", "研究员审阅后方可发布", "出版检查通过"]) assert.match(output, new RegExp(feature));
  assert.match(output, /<table className="market-table"/);
  assert.match(output, /<table className="valuation-table"/);
  for (const operation of ["listDataPlugins", "listDataPluginDatasets", "ingestDataPluginDataset", "previewDataset"]) assert.match(output, new RegExp(operation));
  assert.match(output, /不可变 AssetVersion/);
  assert.match(output, /mode:\"REAL_API\"/);
  assert.doesNotMatch(output, /AI 排版|告诉 AI|AI 研究解读|AI 辅助研究稿/);
});

test("preserves the merged durable API and version-lineage capabilities", async () => {
  const [client, worker, flow] = await Promise.all([
    readFile(new URL("../lib/api-client.ts", import.meta.url), "utf8"),
    readFile(new URL("../worker/researchos-api.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/live-research-flow.tsx", import.meta.url), "utf8"),
  ]);
  for (const method of ["getBatch", "listObjectVersions", "getAssetVersion", "getGraph", "getProjectState", "getThesis", "getToolRun", "getJobEvents"]) assert.match(client, new RegExp(method));
  for (const route of ["ingest-batches", "object_id", "asset-versions", "project-state", "jobs", "text/event-stream"]) assert.match(worker, new RegExp(route.replaceAll("/", "\\/")));
  assert.match(worker, /ontology/);
  assert.match(worker, /relation_type: "NEW_VERSION_OF"/);
  for (const operation of ["createThesis", "compileThesis", "runMacroTrace", "verifyThesis", "getVersionDiff", "getJobEvents", "getToolRun"]) assert.match(flow, new RegExp(operation));
  assert.match(worker, /env\.DB/);
  assert.match(worker, /env\.UPLOADS\.put/);
});

test("uses B's original MacroTrace workbench instead of a replacement fixture view", async () => {
  const [page, workbench, macrotrace] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/macrotrace-workbench.tsx", import.meta.url), "utf8"),
    readFile(new URL("../../../services/macrotrace/frontend/app.js", import.meta.url), "utf8"),
  ]);
  assert.match(page, /MacroTraceWorkbench/);
  assert.match(page, /showingOriginalMacroTrace/);
  assert.match(workbench, /NEXT_PUBLIC_MACROTRACE_UI_URL/);
  assert.match(workbench, /http:\/\/127\.0\.0\.1:8000/);
  assert.match(workbench, /researchos:macrotrace-run-complete/);
  assert.match(workbench, /event\.origin !== expectedOrigin/);
  assert.match(macrotrace, /researchos:macrotrace-ready/);
  assert.match(macrotrace, /researchos:macrotrace-run-complete/);
  assert.match(macrotrace, /question/);
});

test("retains traceable upload, deduplication, and version metadata", async () => {
  const [workspace, client] = await Promise.all([
    readFile(new URL("../app/real-workspace.tsx", import.meta.url), "utf8"),
    readFile(new URL("../lib/api-client.ts", import.meta.url), "utf8"),
  ]);
  assert.match(workspace, /resolution_status/);
  assert.match(workspace, /DUPLICATE/);
  assert.match(workspace, /version_count/);
  assert.match(workspace, /workspace-drop-overlay/);
  assert.match(client, /resolution_status/);
  assert.match(client, /version_count/);
});

test("defines desktop, tablet, and phone behavior for the product and reports", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  for (const selector of [".app-shell.sidebar-collapsed", ".drawer-content", ".workspace-drop-overlay", ".publication-layout", ".publication-page", ".professional-bar-chart", ".professional-line-chart"]) assert.match(css, new RegExp(selector.replaceAll(".", "\\.")));
  assert.match(css, /@media\(max-width:1120px\)/);
  assert.match(css, /@media\(max-width:760px\)/);
  assert.match(css, /safe-area-inset-bottom/);
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

test("catalogues encrypted connectors while executing research data through B plugins", async () => {
  const [page, component, client, catalog, connectorWorker, worker, css] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/data-connector-settings.tsx", import.meta.url), "utf8"),
    readFile(new URL("../lib/api-client.ts", import.meta.url), "utf8"),
    readFile(new URL("../lib/connector-catalog.ts", import.meta.url), "utf8"),
    readFile(new URL("../worker/connector-api.ts", import.meta.url), "utf8"),
    readFile(new URL("../worker/index.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  for (const source of ["FRED / ALFRED", "Tushare Pro", "Alpha Vantage", "Nasdaq Data Link", "World Bank Open Data", "AKShare", "巨潮资讯", "Wind", "Bloomberg"]) assert.match(catalog, new RegExp(source));
  for (const method of ["listConnectors", "configureConnector", "testConnector", "queryConnector", "clearConnector"]) assert.match(client, new RegExp(method));
  for (const method of ["listDataPlugins", "setDataPluginEnabled", "listDataPluginDatasets", "ingestDataPluginDataset", "previewDataset"]) assert.match(client, new RegExp(method));
  assert.match(page, /DataConnectorSettings/);
  assert.match(component, /密钥由 ResearchOS 后端环境管理/);
  assert.match(component, /尚未注册到 B 的版本化数据插件系统/);
  assert.match(component, /需要桥接服务/);
  assert.match(connectorWorker, /AES-GCM/);
  assert.match(connectorWorker, /CONNECTOR_ENCRYPTION_KEY/);
  assert.match(connectorWorker, /server-encrypted/);
  assert.doesNotMatch(connectorWorker, /apiKeyMasked:\s*apiKey/);
  assert.match(worker, /handleConnectorApi/);
  assert.match(css, /Financial Data Layer/);
});
