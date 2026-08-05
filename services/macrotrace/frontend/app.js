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
const DISPLAY_LABELS = {
  COMPLETE:"完成", PARTIAL:"部分完成", FAILED:"失败", CANCELLED:"已取消", QUEUED:"排队中",
  PARSING_QUERY:"解析问题", CLASSIFYING_WORKFLOW:"识别任务", ROUTING_LANES:"选择通道",
  ROUTING_NODES:"选择节点", SELECTING_FACTORS:"选择因子", PLANNING_MODELS:"规划模型",
  SELECTING_PARAMETERS:"选择参数", VALIDATING_PLAN:"验证计划", EXECUTING_MODELS:"执行模型",
  AGGREGATING_LANES:"聚合通道", SYNTHESIZING:"生成结论", SUCCESS:"成功", WARNING:"警告",
  RUNNING:"运行中", BLOCKED:"受阻", NOT_ROUTED:"未路由", PLANNED:"已规划", PENDING:"等待中",
  FULL:"完整", UNSUPPORTED:"暂不支持", ANSWERABLE:"可回答", CONDITIONAL:"有条件可回答",
  POLICY_DEFAULT:"工作流默认", USER_EXPLICIT:"用户明确指定", DAYS:"天", WEEKS:"周", MONTHS:"个月",
  QUARTERS:"季度", YEARS:"年", HIGH:"高", MEDIUM:"中", LOW:"低", GLOBAL:"全局",
  QUESTION:"原始问题", QUERY:"结构化问题", RESEARCH_DEPTH_GATE:"研究深度闸门", LANE:"研究通道",
  MECHANISM:"作用机制", RESEARCH_NODE:"研究节点", CLAIM:"中间判断", FACTOR:"实证因子",
  DATASET:"数据集", TRANSFORM:"数据变换", MODEL_SPECIFICATION:"模型设定", MODEL_RUN:"模型运行",
  DIAGNOSTIC:"模型诊断", EVIDENCE:"证据", LANE_SIGNAL:"通道信号", AGGREGATION:"证据聚合",
  FINAL_CLAIM:"最终结论", FALSIFIER:"证伪条件",
};

const state = {
  dailyBrief: null,
  dailyDomain: "全部",
  dailyView: "brief",
  selectedExcerpt: "",
  pdfDocument: null,
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
  const raw = String(value ?? "—");
  return DISPLAY_LABELS[raw] || raw.replaceAll("_", " ");
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
  items.unshift({ job_id: job.job_id, question: question || job.question || "实证研究", status: job.status, created_at: job.created_at || new Date().toISOString() });
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
      <span><i>${escapeHtml(pretty(item.status))}</i><time>${escapeHtml(String(item.created_at).slice(0, 16).replace("T", " "))}</time></span>
      <strong>${escapeHtml(item.question)}</strong>
    </button>`).join("") : `<div class="history-item"><strong>还没有本地研究任务。</strong></div>`;
}

async function boot() {
  document.body.dataset.workspaceMode = "empty";
  renderHistory();
  loadDailyBrief().catch((error) => renderDailyBriefError(error.message));
  try {
    const [health, dataStatus, examples] = await Promise.all([api("/v1/health"), api("/v1/data/status"), api("/v1/examples")]);
    state.health = health;
    state.dataStatus = dataStatus;
    state.examples = examples.questions;
    $("#healthPulse").classList.add("live");
    $("#healthText").textContent = health.database_ready ? "系统就绪" : "需要同步数据";
    $("#seriesCount").textContent = `${dataStatus.series_count} 条序列`;
    const latest = dataStatus.series.map((item) => item.last_period).filter(Boolean).sort().at(-1);
    $("#dataFreshness").textContent = dataStatus.ready ? `${dataStatus.series_count} 条真实序列 / 最近更新 ${String(latest || "—").slice(0, 10)}` : "真实数据仓库为空";
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
    $("#healthText").textContent = "离线";
    $("#dataFreshness").textContent = error.message;
  }
  const saved = new URLSearchParams(window.location.search).get("job") || localStorage.getItem("macrotrace.currentJob");
  if (saved) {
    try { await loadJob(saved, true); }
    catch { localStorage.removeItem("macrotrace.currentJob"); }
  }
}

function renderDailyBriefError(message) {
  $("#dailyBriefHeadline").textContent = "日报暂时无法读取";
  $("#dailyBriefSummary").textContent = message || "请确认本地服务已启动。";
  $("#dailyBriefCards").innerHTML = `<article class="daily-empty"><strong>日报不会使用虚构内容</strong><p>来源恢复后再刷新；研究工作台仍可独立使用。</p></article>`;
}

async function loadDailyBrief(refresh = false) {
  const button = $("#refreshDailyBrief");
  button.disabled = true;
  button.querySelector("span").textContent = refresh ? "正在搜索并生成…" : "正在读取日报…";
  try {
    state.dailyBrief = await api(refresh ? "/v1/daily-brief/refresh" : "/v1/daily-brief", refresh ? { method: "POST" } : {});
    renderDailyBrief();
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "刷新今日日报";
  }
}

function dailyItems() {
  const items = state.dailyBrief?.items || [];
  return state.dailyDomain === "全部" ? items : items.filter((item) => item.domain === state.dailyDomain);
}

function renderDailyBrief() {
  const brief = state.dailyBrief;
  if (!brief) return;
  if (state.dailyView === "pdf" && state.pdfDocument) {
    renderPdfDocument();
    return;
  }
  $("#dailyReaderModeLabel").textContent = "美国市场日报";
  $("#dailyPaperMarket").textContent = "美国市场 · 每日研究简报";
  $("#backToDailyBrief").classList.add("hidden");
  $("#dailyBriefDate").textContent = brief.as_of_label || "最近可获取信息";
  $("#dailyBriefHeadline").textContent = brief.headline || "今日信息摘要";
  $("#dailyBriefSummary").textContent = brief.summary || "";
  const domains = ["全部", ...new Set((brief.items || []).map((item) => item.domain || "综合市场"))];
  if (!domains.includes(state.dailyDomain)) state.dailyDomain = "全部";
  $("#dailyDomainFilters").innerHTML = domains.map((domain) => `<button type="button" data-daily-domain="${escapeHtml(domain)}" class="${domain === state.dailyDomain ? "active" : ""}">${escapeHtml(domain)}</button>`).join("");
  const items = dailyItems();
  $("#dailyBriefMeta").textContent = `${items.length} 条可验证线索 · ${new Set(items.map((item) => item.source_id)).size} 个来源`;
  $("#dailySourceState").innerHTML = (brief.source_states || []).map((source) => `<span data-state="${source.status === "成功" ? "ready" : "warning"}"><i></i>${escapeHtml(source.name)} · ${escapeHtml(source.status)}</span>`).join("");
  const groups = [...new Set(items.map((item) => item.domain || "综合市场"))];
  $("#dailyBriefCards").innerHTML = items.length ? groups.map((domain, groupIndex) => {
    const rows = items.filter((item) => (item.domain || "综合市场") === domain);
    return `<section class="daily-report-section" data-domain="${escapeHtml(domain)}">
      <header><span>${String(groupIndex + 1).padStart(2, "0")}</span><h3>${escapeHtml(domain)}</h3></header>
      ${rows.map((item, index) => `<article class="daily-report-item" data-index="${String(index + 1).padStart(2, "0")}" data-daily-item="${escapeHtml(item.item_id)}">
        <h4>${escapeHtml(item.headline || item.title)}</h4>
        <p>${escapeHtml(item.summary || "")}</p>
        <p class="daily-report-meaning"><strong>研究含义：</strong>${escapeHtml(item.significance || "")}</p>
        <footer><span>${escapeHtml(String(item.published_at || "时间未标注").slice(0, 16).replace("T", " "))}</span><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.source_name)} · 原文 ↗</a></footer>
      </article>`).join("")}
    </section>`;
  }).join("") : `<article class="daily-empty"><strong>这个分类暂时没有新条目</strong><p>切换分类或刷新日报。</p></article>`;
  $("#dailyBriefLimitations").innerHTML = normalizeTextList(brief.limitations).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function placeResearchQuestion(question) {
  $("#questionInput").value = question;
  $("#charCount").textContent = `${question.length} / 4000`;
  state.lastQuestion = question;
  $("#researchForm").scrollIntoView({ behavior: "smooth", block: "center" });
  $("#questionInput").focus({ preventScroll: true });
}

async function compileSelectedExcerpt() {
  const excerpt = state.selectedExcerpt.trim();
  if (excerpt.length < 8) return;
  const button = $("#selectionResearchButton");
  button.disabled = true;
  button.textContent = "正在编译研究问题…";
  try {
    const result = await api("/v1/daily-brief/research-question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ excerpt }),
    });
    placeResearchQuestion(result.question);
    window.getSelection()?.removeAllRanges();
    $("#selectionToolbar").classList.add("hidden");
    toast("选中的观点已编译为完整研究问题，可直接开始实证。 ");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "进入实证研究 →";
  }
}

function showSelectionAction() {
  const selection = window.getSelection();
  const paper = $("#dailyBriefDocument");
  const excerpt = String(selection || "").replace(/\s+/g, " ").trim().slice(0, 1800);
  const anchor = selection?.anchorNode;
  const focus = selection?.focusNode;
  const toolbar = $("#selectionToolbar");
  if (excerpt.length < 8 || !anchor || !focus || !paper.contains(anchor) || !paper.contains(focus) || !selection.rangeCount) {
    toolbar.classList.add("hidden");
    return;
  }
  state.selectedExcerpt = excerpt;
  const rect = selection.getRangeAt(0).getBoundingClientRect();
  toolbar.style.left = `${Math.min(window.innerWidth - 115, Math.max(115, rect.left + rect.width / 2))}px`;
  toolbar.style.top = `${Math.max(80, rect.top - 9)}px`;
  toolbar.classList.remove("hidden");
}

function renderPdfDocument() {
  const documentData = state.pdfDocument;
  $("#dailyReaderModeLabel").textContent = "本地研报阅读器";
  $("#dailyPaperMarket").textContent = "本地文件 · 只在内存中读取";
  $("#dailyBriefDate").textContent = `${documentData.page_count} 页 PDF`;
  $("#dailyBriefHeadline").textContent = documentData.filename;
  $("#dailyBriefSummary").textContent = `已提取 ${documentData.pages.length} 页可选择文字。拖动选中一句或几段，即可编译为美国市场实证研究问题；原文件不会保存到本地数据仓库。`;
  $("#dailyDomainFilters").innerHTML = "";
  $("#dailySourceState").innerHTML = `<span data-state="ready"><i></i>本地 PDF · 已读取</span>`;
  $("#dailyBriefMeta").textContent = `${documentData.pages.length} 页可选文字`;
  $("#backToDailyBrief").classList.remove("hidden");
  $("#dailyBriefCards").innerHTML = documentData.pages.map((page) => `<section class="pdf-page"><span>第 ${page.page} 页</span><p>${escapeHtml(page.text)}</p></section>`).join("");
  $("#dailyBriefLimitations").innerHTML = `<span>扫描图片型 PDF 暂不进行 OCR；当前只显示成功提取的文字页。</span>`;
}

async function readPdfFile(file) {
  if (!file) return;
  if (file.size > 20 * 1024 * 1024) {
    toast("PDF 不能超过 20 MB。 ");
    return;
  }
  $("#dailyBriefCards").innerHTML = `<div class="daily-uploading">正在读取 ${escapeHtml(file.name)}…</div>`;
  const form = new FormData();
  form.append("file", file);
  try {
    state.pdfDocument = await api("/v1/documents/read-pdf", { method: "POST", body: form });
    state.dailyView = "pdf";
    renderPdfDocument();
  } catch (error) {
    renderDailyBrief();
    toast(error.message);
  } finally {
    $("#dailyPdfInput").value = "";
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
    return { label: "研究边界", text: originalHeadline };
  }
  if (synthesis.evidence_state === "CONDITIONAL_SCENARIO") {
    return { label: "方法说明", text: "条件响应依赖已注册冲击、代理映射与识别假设，不自动等同于因果效应。" };
  }
  if (synthesis.evidence_state === "BASELINE_ONLY") {
    return { label: "研究边界", text: "以下为基线状态，不代表情景冲击的条件效应。" };
  }
  if (synthesis.evidence_state === "ASSOCIATIONAL_ONLY") {
    return { label: "IDENTIFICATION LIMIT", text: "现有模型提供关联性与预测性证据，不能据此识别因果效应。" };
  }
  if (synthesis.answerability === "UNSUPPORTED" && gaps.length) {
    return { label: "覆盖边界", text: gaps[0] };
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
  $("#coverageLabel").textContent = `${pretty(synthesis.coverage)}覆盖 / ${pretty(synthesis.answerability || "历史版本")} / ${pretty(synthesis.evidence_state || synthesis.stance)}`;
  $("#answerAsOf").textContent = `截至 ${result.as_of_date} · ${result.horizon.minimum}–${result.horizon.maximum} ${pretty(result.horizon.unit)} · ${pretty(result.horizon.source)}`;
  $("#answerHeadline").textContent = displayHeadline;
  const qualifier = displayConclusionQualifier(synthesis, gaps);
  $("#answerQualifier").classList.toggle("hidden", !qualifier);
  $("#answerQualifier").textContent = qualifier?.text || "";
  $("#answerQualifier").dataset.label = qualifier?.label || "研究边界";
  $("#answerNarrative").textContent = directAnswer;
  $("#confidenceValue").textContent = synthesis.confidence;
  $("#coverageMeter").style.width = `${Math.max(0, Math.min(100, synthesis.coverage_score * 100))}%`;
  $("#coverageValue").textContent = `${Math.round(synthesis.coverage_score * 100)}% 覆盖度`;
  const falsifiers = normalizeTextList(synthesis.falsifiers);
  $("#falsifierList").innerHTML = falsifiers.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("#limitationList").innerHTML = gaps.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>没有已记录的覆盖缺口。</li>";
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
            <span>实证分析 ${String(index + 1).padStart(2, "0")}</span>
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

function stableHash(value) {
  let hash = 2166136261;
  for (const char of String(value)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return hash >>> 0;
}

function computeClusteredDataLayout(items, edges) {
  const width = 1880, height = 920, nodeSize = 82;
  const centers = {
    catalog: { x: 330, y: 470 },
    evidence: { x: 920, y: 470 },
    factor: { x: 1510, y: 470 },
  };
  const positions = new Map();
  items.forEach((item, index) => {
    const center = centers[item.cluster] || centers.evidence;
    const seed = stableHash(item.node_id);
    const angle = (seed % 6283) / 1000 + index * .41;
    const radius = 55 + ((seed >>> 7) % 250);
    positions.set(item.node_id, {
      x: center.x + Math.cos(angle) * radius - nodeSize / 2,
      y: center.y + Math.sin(angle) * radius * .78 - nodeSize / 2,
      width: nodeSize,
      height: nodeSize,
      cluster: item.cluster,
    });
  });
  const linked = edges.filter((edge) => positions.has(edge.source) && positions.has(edge.target));
  for (let iteration = 0; iteration < 120; iteration += 1) {
    const cooling = 1 - iteration / 145;
    items.forEach((item) => {
      const point = positions.get(item.node_id);
      const center = centers[item.cluster] || centers.evidence;
      point.x += (center.x - nodeSize / 2 - point.x) * .018 * cooling;
      point.y += (center.y - nodeSize / 2 - point.y) * .018 * cooling;
    });
    for (let i = 0; i < items.length; i += 1) {
      const left = positions.get(items[i].node_id);
      for (let j = i + 1; j < items.length; j += 1) {
        const right = positions.get(items[j].node_id);
        const dx = right.x - left.x, dy = right.y - left.y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const minimum = left.cluster === right.cluster ? 104 : 88;
        if (distance >= minimum) continue;
        const push = (minimum - distance) * .15 * cooling;
        const ux = dx / distance, uy = dy / distance;
        left.x -= ux * push; left.y -= uy * push;
        right.x += ux * push; right.y += uy * push;
      }
    }
    linked.forEach((edge) => {
      const source = positions.get(edge.source), target = positions.get(edge.target);
      const dx = target.x - source.x, dy = target.y - source.y;
      const desired = source.cluster === target.cluster ? 135 : 390;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const pull = (distance - desired) * .003 * cooling;
      source.x += dx / distance * pull; source.y += dy / distance * pull;
      target.x -= dx / distance * pull; target.y -= dy / distance * pull;
    });
    positions.forEach((point) => {
      point.x = Math.max(45, Math.min(width - nodeSize - 45, point.x));
      point.y = Math.max(105, Math.min(height - nodeSize - 45, point.y));
    });
  }
  return { positions, width, height, centers };
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
    cluster: "catalog",
  }));
  const akshareCatalog = (state.pluginCatalog.akshare || []).map((item) => ({
    node_id: `CATALOG::AKSHARE::${item.dataset_id}`,
    label: item.dataset_id.replace(/^macro_/, ""),
    detail: item.description,
    node_type: "AKSHARE",
    status: "available",
    cluster: "catalog",
  }));
  const assets = (state.assetGraph?.nodes || []).map((item) => ({
    node_id: `ASSET::${item.node_id}`,
    label: item.label,
    detail: `${item.ref?.representation || "ASSET"} · ${String(item.ref?.content_hash || "").slice(0, 10)}`,
    node_type: item.ref?.representation || "ASSET",
    status: "asset",
    cluster: "evidence",
  }));

  const visibleDatasets = datasets.map((item) => ({ ...item, detail: item.summary, status: dataNodeStatus(item), cluster: "evidence" }));
  const visibleFactors = factors.map((item) => ({ ...item, detail: item.metadata?.series_id || item.summary, status: dataNodeStatus(item), cluster: "factor" }));
  const all = [...akshareCatalog, ...fredCatalog, ...visibleDatasets, ...assets, ...visibleFactors];
  const edgeRows = [];
  datasets.forEach((dataset) => {
    (dataset.metadata?.series_ids || []).forEach((seriesId) => {
      const source = `CATALOG::FRED::${seriesId}`;
      edgeRows.push({ source, target: dataset.node_id, relation: "提供数据" });
    });
  });
  graphEdges.forEach((edge) => edgeRows.push(edge));
  (state.assetGraph?.edges || []).forEach((edge) => {
    const source = `ASSET::${edge.source_ref}`;
    const target = `ASSET::${edge.target_ref}`;
    edgeRows.push({ source, target, relation: edge.relation_type });
  });
  const layout = computeClusteredDataLayout(all, edgeRows);
  const { positions, width, height, centers } = layout;
  state.dataLayout = layout;
  const canvas = $("#dataEvidenceCanvas");
  const edgeSvg = $("#dataEvidenceEdges");
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  edgeSvg.setAttribute("width", width);
  edgeSvg.setAttribute("height", height);
  edgeSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  edgeSvg.innerHTML = edgeRows.map((edge) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) return "";
    const used = [edge.source, edge.target].some((id) => all.find((item) => item.node_id === id)?.status === "used");
    const sx = source.x + 41, sy = source.y + 41, tx = target.x + 41, ty = target.y + 41;
    const hubX = source.cluster === target.cluster ? (sx + tx) / 2 : (centers[source.cluster].x + centers[target.cluster].x) / 2;
    return `<path data-source="${escapeHtml(edge.source)}" data-target="${escapeHtml(edge.target)}" class="data-evidence-edge ${used ? "used" : ""}" d="M${sx},${sy} C${hubX},${sy} ${hubX},${ty} ${tx},${ty}"></path>`;
  }).join("");
  container.innerHTML = [
    `<span class="data-cluster-label" style="left:90px"><b>数据目录</b><small>AKShare / FRED / 官方来源</small></span>`,
    `<span class="data-cluster-label" style="left:690px"><b>版本化证据</b><small>数据集 / 文档 / 快照</small></span>`,
    `<span class="data-cluster-label" style="left:1280px"><b>实证因子</b><small>本次路由与可用因子</small></span>`,
    ...all.map((item) => {
      const point = positions.get(item.node_id);
      return `<button class="data-evidence-node" type="button" data-node-id="${escapeHtml(item.node_id)}" data-cluster="${escapeHtml(item.cluster)}" data-status="${escapeHtml(item.status)}" data-type="${escapeHtml(item.node_type)}" title="${escapeHtml(item.detail || item.label)}" style="left:${point.x}px;top:${point.y}px"><i></i><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.node_type)}</small></button>`;
    }),
  ].join("");
  const routedDatasets = datasets.filter((node) => dataNodeStatus(node) === "used").length;
  const routedFactors = factors.filter((node) => dataNodeStatus(node) === "used").length;
  $("#dataUniverseCount").textContent = String(all.length);
  $("#dataRoutedCount").textContent = String(routedDatasets);
  $("#dataFactorCount").textContent = String(routedFactors);
  $("#dataPluginBadges").innerHTML = state.dataPlugins.length
    ? state.dataPlugins.map((plugin) => `<button type="button" data-plugin-toggle="${escapeHtml(plugin.plugin_id)}" data-enabled="${String(plugin.enabled)}" data-state="${plugin.enabled ? "on" : "off"}" ${plugin.configured ? "" : "disabled"} title="${plugin.configured ? "点击切换数据插件" : "需要先在本机配置该来源"}"><b>${escapeHtml(plugin.name)}</b>${plugin.enabled ? "已启用 ✓" : plugin.configured ? "点击启用" : "待配置"}</button>`).join("")
    : `<span><b>注册表</b>${datasets.length} 组官方数据 · ${assets.length} 个 A 类资产</span>`;
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
  state.dataZoom = Math.max(.42, Math.min(.9, (viewport.clientWidth - 34) / (state.dataLayout?.width || 1880)));
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
    ...layout.bands.map((band) => `<div class="lane-band" style="left:0;top:${band.y}px;width:${layout.width}px;height:${band.height}px"><span class="lane-label">${escapeHtml(band.lane === "__GLOBAL__" ? "全局编译链" : band.lane)}</span></div>`),
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
  $("#graphStats").textContent = `${nodes.length} 个可见 / 共 ${allNodes.length} 个 · ${planned} 个已路由 · ${blocked} 个受阻 · ${notRouted} 个未路由`;
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
  $("#drawerType").textContent = pretty(node.node_type);
  $("#drawerTitle").textContent = node.label;
  $("#drawerSubtitle").textContent = `${node.node_id} · ${pretty(node.status)}`;
  $("#detailDrawer").classList.add("open");
  $("#detailDrawer").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  $(".drawer-close", $("#detailDrawer"))?.focus({ preventScroll: true });
  updateDrawerTabs();
  $("#drawerBody").innerHTML = `<div class="detail-section"><h3>正在读取节点详情…</h3></div>`;
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
  const title = detail.title || node.label || detail.node_id || node.node_id || "该研究对象";
  const summaries = {
    QUESTION: ["保存用户的原始研究问题，作为整张图的起点。", "防止后续路由和模型偏离用户真正提出的问题。"],
    QUERY: ["把自然语言问题编译成结构化任务、期限和输出要求。", "通道选择和模型执行前，Python 必须先获得经过验证的问题合同。"],
    RESEARCH_DEPTH_GATE: ["检查计划中的证据深度是否与问题复杂度相匹配。", "避免一个重大结论只建立在少量浅层统计上。"],
    LANE: ["拆出一个独立研究通道并汇集其中的证据。", "复杂问题需要先按机制并行研究，再进行跨通道综合。"],
    MECHANISM: ["提出通道内可被数据检验的作用机制。", "把宽泛叙事连接到可观测因子和已登记模型。"],
    RESEARCH_NODE: ["生成一个边界清晰的中间研究判断。", "证据必须先在中间判断层闭合，才能进入总论。"],
    CLAIM: ["保存一条可被证据支持或反驳的中间判断。", "避免把不可比较的估计结果直接相加。"],
    FACTOR: ["定义机制所使用的可观测变量。", "变量必须先固定定义、来源、单位和频率，才能进入模型。"],
    DATASET: ["定义数据来源和历史版本合同。", "保证结果可复现，并防止历史任务读取未来修订值。"],
    TRANSFORM: ["把原始序列转换成模型允许使用的形式。", "估计前必须控制尺度、频率和趋势处理。"],
    MODEL_SPECIFICATION: ["冻结实证设计、变量、参数和诊断要求。", "AI 可以选择已登记积木，但不能改写模型代码。"],
    MODEL_RUN: ["执行已登记的 Python 统计模型并产生定量证据。", "机制在这里接受真实观测检验，而不是由大语言模型描述。"],
    DIAGNOSTIC: ["检验上游模型是否足够可信。", "系数或预测只有通过方法专属诊断后才能进入结论。"],
    EVIDENCE: ["把模型结果标准化为可追溯证据对象。", "不同方法共享证据边界，同时保留各自解释限制。"],
    LANE_SIGNAL: ["综合同一研究通道内已诊断的证据。", "跨通道综合前，需要透明记录每条通道的方向和贡献。"],
    AGGREGATION: ["把异质通道证据综合成总答案。", "复杂问题不能由单个模型独立回答。"],
    FINAL_CLAIM: ["给出面向用户的主要结论。", "结论闭合研究链，同时保留到底层模型和数据快照的链接。"],
    FALSIFIER: ["记录可能推翻当前结论的可观测条件。", "研究结论必须说明在什么情况下需要修订。"],
  };
  const [purpose, why] = summaries[type] || [`把“${title}”作为可追溯研究步骤保存并执行。`, "让这部分研究过程可以在图谱中展开检查。"];
  const variables = detail.variables || [];
  const sample = detail.sample;
  const data = variables.length
    ? `使用 ${variables.length} 个已登记变量${sample ? `，样本期为 ${sample.start} 至 ${sample.end}，共 ${sample.observations || "—"} 个观测` : ""}。`
    : "使用结构化上游输入；这个节点本身不额外运行新的数据序列。";
  return {
    purpose,
    why_it_exists: why,
    mechanism: detail.specification?.estimand || detail.specification?.hypothesis || detail.summary || node.summary || "这是受约束的研究、路由或治理步骤，不是一项新的实证估计。",
    data_summary: data,
    output_summary: "结构化结果会传给相连的下游研究节点。",
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
      <div><span>节点摘要</span><strong>这一步在研究链中做什么</strong></div>
      <em class="explanation-source ${usesLlm ? "llm" : "fixed"}">${usesLlm ? "证据约束的模型解释" : "注册表固定说明"}</em>
    </header>
    <p class="node-brief-lead">${escapeHtml(narrative)}</p>
    <div class="node-brief-grid">
      <section><span>具体作用</span><p>${escapeHtml(facts.purpose)}</p></section>
      <section><span>存在原因</span><p>${escapeHtml(facts.why_it_exists)}</p></section>
      <section><span>机制</span><p>${escapeHtml(mechanism)}</p></section>
      <section><span>数据 / 输入</span><p>${escapeHtml(facts.data_summary)}</p></section>
    </div>
    <footer><span>输出</span><p>${escapeHtml(facts.output_summary)}</p></footer>
  </article>`;
}

function renderOverview(detail) {
  if (detail.error) return `<div class="detail-section"><h3>节点暂不可用</h3><div class="detail-card wide"><p>${escapeHtml(detail.error)}</p></div></div>`;
  const overview = detail.overview || {};
  const method = detail.method || detail.specification?.method || detail.metadata?.model_recipe_id || state.selectedNode?.node_type;
  const lane = detail.lane_id || overview.lane_id || state.selectedNode?.lane_id || "GLOBAL";
  const role = detail.role || overview.role || state.selectedNode?.role || "—";
  return `<div class="detail-section"><h3>研究目的与结论贡献</h3>${renderNodeBrief(detail)}<div class="detail-grid execution-detail-grid">
    ${detailCard("状态", pretty(detail.status || detail.node_status), detail.summary || state.selectedNode?.summary || "暂无摘要")}
    ${detailCard("方法 / 对象", method, detail.evidence_type ? `证据类型：${pretty(detail.evidence_type)}` : `通道：${pretty(lane)} · 角色：${pretty(role)}`)}
    ${detailCard("方向", pretty(detail.direction || "—"), `置信度：${pretty(detail.confidence || "—")} · 信号：${formatNumber(detail.signal)}`)}
    ${detailCard("样本", detail.sample ? `${detail.sample.start} → ${detail.sample.end}` : "不适用", detail.sample ? `${detail.sample.observations || "—"} 个观测 · ${detail.sample.frequency || "—"}` : "即使尚未执行数值估计，这个对象也可以被检查。")}
    ${detail.specification ? detailCard("估计对象 / 假设", detail.specification.estimand || detail.specification.hypothesis || detail.specification.intermediate_claim || "已登记研究对象", detail.specification.dependent_variable ? `因变量：${detail.specification.dependent_variable}` : detail.specification.estimand_boundary || "详见模型设定与来源追溯页签。", "wide") : ""}
    ${overview.upstream ? detailCard("数据沿革", `${overview.upstream.length} 个上游 · ${overview.downstream?.length || 0} 个下游`, "每个相连对象都可在这份不可变任务图中追溯。", "wide") : ""}
  </div>${renderCharts(detail.charts || [])}</div>`;
}

function detailCard(kicker, title, text, className = "") {
  return `<article class="detail-card ${className}"><span>${escapeHtml(kicker)}</span><h4>${escapeHtml(title)}</h4><p>${escapeHtml(text)}</p></article>`;
}

function renderSpecification(detail) {
  const spec = detail.specification;
  if (!spec) return emptyDetail("模型设定", "这个节点没有已登记的模型设定合同。 ");
  return `<div class="detail-section"><h3>已登记模型设定</h3>${spec.formula ? `<div id="formulaBox" class="formula-box">${escapeHtml(spec.formula)}</div>` : ""}<dl class="definition-list">
    <div><dt>方法</dt><dd>${escapeHtml(spec.method || detail.method || "非模型研究对象")}</dd></div>
    <div><dt>研究假设</dt><dd>${escapeHtml(spec.hypothesis || spec.intermediate_claim || "—")}</dd></div>
    <div><dt>估计对象</dt><dd>${escapeHtml(spec.estimand || spec.estimand_boundary || "在下游模型设定中定义")}</dd></div>
    <div><dt>因变量</dt><dd>${escapeHtml(spec.dependent_variable || "—")}</dd></div>
    <div><dt>自变量</dt><dd>${escapeHtml((spec.independent_variables || spec.factor_ids || []).join(" · ") || "—")}</dd></div>
    <div><dt>控制变量</dt><dd>${escapeHtml((spec.controls || []).join(" · ") || "无")}</dd></div>
    ${spec.fixed_effects ? `<div><dt>固定效应</dt><dd>${escapeHtml(spec.fixed_effects)}</dd></div>` : ""}
    <div><dt>参数</dt><dd>${escapeHtml(JSON.stringify(spec.parameters || detail.parameters?.values || {}, null, 0))}</dd></div>
    <div><dt>参数来源</dt><dd>${escapeHtml(detail.parameters?.source || "注册表政策 / 不可变设定")}</dd></div>
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
      ? `<div class="detail-section"><h3>已登记因子依赖</h3><pre class="json-block">${escapeHtml(JSON.stringify(factorIds, null, 2))}</pre></div>`
      : emptyDetail("数据与变量", "这个对象没有变量层数据合同；请查看相连的因子或模型节点。 ");
  }
  return `<div class="detail-section"><h3>数据、变量与历史版本</h3><div class="table-scroll"><table class="variable-table"><thead><tr><th>因子</th><th>定义</th><th>序列</th><th>单位</th><th>频率</th><th>数据集</th><th>发布时间</th></tr></thead><tbody>${variables.map((variable) => `<tr><td>${escapeHtml(variable.factor_id)}</td><td>${escapeHtml(variable.definition)}</td><td>${escapeHtml(variable.series_id)}</td><td>${escapeHtml(variable.unit)}</td><td>${escapeHtml(variable.frequency)}</td><td>${escapeHtml(variable.dataset_id)}</td><td>${escapeHtml(variable.release_lag)}</td></tr>`).join("")}</tbody></table></div>
    <h3 style="margin-top:28px">样本合同</h3><pre class="json-block">${escapeHtml(JSON.stringify(detail.sample || {}, null, 2))}</pre></div>`;
}

function renderResults(detail) {
  const table = detail.table;
  if (!table) {
    if (detail.status === "FAILED") return emptyDetail("结果", `模型失败：${detail.error_type || "未知错误"}`);
    return `<div class="detail-section"><h3>结构化结果状态</h3><pre class="json-block">${escapeHtml(JSON.stringify(detail.results || { status: detail.status, note: "只有实际执行的模型运行才会产生数值结果。" }, null, 2))}</pre></div>`;
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
  return `<div class="detail-section"><h3>学术结果</h3><p class="table-title">${escapeHtml(table.title)}</p>${artifactLinks(detail.artifacts)}<div class="table-scroll"><table class="academic-table"><thead><tr><th>变量</th>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr></thead><tbody>${variableRows}${statisticRows}</tbody></table></div><p class="table-notes">${escapeHtml((table.notes || []).join(" "))}</p>${renderCharts(detail.charts || [])}</div>`;
}

function artifactLinks(artifacts = []) {
  const tableArtifacts = artifacts.filter((item) => ["CSV", "JSON", "HTML", "LATEX"].includes(item.artifact_type));
  if (!tableArtifacts.length) return "";
  return `<div class="artifact-row">${tableArtifacts.map((item) => `<a href="${escapeHtml(apiUrl(`/v1/artifacts/${encodeURIComponent(item.artifact_id)}`))}" target="_blank" rel="noopener">${escapeHtml(item.artifact_type)} ↗</a>`).join("")}</div>`;
}

function renderDiagnostics(detail) {
  const diagnostics = detail.diagnostics || [];
  if (!diagnostics.length) return emptyDetail("诊断", detail.status === "FAILED" ? `执行失败：${detail.error_type || "未知错误"}` : "该节点没有方法专属诊断。");
  const normalized = diagnostics.map((item) => typeof item === "string"
    ? { status: "PLANNED", name: pretty(item), interpretation: "已登记模型配方要求执行这项诊断。", credibility_impact: "只有报告这项诊断后，该证据才能进入可信结论。", statistic: null, p_value: null }
    : item);
  return `<div class="detail-section"><h3>方法专属诊断</h3><div class="diagnostic-list">${normalized.map((item) => `<article class="diagnostic-card ${String(item.status).toLowerCase()}"><div class="diagnostic-status">${escapeHtml(pretty(item.status))}</div><div class="diagnostic-main"><h4>${escapeHtml(item.name)}</h4><p>${escapeHtml(item.interpretation)}</p><p><strong>可信度影响：</strong> ${escapeHtml(item.credibility_impact)}</p></div><div class="diagnostic-stat">统计量 ${escapeHtml(formatNumber(item.statistic, 6))}<br>p-value ${escapeHtml(formatNumber(item.p_value, 6))}</div></article>`).join("")}</div>${renderCharts(detail.charts || [])}</div>`;
}

function renderRobustness(detail) {
  if (!detail.robustness) return emptyDetail("稳健性", "该节点没有稳健性或样本外结果。");
  return `<div class="detail-section"><h3>稳健性与样本外检验</h3><pre class="json-block">${escapeHtml(JSON.stringify(detail.robustness, null, 2))}</pre>${renderCharts(detail.charts || [])}</div>`;
}

function renderProvenance(detail) {
  const provenance = detail.provenance || detail.metadata || {};
  const registryMetadata = provenance.registry_metadata || {};
  return `<div class="detail-section"><h3>不可变来源追溯</h3>${artifactLinks(detail.artifacts)}<dl class="definition-list">
    <div><dt>模型配方</dt><dd>${escapeHtml(provenance.model_recipe_id || registryMetadata.model_recipe_id || detail.model_recipe_id || "—")}</dd></div>
    <div><dt>代码制品</dt><dd>${escapeHtml(provenance.code_artifact || registryMetadata.code_artifact || "注册表图对象")}</dd></div>
    <div><dt>注册表版本</dt><dd>${escapeHtml(provenance.registry_version || "0.2.0 + 深度扩展")}</dd></div>
    <div><dt>参数决策</dt><dd>${escapeHtml(JSON.stringify(detail.parameters || {}, null, 0))}</dd></div>
  </dl><h3 style="margin-top:28px">研报页码证据</h3><pre class="json-block">${escapeHtml(JSON.stringify(provenance.report_evidence || [], null, 2))}</pre><h3 style="margin-top:28px">注册表对象</h3><pre class="json-block">${escapeHtml(JSON.stringify(registryMetadata, null, 2))}</pre><h3 style="margin-top:28px">数据快照</h3><pre class="json-block">${escapeHtml(JSON.stringify(provenance.data_lineage || [], null, 2))}</pre></div>`;
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
  if (!points.length) return `<p>没有可绘制的图表数据。</p>`;
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
  $("#llmConfigStatus").textContent = status.configured ? `${status.provider_label} / 已就绪` : "尚未配置";
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
  button.textContent = "正在同步…";
  try {
    const result = await api("/v1/data/sync", { method: "POST" });
    toast(`数据同步 ${pretty(result.status)} · ${Object.values(result.rows_by_source || {}).reduce((sum, value) => sum + Number(value || 0), 0)} 行`);
    state.dataStatus = await api("/v1/data/status");
    $("#seriesCount").textContent = `${state.dataStatus.series_count} 条序列`;
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "同步已配置来源";
  }
}

// Event wiring
$("#refreshDailyBrief").addEventListener("click", () => {
  state.dailyView = "brief";
  loadDailyBrief(true).catch((error) => {
    renderDailyBriefError(error.message);
    toast(error.message);
  });
});
$("#dailyDomainFilters").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-daily-domain]");
  if (!button) return;
  state.dailyDomain = button.dataset.dailyDomain;
  renderDailyBrief();
});
$("#dailyBriefDocument").addEventListener("mouseup", () => window.setTimeout(showSelectionAction, 0));
$("#selectionToolbar").addEventListener("mousedown", (event) => event.preventDefault());
$("#selectionResearchButton").addEventListener("click", () => compileSelectedExcerpt());
$("#dailyPdfInput").addEventListener("change", (event) => readPdfFile(event.target.files?.[0]));
$("#backToDailyBrief").addEventListener("click", () => {
  state.dailyView = "brief";
  state.pdfDocument = null;
  renderDailyBrief();
});
document.addEventListener("mousedown", (event) => {
  if (!event.target.closest("#selectionToolbar") && !event.target.closest("#dailyBriefDocument")) {
    $("#selectionToolbar").classList.add("hidden");
  }
});
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
  $("#detailToggle").lastChild.textContent = state.showDetail ? " 隐藏数据层" : " 显示数据层";
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
$("#dataEvidenceNodes").addEventListener("mouseover", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (!node) return;
  const nodeId = node.dataset.nodeId;
  const neighbors = new Set([nodeId]);
  $$(".data-evidence-edge").forEach((edge) => {
    const adjacent = edge.dataset.source === nodeId || edge.dataset.target === nodeId;
    edge.classList.toggle("focused", adjacent);
    edge.classList.toggle("dimmed", !adjacent);
    if (adjacent) {
      neighbors.add(edge.dataset.source);
      neighbors.add(edge.dataset.target);
    }
  });
  $$(".data-evidence-node").forEach((item) => item.classList.toggle("dimmed", !neighbors.has(item.dataset.nodeId)));
});
$("#dataEvidenceNodes").addEventListener("mouseout", (event) => {
  if (event.relatedTarget?.closest?.(".data-evidence-node")) return;
  $$(".data-evidence-edge").forEach((edge) => edge.classList.remove("focused", "dimmed"));
  $$(".data-evidence-node").forEach((item) => item.classList.remove("dimmed"));
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
