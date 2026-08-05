const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const API_BASE_URL = String(window.MACROTRACE_CONFIG?.apiBaseUrl || "").replace(/\/$/, "");

function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
const TERMINAL = new Set(["COMPLETE", "PARTIAL", "FAILED", "CANCELLED"]);
const TECHNICAL_TYPES = new Set(["FACTOR", "DATASET", "TRANSFORM", "DIAGNOSTIC"]);
const COLORS = ["#1769d2", "#087b6c", "#b42318", "#9a6100", "#6555a6", "#66707d"];
const STAGE_ORDER = ["PARSING_QUERY", "CLASSIFYING_WORKFLOW", "ROUTING_LANES", "ROUTING_NODES", "SELECTING_FACTORS", "PLANNING_MODELS", "SELECTING_PARAMETERS", "VALIDATING_PLAN", "EXECUTING_MODELS", "AGGREGATING_LANES", "SYNTHESIZING"];
const COLUMN_BY_TYPE = {
  QUESTION: 0, QUERY: 1, RESEARCH_DEPTH_GATE: 2, LANE: 2,
  MECHANISM: 3, RESEARCH_NODE: 4, FACTOR: 5, DATASET: 5,
  TRANSFORM: 6, MODEL_SPECIFICATION: 7, MODEL_RUN: 8,
  DIAGNOSTIC: 9, EVIDENCE: 9, CLAIM: 10, LANE_SIGNAL: 11,
  AGGREGATION: 12, FINAL_CLAIM: 13, FALSIFIER: 14,
};

const state = {
  health: null,
  dataStatus: null,
  examples: [],
  currentJob: null,
  graph: null,
  result: null,
  eventSource: null,
  refreshTimer: null,
  showDetail: false,
  zoom: 1,
  panX: 20,
  panY: 20,
  graphInitialized: false,
  layout: null,
  selectedNode: null,
  expandedNodes: new Set(),
  nodeDetail: null,
  activeTab: "overview",
  lastQuestion: "",
  drawerReturnFocus: null,
  historyReturnFocus: null,
  settingsCatalog: null,
  settingsStatus: null,
  assetGraph: null,
  dataPlugins: [],
  pluginCatalog: { akshare: [], fred: [] },
  dataZoom: .78,
  dataPanX: 18,
  dataPanY: 18,
  dataLayout: null,
  dataInitialized: false,
  selectedProvider: "deepseek",
  settingsReturnFocus: null,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pretty(value) {
  return String(value ?? "—").replaceAll("_", " ");
}

function formatNumber(value, digits = 4) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (Math.abs(number) >= 1000) return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return number.toLocaleString(undefined, { maximumFractionDigits: digits });
}

async function api(url, options = {}) {
  const response = await fetch(apiUrl(url), options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`);
  }
  return response.json();
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("show"), 2600);
}

function readHistory() {
  try { return JSON.parse(localStorage.getItem("macrotrace.history") || "[]"); }
  catch { return []; }
}

function rememberJob(job, question = state.lastQuestion) {
  const items = readHistory().filter((item) => item.job_id !== job.job_id);
  items.unshift({ job_id: job.job_id, question: question || job.question || "Macro research", status: job.status, created_at: job.created_at || new Date().toISOString() });
  localStorage.setItem("macrotrace.history", JSON.stringify(items.slice(0, 20)));
  localStorage.setItem("macrotrace.currentJob", job.job_id);
  const url = new URL(window.location.href);
  url.searchParams.set("job", job.job_id);
  window.history.replaceState(null, "", url);
  renderHistory();
}

function renderHistory() {
  const items = readHistory();
  $("#historyList").innerHTML = items.length ? items.map((item) => `
    <button class="history-item" type="button" data-job-id="${escapeHtml(item.job_id)}">
      <span><i>${escapeHtml(item.status)}</i><time>${escapeHtml(String(item.created_at).slice(0, 16).replace("T", " "))}</time></span>
      <strong>${escapeHtml(item.question)}</strong>
    </button>`).join("") : `<div class="history-item"><strong>还没有本地研究任务。</strong></div>`;
}

async function boot() {
  document.body.dataset.workspaceMode = "empty";
  renderHistory();
  try {
    const [health, dataStatus, examples] = await Promise.all([api("/v1/health"), api("/v1/data/status"), api("/v1/examples")]);
    state.health = health;
    state.dataStatus = dataStatus;
    state.examples = examples.questions;
    $("#healthPulse").classList.add("live");
    $("#healthText").textContent = health.database_ready ? "SYSTEM READY" : "SYNC REQUIRED";
    $("#seriesCount").textContent = `${dataStatus.series_count} SERIES`;
    const latest = dataStatus.series.map((item) => item.last_period).filter(Boolean).sort().at(-1);
    $("#dataFreshness").textContent = dataStatus.ready ? `${dataStatus.series_count} official series / latest ${String(latest || "—").slice(0, 10)}` : "Official-data warehouse is empty";
    renderExamples();
    await loadConnectionSettings().catch((error) => {
      $("#providerSetupLabel").textContent = "API 配置中心暂不可用";
      console.warn("Local provider settings unavailable:", error.message);
    });
    await loadDataEvidenceCatalog().catch((error) => {
      console.warn("ResearchOS data layer unavailable:", error.message);
    });
  } catch (error) {
    $("#healthPulse").classList.add("fail");
    $("#healthText").textContent = "OFFLINE";
    $("#dataFreshness").textContent = error.message;
  }
  const saved = new URLSearchParams(window.location.search).get("job") || localStorage.getItem("macrotrace.currentJob");
  if (saved) {
    try { await loadJob(saved, true); }
    catch { localStorage.removeItem("macrotrace.currentJob"); }
  }
}

async function loadDataEvidenceCatalog() {
  const safe = async (path, fallback) => {
    try { return await api(path); }
    catch { return fallback; }
  };
  const [plugins, workspaces, akshare, fred] = await Promise.all([
    safe("/api/v1/data-plugins", []),
    safe("/api/v1/workspaces", []),
    safe("/api/v1/data-plugins/akshare/datasets?q=macro&limit=48", []),
    safe("/api/v1/data-plugins/fred/datasets?limit=100", []),
  ]);
  state.dataPlugins = plugins;
  state.pluginCatalog = { akshare, fred };
  state.assetGraph = workspaces.length
    ? await safe(`/api/v1/workspaces/${encodeURIComponent(workspaces[0].id)}/ontology/graph`, null)
    : null;
  renderDataEvidenceLayer();
}

function renderExamples() {
  $("#exampleQuestions").innerHTML = state.examples.map((question, index) => `<button type="button" data-example="${index}" title="${escapeHtml(question)}">${String(index + 1).padStart(2, "0")} · ${escapeHtml(question.slice(0, 22))}${question.length > 22 ? "…" : ""}</button>`).join("");
}

function setWorkspaceMode(mode) {
  document.body.dataset.workspaceMode = mode;
  $("#emptyState").classList.toggle("hidden", mode !== "empty");
  $("#errorState").classList.toggle("hidden", mode !== "error");
  $("#workspace").classList.toggle("hidden", mode === "empty" || mode === "error");
  $("#jobStrip").classList.toggle("hidden", mode === "empty");
}

async function submitResearch(event) {
  event?.preventDefault();
  const question = $("#questionInput").value.trim();
  if (!question) return;
  state.lastQuestion = question;
  closeEventSource();
  state.graph = null;
  state.result = null;
  state.expandedNodes = new Set();
  state.graphInitialized = false;
  state.dataZoom = .78;
  state.dataPanX = 18;
  state.dataPanY = 18;
  state.dataInitialized = false;
  $("#runButton").disabled = true;
  setWorkspaceMode("running");
  $("#conclusionCard").classList.add("hidden");
  $("#researchReport").classList.add("hidden");
  try {
    const job = await api("/v1/research-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, display_mode: "ACADEMIC" }),
    });
    state.currentJob = job;
    rememberJob(job, question);
    updateJobStrip(job);
    connectEvents(job.job_id);
    await refreshJob(job.job_id);
  } catch (error) {
    showError("无法创建研究任务", error.message);
  } finally {
    $("#runButton").disabled = false;
  }
}

async function loadJob(jobId, resumed = false) {
  closeEventSource();
  const job = await api(`/v1/research-jobs/${encodeURIComponent(jobId)}`);
  state.currentJob = job;
  state.lastQuestion = job.question;
  $("#questionInput").value = job.question;
  $("#charCount").textContent = `${job.question.length} / 4000`;
  rememberJob(job, job.question);
  setWorkspaceMode("running");
  updateJobStrip(job);
  await refreshJob(jobId);
  if (!TERMINAL.has(job.status)) connectEvents(jobId);
  if (resumed) toast(`已恢复任务 ${jobId}`);
}

function connectEvents(jobId) {
  closeEventSource();
  const source = new EventSource(apiUrl(`/v1/research-jobs/${encodeURIComponent(jobId)}/events`));
  state.eventSource = source;
  const handler = () => scheduleRefresh(jobId);
  source.addEventListener("job_progress", handler);
  source.addEventListener("job_terminal", handler);
  source.addEventListener("stream_complete", () => { scheduleRefresh(jobId); closeEventSource(); });
  source.onerror = () => {
    if (!state.currentJob || TERMINAL.has(state.currentJob.status)) return;
    scheduleRefresh(jobId, 900);
  };
}

function closeEventSource() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = null;
}

function scheduleRefresh(jobId, delay = 120) {
  clearTimeout(state.refreshTimer);
  state.refreshTimer = setTimeout(() => refreshJob(jobId).catch((error) => toast(error.message)), delay);
}

async function refreshJob(jobId) {
  const [job, graph] = await Promise.all([
    api(`/v1/research-jobs/${encodeURIComponent(jobId)}`),
    api(`/v1/research-jobs/${encodeURIComponent(jobId)}/graph`),
  ]);
  if (state.currentJob?.job_id !== jobId) return;
  state.currentJob = job;
  state.graph = graph;
  rememberJob(job, job.question);
  updateJobStrip(job);
  renderGraph();
  if (TERMINAL.has(job.status)) {
    closeEventSource();
    if (job.status === "CANCELLED") {
      showError("研究任务已取消", "任务保留了取消前的图谱与审计事件。你可以修改问题后重新执行。");
      return;
    }
    if (job.status === "FAILED" && !job.coverage_score) {
      showError("研究任务未产生合法证据", job.error?.message || "查看 trace 以定位失败阶段。");
      return;
    }
    try {
      state.result = await api(`/v1/research-jobs/${encodeURIComponent(jobId)}/result`);
      renderConclusion(state.result);
      setWorkspaceMode("result");
    } catch (error) {
      if (job.status === "FAILED") showError("研究任务失败", error.message);
    }
  }
}

function updateJobStrip(job) {
  $("#jobStatus").textContent = pretty(job.status);
  $("#jobId").textContent = job.job_id;
  $("#progressBar").style.width = `${Math.max(1, Number(job.progress || 0) * 100)}%`;
  const current = STAGE_ORDER.indexOf(job.status);
  $$("#stageRail li").forEach((item, index) => {
    item.classList.toggle("done", current > index || TERMINAL.has(job.status));
    item.classList.toggle("active", current === index);
  });
  $("#cancelButton").disabled = TERMINAL.has(job.status);
}

function showError(title, detail) {
  setWorkspaceMode("error");
  $("#errorTitle").textContent = title;
  $("#errorDetail").textContent = detail;
}

function compactConclusionFinding(item) {
  return String(item?.finding_zh || "")
    .split("（", 1)[0]
    .replace("方向：", "")
    .replaceAll("：", "")
    .replace(/[。；\s]+$/g, "")
    .trim();
}

function isLimitationHeadline(value) {
  const text = String(value || "");
  return ["当前只能", "尚不能", "无法回答", "无法覆盖", "没有足以识别", "只描述相关性", "不能支持", "Registry 无法覆盖"]
    .some((marker) => text.includes(marker));
}

function displayConclusionHeadline(synthesis) {
  const findings = (synthesis.primary_findings?.length ? synthesis.primary_findings : synthesis.claim_summaries) || [];
  const parts = findings.map(compactConclusionFinding).filter(Boolean).slice(0, 2);
  if (parts.length) return parts.join("；");
  if (synthesis.answerability === "UNSUPPORTED") return "本轮未形成可验证的研究结论";
  return isLimitationHeadline(synthesis.headline) ? "本轮未形成可验证的研究结论" : synthesis.headline;
}

function displayConclusionQualifier(synthesis, gaps) {
  const originalHeadline = String(synthesis.headline || "").trim();
  if (isLimitationHeadline(originalHeadline)) {
    return { label: "RESEARCH LIMIT", text: originalHeadline };
  }
  if (synthesis.evidence_state === "CONDITIONAL_SCENARIO") {
    return { label: "METHOD NOTE", text: "条件响应依赖已注册冲击、代理映射与识别假设，不自动等同于因果效应。" };
  }
  if (synthesis.evidence_state === "BASELINE_ONLY") {
    return { label: "RESEARCH LIMIT", text: "以下为基线宏观状态，不代表情景冲击的条件效应。" };
  }
  if (synthesis.evidence_state === "ASSOCIATIONAL_ONLY") {
    return { label: "IDENTIFICATION LIMIT", text: "现有模型提供关联性与预测性证据，不能据此识别因果效应。" };
  }
  if (synthesis.answerability === "UNSUPPORTED" && gaps.length) {
    return { label: "COVERAGE LIMIT", text: gaps[0] };
  }
  return null;
}

function renderConclusion(result) {
  const synthesis = result.synthesis;
  const report = result.report || synthesis.report || null;
  const unsupported = normalizeTextList(synthesis.unsupported_aspects);
  const limitations = normalizeTextList(synthesis.limitations);
  const gaps = [...new Set([...unsupported, ...limitations])];
  const displayHeadline = report?.direct_answer?.headline || displayConclusionHeadline(synthesis);
  const directAnswer = report?.direct_answer?.text || synthesis.answer;
  $("#conclusionCard").classList.remove("hidden");
  $("#coverageLabel").textContent = `${synthesis.coverage} COVERAGE / ${pretty(synthesis.answerability || "LEGACY")} / ${pretty(synthesis.evidence_state || synthesis.stance)}`;
  $("#answerAsOf").textContent = `AS OF ${result.as_of_date} · ${result.horizon.minimum}–${result.horizon.maximum} ${result.horizon.unit} · ${result.horizon.source}`;
  $("#answerHeadline").textContent = displayHeadline;
  const qualifier = displayConclusionQualifier(synthesis, gaps);
  $("#answerQualifier").classList.toggle("hidden", !qualifier);
  $("#answerQualifier").textContent = qualifier?.text || "";
  $("#answerQualifier").dataset.label = qualifier?.label || "RESEARCH LIMIT";
  $("#answerNarrative").textContent = directAnswer;
  $("#confidenceValue").textContent = synthesis.confidence;
  $("#coverageMeter").style.width = `${Math.max(0, Math.min(100, synthesis.coverage_score * 100))}%`;
  $("#coverageValue").textContent = `${Math.round(synthesis.coverage_score * 100)}% COVERAGE`;
  const falsifiers = normalizeTextList(synthesis.falsifiers);
  $("#falsifierList").innerHTML = falsifiers.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("#limitationList").innerHTML = gaps.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No registered coverage gap.</li>";
  renderResearchReport(report);
  const finalClaim = state.graph?.nodes?.find((node) => node.node_type === "FINAL_CLAIM");
  if (finalClaim && finalClaim.label !== displayHeadline) {
    finalClaim.label = displayHeadline;
    finalClaim.summary = directAnswer;
    renderGraph();
  }
}

function renderResearchReport(report) {
  const container = $("#researchReport");
  if (!report?.abstract || !report?.conclusion) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  $("#reportQuestion").textContent = report.question ? `研究问题：${report.question}` : "";
  $("#reportAbstract").textContent = report.abstract.text || "";
  $("#reportKeyPoints").innerHTML = normalizeTextList(report.abstract.key_points)
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const mechanisms = Array.isArray(report.economic_mechanisms) ? report.economic_mechanisms : [];
  $("#mechanismList").innerHTML = mechanisms.length
    ? mechanisms.map((item, index) => {
        const sourceNode = normalizeTextList(item.source_node_ids)[0];
        const role = item.role === "CORE" ? "核心机制" : "辅助机制";
        return `<article class="mechanism-card">
          <header><span>${String(index + 1).padStart(2, "0")}</span><h4>${escapeHtml(item.title || "经济传导机制")}</h4><i>${role}</i></header>
          <p>${escapeHtml(item.explanation || "该机制的解释记录在研究图中。")}</p>
          <div class="transmission-note"><span>传导路径</span><p>${escapeHtml(item.transmission_chain || "")}</p></div>
          ${sourceNode ? `<button type="button" data-report-node="${escapeHtml(sourceNode)}">查看关联实证证据 →</button>` : ""}
        </article>`;
      }).join("")
    : `<p class="report-empty-note">本轮没有形成可展示的经济机制链，相关缺口已列入限制条件。</p>`;

  const evidence = Array.isArray(report.empirical_evidence) ? report.empirical_evidence : [];
  const summary = report.method_summary || {};
  const total = Number(summary.successful_runs || evidence.length);
  const highlighted = Number(summary.highlighted_runs || evidence.length);
  const additional = Number(summary.additional_runs || Math.max(0, total - highlighted));
  $("#empiricalIntro").textContent = additional > 0
    ? `本轮共有 ${total} 项数据或计量规格完成运行。下方重点解释对结论影响最大的 ${highlighted} 项；其余 ${additional} 项基准、稳健性或反证规格可在 Research Graph 中逐项展开。`
    : `本轮共有 ${total} 项数据或计量规格完成运行，下方解释其中对结论影响最大的分析。`;
  $("#empiricalList").innerHTML = evidence.length
    ? evidence.map((item, index) => {
        const sourceNode = normalizeTextList(item.source_node_ids)[0] || item.node_id;
        const variables = normalizeTextList(item.variables);
        return `<article class="empirical-card">
          <header>
            <span>EMPIRICAL ${String(index + 1).padStart(2, "0")}</span>
            <h4>${escapeHtml(item.title || item.method || "实证分析")}</h4>
            <div><i>${escapeHtml(item.method || "已注册模型")}</i><i>${escapeHtml(item.role || "主要分析")}</i></div>
          </header>
          <div class="empirical-question"><span>这项分析回答什么</span><p>${escapeHtml(item.question_addressed || "")}</p></div>
          <dl class="empirical-meta">
            <div><dt>数据与样本</dt><dd>${escapeHtml(item.data_and_sample || "详见节点数据页签")}</dd></div>
            <div><dt>主要变量</dt><dd>${escapeHtml(variables.join("；") || "详见节点变量表")}</dd></div>
            <div class="wide"><dt>模型规格</dt><dd>${escapeHtml(item.specification || "详见节点规格页签")}</dd></div>
          </dl>
          <div class="empirical-result"><span>结果</span><p>${escapeHtml(item.finding || "")}</p></div>
          <div class="empirical-implication"><span>经济含义</span><p>${escapeHtml(item.implication || "")}</p></div>
          <footer><p>${escapeHtml(item.diagnostics || "")}</p>${sourceNode ? `<button type="button" data-report-node="${escapeHtml(sourceNode)}">打开模型、回归表与诊断 →</button>` : ""}</footer>
        </article>`;
      }).join("")
    : `<p class="report-empty-note">没有足够的成功模型可形成实证摘要；请结合上方限制条件解释本轮结果。</p>`;

  $("#reportConclusion").textContent = report.conclusion.text || "";
}

function normalizeTextList(value) {
  if (value == null || value === "") return [];
  const items = (Array.isArray(value) ? value : [value])
    .filter((item) => item != null)
    .map((item) => String(item));
  // v0.1 persisted some LLM strings as arrays of Unicode characters. Treat that
  // unmistakable legacy shape as one sentence while keeping normal lists intact.
  if (items.length >= 4 && items.every((item) => [...item].length <= 1)) {
    return [items.join("").trim()].filter(Boolean);
  }
  return items.map((item) => item.trim()).filter(Boolean);
}

function dataNodeStatus(node) {
  return !node || node.status === "NOT_ROUTED" ? "available" : node.status === "BLOCKED" ? "blocked" : "used";
}

function renderDataEvidenceLayer() {
  const container = $("#dataEvidenceNodes");
  if (!container) return;
  const graphNodes = state.graph?.nodes || [];
  const graphEdges = state.graph?.edges || [];
  const datasets = graphNodes.filter((node) => node.node_type === "DATASET")
    .sort((a, b) => dataNodeStatus(b).localeCompare(dataNodeStatus(a)) || a.label.localeCompare(b.label));
  const factors = graphNodes.filter((node) => node.node_type === "FACTOR")
    .sort((a, b) => dataNodeStatus(b).localeCompare(dataNodeStatus(a)) || a.label.localeCompare(b.label));
  const selectedSeries = new Set(datasets
    .filter((node) => dataNodeStatus(node) === "used")
    .flatMap((node) => node.metadata?.series_ids || []));
  const fredCatalog = (state.pluginCatalog.fred || []).map((item) => ({
    node_id: `CATALOG::FRED::${item.dataset_id}`,
    label: item.dataset_id,
    detail: item.description,
    node_type: "FRED SERIES",
    status: selectedSeries.has(item.dataset_id) ? "used" : "available",
  }));
  const akshareCatalog = (state.pluginCatalog.akshare || []).map((item) => ({
    node_id: `CATALOG::AKSHARE::${item.dataset_id}`,
    label: item.dataset_id.replace(/^macro_/, ""),
    detail: item.description,
    node_type: "AKSHARE",
    status: "available",
  }));
  const assets = (state.assetGraph?.nodes || []).map((item) => ({
    node_id: `ASSET::${item.node_id}`,
    label: item.label,
    detail: `${item.ref?.representation || "ASSET"} · ${String(item.ref?.content_hash || "").slice(0, 10)}`,
    node_type: item.ref?.representation || "ASSET",
    status: "asset",
  }));

  const visibleDatasets = datasets.map((item) => ({ ...item, detail: item.summary, status: dataNodeStatus(item) }));
  const visibleFactors = factors.map((item) => ({ ...item, detail: item.metadata?.series_id || item.summary, status: dataNodeStatus(item) }));
  const all = [...akshareCatalog, ...fredCatalog, ...visibleDatasets, ...assets, ...visibleFactors];
  const positions = new Map();
  const placeGrid = (items, startX, columns, rowGap, startY = 86, columnGap = 108) => {
    items.forEach((item, index) => positions.set(item.node_id, {
      x: startX + (index % columns) * columnGap,
      y: startY + Math.floor(index / columns) * rowGap,
      width: 78,
      height: 78,
    }));
    return Math.ceil(items.length / columns);
  };
  const leftRows = placeGrid(akshareCatalog, 72, 5, 108);
  const sourceRows = placeGrid([...fredCatalog, ...visibleDatasets, ...assets], 650, 4, 108);
  const factorRows = placeGrid(visibleFactors, 1160, 6, 108, 86, 112);
  const width = 1900;
  const height = Math.max(720, Math.max(leftRows, sourceRows, factorRows) * 108 + 150);
  state.dataLayout = { positions, width, height };
  const canvas = $("#dataEvidenceCanvas");
  const edgeSvg = $("#dataEvidenceEdges");
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  edgeSvg.setAttribute("width", width);
  edgeSvg.setAttribute("height", height);
  edgeSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const edgeRows = [];
  graphEdges.forEach((edge) => {
    if (positions.has(edge.source) && positions.has(edge.target)) edgeRows.push(edge);
  });
  datasets.forEach((dataset) => {
    (dataset.metadata?.series_ids || []).forEach((seriesId) => {
      const source = `CATALOG::FRED::${seriesId}`;
      if (positions.has(source)) edgeRows.push({ source, target: dataset.node_id, relation: "CATALOGS" });
    });
  });
  (state.assetGraph?.edges || []).forEach((edge) => {
    const source = `ASSET::${edge.source_ref}`;
    const target = `ASSET::${edge.target_ref}`;
    if (positions.has(source) && positions.has(target)) edgeRows.push({ source, target, relation: edge.relation_type });
  });
  edgeSvg.innerHTML = edgeRows.map((edge) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    const used = [edge.source, edge.target].some((id) => all.find((item) => item.node_id === id)?.status === "used");
    return `<path class="data-evidence-edge ${used ? "used" : ""}" d="M${source.x + 39},${source.y + 39} C${source.x + 150},${source.y + 39} ${target.x - 70},${target.y + 39} ${target.x + 39},${target.y + 39}"></path>`;
  }).join("");
  container.innerHTML = [
    `<span class="data-cluster-label" style="left:72px">AKSHARE MACRO CATALOG</span>`,
    `<span class="data-cluster-label" style="left:650px">OFFICIAL DATA + VERSIONED ASSETS</span>`,
    `<span class="data-cluster-label" style="left:1160px">ROUTED EMPIRICAL FACTORS</span>`,
    ...all.map((item) => {
      const point = positions.get(item.node_id);
      return `<button class="data-evidence-node" type="button" data-node-id="${escapeHtml(item.node_id)}" data-status="${escapeHtml(item.status)}" data-type="${escapeHtml(item.node_type)}" title="${escapeHtml(item.detail || item.label)}" style="left:${point.x}px;top:${point.y}px"><i></i><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.node_type)}</small></button>`;
    }),
  ].join("");
  const routedDatasets = datasets.filter((node) => dataNodeStatus(node) === "used").length;
  const routedFactors = factors.filter((node) => dataNodeStatus(node) === "used").length;
  $("#dataUniverseCount").textContent = String(all.length);
  $("#dataRoutedCount").textContent = String(routedDatasets);
  $("#dataFactorCount").textContent = String(routedFactors);
  $("#dataPluginBadges").innerHTML = state.dataPlugins.length
    ? state.dataPlugins.map((plugin) => `<button type="button" data-plugin-toggle="${escapeHtml(plugin.plugin_id)}" data-enabled="${String(plugin.enabled)}" data-state="${plugin.enabled ? "on" : "off"}" ${plugin.configured ? "" : "disabled"} title="${plugin.configured ? "点击切换数据插件" : "需要先在本机配置该来源"}"><b>${escapeHtml(plugin.name)}</b>${plugin.enabled ? "已启用 ✓" : plugin.configured ? "点击启用" : "待配置"}</button>`).join("")
    : `<span><b>Registry</b>${datasets.length} 组官方数据 · ${assets.length} 个 A 资产</span>`;
  if (!state.dataInitialized && all.length) {
    requestAnimationFrame(resetDataView);
    state.dataInitialized = true;
  } else {
    applyDataTransform();
  }
}

function applyDataTransform() {
  $("#dataEvidenceCanvas").style.transform = `translate(${state.dataPanX}px, ${state.dataPanY}px) scale(${state.dataZoom})`;
  $("#dataZoomReset").textContent = `${Math.round(state.dataZoom * 100)}%`;
}

function adjustDataZoom(delta) {
  state.dataZoom = Math.max(.35, Math.min(1.5, state.dataZoom + delta));
  applyDataTransform();
}

function resetDataView() {
  const viewport = $("#dataEvidenceViewport");
  state.dataZoom = Math.max(.42, Math.min(.9, (viewport.clientWidth - 34) / 1900));
  state.dataPanX = 16;
  state.dataPanY = 16;
  applyDataTransform();
}

function visibleGraphNodes() {
  if (!state.graph?.nodes) return [];
  const lane = $("#laneFilter").value;
  const status = $("#statusFilter").value;
  const evidence = $("#evidenceFilter").value;
  const locallyVisible = new Set();
  if (!state.showDetail && state.expandedNodes.size) {
    (state.graph.edges || []).forEach((edge) => {
      if (state.expandedNodes.has(edge.source)) locallyVisible.add(edge.target);
      if (state.expandedNodes.has(edge.target)) locallyVisible.add(edge.source);
    });
  }
  return state.graph.nodes.filter((node) => {
    if (!state.showDetail && TECHNICAL_TYPES.has(node.node_type) && !state.expandedNodes.has(node.node_id) && !locallyVisible.has(node.node_id)) return false;
    if (lane !== "ALL" && node.lane_id && node.lane_id !== lane) return false;
    if (status !== "ALL" && node.status !== status && !["QUESTION", "QUERY", "AGGREGATION", "FINAL_CLAIM"].includes(node.node_type)) return false;
    if (evidence !== "ALL" && ["MODEL_RUN", "EVIDENCE"].includes(node.node_type)) {
      const nodeEvidence = node.metadata?.evidence_type || node.role;
      if (nodeEvidence !== evidence) return false;
    }
    return true;
  });
}

function updateLaneFilter() {
  const select = $("#laneFilter");
  const current = select.value;
  const lanes = [...new Set((state.graph?.nodes || []).map((node) => node.lane_id).filter(Boolean))];
  select.innerHTML = `<option value="ALL">All lanes</option>${lanes.map((lane) => `<option value="${escapeHtml(lane)}">${escapeHtml(lane)}</option>`).join("")}`;
  select.value = lanes.includes(current) ? current : "ALL";
}

function computeLayout(nodes) {
  const lanes = ["__GLOBAL__", ...[...new Set(nodes.map((node) => node.lane_id).filter(Boolean))]];
  const groups = new Map();
  lanes.forEach((lane) => groups.set(lane, []));
  nodes.forEach((node) => groups.get(node.lane_id || "__GLOBAL__")?.push(node));
  const positions = new Map();
  const bands = [];
  let yCursor = 0;
  lanes.forEach((lane) => {
    const group = groups.get(lane) || [];
    if (!group.length) return;
    const byColumn = new Map();
    group.forEach((node) => {
      const column = COLUMN_BY_TYPE[node.node_type] ?? 5;
      if (!byColumn.has(column)) byColumn.set(column, []);
      byColumn.get(column).push(node);
    });
    const maxCount = Math.max(1, ...[...byColumn.values()].map((items) => items.length));
    const height = Math.max(lane === "__GLOBAL__" ? 174 : 198, maxCount * 116 + 68);
    bands.push({ lane, y: yCursor, height });
    byColumn.forEach((items, column) => {
      items.forEach((node, index) => positions.set(node.node_id, { x: 78 + column * 282, y: yCursor + 42 + index * 116, width: 246, height: 94 }));
    });
    yCursor += height;
  });
  return { positions, bands, width: 78 + 15 * 282 + 274, height: Math.max(560, yCursor + 36) };
}

function renderGraph() {
  if (!state.graph) return;
  renderDataEvidenceLayer();
  updateLaneFilter();
  const nodes = visibleGraphNodes();
  const visibleIds = new Set(nodes.map((node) => node.node_id));
  const edges = (state.graph.edges || []).filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const layout = computeLayout(nodes);
  state.layout = layout;
  const canvas = $("#graphCanvas");
  const edgeSvg = $("#graphEdges");
  canvas.style.width = `${layout.width}px`;
  canvas.style.height = `${layout.height}px`;
  edgeSvg.setAttribute("width", layout.width);
  edgeSvg.setAttribute("height", layout.height);
  edgeSvg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  const hiddenCounts = new Map();
  if (!state.showDetail) {
    (state.graph.edges || []).forEach((edge) => {
      const source = state.graph.nodes.find((node) => node.node_id === edge.source);
      const target = state.graph.nodes.find((node) => node.node_id === edge.target);
      if (target && TECHNICAL_TYPES.has(target.node_type) && visibleIds.has(edge.source)) hiddenCounts.set(edge.source, (hiddenCounts.get(edge.source) || 0) + 1);
      if (source && TECHNICAL_TYPES.has(source.node_type) && visibleIds.has(edge.target)) hiddenCounts.set(edge.target, (hiddenCounts.get(edge.target) || 0) + 1);
    });
  }
  $("#graphNodes").innerHTML = [
    ...layout.bands.map((band) => `<div class="lane-band" style="left:0;top:${band.y}px;width:${layout.width}px;height:${band.height}px"><span class="lane-label">${escapeHtml(band.lane === "__GLOBAL__" ? "GLOBAL COMPILER" : band.lane)}</span></div>`),
    ...nodes.map((node) => {
      const position = layout.positions.get(node.node_id);
      const collapsed = hiddenCounts.get(node.node_id) || 0;
      const counts = node.metadata?.universe_counts;
      const countLabel = counts ? `${counts.mechanisms || 0}M · ${counts.factors || 0}F · ${counts.model_specifications || 0}S` : "";
      return `<button class="graph-node" type="button" data-node-id="${escapeHtml(node.node_id)}" data-type="${escapeHtml(node.node_type)}" data-status="${escapeHtml(node.status)}" data-role="${escapeHtml(node.role || "")}" style="left:${position.x}px;top:${position.y}px">
        <span class="node-top"><i>${escapeHtml(node.node_type)}</i><b class="node-status"></b></span>
        <strong class="node-label">${escapeHtml(node.label)}</strong>
        ${countLabel ? `<span class="node-density">${escapeHtml(countLabel)}</span>` : ""}
        <span class="node-foot"><i>${escapeHtml(node.lane_id || node.status)}</i>${collapsed ? `<b class="collapsed-count" title="Click to expand connected data nodes">+${collapsed}</b>` : `<i>${escapeHtml(node.status)}</i>`}</span>
      </button>`;
    }),
  ].join("");
  edgeSvg.innerHTML = edges.map((edge) => {
    const source = layout.positions.get(edge.source);
    const target = layout.positions.get(edge.target);
    const sx = source.x + source.width, sy = source.y + source.height / 2;
    const tx = target.x, ty = target.y + target.height / 2;
    const dx = Math.max(35, (tx - sx) * .48);
    const targetNode = nodes.find((node) => node.node_id === edge.target);
    const classes = ["graph-edge", targetNode?.status === "FAILED" ? "failed" : ""].filter(Boolean).join(" ");
    return `<path class="${classes}" data-source="${escapeHtml(edge.source)}" data-target="${escapeHtml(edge.target)}" d="M${sx},${sy} C${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}"></path>`;
  }).join("");
  const allNodes = state.graph.nodes || [];
  const planned = allNodes.filter((node) => ["PLANNED", "PENDING", "RUNNING", "SUCCESS", "WARNING", "FAILED"].includes(node.status)).length;
  const blocked = allNodes.filter((node) => node.status === "BLOCKED").length;
  const notRouted = allNodes.filter((node) => node.status === "NOT_ROUTED").length;
  $("#graphStats").textContent = `${nodes.length} visible / ${allNodes.length} total · ${planned} routed · ${blocked} blocked · ${notRouted} not routed`;
  if (!state.graphInitialized && nodes.length) {
    resetGraphView();
    state.graphInitialized = true;
  } else {
    applyGraphTransform();
  }
}

function applyGraphTransform() {
  $("#graphCanvas").style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  $("#zoomReset").textContent = `${Math.round(state.zoom * 100)}%`;
}

function resetGraphView() {
  const viewport = $("#graphViewport");
  const width = state.layout?.width || 2400;
  // On phones, preserve readable node typography and let the user pan through
  // the graph instead of shrinking the entire DAG into illegible thumbnails.
  state.zoom = window.innerWidth <= 640
    ? .68
    : Math.max(.38, Math.min(.85, (viewport.clientWidth - 40) / width));
  state.panX = 20;
  state.panY = 15;
  applyGraphTransform();
}

function adjustZoom(delta) {
  state.zoom = Math.max(.3, Math.min(1.45, state.zoom + delta));
  applyGraphTransform();
}

async function openNode(nodeId) {
  const node = state.graph?.nodes?.find((item) => item.node_id === nodeId);
  if (!node) return;
  if (!state.showDetail) {
    state.expandedNodes.add(nodeId);
    renderGraph();
  }
  state.selectedNode = node;
  state.nodeDetail = null;
  state.activeTab = "overview";
  state.drawerReturnFocus = document.activeElement;
  $("#drawerType").textContent = node.node_type;
  $("#drawerTitle").textContent = node.label;
  $("#drawerSubtitle").textContent = `${node.node_id} · ${node.status}`;
  $("#detailDrawer").classList.add("open");
  $("#detailDrawer").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  $(".drawer-close", $("#detailDrawer"))?.focus({ preventScroll: true });
  updateDrawerTabs();
  $("#drawerBody").innerHTML = `<div class="detail-section"><h3>Loading node detail…</h3></div>`;
  try {
    state.nodeDetail = await api(`/v1/research-jobs/${encodeURIComponent(state.currentJob.job_id)}/nodes/${encodeURIComponent(node.node_id)}`);
  } catch (error) {
    state.nodeDetail = { error: error.message, status: node.status, metadata: node.metadata, node_type: node.node_type, lane_id: node.lane_id, role: node.role };
  }
  renderDrawer();
}

function closeDrawer() {
  if (!$("#detailDrawer").classList.contains("open")) return;
  $("#detailDrawer").classList.remove("open");
  $("#detailDrawer").setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  state.drawerReturnFocus?.focus?.();
  state.drawerReturnFocus = null;
}

function focusable(container) {
  return $$("button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])", container)
    .filter((element) => element.offsetParent !== null);
}

function trapFocus(event, container) {
  if (event.key !== "Tab") return;
  const items = focusable(container);
  if (!items.length) return;
  const first = items[0], last = items.at(-1);
  if (!container.contains(document.activeElement)) { event.preventDefault(); first.focus(); }
  else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function openHistory() {
  state.historyReturnFocus = document.activeElement;
  $("#historyPanel").classList.add("open");
  $("#historyPanel").setAttribute("aria-hidden", "false");
  // Focus after the visibility transition has entered the rendering pipeline;
  // otherwise the activating button can reclaim focus at the end of its click.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if ($("#historyPanel").classList.contains("open")) {
      $("#historyClose").focus({ preventScroll: true });
    }
  }));
}

function closeHistory() {
  if (!$("#historyPanel").classList.contains("open")) return;
  $("#historyPanel").classList.remove("open");
  $("#historyPanel").setAttribute("aria-hidden", "true");
  state.historyReturnFocus?.focus?.();
  state.historyReturnFocus = null;
}

function updateDrawerTabs() {
  $$("#drawerTabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === state.activeTab));
}

function renderDrawer() {
  updateDrawerTabs();
  const detail = state.nodeDetail || {};
  const renderers = { overview: renderOverview, specification: renderSpecification, data: renderDataVariables, results: renderResults, diagnostics: renderDiagnostics, robustness: renderRobustness, provenance: renderProvenance };
  $("#drawerBody").innerHTML = (renderers[state.activeTab] || renderOverview)(detail);
  if (state.activeTab === "specification") renderFormula(detail.specification?.formula);
}

function fallbackNodeExplanation(detail) {
  const node = state.selectedNode || {};
  const type = detail.node_type || node.node_type || (String(detail.node_id || node.node_id || "").startsWith("MR::") ? "MODEL_RUN" : "RESEARCH_OBJECT");
  const title = detail.title || node.label || detail.node_id || node.node_id || "this research object";
  const summaries = {
    QUESTION: ["Preserves the user's original research question as the root of the graph.", "It prevents downstream routing and models from drifting away from the actual question."],
    QUERY: ["Compiles the natural-language question into a structured task, horizon and output contract.", "Python needs a validated query contract before it can route lanes or execute registered models."],
    RESEARCH_DEPTH_GATE: ["Checks whether the planned evidence is deep enough for the question.", "It blocks a large macro conclusion from resting on only a few shallow statistics."],
    LANE: ["Separates one macro transmission domain and gathers its evidence.", "Large macro questions need parallel, mechanism-specific research before cross-lane synthesis."],
    MECHANISM: ["States a testable transmission hypothesis inside a macro lane.", "It connects the broad economic narrative to measurable factors and registered models."],
    RESEARCH_NODE: ["Produces one bounded intermediate research claim.", "Evidence closes at the claim level before it is allowed into the overall conclusion."],
    CLAIM: ["Holds an intermediate proposition that evidence may support or refute.", "It prevents incomparable estimates from being added together directly."],
    FACTOR: ["Defines one measurable macro variable used by the research mechanism.", "A variable needs a fixed definition, source, unit and frequency before it can enter a model."],
    DATASET: ["Defines the official data source and vintage contract.", "This protects reproducibility and prevents historical jobs from reading future revisions."],
    TRANSFORM: ["Converts a raw series into an allow-listed model-ready representation.", "Scale, frequency and trend treatment must be controlled before estimation."],
    MODEL_SPECIFICATION: ["Freezes the empirical design, variables, parameters and diagnostics.", "AI may select registered building blocks but cannot rewrite the model code."],
    MODEL_RUN: ["Executes registered Python statistical code and produces quantitative evidence.", "This is where the mechanism is tested against real observations rather than described by an LLM."],
    DIAGNOSTIC: ["Tests whether the parent model is credible enough to use.", "A coefficient or forecast is not trusted until its method-specific assumptions and errors are checked."],
    EVIDENCE: ["Normalizes a model result into a traceable evidence object.", "Different methods need a common evidence boundary without losing their interpretation limits."],
    LANE_SIGNAL: ["Combines diagnosed claims within one macro lane.", "Cross-lane synthesis first needs a transparent lane-level direction and contribution record."],
    AGGREGATION: ["Combines heterogeneous lane evidence into the overall answer.", "No single model can answer a complex macro question on its own."],
    FINAL_CLAIM: ["States the principal user-facing conclusion.", "It closes the research chain while preserving links to every underlying model and data snapshot."],
    FALSIFIER: ["Records an observable condition that could overturn the conclusion.", "A research conclusion needs an explicit boundary under which it should be revised."],
  };
  const [purpose, why] = summaries[type] || [`Records and executes ${title} as a traceable research step.`, "It keeps this part of the research process inspectable in the graph."];
  const variables = detail.variables || [];
  const sample = detail.sample;
  const data = variables.length
    ? `Uses ${variables.length} registered variable${variables.length === 1 ? "" : "s"}${sample ? ` from ${sample.start} to ${sample.end} (${sample.observations || "—"} observations)` : ""}.`
    : "Uses structured upstream inputs; this node does not independently run a new macro series.";
  return {
    purpose,
    why_it_exists: why,
    mechanism: detail.specification?.estimand || detail.specification?.hypothesis || detail.summary || node.summary || "This is a constrained research, routing or governance mechanism rather than a new empirical estimate.",
    data_summary: data,
    output_summary: "Its structured output is passed to the connected downstream research node.",
    plain_summary: `${purpose} ${why}`,
  };
}

function renderNodeBrief(detail) {
  const facts = detail.explanation || fallbackNodeExplanation(detail);
  const llm = facts.llm || {};
  const usesLlm = llm.status === "SUCCESS";
  const narrative = llm.narrative_summary || facts.plain_summary || `${facts.purpose} ${facts.why_it_exists}`;
  const mechanism = llm.mechanism_walkthrough || facts.mechanism;
  return `<article class="node-brief">
    <header class="node-brief-head">
      <div><span>NODE BRIEF</span><strong>这一步在研究链中做什么</strong></div>
      <em class="explanation-source ${usesLlm ? "llm" : "fixed"}">${usesLlm ? "GROUNDED LLM EXPLANATION" : "REGISTRY FACTS"}</em>
    </header>
    <p class="node-brief-lead">${escapeHtml(narrative)}</p>
    <div class="node-brief-grid">
      <section><span>WHAT IT DOES</span><p>${escapeHtml(facts.purpose)}</p></section>
      <section><span>WHY IT EXISTS</span><p>${escapeHtml(facts.why_it_exists)}</p></section>
      <section><span>MECHANISM</span><p>${escapeHtml(mechanism)}</p></section>
      <section><span>DATA / INPUT</span><p>${escapeHtml(facts.data_summary)}</p></section>
    </div>
    <footer><span>OUTPUT</span><p>${escapeHtml(facts.output_summary)}</p></footer>
  </article>`;
}

function renderOverview(detail) {
  if (detail.error) return `<div class="detail-section"><h3>Node unavailable</h3><div class="detail-card wide"><p>${escapeHtml(detail.error)}</p></div></div>`;
  const overview = detail.overview || {};
  const method = detail.method || detail.specification?.method || detail.metadata?.model_recipe_id || state.selectedNode?.node_type;
  const lane = detail.lane_id || overview.lane_id || state.selectedNode?.lane_id || "GLOBAL";
  const role = detail.role || overview.role || state.selectedNode?.role || "—";
  return `<div class="detail-section"><h3>Research purpose & contribution</h3>${renderNodeBrief(detail)}<div class="detail-grid execution-detail-grid">
    ${detailCard("STATUS", pretty(detail.status || detail.node_status), detail.summary || state.selectedNode?.summary || "No summary")}
    ${detailCard("METHOD / OBJECT", method, detail.evidence_type ? `Evidence type: ${pretty(detail.evidence_type)}` : `Lane: ${lane} · role: ${role}`)}
    ${detailCard("DIRECTION", pretty(detail.direction || "—"), `Confidence: ${pretty(detail.confidence || "—")} · signal: ${formatNumber(detail.signal)}`)}
    ${detailCard("SAMPLE", detail.sample ? `${detail.sample.start} → ${detail.sample.end}` : "Not applicable", detail.sample ? `${detail.sample.observations || "—"} observations · ${detail.sample.frequency || "—"}` : "This object remains inspectable even before numeric execution.")}
    ${detail.specification ? detailCard("ESTIMAND / HYPOTHESIS", detail.specification.estimand || detail.specification.hypothesis || detail.specification.intermediate_claim || "Registered research object", detail.specification.dependent_variable ? `DV: ${detail.specification.dependent_variable}` : detail.specification.estimand_boundary || "See Specification and Provenance tabs.", "wide") : ""}
    ${overview.upstream ? detailCard("LINEAGE", `${overview.upstream.length} upstream · ${overview.downstream?.length || 0} downstream`, "Every connected object is traceable in this immutable job graph.", "wide") : ""}
  </div>${renderCharts(detail.charts || [])}</div>`;
}

function detailCard(kicker, title, text, className = "") {
  return `<article class="detail-card ${className}"><span>${escapeHtml(kicker)}</span><h4>${escapeHtml(title)}</h4><p>${escapeHtml(text)}</p></article>`;
}

function renderSpecification(detail) {
  const spec = detail.specification;
  if (!spec) return emptyDetail("Specification", "This node has no registered specification contract.");
  return `<div class="detail-section"><h3>Registered specification</h3>${spec.formula ? `<div id="formulaBox" class="formula-box">${escapeHtml(spec.formula)}</div>` : ""}<dl class="definition-list">
    <div><dt>Method</dt><dd>${escapeHtml(spec.method || detail.method || "Registered non-model object")}</dd></div>
    <div><dt>Hypothesis</dt><dd>${escapeHtml(spec.hypothesis || spec.intermediate_claim || "—")}</dd></div>
    <div><dt>Estimand</dt><dd>${escapeHtml(spec.estimand || spec.estimand_boundary || "Defined at the downstream model specification")}</dd></div>
    <div><dt>Dependent variable</dt><dd>${escapeHtml(spec.dependent_variable || "—")}</dd></div>
    <div><dt>Independent variables</dt><dd>${escapeHtml((spec.independent_variables || spec.factor_ids || []).join(" · ") || "—")}</dd></div>
    <div><dt>Controls</dt><dd>${escapeHtml((spec.controls || []).join(" · ") || "None")}</dd></div>
    ${spec.fixed_effects ? `<div><dt>Fixed effects</dt><dd>${escapeHtml(spec.fixed_effects)}</dd></div>` : ""}
    <div><dt>Parameters</dt><dd>${escapeHtml(JSON.stringify(spec.parameters || detail.parameters?.values || {}, null, 0))}</dd></div>
    <div><dt>Parameter source</dt><dd>${escapeHtml(detail.parameters?.source || "Registry policy / immutable specification")}</dd></div>
  </dl></div>`;
}

function renderFormula(formula) {
  const target = $("#formulaBox");
  if (!target || !formula || !window.katex) return;
  try { window.katex.render(formula, target, { displayMode: true, throwOnError: false }); }
  catch { target.textContent = formula; }
}

function renderDataVariables(detail) {
  const variables = detail.variables || [];
  if (!variables.length) {
    const factorIds = detail.specification?.factor_ids || detail.provenance?.registry_metadata?.factor_pool || [];
    return factorIds.length
      ? `<div class="detail-section"><h3>Registered factor dependencies</h3><pre class="json-block">${escapeHtml(JSON.stringify(factorIds, null, 2))}</pre></div>`
      : emptyDetail("Data & Variables", "This object has no variable-level data contract; inspect its connected factor or model nodes.");
  }
  return `<div class="detail-section"><h3>Data, variables & vintage</h3><div class="table-scroll"><table class="variable-table"><thead><tr><th>Factor</th><th>Definition</th><th>Series</th><th>Unit</th><th>Frequency</th><th>Dataset</th><th>Release</th></tr></thead><tbody>${variables.map((variable) => `<tr><td>${escapeHtml(variable.factor_id)}</td><td>${escapeHtml(variable.definition)}</td><td>${escapeHtml(variable.series_id)}</td><td>${escapeHtml(variable.unit)}</td><td>${escapeHtml(variable.frequency)}</td><td>${escapeHtml(variable.dataset_id)}</td><td>${escapeHtml(variable.release_lag)}</td></tr>`).join("")}</tbody></table></div>
    <h3 style="margin-top:28px">Sample contract</h3><pre class="json-block">${escapeHtml(JSON.stringify(detail.sample || {}, null, 2))}</pre></div>`;
}

function renderResults(detail) {
  const table = detail.table;
  if (!table) {
    if (detail.status === "FAILED") return emptyDetail("Results", `模型失败：${detail.error_type || "unknown error"}`);
    return `<div class="detail-section"><h3>Structured result state</h3><pre class="json-block">${escapeHtml(JSON.stringify(detail.results || { status: detail.status, note: "Numeric results are produced only by an executed model run." }, null, 2))}</pre></div>`;
  }
  const columns = table.columns || [];
  const variables = [];
  const matrix = new Map();
  const labels = new Map();
  Object.entries(table.coefficients || {}).forEach(([column, coefficients]) => coefficients.forEach((item) => {
    if (!variables.includes(item.variable_id)) variables.push(item.variable_id);
    labels.set(item.variable_id, item.label);
    matrix.set(`${item.variable_id}::${column}`, item);
  }));
  const variableRows = variables.map((variable) => {
    const estimates = columns.map((column) => {
      const item = matrix.get(`${variable}::${column}`);
      return `<td>${item ? `${formatNumber(item.coefficient)}${escapeHtml(item.stars || "")}` : ""}</td>`;
    }).join("");
    const errors = columns.map((column) => {
      const item = matrix.get(`${variable}::${column}`);
      return `<td>${item ? `(${formatNumber(item.standard_error)})` : ""}</td>`;
    }).join("");
    const details = columns.map((column) => {
      const item = matrix.get(`${variable}::${column}`);
      return `<td>${item ? `p=${formatNumber(item.p_value, 6)}<br>CI [${formatNumber(item.ci_low)}, ${formatNumber(item.ci_high)}]` : ""}</td>`;
    }).join("");
    return `<tr><th>${escapeHtml(labels.get(variable) || variable)}</th>${estimates}</tr><tr class="se-row"><th></th>${errors}</tr><tr class="detail-row"><th></th>${details}</tr>`;
  }).join("");
  const statisticRows = Object.entries(table.statistics || {}).map(([label, values], index) => `<tr class="${index === 0 ? "stat-start" : ""}"><th>${escapeHtml(label)}</th>${columns.map((_, columnIndex) => `<td>${escapeHtml(values[columnIndex] ?? "")}</td>`).join("")}</tr>`).join("");
  return `<div class="detail-section"><h3>Academic results</h3><p class="table-title">${escapeHtml(table.title)}</p>${artifactLinks(detail.artifacts)}<div class="table-scroll"><table class="academic-table"><thead><tr><th>Variable</th>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr></thead><tbody>${variableRows}${statisticRows}</tbody></table></div><p class="table-notes">${escapeHtml((table.notes || []).join(" "))}</p>${renderCharts(detail.charts || [])}</div>`;
}

function artifactLinks(artifacts = []) {
  const tableArtifacts = artifacts.filter((item) => ["CSV", "JSON", "HTML", "LATEX"].includes(item.artifact_type));
  if (!tableArtifacts.length) return "";
  return `<div class="artifact-row">${tableArtifacts.map((item) => `<a href="${escapeHtml(apiUrl(`/v1/artifacts/${encodeURIComponent(item.artifact_id)}`))}" target="_blank" rel="noopener">${escapeHtml(item.artifact_type)} ↗</a>`).join("")}</div>`;
}

function renderDiagnostics(detail) {
  const diagnostics = detail.diagnostics || [];
  if (!diagnostics.length) return emptyDetail("Diagnostics", detail.status === "FAILED" ? `执行失败：${detail.error_type || "unknown"}` : "该节点没有方法专属诊断。");
  const normalized = diagnostics.map((item) => typeof item === "string"
    ? { status: "PLANNED", name: pretty(item), interpretation: "Required by the registered model recipe.", credibility_impact: "Execution must report this diagnostic before the evidence can be trusted.", statistic: null, p_value: null }
    : item);
  return `<div class="detail-section"><h3>Method-specific diagnostics</h3><div class="diagnostic-list">${normalized.map((item) => `<article class="diagnostic-card ${String(item.status).toLowerCase()}"><div class="diagnostic-status">${escapeHtml(item.status)}</div><div class="diagnostic-main"><h4>${escapeHtml(item.name)}</h4><p>${escapeHtml(item.interpretation)}</p><p><strong>Credibility:</strong> ${escapeHtml(item.credibility_impact)}</p></div><div class="diagnostic-stat">STAT ${escapeHtml(formatNumber(item.statistic, 6))}<br>P ${escapeHtml(formatNumber(item.p_value, 6))}</div></article>`).join("")}</div>${renderCharts(detail.charts || [])}</div>`;
}

function renderRobustness(detail) {
  if (!detail.robustness) return emptyDetail("Robustness", "该节点没有稳健性或样本外结果。");
  return `<div class="detail-section"><h3>Robustness & out-of-sample checks</h3><pre class="json-block">${escapeHtml(JSON.stringify(detail.robustness, null, 2))}</pre>${renderCharts(detail.charts || [])}</div>`;
}

function renderProvenance(detail) {
  const provenance = detail.provenance || detail.metadata || {};
  const registryMetadata = provenance.registry_metadata || {};
  return `<div class="detail-section"><h3>Immutable provenance</h3>${artifactLinks(detail.artifacts)}<dl class="definition-list">
    <div><dt>Model recipe</dt><dd>${escapeHtml(provenance.model_recipe_id || registryMetadata.model_recipe_id || detail.model_recipe_id || "—")}</dd></div>
    <div><dt>Code artifact</dt><dd>${escapeHtml(provenance.code_artifact || registryMetadata.code_artifact || "Registry graph object")}</dd></div>
    <div><dt>Registry version</dt><dd>${escapeHtml(provenance.registry_version || "0.2.0 + depth extension")}</dd></div>
    <div><dt>Parameter decision</dt><dd>${escapeHtml(JSON.stringify(detail.parameters || {}, null, 0))}</dd></div>
  </dl><h3 style="margin-top:28px">Report page evidence</h3><pre class="json-block">${escapeHtml(JSON.stringify(provenance.report_evidence || [], null, 2))}</pre><h3 style="margin-top:28px">Registry object</h3><pre class="json-block">${escapeHtml(JSON.stringify(registryMetadata, null, 2))}</pre><h3 style="margin-top:28px">Data snapshots</h3><pre class="json-block">${escapeHtml(JSON.stringify(provenance.data_lineage || [], null, 2))}</pre></div>`;
}

function emptyDetail(title, message) {
  return `<div class="detail-section"><h3>${escapeHtml(title)}</h3><div class="detail-card wide"><p>${escapeHtml(message)}</p></div></div>`;
}

function renderCharts(charts) {
  if (!charts.length) return "";
  return charts.map((chart) => `<article class="chart-card"><h4>${escapeHtml(chart.title)}</h4><span>${escapeHtml(pretty(chart.kind))}</span>${chartSvg(chart)}<div class="chart-legend">${(chart.series || []).map((series, index) => `<span><i style="background:${COLORS[index % COLORS.length]}"></i>${escapeHtml(series.label)}</span>`).join("")}</div></article>`).join("");
}

function chartSvg(chart) {
  const series = chart.series || [];
  const points = series.flatMap((item) => item.points || []).filter((point) => Number.isFinite(Number(point.value)));
  if (!points.length) return `<p>No chart data.</p>`;
  const categories = [...new Set(points.map((point) => String(point.date)))];
  const values = points.map((point) => Number(point.value));
  let min = Math.min(...values), max = Math.max(...values);
  if (min === max) { min -= 1; max += 1; }
  const pad = Math.max((max - min) * .12, .05);
  min -= pad; max += pad;
  const width = 820, height = 300, left = 52, right = 16, top = 16, bottom = 34;
  const x = (category) => left + categories.indexOf(String(category)) / Math.max(1, categories.length - 1) * (width - left - right);
  const y = (value) => top + (max - Number(value)) / (max - min) * (height - top - bottom);
  const grid = [0, .5, 1].map((ratio) => {
    const yy = top + ratio * (height - top - bottom);
    return `<line class="chart-gridline" x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}"></line><text class="chart-axis" x="2" y="${yy + 3}">${formatNumber(max - ratio * (max - min), 2)}</text>`;
  }).join("");
  const zero = min < 0 && max > 0 ? `<line class="chart-zero" x1="${left}" y1="${y(0)}" x2="${width - right}" y2="${y(0)}"></line>` : "";
  let marks;
  if (chart.kind === "factor_loadings") {
    const barWidth = Math.max(4, (width - left - right) / Math.max(1, categories.length) * .55);
    marks = points.map((point, index) => {
      const xx = x(point.date) - barWidth / 2, yy = y(Math.max(0, Number(point.value))), y0 = y(0);
      return `<rect x="${xx}" y="${Math.min(yy, y0)}" width="${barWidth}" height="${Math.max(1, Math.abs(y0 - yy))}" fill="${COLORS[index % COLORS.length]}"></rect>`;
    }).join("");
  } else {
    marks = series.map((item, index) => {
      const valid = (item.points || []).filter((point) => Number.isFinite(Number(point.value)));
      const d = valid.map((point, pointIndex) => `${pointIndex ? "L" : "M"}${x(point.date).toFixed(1)},${y(point.value).toFixed(1)}`).join(" ");
      return `<path class="chart-line" d="${d}" stroke="${COLORS[index % COLORS.length]}"></path>`;
    }).join("");
  }
  const first = categories[0], last = categories.at(-1);
  return `<div class="table-scroll"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(chart.title)}">${grid}${zero}${marks}<text class="chart-axis" x="${left}" y="${height - 5}">${escapeHtml(first)}</text><text class="chart-axis" text-anchor="end" x="${width - right}" y="${height - 5}">${escapeHtml(last)}</text></svg></div>`;
}

async function cancelCurrentJob() {
  if (!state.currentJob || TERMINAL.has(state.currentJob.status)) return;
  try {
    await api(`/v1/research-jobs/${encodeURIComponent(state.currentJob.job_id)}/cancel`, { method: "POST" });
    toast("已发送取消请求");
  } catch (error) { toast(error.message); }
}

async function loadConnectionSettings() {
  const [catalog, status] = await Promise.all([
    api("/v1/settings/catalog"),
    api("/v1/settings/status"),
  ]);
  state.settingsCatalog = catalog;
  state.settingsStatus = status;
  state.selectedProvider = status.llm.provider || "deepseek";
  renderConnectionSummary();
  renderLlmSettings(true);
  renderDataSources();
}

function renderConnectionSummary() {
  const status = state.settingsStatus;
  if (!status) return;
  const llm = status.llm;
  const required = status.data_sources.filter((item) => item.key_required);
  const ready = required.filter((item) => item.configured).length;
  $("#providerSetupDot").classList.toggle("ready", llm.configured && ready > 0);
  $("#providerSetupLabel").textContent = llm.configured
    ? `${llm.provider_label} / ${llm.model} · 数据 Key ${ready}/${required.length}`
    : `配置你自己的模型与数据 API · 数据 Key ${ready}/${required.length}`;
}

function openSettings(tab = "model") {
  state.settingsReturnFocus = document.activeElement;
  $("#settingsPanel").setAttribute("aria-hidden", "false");
  document.body.classList.add("settings-open");
  selectSettingsTab(tab);
  $(".settings-close", $("#settingsPanel")).focus();
}

function closeSettings() {
  $("#settingsPanel").setAttribute("aria-hidden", "true");
  document.body.classList.remove("settings-open");
  state.settingsReturnFocus?.focus?.();
}

function selectSettingsTab(tab) {
  $$("#settingsTabs button").forEach((button) => button.classList.toggle("active", button.dataset.settingsTab === tab));
  $$(".settings-tab").forEach((panel) => panel.classList.toggle("active", panel.dataset.settingsPanel === tab));
  $(".settings-body", $("#settingsPanel")).scrollTop = 0;
}

function providerConfig(providerId = state.selectedProvider) {
  return state.settingsCatalog?.llm_providers.find((item) => item.provider_id === providerId);
}

function selectLlmProvider(providerId, preserveCurrent = false) {
  const config = providerConfig(providerId);
  if (!config) return;
  state.selectedProvider = providerId;
  $$("#llmProviderPills button").forEach((button) => button.classList.toggle("active", button.dataset.provider === providerId));
  const select = $("#llmModelSelect");
  select.innerHTML = config.models.map((model) => `<option value="${escapeHtml(model.id)}">${escapeHtml(model.label)} · ${escapeHtml(model.tier)}</option>`).join("")
    + `<option value="__custom__">自定义模型 ID…</option>`;
  const current = preserveCurrent && state.settingsStatus?.llm.provider === providerId ? state.settingsStatus.llm : null;
  const selectedModel = current?.model || config.default_model;
  const exists = config.models.some((model) => model.id === selectedModel);
  select.value = exists ? selectedModel : "__custom__";
  $("#llmCustomModelField").classList.toggle("hidden", exists);
  $("#llmCustomModel").value = exists ? "" : selectedModel;
  $("#llmBaseUrl").value = current?.base_url || config.default_base_url || "";
  $("#llmApiKey").placeholder = current?.api_key_masked
    ? `${current.api_key_masked} 已配置；留空则保留`
    : config.key_placeholder || "输入 API Key";
  $("#llmKeyHint").textContent = current?.configured
    ? `当前密钥：${current.api_key_masked || "已配置"}；存储方式：${pretty(current.storage)}。`
    : "默认只保留到本次 Python 服务器关闭。";
  renderLlmGuide(config);
}

function renderLlmSettings(preserveCurrent = false) {
  if (!state.settingsCatalog || !state.settingsStatus) return;
  $("#llmProviderPills").innerHTML = state.settingsCatalog.llm_providers
    .map((item) => `<button type="button" role="radio" aria-checked="${item.provider_id === state.selectedProvider}" data-provider="${escapeHtml(item.provider_id)}">${escapeHtml(item.label)}</button>`)
    .join("");
  const status = state.settingsStatus.llm;
  $("#llmConfigStatus").textContent = status.configured ? `${status.provider_label} / READY` : "NOT CONFIGURED";
  $("#llmConfigStatus").classList.toggle("ready", status.configured);
  $("#llmPersist").checked = status.storage === "persistent";
  selectLlmProvider(state.selectedProvider, preserveCurrent);
}

function renderLlmGuide(config) {
  const links = [
    config.key_url ? `<a href="${escapeHtml(config.key_url)}" target="_blank" rel="noopener">打开 API Key 申请页 ↗</a>` : "",
    config.docs_url ? `<a href="${escapeHtml(config.docs_url)}" target="_blank" rel="noopener">查看官方模型 / API 文档 ↗</a>` : "",
  ].filter(Boolean).join(" · ");
  $("#llmGuideBody").innerHTML = `<ol>${config.guide_steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol><p>${links}</p>`;
}

function selectedLlmModel() {
  return $("#llmModelSelect").value === "__custom__"
    ? $("#llmCustomModel").value.trim()
    : $("#llmModelSelect").value;
}

async function saveLlmSettings() {
  const button = $("#saveLlmSettings");
  button.disabled = true;
  setTestResult($("#llmTestResult"), "正在保存…");
  try {
    const key = $("#llmApiKey").value.trim();
    const payload = {
      provider: state.selectedProvider,
      model: selectedLlmModel(),
      base_url: $("#llmBaseUrl").value.trim(),
      persist: $("#llmPersist").checked,
    };
    if (key) payload.api_key = key;
    await api("/v1/settings/llm", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    $("#llmApiKey").value = "";
    await refreshSettingsStatus();
    setTestResult($("#llmTestResult"), "配置已保存；尚未发送模型请求。", true);
  } catch (error) {
    setTestResult($("#llmTestResult"), error.message, false);
  } finally {
    button.disabled = false;
  }
}

async function testLlmSettings() {
  const button = $("#testLlmSettings");
  button.disabled = true;
  setTestResult($("#llmTestResult"), "正在发送最小结构化输出测试…");
  try {
    const result = await api("/v1/settings/llm/test", { method: "POST" });
    setTestResult($("#llmTestResult"), `${result.model} · ${result.latency_ms} ms · ${result.detail}`, true);
  } catch (error) {
    setTestResult($("#llmTestResult"), error.message, false);
  } finally {
    button.disabled = false;
  }
}

async function clearLlmSettings() {
  try {
    const cleared = await api("/v1/settings/llm", { method: "DELETE" });
    $("#llmApiKey").value = "";
    await refreshSettingsStatus();
    setTestResult(
      $("#llmTestResult"),
      cleared.storage === "environment"
        ? "当前密钥来自 .env.local；请删除对应环境变量并重启服务器。"
        : "本地设置文件中的模型密钥已清除。",
      cleared.storage === "environment" ? null : true,
    );
  } catch (error) {
    setTestResult($("#llmTestResult"), error.message, false);
  }
}

function setTestResult(element, message, success = null) {
  element.textContent = message;
  element.classList.toggle("success", success === true);
  element.classList.toggle("failure", success === false);
}

async function refreshSettingsStatus() {
  state.settingsStatus = await api("/v1/settings/status");
  state.selectedProvider = state.settingsStatus.llm.provider || state.selectedProvider;
  renderConnectionSummary();
  renderLlmSettings(true);
  renderDataSources();
  if (state.health) {
    state.health.llm_configured = state.settingsStatus.llm.configured;
    state.health.llm_provider = state.settingsStatus.llm.provider;
    state.health.llm_model = state.settingsStatus.llm.model;
  }
}

function dataStatus(sourceId) {
  return state.settingsStatus?.data_sources.find((item) => item.source_id === sourceId);
}

function renderDataSources() {
  if (!state.settingsCatalog || !state.settingsStatus) return;
  $("#dataSourceList").innerHTML = state.settingsCatalog.data_sources.map((source) => {
    const status = dataStatus(source.source_id);
    const statusText = status?.configured ? (source.key_required ? "KEY READY" : "NO KEY REQUIRED") : "KEY REQUIRED";
    const guide = `<details class="data-source-guide"><summary>申请步骤与官方文档</summary><ol>${source.guide_steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol><div class="data-source-links">${source.key_url ? `<a href="${escapeHtml(source.key_url)}" target="_blank" rel="noopener">申请 / 管理 API Key ↗</a>` : ""}<a href="${escapeHtml(source.docs_url)}" target="_blank" rel="noopener">官方 API 文档 ↗</a></div></details>`;
    const controls = source.key_required ? `
      <div class="data-source-controls">
        <div class="data-secret-row">
          <input type="password" autocomplete="off" spellcheck="false" data-source-key="${escapeHtml(source.source_id)}" placeholder="${status?.api_key_masked ? `${escapeHtml(status.api_key_masked)} 已配置；输入新 Key 可替换` : escapeHtml(source.key_placeholder)}">
          <button class="primary" type="button" data-source-action="save" data-source-id="${escapeHtml(source.source_id)}">保存</button>
          <button type="button" data-source-action="test" data-source-id="${escapeHtml(source.source_id)}">测试</button>
          <button type="button" data-source-action="clear" data-source-id="${escapeHtml(source.source_id)}">清除</button>
        </div>
        <div class="data-source-options">
          <label><input type="checkbox" data-source-persist="${escapeHtml(source.source_id)}" ${status?.storage === "persistent" ? "checked" : ""}> 保存到这台电脑</label>
          <span data-source-result="${escapeHtml(source.source_id)}">${status?.configured ? `${escapeHtml(pretty(status.storage))} STORAGE` : "NOT CONFIGURED"}</span>
        </div>
      </div>` : `
      <div class="source-no-key"><span>这个官方连接器不需要用户密钥，可以直接测试。</span><button type="button" data-source-action="test" data-source-id="${escapeHtml(source.source_id)}">测试公开接口</button></div>`;
    return `<article class="data-source-card" data-source-card="${escapeHtml(source.source_id)}">
      <div class="data-source-head"><div><span>${escapeHtml(source.source_id)} / ${escapeHtml(source.institution)}</span><h4>${escapeHtml(source.label)}</h4><p>${escapeHtml(source.coverage)}</p></div><b class="source-state ${status?.configured ? "ready" : ""}">${statusText}</b></div>
      ${controls}${guide}
    </article>`;
  }).join("");
}

async function saveDataSource(sourceId) {
  const input = $(`[data-source-key="${CSS.escape(sourceId)}"]`);
  const result = $(`[data-source-result="${CSS.escape(sourceId)}"]`);
  if (!input?.value.trim()) {
    setTestResult(result, "请先填写 API Key。", false);
    return;
  }
  setTestResult(result, "正在保存…");
  try {
    await api(`/v1/settings/data-sources/${encodeURIComponent(sourceId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: input.value.trim(),
        persist: Boolean($(`[data-source-persist="${CSS.escape(sourceId)}"]`)?.checked),
      }),
    });
    input.value = "";
    await refreshSettingsStatus();
    setTestResult($(`[data-source-result="${CSS.escape(sourceId)}"]`), "已保存；建议继续测试连接。", true);
  } catch (error) {
    setTestResult(result, error.message, false);
  }
}

async function testDataSource(sourceId) {
  const result = $(`[data-source-result="${CSS.escape(sourceId)}"]`) || $(".source-no-key span", $(`[data-source-card="${CSS.escape(sourceId)}"]`));
  setTestResult(result, "正在连接官方接口…");
  try {
    const response = await api(`/v1/settings/data-sources/${encodeURIComponent(sourceId)}/test`, { method: "POST" });
    setTestResult(result, `${response.latency_ms} ms · ${response.detail}`, true);
  } catch (error) {
    setTestResult(result, error.message, false);
  }
}

async function clearDataSource(sourceId) {
  const result = $(`[data-source-result="${CSS.escape(sourceId)}"]`);
  try {
    const cleared = await api(`/v1/settings/data-sources/${encodeURIComponent(sourceId)}`, { method: "DELETE" });
    await refreshSettingsStatus();
    setTestResult(
      $(`[data-source-result="${CSS.escape(sourceId)}"]`),
      cleared.storage === "environment"
        ? "该密钥来自 .env.local；请删除环境变量并重启服务器。"
        : "本地设置文件中的密钥已清除。",
      cleared.storage === "environment" ? null : true,
    );
  } catch (error) {
    setTestResult(result, error.message, false);
  }
}

async function syncConfiguredSources() {
  const button = $("#syncConfiguredSources");
  button.disabled = true;
  button.textContent = "SYNCING…";
  try {
    const result = await api("/v1/data/sync", { method: "POST" });
    toast(`数据同步 ${result.status} · ${Object.values(result.rows_by_source || {}).reduce((sum, value) => sum + Number(value || 0), 0)} rows`);
    state.dataStatus = await api("/v1/data/status");
    $("#seriesCount").textContent = `${state.dataStatus.series_count} SERIES`;
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "同步已配置来源";
  }
}

// Event wiring
$("#researchForm").addEventListener("submit", submitResearch);
$("#questionInput").addEventListener("input", (event) => $("#charCount").textContent = `${event.target.value.length} / 4000`);
$("#exampleQuestions").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-example]");
  if (!button) return;
  $("#questionInput").value = state.examples[Number(button.dataset.example)];
  $("#charCount").textContent = `${$("#questionInput").value.length} / 4000`;
  $("#questionInput").focus();
});
$("#retryButton").addEventListener("click", submitResearch);
$("#cancelButton").addEventListener("click", cancelCurrentJob);
$("#detailToggle").addEventListener("click", () => {
  state.showDetail = !state.showDetail;
  $("#detailToggle").setAttribute("aria-pressed", String(state.showDetail));
  $("#detailToggle").lastChild.textContent = state.showDetail ? " Hide data layer" : " Show data layer";
  renderGraph();
});
["#dataZoomIn", "#dataZoomOut", "#dataZoomReset"].forEach((selector) => {
  const button = $(selector);
  if (!button) return;
  button.addEventListener("click", () => {
    if (selector === "#dataZoomIn") adjustDataZoom(.1);
    else if (selector === "#dataZoomOut") adjustDataZoom(-.1);
    else resetDataView();
  });
});
$("#dataEvidenceNodes").addEventListener("click", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (!node) return;
  const nodeId = node.dataset.nodeId;
  if ((state.graph?.nodes || []).some((item) => item.node_id === nodeId)) {
    openNode(nodeId).catch((error) => toast(error.message));
  } else {
    toast(node.title || "该节点来自 Part A 的可用数据空间");
  }
});
$("#dataPluginBadges").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-plugin-toggle]");
  if (!button || button.disabled) return;
  button.disabled = true;
  try {
    await api(`/api/v1/data-plugins/${encodeURIComponent(button.dataset.pluginToggle)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: button.dataset.enabled !== "true", actor_id: "local-product-user" }),
    });
    await loadDataEvidenceCatalog();
  } catch (error) {
    toast(error.message);
    button.disabled = false;
  }
});
["#laneFilter", "#statusFilter", "#evidenceFilter"].forEach((selector) => $(selector).addEventListener("change", renderGraph));
$("#zoomIn").addEventListener("click", () => adjustZoom(.1));
$("#zoomOut").addEventListener("click", () => adjustZoom(-.1));
$("#zoomReset").addEventListener("click", resetGraphView);
$("#graphNodes").addEventListener("click", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (node) openNode(node.dataset.nodeId);
});
$("#graphNodes").addEventListener("mouseover", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (!node) return;
  $$(".graph-edge").forEach((edge) => edge.classList.toggle("active", edge.dataset.source === node.dataset.nodeId || edge.dataset.target === node.dataset.nodeId));
});
$("#graphNodes").addEventListener("mouseout", () => $$(".graph-edge").forEach((edge) => edge.classList.remove("active")));
let dataDrag = null;
$("#dataEvidenceViewport").addEventListener("pointerdown", (event) => {
  if (event.target.closest(".data-evidence-node")) return;
  dataDrag = { x: event.clientX, y: event.clientY, panX: state.dataPanX, panY: state.dataPanY };
  $("#dataEvidenceViewport").setPointerCapture?.(event.pointerId);
  $("#dataEvidenceViewport").classList.add("dragging");
});
$("#dataEvidenceViewport").addEventListener("pointermove", (event) => {
  if (!dataDrag) return;
  state.dataPanX = dataDrag.panX + event.clientX - dataDrag.x;
  state.dataPanY = dataDrag.panY + event.clientY - dataDrag.y;
  applyDataTransform();
});
const endDataDrag = () => { dataDrag = null; $("#dataEvidenceViewport").classList.remove("dragging"); };
$("#dataEvidenceViewport").addEventListener("pointerup", endDataDrag);
$("#dataEvidenceViewport").addEventListener("pointercancel", endDataDrag);
$("#dataEvidenceViewport").addEventListener("wheel", (event) => {
  if (!event.ctrlKey && Math.abs(event.deltaY) < Math.abs(event.deltaX)) return;
  event.preventDefault();
  adjustDataZoom(event.deltaY > 0 ? -.06 : .06);
}, { passive: false });
$("#researchReport").addEventListener("click", (event) => {
  const button = event.target.closest("[data-report-node]");
  if (!button) return;
  openNode(button.dataset.reportNode).catch((error) => toast(error.message));
});
$$('[data-close-drawer]').forEach((element) => element.addEventListener("click", closeDrawer));
$("#drawerTabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) return;
  state.activeTab = button.dataset.tab;
  renderDrawer();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if ($("#settingsPanel").getAttribute("aria-hidden") === "false") closeSettings();
    else if ($("#detailDrawer").classList.contains("open")) closeDrawer();
    else closeHistory();
    return;
  }
  if ($("#settingsPanel").getAttribute("aria-hidden") === "false") trapFocus(event, $(".settings-sheet", $("#settingsPanel")));
  else if ($("#detailDrawer").classList.contains("open")) trapFocus(event, $(".drawer-sheet", $("#detailDrawer")));
  else if ($("#historyPanel").classList.contains("open")) trapFocus(event, $("#historyPanel"));
});
$("#historyButton").addEventListener("click", openHistory);
$("#historyClose").addEventListener("click", closeHistory);
$("#historyList").addEventListener("click", (event) => {
  const item = event.target.closest("[data-job-id]");
  if (!item) return;
  closeHistory();
  loadJob(item.dataset.jobId, true).catch((error) => toast(error.message));
});
$("#settingsButton").addEventListener("click", () => openSettings("model"));
$("#mobileSettingsButton").addEventListener("click", () => openSettings("model"));
$("#heroSettingsButton").addEventListener("click", () => openSettings("model"));
$$("[data-close-settings]").forEach((element) => element.addEventListener("click", closeSettings));
$("#settingsTabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-settings-tab]");
  if (button) selectSettingsTab(button.dataset.settingsTab);
});
$("#llmProviderPills").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-provider]");
  if (!button) return;
  selectLlmProvider(button.dataset.provider, false);
  $$("#llmProviderPills button").forEach((item) => item.setAttribute("aria-checked", String(item === button)));
});
$("#llmModelSelect").addEventListener("change", () => {
  const custom = $("#llmModelSelect").value === "__custom__";
  $("#llmCustomModelField").classList.toggle("hidden", !custom);
  if (custom) $("#llmCustomModel").focus();
});
$("#llmKeyVisibility").addEventListener("click", () => {
  const input = $("#llmApiKey");
  const visible = input.type === "text";
  input.type = visible ? "password" : "text";
  $("#llmKeyVisibility").textContent = visible ? "显示" : "隐藏";
});
$("#saveLlmSettings").addEventListener("click", saveLlmSettings);
$("#testLlmSettings").addEventListener("click", testLlmSettings);
$("#clearLlmSettings").addEventListener("click", clearLlmSettings);
$("#syncConfiguredSources").addEventListener("click", syncConfiguredSources);
$("#dataSourceList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-source-action]");
  if (!button) return;
  const sourceId = button.dataset.sourceId;
  if (button.dataset.sourceAction === "save") saveDataSource(sourceId);
  else if (button.dataset.sourceAction === "test") testDataSource(sourceId);
  else if (button.dataset.sourceAction === "clear") clearDataSource(sourceId);
});
$("#copyConnectorPrompt").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("#connectorPrompt").textContent);
    $("#copyConnectorPrompt").textContent = "已复制";
    setTimeout(() => { $("#copyConnectorPrompt").textContent = "复制给 Codex"; }, 1800);
  } catch {
    toast("浏览器未允许剪贴板访问，请手动复制。");
  }
});

// Pan and wheel zoom for the research graph.
let drag = null;
$("#graphViewport").addEventListener("pointerdown", (event) => {
  if (event.target.closest(".graph-node")) return;
  drag = { x: event.clientX, y: event.clientY, panX: state.panX, panY: state.panY };
  $("#graphViewport").classList.add("dragging");
  event.currentTarget.setPointerCapture(event.pointerId);
});
$("#graphViewport").addEventListener("pointermove", (event) => {
  if (!drag) return;
  state.panX = drag.panX + event.clientX - drag.x;
  state.panY = drag.panY + event.clientY - drag.y;
  applyGraphTransform();
});
$("#graphViewport").addEventListener("pointerup", () => { drag = null; $("#graphViewport").classList.remove("dragging"); });
$("#graphViewport").addEventListener("wheel", (event) => {
  if (!event.ctrlKey) return;
  event.preventDefault();
  adjustZoom(event.deltaY > 0 ? -.06 : .06);
}, { passive: false });

boot();
