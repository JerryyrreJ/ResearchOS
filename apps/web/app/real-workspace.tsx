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
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "2-digit" }).format(
    new Date(value),
  );
}

const STATUS_LABELS: Record<QueueStatus, string> = {
  QUEUED: "排队中",
  UPLOADING: "上传中",
  COMPLETED: "已完成",
  DUPLICATE: "重复文件",
  FAILED: "失败",
};

export default function RealWorkspace({ onSelect, onObjectCount }: RealWorkspaceProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [workspaceId, setWorkspaceId] = useState<string>();
  const [objects, setObjects] = useState<ObjectSummary[]>([]);
  const [state, setState] = useState<ProjectState>();
  const [graph, setGraph] = useState<OntologyGraph>();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [query, setQuery] = useState("");
  const [workspaceTab, setWorkspaceTab] = useState<"objects" | "relations" | "conflicts">("objects");
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
          const created = await researchosApi.createWorkspace("研究空间");
          workspaces = [created];
        }
        if (cancelled) return;
        const id = workspaces[0].id;
        setWorkspaceId(id);
        await refresh(id);
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "无法加载 API 工作空间。");
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
                ? { ...item, status: "FAILED", detail: caught instanceof Error ? caught.message : "上传失败" }
                : item,
            ),
          );
        }
      }
      await researchosApi.finalizeBatch(batch.id);
      await refresh(workspaceId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法处理上传批次。");
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
          <div className="eyebrow"><span className="status-dot green" /> REAL API · M1 资产基座</div>
          <h2>实时研究工作区</h2>
          <p>以下文件、版本和解析结果均来自确定性 ResearchOS API。</p>
        </div>
        <button className="button secondary" onClick={() => workspaceId && void refresh(workspaceId, query)}>↻ 刷新</button>
      </section>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { if (event.currentTarget === event.target) setDragging(false); }}
        onDrop={onDrop}
      >
        <div className="dropzone-icon">＋</div>
        <div><b>拖拽研究文件到此处</b><small>支持 Markdown、DOCX、XLSX、CSV 和文本 PDF · API 负责确定事实和版本</small></div>
        <button className="button primary small" onClick={() => inputRef.current?.click()}>选择文件</button>
        <input ref={inputRef} type="file" multiple hidden onChange={onInputChange} />
      </div>

      {error && <div className="api-error" role="alert"><b>API 不可用</b><span>{error}</span><button onClick={() => workspaceId && void refresh(workspaceId, query)}>重试</button></div>}

      {queue.length > 0 && (
        <section className="upload-queue">
          <div className="section-title"><div><h2>上传队列</h2><p>每个文件独立处理，单一失败不会回滚整个批次。</p></div></div>
          {queue.map((item) => <div className="upload-row" key={item.id}><span className={`upload-state ${item.status.toLowerCase()}`}>{STATUS_LABELS[item.status]}</span><b>{item.fileName}</b><small>{item.detail ?? ""}</small></div>)}
        </section>
      )}

      <div className="summary-strip api-summary">
        <div><span>研究对象</span><b>{loading ? "…" : objects.length}</b></div>
        <div><span>版本</span><b>{loading ? "…" : state?.version_count ?? 0}</b></div>
        <div><span>已解析片段</span><b>{loading ? "…" : state?.fragment_count ?? 0}</b></div>
        <div><span>语义关系</span><b className="quiet-value">M2 开放</b></div>
      </div>

      <section className="table-section">
        <div className="section-title"><div><h2>研究对象</h2><p>来自实时工作区的版本锁定源文件。</p></div><div className="segmented"><button className={workspaceTab === "objects" ? "active" : ""} onClick={() => setWorkspaceTab("objects")}>对象</button><button className={workspaceTab === "relations" ? "active" : ""} onClick={() => setWorkspaceTab("relations")}>关系</button><button className={workspaceTab === "conflicts" ? "active" : ""} onClick={() => setWorkspaceTab("conflicts")}>冲突</button></div></div>
        <form className="filter-row" onSubmit={submitSearch}>
          <span className="table-search"><span>⌕</span><input aria-label="搜索对象" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="筛选对象…" /></span>
          <button className="button primary small" type="submit">搜索</button>
        </form>
        {workspaceTab === "objects" ? (loading ? <div className="api-empty">正在加载实时工作区…</div> : objects.length === 0 ? <div className="api-empty">暂无资产。在上方拖入研究文件以创建第一个对象。</div> : <div className="research-table"><div className="table-head"><span>名称</span><span>类型</span><span>状态</span><span>版本</span><span>更新时间</span></div>{objects.map((item, index) => { const source = sourceFromObject(item); return <button className="table-row" key={item.object_id} onClick={() => onSelect(source)}><span className="name-cell"><i className={`file-icon f${index % 4}`}>{source.formatKind.slice(0, 1)}</i><span><b>{source.name}</b><small className="mono">{source.id}</small></span></span><span>{source.type}</span><span><span className="badge badge-blue">{source.state}</span></span><span className="mono">{source.version}</span><span>{formatDate(source.updatedAt)}</span></button>; })}</div>) : workspaceTab === "relations" ? <div className="api-empty">{graph?.edges.length ?? 0} 条确定性版本关系。语义关系将在 M2 阶段提供。</div> : <div className="api-empty">暂无未解决的确定性导入冲突。</div>}
      </section>

      <section className="relations api-relations"><div className="section-title"><div><h2>版本结构</h2><p>此处仅显示确定性版本谱系。语义关系将在 M2 阶段提供。</p></div><span className="badge badge-blue">{graph?.edges.length ?? 0} 条系统边</span></div>{graph?.edges.length ? <div className="api-edge-list">{graph.edges.map((edge) => <div className="api-edge" key={edge.edge_id}><span className="mono">{edge.source_ref}</span><b>{edge.relation_type}</b><span className="mono">{edge.target_ref}</span></div>)}</div> : <div className="api-empty">暂无版本谱系边。</div>}</section>
    </div>
  );
}
