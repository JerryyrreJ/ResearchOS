export type Workspace = {
  id: string;
  name: string;
  description: string | null;
  created_by: string;
  created_at: string;
  status: string;
};

export type ObjectReference = {
  contract_version: "0.1.0-m1";
  object_id: string;
  version_id: string;
  object_type: "SOURCE_FILE";
  name: string;
  representation: string;
  schema_version: string;
  content_hash: string;
  access_scope: string;
  source_filename: string;
  mime_type: string;
  format_kind: string;
  size_bytes: number;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type ObjectSummary = {
  object_id: string;
  workspace_id: string;
  name: string;
  current_version_id: string | null;
  status: string;
  created_by: string;
  created_at: string;
  version_count: number;
  representation_count: number;
  fragment_count: number;
  current_version: ObjectReference | null;
};

export type ObjectDetail = {
  summary: ObjectSummary;
  versions: ObjectReference[];
};

export type ProjectState = {
  workspace_id: string;
  asset_count: number;
  version_count: number;
  representation_count: number;
  fragment_count: number;
  parse_run_counts: Record<string, number>;
  ingest_item_counts: Record<string, number>;
};

export type OntologyGraph = {
  contract_version: "0.1.0-m1";
  workspace_id: string;
  generated_at: string;
  nodes: Array<{
    node_id: string;
    ref: ObjectReference;
    label: string;
    metadata: Record<string, unknown>;
  }>;
  edges: Array<{
    edge_id: string;
    source_ref: string;
    target_ref: string;
    relation_type: "NEW_VERSION_OF";
    state: "SYSTEM_DERIVED";
    created_by: "SYSTEM";
    metadata: Record<string, unknown>;
  }>;
};

export type IngestOutcome = {
  item_id: string;
  asset_id: string | null;
  version_id: string | null;
  resolution_status: string | null;
  status: string;
  error: string | null;
};

export type Batch = {
  id: string;
  workspace_id: string;
  status: string;
  items: Array<{
    id: string;
    original_filename: string;
    status: string;
    resolution_status: string | null;
    error: string | null;
  }>;
};

export type WorkspaceSource = {
  type: string;
  name: string;
  id: string;
  version: string;
  state: string;
  origin: "api";
  formatKind: string;
  sizeBytes: number;
  fragmentCount: number;
  versionCount: number;
  updatedAt: string;
};

export type CompileIssue = {
  code: string;
  severity: string;
  blocking: boolean;
  message: string;
  suggested_actions: string[];
};

export type ValidationStep = {
  step_id: string;
  label: string;
  status: string;
  tool_request_id: string | null;
};

export type CompileResult = {
  build_id: string;
  thesis_id: string;
  version_id: string;
  parent_build_id: string | null;
  build_status: string;
  conclusion_state: string;
  original_claim: string;
  compiled_claim: string | null;
  issues: CompileIssue[];
  validation_plan: ValidationStep[];
  evidence_bundle_refs: string[];
  language_policy: { requested_level: string; allowed_level: string; reason: string };
  affected_node_ids: string[];
  reused_node_ids: string[];
};

export type ToolRequest = Record<string, unknown> & { request_id: string };
export type EvidenceBundle = Record<string, unknown> & {
  bundle_id: string;
  status: string;
  coverage: string;
  evidence_type: string;
  engine_claim: string | null;
  model_runs: Array<Record<string, unknown> & { model_run_id: string; model_recipe_id: string; status: string; summary: string }>;
  diagnostics: Array<Record<string, unknown> & { diagnostic_id: string; status: string; blocking: boolean; interpretation: string }>;
  limitations: string[];
  trace_ref: string;
};

export type CompileEnvelope = { job_id: string | null; compile_result: CompileResult; tool_request: ToolRequest };
export type ToolRunEnvelope = {
  tool_run_id: string;
  request_id: string;
  status: string;
  progress: number;
  mode: string;
  evidence_bundle: EvidenceBundle;
};
export type VerifyEnvelope = { job_id: string | null; compile_result: CompileResult; idempotent_replay: boolean };
export type VersionDiff = {
  diff_id: string;
  from_version_id: string;
  to_version_id: string;
  changed_objects: Array<{ field: string; from: unknown; to: unknown }>;
  affected_model_runs: string[];
  affected_claims: string[];
  reused_refs: string[];
  summary: string;
};

export type JobEvent = { sequence: number; event_type: string; status: string; payload: Record<string, unknown> };

export class ResearchOSApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ResearchOSApiError";
    this.status = status;
  }
}

type RequestOptions = RequestInit & { searchParams?: Record<string, string | undefined> };

function getBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_RESEARCHOS_API_BASE_URL;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") return `${window.location.origin}/api/v1`;
  return "http://127.0.0.1:8000/api/v1";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { searchParams, ...init } = options;
  const url = new URL(`${getBaseUrl()}${path}`);
  for (const [key, value] of Object.entries(searchParams ?? {})) {
    if (value) url.searchParams.set(key, value);
  }
  const response = await fetch(url, { ...init, headers: { Accept: "application/json", ...init.headers } });
  if (!response.ok) {
    let detail = `ResearchOS API request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown; message?: unknown };
      const candidate = body.detail ?? body.message;
      detail = typeof candidate === "string" ? candidate : candidate ? JSON.stringify(candidate) : detail;
    } catch {
      // Preserve the status-based error when the server did not return JSON.
    }
    throw new ResearchOSApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

async function requestJobEvents(jobId: string) {
  const response = await fetch(`${getBaseUrl()}/jobs/${encodeURIComponent(jobId)}/events`, { headers: { Accept: "text/event-stream" } });
  if (!response.ok) throw new ResearchOSApiError(`ResearchOS job events failed (${response.status})`, response.status);
  const text = await response.text();
  return text.split("\n").filter(line => line.startsWith("data: ")).map(line => JSON.parse(line.slice(6)) as JobEvent);
}

export const researchosApi = {
  listWorkspaces: () => request<Workspace[]>("/workspaces"),

  createWorkspace: (name: string) =>
    request<Workspace>("/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: "Browser workspace", actor_id: "web-demo" }),
    }),

  createBatch: (workspaceId: string) =>
    request<Batch>(`/workspaces/${encodeURIComponent(workspaceId)}/ingest-batches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor_id: "web-demo" }),
    }),

  uploadFile: (batchId: string, file: File, workspaceId: string) => {
    const form = new FormData();
    form.set("actor_id", "web-demo");
    form.set("source_key", `browser:${workspaceId}:${file.name}`);
    form.set("force_new_asset", "false");
    form.set("file", file);
    return request<IngestOutcome>(`/ingest-batches/${encodeURIComponent(batchId)}/items`, {
      method: "POST",
      body: form,
    });
  },

  finalizeBatch: (batchId: string) =>
    request<Batch>(`/ingest-batches/${encodeURIComponent(batchId)}/finalize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor_id: "web-demo" }),
    }),

  getBatch: (batchId: string) => request<Batch>(`/ingest-batches/${encodeURIComponent(batchId)}`),

  listAssets: (workspaceId: string) => request<Array<Record<string, unknown>>>(`/workspaces/${encodeURIComponent(workspaceId)}/assets`),

  listObjects: (workspaceId: string, query?: string) =>
    request<ObjectSummary[]>(`/workspaces/${encodeURIComponent(workspaceId)}/objects`, {
      searchParams: { q: query },
    }),

  getObject: (objectId: string) =>
    request<ObjectDetail>(`/objects/${encodeURIComponent(objectId)}`),

  listObjectVersions: (objectId: string) => request<ObjectReference[]>(`/objects/${encodeURIComponent(objectId)}/versions`),

  getAsset: (assetId: string) => request<Record<string, unknown>>(`/assets/${encodeURIComponent(assetId)}`),

  getAssetVersion: (versionId: string) => request<Record<string, unknown>>(`/asset-versions/${encodeURIComponent(versionId)}`),

  getGraph: (workspaceId: string) =>
    request<OntologyGraph>(
      `/workspaces/${encodeURIComponent(workspaceId)}/ontology/graph`,
    ),

  getProjectState: (workspaceId: string) =>
    request<ProjectState>(
      `/workspaces/${encodeURIComponent(workspaceId)}/project-state`,
    ),

  createThesis: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/theses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getThesis: (thesisId: string) => request<Record<string, unknown>>(`/theses/${encodeURIComponent(thesisId)}`),

  compileThesis: (thesisId: string) =>
    request<CompileEnvelope>(`/theses/${encodeURIComponent(thesisId)}/compile`, { method: "POST" }),

  runMacroTrace: (toolRequest: ToolRequest) =>
    request<ToolRunEnvelope>("/tool-runs/macrotrace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toolRequest),
    }),

  verifyThesis: (thesisId: string, evidenceBundle: EvidenceBundle) =>
    request<VerifyEnvelope>(`/theses/${encodeURIComponent(thesisId)}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ evidence_bundle: evidenceBundle }),
    }),

  listThesisVersions: (thesisId: string) =>
    request<CompileResult[]>(`/theses/${encodeURIComponent(thesisId)}/versions`),

  getVersionDiff: (fromBuildId: string, toBuildId: string) =>
    request<VersionDiff>(`/thesis-versions/${encodeURIComponent(fromBuildId)}/diff/${encodeURIComponent(toBuildId)}`),

  getToolGraph: (toolRunId: string) =>
    request<Record<string, unknown>>(`/tool-runs/${encodeURIComponent(toolRunId)}/graph`),

  getToolRun: (toolRunId: string) => request<ToolRunEnvelope>(`/tool-runs/${encodeURIComponent(toolRunId)}`),

  getToolArtifacts: (toolRunId: string) =>
    request<{ items: Array<Record<string, unknown>> }>(`/tool-runs/${encodeURIComponent(toolRunId)}/artifacts`),

  getJobEvents: requestJobEvents,
};
