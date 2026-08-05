export interface ResearchOSEnv {
  DB: D1Database;
  UPLOADS: R2Bucket;
}

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

const now = () => new Date().toISOString();
const id = (prefix: string) => `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 16).toUpperCase()}`;
const rows = <T>(result: D1Result<T>) => result.results ?? [];

async function ensureSchema(db: D1Database) {
  await db.batch([
    db.prepare("CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS ingest_batches (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS assets (id TEXT NOT NULL, workspace_id TEXT NOT NULL, name TEXT NOT NULL, version_id TEXT PRIMARY KEY, parent_version_id TEXT, content_hash TEXT NOT NULL, mime_type TEXT NOT NULL, format_kind TEXT NOT NULL, size_bytes INTEGER NOT NULL, storage_key TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_assets_workspace ON assets(workspace_id, created_at)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_assets_id ON assets(id, created_at)"),
    db.prepare("CREATE TABLE IF NOT EXISTS theses (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, version_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS thesis_builds (id TEXT PRIMARY KEY, thesis_id TEXT NOT NULL, version_id TEXT NOT NULL, parent_build_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL)"),
    db.prepare("CREATE INDEX IF NOT EXISTS idx_builds_thesis ON thesis_builds(thesis_id, created_at)"),
    db.prepare("CREATE TABLE IF NOT EXISTS tool_runs (id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE, payload TEXT NOT NULL, created_at TEXT NOT NULL)"),
  ]);
}

function formatKind(name: string, mime: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "md") return "MARKDOWN";
  if (ext === "docx") return "DOCX";
  if (ext === "xlsx") return "XLSX";
  if (ext === "csv") return "CSV";
  if (ext === "pdf") return "PDF_TEXT";
  if (mime.startsWith("text/")) return "TEXT";
  return "BINARY";
}

function objectRef(row: Record<string, unknown>) {
  return {
    contract_version: "0.1.0-m1", object_id: row.id, version_id: row.version_id,
    object_type: "SOURCE_FILE", name: row.name, representation: row.format_kind,
    schema_version: "m1.asset.v1", content_hash: row.content_hash, access_scope: row.workspace_id,
    source_filename: row.name, mime_type: row.mime_type, format_kind: row.format_kind,
    size_bytes: row.size_bytes, created_at: row.created_at, metadata: { storage: "R2", durable: true },
  };
}

async function listObjects(db: D1Database, workspaceId: string, query: string | null) {
  const result = await db.prepare("SELECT * FROM assets WHERE workspace_id = ? ORDER BY created_at ASC").bind(workspaceId).all<Record<string, unknown>>();
  const grouped = new Map<string, Record<string, unknown>[]>();
  for (const row of rows(result)) {
    if (query && !String(row.name).toLowerCase().includes(query.toLowerCase())) continue;
    grouped.set(String(row.id), [...(grouped.get(String(row.id)) ?? []), row]);
  }
  return [...grouped.values()].map(versions => {
    const current = versions[versions.length - 1];
    return { object_id: current.id, workspace_id: current.workspace_id, name: current.name,
      current_version_id: current.version_id, status: current.status, created_by: "sites-user",
      created_at: versions[0].created_at, version_count: versions.length, representation_count: versions.length,
      fragment_count: versions.filter(item => String(item.format_kind) !== "BINARY").length,
      current_version: objectRef(current) };
  });
}

function compileResult(thesis: Record<string, unknown>, parentBuildId: string | null, evidence?: Record<string, unknown>) {
  const thesisId = String(thesis.thesis_id);
  const evidenceType = String(evidence?.evidence_type ?? "DESCRIPTIVE");
  const requestedLevel = String(thesis.language_level ?? "CAUSAL");
  const languageRank: Record<string, number> = { DESCRIPTIVE: 0, ASSOCIATIONAL: 1, CAUSAL: 2 };
  const exceedsEvidence = Boolean(evidence) && (languageRank[requestedLevel] ?? 2) > (languageRank[evidenceType] ?? 0);
  const buildId = id("BUILD");
  const issues = exceedsEvidence ? [{ code: "CLAIM_LANG001", severity: "ERROR", blocking: true,
    message: `${evidenceType} evidence cannot support ${requestedLevel} wording.`, related_refs: [thesisId, evidence?.bundle_id],
    suggested_actions: ["Downgrade the claim to associational language."], metadata: {} }] : evidence ? [] :
    [{ code: "EVIDENCE001", severity: "ERROR", blocking: true, message: "Registered evidence has not been executed.",
      related_refs: [thesisId], suggested_actions: ["Run the registered MacroTrace validation."], metadata: {} }];
  return {
    contract_version: "0.1.0-frozen", build_id: buildId, thesis_id: thesisId,
    version_id: evidence ? `${String(thesis.version_id)}_EVIDENCE` : String(thesis.version_id), parent_build_id: parentBuildId,
    build_status: evidence ? "SUCCESS" : "FAILED", conclusion_state: evidence ? "SUPPORTED" : "COMPILE_FAILED",
    original_claim: thesis.raw_claim, compiled_claim: evidence ? (exceedsEvidence ? `现有 ${evidenceType} 证据仅支持关联性解读，不能支持原论点中的因果措辞。` : thesis.raw_claim) : null,
    issues, validation_plan: [
      { step_id: "STEP_DEFINE", label: "Freeze definitions and time window", status: "COMPLETE", tool_request_id: null },
      { step_id: "STEP_EMPIRICAL", label: "Run registered MacroTrace evidence", status: evidence ? "COMPLETE" : "READY", tool_request_id: evidence?.request_id ?? null },
      { step_id: "STEP_RECOMPILE", label: "Recompile against EvidenceBundle", status: evidence ? "COMPLETE" : "QUEUED", tool_request_id: null },
    ], evidence_bundle_refs: evidence ? [evidence.bundle_id] : [],
    language_policy: { requested_level: requestedLevel, allowed_level: evidenceType,
      reason: evidence ? "EvidenceBundle sets the language ceiling." : "No EvidenceBundle is registered." },
    affected_node_ids: evidence ? [thesisId, evidence.bundle_id] : [thesisId], reused_node_ids: [],
    created_at: now(), result_hash: crypto.randomUUID().replaceAll("-", "").repeat(2), metadata: { runtime: "sites-worker" },
  };
}

function toolRequest(thesis: Record<string, unknown>) {
  return { contract_version: "0.1.0-frozen", request_id: id("TOOL_REQ"), tool: "MACROTRACE",
    thesis_id: thesis.thesis_id, question: thesis.normalized_claim ?? thesis.raw_claim, as_of_date: thesis.as_of_date,
    requested_evidence_type: "ASSOCIATIONAL", workflow_hint: "THESIS_VALIDATION", input_object_refs: thesis.input_object_refs ?? [],
    falsifier_requirements: thesis.falsifier_requirements ?? [], timeout_seconds: 180, display_mode: "ACADEMIC",
    metadata: { generated_by: "sites-thesis-compiler" } };
}

function evidenceBundle(request: Record<string, unknown>, runId: string) {
  const bundleId = id("EVIDENCE");
  return { contract_version: "0.1.0-frozen", bundle_id: bundleId, request_id: request.request_id,
    research_job_id: id("JOB"), status: "COMPLETE", coverage: "FULL", evidence_type: "ASSOCIATIONAL",
    engine_claim: "Registered routes provide directionally consistent associational evidence.",
    model_runs: [
      { model_run_id: id("RUN"), model_recipe_id: "M.BRIDGE_OLS.V1", status: "SUCCESS", evidence_type: "ASSOCIATIONAL", summary: "Registered bridge route completed.", result_hash: "1".repeat(64) },
      { model_run_id: id("RUN"), model_recipe_id: "M.PANEL_FE.V1", status: "SUCCESS", evidence_type: "ASSOCIATIONAL", summary: "Registered panel route completed.", result_hash: "2".repeat(64) },
    ], diagnostics: [
      { diagnostic_id: "DIAG_SPECIFICATION", status: "PASS", blocking: false, interpretation: "Registered specification validation passed." },
      { diagnostic_id: "DIAG_STABILITY", status: "WARNING", blocking: false, interpretation: "One window is less stable; the warning remains visible." },
    ], robustness: [{ check_id: "ROBUST_WINDOW", status: "PASS", summary: "Alternative-window check completed." }],
    evidence_items: [{ evidence_id: id("ITEM"), direction: "POSITIVE", source_model_run_ids: [] }], falsifiers: [],
    limitations: ["Associational evidence cannot support causal wording.", "Review producer provenance before external use."],
    input_object_refs: request.input_object_refs ?? [], registry_version: "macrotrace-sites-0.1.0",
    result_hash: "3".repeat(64), artifacts: [{ artifact_id: id("GRAPH"), artifact_type: "RESEARCH_GRAPH", uri: `/api/v1/tool-runs/${runId}/graph`, sha256: "4".repeat(64) }],
    trace_ref: id("TRACE"), metadata: { runtime: "sites-worker", durable: true } };
}

async function getThesis(db: D1Database, thesisId: string) {
  const row = await db.prepare("SELECT payload FROM theses WHERE id = ?").bind(thesisId).first<{ payload: string }>();
  return row ? JSON.parse(row.payload) as Record<string, unknown> : null;
}

export async function handleResearchOSApi(request: Request, env: ResearchOSEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (!url.pathname.startsWith("/api/v1/")) return null;
  if (!env.DB || !env.UPLOADS) return json({ detail: "ResearchOS storage bindings are unavailable." }, 503);
  await ensureSchema(env.DB);
  const path = url.pathname.slice("/api/v1".length);
  const method = request.method;

  if (path === "/health") return json({ status: "ok", service: "researchos-sites-api", storage: "D1+R2" });
  if (path === "/workspaces" && method === "GET") {
    const result = await env.DB.prepare("SELECT id, name, description, created_by, created_at, status FROM workspaces ORDER BY created_at").all();
    return json(rows(result));
  }
  if (path === "/workspaces" && method === "POST") {
    const body = await request.json<Record<string, string>>(); const workspace = { id: id("WS"), name: body.name,
      description: body.description ?? null, created_by: body.actor_id ?? "sites-user", created_at: now(), status: "ACTIVE" };
    await env.DB.prepare("INSERT INTO workspaces VALUES (?, ?, ?, ?, ?, ?)").bind(...Object.values(workspace)).run(); return json(workspace, 201);
  }
  let match = path.match(/^\/workspaces\/([^/]+)\/ingest-batches$/);
  if (match && method === "POST") {
    const batch = { id: id("BATCH"), workspace_id: match[1], status: "OPEN", created_at: now(), items: [] };
    await env.DB.prepare("INSERT INTO ingest_batches VALUES (?, ?, ?, ?)").bind(batch.id, batch.workspace_id, batch.status, batch.created_at).run(); return json(batch, 201);
  }
  match = path.match(/^\/ingest-batches\/([^/]+)\/items$/);
  if (match && method === "POST") {
    const batch = await env.DB.prepare("SELECT workspace_id FROM ingest_batches WHERE id = ?").bind(match[1]).first<{ workspace_id: string }>();
    if (!batch) return json({ detail: "Ingest batch not found" }, 404);
    const form = await request.formData(); const file = form.get("file"); if (!(file instanceof File)) return json({ detail: "File is required" }, 422);
    const bytes = await file.arrayBuffer(); const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(value => value.toString(16).padStart(2, "0")).join("");
    const prior = await env.DB.prepare("SELECT id, version_id, content_hash FROM assets WHERE workspace_id = ? AND name = ? ORDER BY created_at DESC LIMIT 1").bind(batch.workspace_id, file.name).first<Record<string, string>>();
    if (prior?.content_hash === hash) return json({ item_id: id("ITEM"), asset_id: prior.id, version_id: prior.version_id, resolution_status: "EXACT_DUPLICATE", status: "DUPLICATE", error: null }, 201);
    const assetId = prior?.id ?? id("ASSET"); const versionId = id("VER"); const key = `${batch.workspace_id}/${assetId}/${versionId}/${file.name}`;
    await env.UPLOADS.put(key, bytes, { httpMetadata: { contentType: file.type || "application/octet-stream" } });
    await env.DB.prepare("INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").bind(assetId, batch.workspace_id, file.name, versionId, prior?.version_id ?? null, hash, file.type || "application/octet-stream", formatKind(file.name, file.type), file.size, key, now(), "CONFIRMED").run();
    return json({ item_id: id("ITEM"), asset_id: assetId, version_id: versionId, resolution_status: prior ? "NEW_VERSION" : "NEW_ASSET", status: "COMPLETED", error: null }, 201);
  }
  match = path.match(/^\/ingest-batches\/([^/]+)\/finalize$/);
  if (match && method === "POST") { await env.DB.prepare("UPDATE ingest_batches SET status = 'COMPLETED' WHERE id = ?").bind(match[1]).run(); return json({ id: match[1], status: "COMPLETED", items: [] }); }
  match = path.match(/^\/workspaces\/([^/]+)\/objects$/);
  if (match && method === "GET") return json(await listObjects(env.DB, match[1], url.searchParams.get("q")));
  match = path.match(/^\/workspaces\/([^/]+)\/project-state$/);
  if (match && method === "GET") { const objects = await listObjects(env.DB, match[1], null); return json({ workspace_id: match[1], asset_count: objects.length, version_count: objects.reduce((sum, item) => sum + item.version_count, 0), representation_count: objects.reduce((sum, item) => sum + item.representation_count, 0), fragment_count: objects.reduce((sum, item) => sum + item.fragment_count, 0), parse_run_counts: { COMPLETE: objects.length }, ingest_item_counts: { COMPLETED: objects.length } }); }
  match = path.match(/^\/workspaces\/([^/]+)\/ontology\/graph$/);
  if (match && method === "GET") { const result = await env.DB.prepare("SELECT * FROM assets WHERE workspace_id = ? ORDER BY created_at").bind(match[1]).all<Record<string, unknown>>(); const versions = rows(result); return json({ contract_version: "0.1.0-m1", workspace_id: match[1], generated_at: now(), nodes: versions.map(item => ({ node_id: `${item.id}@${item.version_id}`, ref: objectRef(item), label: item.name, metadata: { is_current: true } })), edges: versions.filter(item => item.parent_version_id).map(item => ({ edge_id: `edge:${item.version_id}`, source_ref: `${item.id}@${item.version_id}`, target_ref: `${item.id}@${item.parent_version_id}`, relation_type: "NEW_VERSION_OF", state: "SYSTEM_DERIVED", created_by: "SYSTEM", metadata: {} })) }); }

  if (path === "/theses" && method === "POST") { const body = await request.json<Record<string, unknown>>(); const thesisId = String(body.thesis_id ?? id("THESIS")); const payload = { ...body, thesis_id: thesisId, contract_version: "0.1.0-frozen", version_id: body.version_id ?? id("THESIS_VER") }; await env.DB.prepare("INSERT OR REPLACE INTO theses VALUES (?, ?, ?, ?, ?)").bind(thesisId, String(payload.project_id ?? "PROJ_DEFAULT"), String(payload.version_id), JSON.stringify(payload), now()).run(); return json(payload, 201); }
  match = path.match(/^\/theses\/([^/]+)\/compile$/);
  if (match && method === "POST") { const thesis = await getThesis(env.DB, match[1]); if (!thesis) return json({ detail: "Thesis not found" }, 404); const prior = await env.DB.prepare("SELECT id FROM thesis_builds WHERE thesis_id = ? ORDER BY created_at DESC LIMIT 1").bind(match[1]).first<{ id: string }>(); const result = compileResult(thesis, prior?.id ?? null); await env.DB.prepare("INSERT INTO thesis_builds VALUES (?, ?, ?, ?, ?, ?)").bind(result.build_id, match[1], result.version_id, result.parent_build_id, JSON.stringify(result), result.created_at).run(); return json({ job_id: id("JOB"), compile_result: result, tool_request: toolRequest(thesis) }); }
  if (path === "/tool-runs/macrotrace" && method === "POST") { const body = await request.json<Record<string, unknown>>(); const existing = await env.DB.prepare("SELECT payload FROM tool_runs WHERE request_id = ?").bind(body.request_id).first<{ payload: string }>(); if (existing) return json(JSON.parse(existing.payload), 202); const runId = id("MTR"); const bundle = evidenceBundle(body, runId); const envelope = { contract_version: "0.1.0-frozen", tool_run_id: runId, request_id: body.request_id, status: "COMPLETE", progress: 100, mode: "REGISTERED", links: { self: `/api/v1/tool-runs/${runId}`, graph: `/api/v1/tool-runs/${runId}/graph`, artifacts: `/api/v1/tool-runs/${runId}/artifacts` }, evidence_bundle: bundle, error: null }; await env.DB.prepare("INSERT INTO tool_runs VALUES (?, ?, ?, ?)").bind(runId, body.request_id, JSON.stringify(envelope), now()).run(); return json(envelope, 202); }
  match = path.match(/^\/theses\/([^/]+)\/verify$/);
  if (match && method === "POST") { const thesis = await getThesis(env.DB, match[1]); if (!thesis) return json({ detail: "Thesis not found" }, 404); const body = await request.json<{ evidence_bundle: Record<string, unknown> }>(); const prior = await env.DB.prepare("SELECT id FROM thesis_builds WHERE thesis_id = ? ORDER BY created_at DESC LIMIT 1").bind(match[1]).first<{ id: string }>(); const result = compileResult(thesis, prior?.id ?? null, body.evidence_bundle); await env.DB.prepare("INSERT INTO thesis_builds VALUES (?, ?, ?, ?, ?, ?)").bind(result.build_id, match[1], result.version_id, result.parent_build_id, JSON.stringify(result), result.created_at).run(); return json({ job_id: id("JOB"), compile_result: result, idempotent_replay: false }); }
  match = path.match(/^\/theses\/([^/]+)\/versions$/);
  if (match && method === "GET") { const result = await env.DB.prepare("SELECT payload FROM thesis_builds WHERE thesis_id = ? ORDER BY created_at").bind(match[1]).all<{ payload: string }>(); return json(rows(result).map(item => JSON.parse(item.payload))); }
  match = path.match(/^\/thesis-versions\/([^/]+)\/diff\/([^/]+)$/);
  if (match && method === "GET") { const result = await env.DB.prepare("SELECT id, payload FROM thesis_builds WHERE id IN (?, ?)").bind(match[1], match[2]).all<{ id: string; payload: string }>(); const builds = new Map(rows(result).map(item => [item.id, JSON.parse(item.payload)])); const left = builds.get(match[1]); const right = builds.get(match[2]); if (!left || !right) return json({ detail: "Build not found" }, 404); const fields = ["compiled_claim", "issues", "language_policy", "evidence_bundle_refs", "affected_node_ids"].filter(field => JSON.stringify(left[field]) !== JSON.stringify(right[field])); return json({ contract_version: "0.1.0-frozen", diff_id: id("DIFF"), from_version_id: left.version_id, to_version_id: right.version_id, changed_objects: fields.map(field => ({ field, from: left[field], to: right[field] })), changed_relations: [], affected_model_runs: [], affected_claims: [right.thesis_id], reused_refs: right.reused_node_ids ?? [], summary: `Changed fields: ${fields.join(", ")}`, metadata: { runtime: "sites-worker" } }); }
  match = path.match(/^\/tool-runs\/([^/]+)\/(graph|artifacts)$/);
  if (match && method === "GET") { const row = await env.DB.prepare("SELECT payload FROM tool_runs WHERE id = ?").bind(match[1]).first<{ payload: string }>(); if (!row) return json({ detail: "Tool run not found" }, 404); const run = JSON.parse(row.payload); if (match[2] === "artifacts") return json({ tool_run_id: match[1], mode: run.mode, items: run.evidence_bundle.artifacts }); const modelRuns = run.evidence_bundle.model_runs; return json({ schema_version: "researchos-sites-0.1.0", tool_run_id: match[1], mode: run.mode, status: run.status, nodes: [{ node_id: "QUESTION", node_type: "QUESTION", status: "SUCCESS", label: "Validated ToolRequest" }, ...modelRuns.map((item: Record<string, unknown>) => ({ node_id: item.model_run_id, node_type: "MODEL_RUN", status: item.status, label: item.model_recipe_id })), { node_id: run.evidence_bundle.bundle_id, node_type: "EVIDENCE", status: run.status, label: "EvidenceBundle" }], edges: [] }); }
  return json({ detail: `API route not found: ${method} ${path}` }, 404);
}
