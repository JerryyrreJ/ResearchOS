"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  researchosApi,
  type ObjectSummary,
  type OntologyGraph,
  type ProjectState,
  type WorkspaceSource,
} from "../lib/api-client";

type QueueStatus = "QUEUED" | "UPLOADING" | "COMPLETED" | "DUPLICATE" | "FAILED";

type QueueItem = {
  id: string;
  fileName: string;
  status: QueueStatus;
  detail?: string;
};

type RealWorkspaceProps = {
  onSelect: (item: WorkspaceSource) => void;
  onObjectCount: (count: number) => void;
};

function sourceFromObject(item: ObjectSummary): WorkspaceSource {
  const current = item.current_version;
  return {
    type: "SOURCE_FILE",
    name: item.name,
    id: item.object_id,
    version: current?.version_id ?? "—",
    state: item.status,
    origin: "api",
    formatKind: current?.format_kind ?? "UNKNOWN",
    sizeBytes: current?.size_bytes ?? 0,
    fragmentCount: item.fragment_count,
    versionCount: item.version_count,
    updatedAt: current?.created_at ?? item.created_at,
  };
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "2-digit" }).format(
    new Date(value),
  );
}

export default function RealWorkspace({ onSelect, onObjectCount }: RealWorkspaceProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [workspaceId, setWorkspaceId] = useState<string>();
  const [objects, setObjects] = useState<ObjectSummary[]>([]);
  const [state, setState] = useState<ProjectState>();
  const [graph, setGraph] = useState<OntologyGraph>();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string>();
  const onObjectCountRef = useRef(onObjectCount);

  useEffect(() => {
    onObjectCountRef.current = onObjectCount;
  }, [onObjectCount]);

  const refresh = useCallback(async (id: string, nextQuery?: string) => {
    const [nextObjects, nextState, nextGraph] = await Promise.all([
      researchosApi.listObjects(id, nextQuery || undefined),
      researchosApi.getProjectState(id),
      researchosApi.getGraph(id),
    ]);
    setObjects(nextObjects);
    setState(nextState);
    setGraph(nextGraph);
    onObjectCountRef.current(nextObjects.length);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        setLoading(true);
        let workspaces = await researchosApi.listWorkspaces();
        if (workspaces.length === 0) {
          const created = await researchosApi.createWorkspace("Research workspace");
          workspaces = [created];
        }
        if (cancelled) return;
        const id = workspaces[0].id;
        setWorkspaceId(id);
        await refresh(id);
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Unable to load the API workspace.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const acceptFiles = async (incoming: File[]) => {
    if (!workspaceId || incoming.length === 0) return;
    setError(undefined);
    const initialQueue = incoming.map((file, index) => ({
      id: `${file.name}-${file.lastModified}-${index}`,
      fileName: file.name,
      status: "QUEUED" as const,
    }));
    setQueue(initialQueue);
    try {
      const batch = await researchosApi.createBatch(workspaceId);
      for (const [index, file] of incoming.entries()) {
        const itemId = initialQueue[index].id;
        setQueue((current) =>
          current.map((item) => (item.id === itemId ? { ...item, status: "UPLOADING" } : item)),
        );
        try {
          const outcome = await researchosApi.uploadFile(batch.id, file, workspaceId);
          const status = (outcome.status === "DUPLICATE" ? "DUPLICATE" : outcome.status) as QueueStatus;
          setQueue((current) =>
            current.map((item) =>
              item.id === itemId
                ? {
                    ...item,
                    status: status === "COMPLETED" || status === "DUPLICATE" ? status : "FAILED",
                    detail: outcome.resolution_status ?? outcome.error ?? undefined,
                  }
                : item,
            ),
          );
        } catch (caught) {
          setQueue((current) =>
            current.map((item) =>
              item.id === itemId
                ? { ...item, status: "FAILED", detail: caught instanceof Error ? caught.message : "Upload failed" }
                : item,
            ),
          );
        }
      }
      await researchosApi.finalizeBatch(batch.id);
      await refresh(workspaceId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to process the upload batch.");
    }
  };

  const onInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    void acceptFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  };

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void acceptFiles(Array.from(event.dataTransfer.files));
  };

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    if (workspaceId) void refresh(workspaceId, query);
  };

  return (
    <div className="workspace-scroll">
      <section className="api-workspace-head">
        <div>
          <div className="eyebrow"><span className="status-dot green" /> REAL API · M1 ASSET FOUNDATION</div>
          <h2>Live research workspace</h2>
          <p>Files, versions and parser results below come from the deterministic ResearchOS API.</p>
        </div>
        <button className="button secondary" onClick={() => workspaceId && void refresh(workspaceId, query)}>↻ Refresh</button>
      </section>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { if (event.currentTarget === event.target) setDragging(false); }}
        onDrop={onDrop}
      >
        <div className="dropzone-icon">＋</div>
        <div><b>Drop research files here</b><small>Markdown, DOCX, XLSX, CSV and text PDF · the API determines facts and versions</small></div>
        <button className="button primary small" onClick={() => inputRef.current?.click()}>Choose files</button>
        <input ref={inputRef} type="file" multiple hidden onChange={onInputChange} />
      </div>

      {error && <div className="api-error" role="alert"><b>API unavailable</b><span>{error}</span><button onClick={() => workspaceId && void refresh(workspaceId, query)}>Retry</button></div>}

      {queue.length > 0 && (
        <section className="upload-queue">
          <div className="section-title"><div><h2>Upload queue</h2><p>Each file is isolated so one failure does not roll back the batch.</p></div></div>
          {queue.map((item) => <div className="upload-row" key={item.id}><span className={`upload-state ${item.status.toLowerCase()}`}>{item.status}</span><b>{item.fileName}</b><small>{item.detail ?? ""}</small></div>)}
        </section>
      )}

      <div className="summary-strip api-summary">
        <div><span>Research objects</span><b>{loading ? "…" : objects.length}</b></div>
        <div><span>Versions</span><b>{loading ? "…" : state?.version_count ?? 0}</b></div>
        <div><span>Parsed fragments</span><b>{loading ? "…" : state?.fragment_count ?? 0}</b></div>
        <div><span>Semantic relations</span><b className="quiet-value">Not in M1</b></div>
      </div>

      <section className="table-section">
        <div className="section-title"><div><h2>Research objects</h2><p>Version-pinned source files from the live workspace.</p></div><div className="segmented"><button className="active">Objects</button><button disabled>Relations</button><button disabled>Conflicts</button></div></div>
        <form className="filter-row" onSubmit={submitSearch}>
          <span className="table-search"><span>⌕</span><input aria-label="Search objects" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter objects…" /></span>
          <button className="button primary small" type="submit">Search</button>
        </form>
        {loading ? <div className="api-empty">Loading the live workspace…</div> : objects.length === 0 ? <div className="api-empty">No assets yet. Drop a research file above to create the first object.</div> : <div className="research-table"><div className="table-head"><span>Name</span><span>Type</span><span>State</span><span>Version</span><span>Updated</span></div>{objects.map((item, index) => { const source = sourceFromObject(item); return <button className="table-row" key={item.object_id} onClick={() => onSelect(source)}><span className="name-cell"><i className={`file-icon f${index % 4}`}>{source.formatKind.slice(0, 1)}</i><span><b>{source.name}</b><small className="mono">{source.id}</small></span></span><span>{source.type}</span><span><span className="badge badge-blue">{source.state}</span></span><span className="mono">{source.version}</span><span>{formatDate(source.updatedAt)}</span></button>; })}</div>}
      </section>

      <section className="relations api-relations"><div className="section-title"><div><h2>Version structure</h2><p>Only deterministic version lineage is shown here. Semantic relations arrive in M2.</p></div><span className="badge badge-blue">{graph?.edges.length ?? 0} system edges</span></div>{graph?.edges.length ? <div className="api-edge-list">{graph.edges.map((edge) => <div className="api-edge" key={edge.edge_id}><span className="mono">{edge.source_ref}</span><b>{edge.relation_type}</b><span className="mono">{edge.target_ref}</span></div>)}</div> : <div className="api-empty">No version lineage edges yet.</div>}</section>
    </div>
  );
}
