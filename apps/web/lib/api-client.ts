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

export class ResearchOSApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ResearchOSApiError";
    this.status = status;
  }
}

type RequestOptions = RequestInit & { searchParams?: Record<string, string | undefined> };

const defaultBaseUrl = "http://127.0.0.1:8000/api/v1";

function getBaseUrl() {
  return (process.env.NEXT_PUBLIC_RESEARCHOS_API_BASE_URL ?? defaultBaseUrl).replace(/\/$/, "");
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
      const body = (await response.json()) as { detail?: string; message?: string };
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // Preserve the status-based error when the server did not return JSON.
    }
    throw new ResearchOSApiError(detail, response.status);
  }
  return (await response.json()) as T;
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

  listObjects: (workspaceId: string, query?: string) =>
    request<ObjectSummary[]>(`/workspaces/${encodeURIComponent(workspaceId)}/objects`, {
      searchParams: { q: query },
    }),

  getObject: (objectId: string) =>
    request<ObjectDetail>(`/objects/${encodeURIComponent(objectId)}`),

  getGraph: (workspaceId: string) =>
    request<OntologyGraph>(
      `/workspaces/${encodeURIComponent(workspaceId)}/ontology/graph`,
    ),

  getProjectState: (workspaceId: string) =>
    request<ProjectState>(
      `/workspaces/${encodeURIComponent(workspaceId)}/project-state`,
    ),
};
