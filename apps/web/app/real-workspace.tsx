"use client";
/* eslint-disable @next/next/no-img-element -- transparent mascot is a pre-optimized static brand asset */

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
  resolution?: "NEW_ASSET" | "NEW_VERSION" | "EXACT_DUPLICATE" | string | null;
  assetId?: string | null;
  versionId?: string | null;
};

type RealWorkspaceProps = {
  onSelect: (item: WorkspaceSource) => void;
  onObjectCount: (count: number) => void;
};

type LibraryCategory = "ALL" | "DOCUMENT" | "DATA" | "NOTE" | "PDF";

function categoryFor(item: ObjectSummary): Exclude<LibraryCategory, "ALL"> {
  const kind = item.current_version?.format_kind ?? "";
  if (kind === "CSV" || kind === "XLSX") return "DATA";
  if (kind === "MARKDOWN" || kind === "TEXT") return "NOTE";
  if (kind === "PDF_TEXT") return "PDF";
  return "DOCUMENT";
}

function readableBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function resolutionCopy(item: QueueItem) {
  if (item.resolution === "EXACT_DUPLICATE" || item.status === "DUPLICATE") return { icon: "≡", label: "重复文件 · 已跳过", detail: "内容哈希完全相同，没有创建副本或占用额外存储。", tone: "duplicate" };
  if (item.resolution === "NEW_VERSION") return { icon: "↟", label: "已建立新版本", detail: "检测到同名文件内容变化，旧版本已保留并建立版本关系。", tone: "version" };
  if (item.status === "COMPLETED") return { icon: "✓", label: "已收录", detail: "文件已保存、分类并加入团队知识库。", tone: "stored" };
  if (item.status === "FAILED") return { icon: "!", label: "处理失败", detail: item.detail ?? "请检查文件后重试。", tone: "failed" };
  if (item.status === "UPLOADING") return { icon: "↻", label: "正在处理", detail: "正在上传、计算内容哈希并检查历史版本…", tone: "working" };
  return { icon: "·", label: "等待处理", detail: "文件已进入上传队列。", tone: "queued" };
}

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
  const dragDepthRef = useRef(0);
  const [workspaceId, setWorkspaceId] = useState<string>();
  const [objects, setObjects] = useState<ObjectSummary[]>([]);
  const [state, setState] = useState<ProjectState>();
  const [graph, setGraph] = useState<OntologyGraph>();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [query, setQuery] = useState("");
  const [workspaceTab, setWorkspaceTab] = useState<"objects" | "relations" | "conflicts">("objects");
  const [category, setCategory] = useState<LibraryCategory>("ALL");
  const [selectedObjectId, setSelectedObjectId] = useState<string>();
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

  useEffect(() => {
    const choose = () => inputRef.current?.click();
    window.addEventListener("researchos:choose-files", choose);
    return () => window.removeEventListener("researchos:choose-files", choose);
  }, []);

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
                    resolution: outcome.resolution_status,
                    assetId: outcome.asset_id,
                    versionId: outcome.version_id,
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
    dragDepthRef.current = 0;
    setDragging(false);
    void acceptFiles(Array.from(event.dataTransfer.files));
  };

  const onWorkspaceDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!event.dataTransfer.types.includes("Files")) return;
    dragDepthRef.current += 1;
    setDragging(true);
  };

  const onWorkspaceDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) setDragging(false);
  };

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    if (workspaceId) void refresh(workspaceId, query);
  };

  const visibleObjects = objects.filter(item => category === "ALL" || categoryFor(item) === category);
  const selectedObject = objects.find(item => item.object_id === selectedObjectId);
  const categories: Array<{ id: LibraryCategory; label: string }> = [
    { id: "ALL", label: "全部" }, { id: "DOCUMENT", label: "文档" }, { id: "DATA", label: "数据" },
    { id: "NOTE", label: "笔记" }, { id: "PDF", label: "PDF" },
  ];

  return (
    <div className={`workspace-scroll api-workspace ${dragging ? "is-dragging" : ""}`} onDragEnter={onWorkspaceDragEnter} onDragOver={(event)=>event.preventDefault()} onDragLeave={onWorkspaceDragLeave} onDrop={onDrop}>
      {dragging && <div className="workspace-drop-overlay" role="status"><img src="/brand/evidence-archivist.png" alt=""/><b>交给证据档案员</b><span>松开后自动保存、分类并建立不可变版本</span></div>}
      <section className="api-workspace-head">
        <div>
          <div className="eyebrow"><span className="status-dot green" /> SHARED · TEAM KNOWLEDGE</div>
          <h2>把团队文件放到同一个地方</h2>
          <p>上传后自动保存、识别类型并建立版本。所有成员看到的是同一份资料库。</p>
        </div>
        <div className="knowledge-presence"><span>TW</span><span>YR</span><span>+3</span><button className="button secondary" onClick={() => workspaceId && void refresh(workspaceId, query)}>↻ 同步</button></div>
      </section>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onClick={()=>inputRef.current?.click()}
      >
        <div className="dropzone-icon">↓</div>
        <div><b>拖入任何团队文件</b><small>松开后立即保存并分类 · 支持 Markdown、Word、Excel、CSV、PDF 与文本</small></div>
        <button className="button primary small" onClick={(event) => { event.stopPropagation(); inputRef.current?.click(); }}>选择文件</button>
        <input ref={inputRef} type="file" multiple hidden onChange={onInputChange} />
      </div>

      {error && <div className="api-error" role="alert"><b>API unavailable</b><span>{error}</span><button onClick={() => workspaceId && void refresh(workspaceId, query)}>Retry</button></div>}

      {queue.length > 0 && (
        <section className="upload-queue">
          <div className="upload-summary"><div><span className="eyebrow">INGEST RESULTS</span><h2>文件处理结果</h2><p>系统会依据内容哈希去重，并为发生变化的同名文件自动建立版本。</p></div><div className="ingest-counts"><span><b>{queue.filter(item=>item.status==="COMPLETED").length}</b> 已收录</span><span><b>{queue.filter(item=>item.resolution==="NEW_VERSION").length}</b> 新版本</span><span><b>{queue.filter(item=>item.status==="DUPLICATE").length}</b> 已去重</span></div></div>
          {queue.map((item) => {const result=resolutionCopy(item);return <div className={`upload-row result-${result.tone}`} key={item.id}><span className="upload-result-icon">{result.icon}</span><span className="upload-result-file"><b>{item.fileName}</b><small>{result.detail}</small></span><span className="upload-result-state"><strong>{result.label}</strong>{item.versionId&&<small className="mono">{item.versionId}</small>}</span></div>})}
        </section>
      )}

      <section className="knowledge-library">
        <div className="library-toolbar"><div><span className="eyebrow">TEAM LIBRARY</span><h2>共享资料库</h2></div><form className="library-search" onSubmit={submitSearch}><span>⌕</span><input aria-label="Search knowledge base" value={query} onChange={event=>setQuery(event.target.value)} placeholder="搜索文件、类型或版本…"/><button>搜索</button></form></div>
        <div className="category-row">{categories.map(item=><button key={item.id} className={category===item.id?"active":""} onClick={()=>setCategory(item.id)}>{item.label}<em>{item.id==="ALL"?objects.length:objects.filter(object=>categoryFor(object)===item.id).length}</em></button>)}</div>
        <div className={`library-layout ${selectedObject ? "has-analysis" : ""}`}>
          <div className="file-collection">{loading ? <div className="knowledge-empty">正在同步团队资料库…</div> : visibleObjects.length===0 ? <button className="knowledge-empty actionable" onClick={()=>inputRef.current?.click()}><img src="/brand/evidence-archivist.png" alt="证据档案员"/><b>档案员正在等待第一份资料</b><span>拖入文件，或点击这里开始建立共享知识库</span></button> : visibleObjects.map(item=>{const source=sourceFromObject(item);const itemCategory=categoryFor(item);return <button className={`knowledge-file ${selectedObjectId===item.object_id?"selected":""}`} key={item.object_id} onClick={()=>setSelectedObjectId(item.object_id)}><i className={`knowledge-file-icon kind-${itemCategory.toLowerCase()}`}>{source.formatKind.slice(0,2)}</i><span><b>{item.name}</b><small>{itemCategory} · {readableBytes(source.sizeBytes)} · {item.version_count} 个版本</small></span><em>{formatDate(source.updatedAt)}</em></button>})}</div>
          {selectedObject&&<aside className="quick-analysis"><div className="analysis-head"><span>基础分析</span><button onClick={()=>setSelectedObjectId(undefined)} aria-label="Close analysis">×</button></div><div className="analysis-file"><i>{selectedObject.current_version?.format_kind.slice(0,2)}</i><h3>{selectedObject.name}</h3><p className="mono">{selectedObject.object_id}</p></div><div className="analysis-summary"><span>自动分类</span><b>{categoryFor(selectedObject)}</b><p>{selectedObject.current_version?.format_kind === "CSV" || selectedObject.current_version?.format_kind === "XLSX" ? "结构化数据文件，可用于后续统计与模型分析。" : "已安全保存并纳入团队检索，可继续建立论题与证据关系。"}</p></div><dl><dt>文件大小</dt><dd>{readableBytes(selectedObject.current_version?.size_bytes ?? 0)}</dd><dt>版本</dt><dd>{selectedObject.version_count}</dd><dt>可解析片段</dt><dd>{selectedObject.fragment_count}</dd><dt>状态</dt><dd>{selectedObject.status}</dd></dl><button className="button primary analysis-action" onClick={()=>window.dispatchEvent(new CustomEvent("researchos:new-thesis",{detail:{name:selectedObject.name}}))}>用于新论题 →</button></aside>}
        </div>
      </section>

      <div className="summary-strip api-summary">
        <div><span>Research objects</span><b>{loading ? "…" : objects.length}</b></div>
        <div><span>Versions</span><b>{loading ? "…" : state?.version_count ?? 0}</b></div>
        <div><span>Parsed fragments</span><b>{loading ? "…" : state?.fragment_count ?? 0}</b></div>
        <div><span>Semantic relations</span><b className="quiet-value">Not in M1</b></div>
      </div>

      <section className="table-section">
        <div className="section-title"><div><h2>Research objects</h2><p>Version-pinned source files from the live workspace.</p></div><div className="segmented"><button className={workspaceTab === "objects" ? "active" : ""} onClick={() => setWorkspaceTab("objects")}>Objects</button><button className={workspaceTab === "relations" ? "active" : ""} onClick={() => setWorkspaceTab("relations")}>Relations</button><button className={workspaceTab === "conflicts" ? "active" : ""} onClick={() => setWorkspaceTab("conflicts")}>Conflicts</button></div></div>
        <form className="filter-row" onSubmit={submitSearch}>
          <span className="table-search"><span>⌕</span><input aria-label="Search objects" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter objects…" /></span>
          <button className="button primary small" type="submit">Search</button>
        </form>
        {workspaceTab === "objects" ? (loading ? <div className="api-empty">Loading the live workspace…</div> : objects.length === 0 ? <div className="api-empty">No assets yet. Drop a research file above to create the first object.</div> : <div className="research-table"><div className="table-head"><span>Name</span><span>Type</span><span>State</span><span>Version</span><span>Updated</span></div>{objects.map((item, index) => { const source = sourceFromObject(item); return <button className="table-row" key={item.object_id} onClick={() => onSelect(source)}><span className="name-cell"><i className={`file-icon f${index % 4}`}>{source.formatKind.slice(0, 1)}</i><span><b>{source.name}</b><small className="mono">{source.id}</small></span></span><span>{source.type}</span><span><span className="badge badge-blue">{source.state}</span></span><span className="mono">{source.version}</span><span>{formatDate(source.updatedAt)}</span></button>; })}</div>) : workspaceTab === "relations" ? <div className="api-empty">{graph?.edges.length ?? 0} deterministic NEW_VERSION_OF relations. Semantic relations arrive in M2.</div> : <div className="api-empty">No unresolved deterministic ingest conflicts. Ambiguous logical identities remain separate assets.</div>}
      </section>

      <section className="relations api-relations"><div className="section-title"><div><h2>Version structure</h2><p>Only deterministic version lineage is shown here. Semantic relations arrive in M2.</p></div><span className="badge badge-blue">{graph?.edges.length ?? 0} system edges</span></div>{graph?.edges.length ? <div className="api-edge-list">{graph.edges.map((edge) => <div className="api-edge" key={edge.edge_id}><span className="mono">{edge.source_ref}</span><b>{edge.relation_type}</b><span className="mono">{edge.target_ref}</span></div>)}</div> : <div className="api-empty">No version lineage edges yet.</div>}</section>
    </div>
  );
}
