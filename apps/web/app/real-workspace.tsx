"use client";
/* eslint-disable @next/next/no-img-element -- transparent mascot is a pre-optimized static brand asset */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Locale } from "./i18n";
import {
  researchosApi,
  type ObjectDetail,
  type ObjectSummary,
  type OntologyGraph,
  type ProjectState,
  type WorkspaceSource,
} from "../lib/api-client";

type QueueStatus =
  | "QUEUED"
  | "UPLOADING"
  | "COMPLETED"
  | "DUPLICATE"
  | "FAILED";

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
  locale: Locale;
  onSelect: (item: WorkspaceSource) => void;
  onObjectCount: (count: number) => void;
};

const workspaceCopy = {
  synced: ["已同步", "已同步", "Synced"], sync: ["同步", "同步", "Sync"], drop: ["拖入文件", "拖入檔案", "Drop files"], dropDetail: ["自动保存、分类和版本管理", "自動儲存、分類和版本管理", "Auto-save, classification, and versioning"], choose: ["选择文件", "選擇檔案", "Choose files"], results: ["文件处理结果", "檔案處理結果", "File processing results"], resultDetail: ["系统依据内容哈希去重，并为变化的同名文件建立版本。", "系統依據內容雜湊去重，並為變更的同名檔案建立版本。", "Content hashes remove duplicates; changed files create new versions."], files: ["文件", "檔案", "Files"], network: ["关系网络", "關係網路", "Relationship network"], versions: ["版本", "版本", "Versions"], search: ["搜索", "搜尋", "Search"], searchPlaceholder: ["搜索文件、类型或版本…", "搜尋檔案、類型或版本…", "Search files, types, or versions…"], all: ["全部", "全部", "All"], documents: ["文档", "文件", "Documents"], data: ["数据", "資料", "Data"], notes: ["笔记", "筆記", "Notes"], syncing: ["正在同步团队资料库…", "正在同步團隊資料庫…", "Syncing team library…"], emptyTitle: ["档案员正在等待第一份资料", "檔案員正在等待第一份資料", "The Archivist is waiting for the first source"], emptyDetail: ["拖入文件，或点击这里开始建立共享知识库", "拖入檔案，或點擊這裡開始建立共享知識庫", "Drop files, or click here to start the shared library"], analysis: ["基础分析", "基礎分析", "Basic analysis"], category: ["自动分类", "自動分類", "Automatic category"], size: ["文件大小", "檔案大小", "File size"], fragments: ["可解析片段", "可解析片段", "Parsed fragments"], status: ["状态", "狀態", "Status"], useThesis: ["用于新论题 →", "用於新論題 →", "Use in new thesis →"], current: ["当前版本", "目前版本", "Current version"], history: ["历史版本", "歷史版本", "Version history"], deterministic: ["仅展示后端确认的确定性版本关系", "僅顯示後端確認的確定性版本關係", "Only backend-confirmed deterministic version relations are shown"], noStructure: ["暂无版本结构", "暫無版本結構", "No version structure yet"], firstVersion: ["上传文件后会自动建立第一个不可变版本。", "上傳檔案後會自動建立第一個不可變版本。", "Uploading a file creates its first immutable version."], teamLibrary: ["团队知识库", "團隊知識庫", "Team library"], fileObjects: ["个文件对象", "個檔案物件", "file objects"], buildingNetwork: ["正在构建关系网络…", "正在建立關係網路…", "Building relationship network…"], firstNode: ["＋ 上传文件以建立第一个节点", "＋ 上傳檔案以建立第一個節點", "＋ Upload a file to create the first node"], nodeRelations: ["节点关联", "節點關聯", "Node relations"], scope: ["关系范围", "關係範圍", "Relation scope"], sameLibrary: ["同一知识库", "同一知識庫", "Same library"], historicalRelations: ["历史关系", "歷史關係", "Historical relations"], fullChain: ["查看完整版本链 →", "檢視完整版本鏈 →", "View full version chain →"], loadingStructure: ["正在读取版本结构…", "正在讀取版本結構…", "Loading version structure…"], relations: ["条关联", "條關聯", "relations"], fileVersions: ["个版本", "個版本", "versions"], retry: ["重试", "重試", "Retry"], apiUnavailable: ["接口暂不可用", "介面暫時無法使用", "API unavailable"], giveArchivist: ["交给证据档案员", "交給證據檔案員", "Give it to the Evidence Archivist"], release: ["松开后自动保存、分类并建立不可变版本", "放開後自動儲存、分類並建立不可變版本", "Release to save, classify, and create an immutable version"], stored: ["已收录", "已收錄", "Stored"], newVersion: ["新版本", "新版本", "New version"], deduped: ["已去重", "已去重", "Deduplicated"],
} as const;

function wc(locale: Locale, key: keyof typeof workspaceCopy) {
  return workspaceCopy[key][locale === "zh-CN" ? 0 : locale === "zh-TW" ? 1 : 2];
}

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

function localized(locale: Locale, cn: string, tw: string, en: string) { return locale === "zh-CN" ? cn : locale === "zh-TW" ? tw : en; }

function resolutionCopy(item: QueueItem, locale: Locale) {
  if (item.resolution === "EXACT_DUPLICATE" || item.status === "DUPLICATE")
    return {
      icon: "≡",
      label: localized(locale, "重复文件 · 已跳过", "重複檔案 · 已略過", "Duplicate · Skipped"),
      detail: localized(locale, "内容哈希完全相同，没有创建副本或占用额外存储。", "內容雜湊完全相同，未建立副本或占用額外儲存空間。", "The content hash is identical; no copy or extra storage was created."),
      tone: "duplicate",
    };
  if (item.resolution === "NEW_VERSION")
    return {
      icon: "↟",
      label: localized(locale, "已建立新版本", "已建立新版本", "New version created"),
      detail: localized(locale, "检测到同名文件内容变化，旧版本已保留并建立版本关系。", "偵測到同名檔案內容變更，舊版本已保留並建立版本關係。", "Changed content was detected; the prior version remains linked."),
      tone: "version",
    };
  if (item.status === "COMPLETED")
    return {
      icon: "✓",
      label: wc(locale, "stored"),
      detail: localized(locale, "文件已保存、分类并加入团队知识库。", "檔案已儲存、分類並加入團隊知識庫。", "The file was saved, classified, and added to the team library."),
      tone: "stored",
    };
  if (item.status === "FAILED")
    return {
      icon: "!",
      label: localized(locale, "处理失败", "處理失敗", "Processing failed"),
      detail: item.detail ?? localized(locale, "请检查文件后重试。", "請檢查檔案後重試。", "Check the file and try again."),
      tone: "failed",
    };
  if (item.status === "UPLOADING")
    return {
      icon: "↻",
      label: localized(locale, "正在处理", "正在處理", "Processing"),
      detail: localized(locale, "正在上传、计算内容哈希并检查历史版本…", "正在上傳、計算內容雜湊並檢查歷史版本…", "Uploading, hashing, and checking version history…"),
      tone: "working",
    };
  return {
    icon: "·",
    label: localized(locale, "等待处理", "等待處理", "Queued"),
    detail: localized(locale, "文件已进入上传队列。", "檔案已進入上傳佇列。", "The file is in the upload queue."),
    tone: "queued",
  };
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
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
  }).format(new Date(value));
}

export default function RealWorkspace({
  locale,
  onSelect,
  onObjectCount,
}: RealWorkspaceProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const dragDepthRef = useRef(0);
  const [workspaceId, setWorkspaceId] = useState<string>();
  const [objects, setObjects] = useState<ObjectSummary[]>([]);
  const [state, setState] = useState<ProjectState>();
  const [graph, setGraph] = useState<OntologyGraph>();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [query, setQuery] = useState("");
  const [workspaceTab, setWorkspaceTab] = useState<
    "objects" | "relations" | "network" | "conflicts"
  >("objects");
  const [category, setCategory] = useState<LibraryCategory>("ALL");
  const [selectedObjectId, setSelectedObjectId] = useState<string>();
  const [, setSelectedDetail] = useState<ObjectDetail>();
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
          const created =
            await researchosApi.createWorkspace("Research workspace");
          workspaces = [created];
        }
        if (cancelled) return;
        const id = workspaces[0].id;
        setWorkspaceId(id);
        await refresh(id);
      } catch (caught) {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load the API workspace.",
          );
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

  useEffect(() => {
    if (!selectedObjectId) {
      setSelectedDetail(undefined);
      return;
    }
    let cancelled = false;
    void researchosApi
      .getObject(selectedObjectId)
      .then((detail) => {
        if (!cancelled) setSelectedDetail(detail);
      })
      .catch(() => {
        if (!cancelled) setSelectedDetail(undefined);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedObjectId]);

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
          current.map((item) =>
            item.id === itemId ? { ...item, status: "UPLOADING" } : item,
          ),
        );
        try {
          const outcome = await researchosApi.uploadFile(
            batch.id,
            file,
            workspaceId,
          );
          const status = (
            outcome.status === "DUPLICATE" ? "DUPLICATE" : outcome.status
          ) as QueueStatus;
          setQueue((current) =>
            current.map((item) =>
              item.id === itemId
                ? {
                    ...item,
                    status:
                      status === "COMPLETED" || status === "DUPLICATE"
                        ? status
                        : "FAILED",
                    detail:
                      outcome.resolution_status ?? outcome.error ?? undefined,
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
                ? {
                    ...item,
                    status: "FAILED",
                    detail:
                      caught instanceof Error
                        ? caught.message
                        : "Upload failed",
                  }
                : item,
            ),
          );
        }
      }
      await researchosApi.finalizeBatch(batch.id);
      await refresh(workspaceId);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to process the upload batch.",
      );
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

  const visibleObjects = objects.filter(
    (item) => category === "ALL" || categoryFor(item) === category,
  );
  const selectedObject = objects.find(
    (item) => item.object_id === selectedObjectId,
  );
  const categories: Array<{ id: LibraryCategory; label: string }> = [
    { id: "ALL", label: wc(locale, "all") },
    { id: "DOCUMENT", label: wc(locale, "documents") },
    { id: "DATA", label: wc(locale, "data") },
    { id: "NOTE", label: wc(locale, "notes") },
    { id: "PDF", label: "PDF" },
  ];

  const lineageGroups = objects.map((object) => {
    const nodes = [
      ...(graph?.nodes.filter(
        (node) => node.ref.object_id === object.object_id,
      ) ?? []),
    ].sort((left, right) =>
      right.ref.created_at.localeCompare(left.ref.created_at),
    );
    const nodeIds = new Set(nodes.map((node) => node.node_id));
    const edges =
      graph?.edges.filter(
        (edge) => nodeIds.has(edge.source_ref) || nodeIds.has(edge.target_ref),
      ) ?? [];
    return { object, nodes, edges };
  });

  return (
    <div
      className={`workspace-scroll api-workspace ${dragging ? "is-dragging" : ""}`}
      onDragEnter={onWorkspaceDragEnter}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={onWorkspaceDragLeave}
      onDrop={onDrop}
    >
      {dragging && (
        <div className="workspace-drop-overlay" role="status">
          <img src="/brand/evidence-archivist.png" alt="" />
          <b>{wc(locale, "giveArchivist")}</b>
          <span>{wc(locale, "release")}</span>
        </div>
      )}
      <section className="api-workspace-head">
        <div>
          <div className="eyebrow">
            <span className="status-dot green" /> TEAM SPACE · {wc(locale, "synced")}
          </div>
        </div>
        <div className="knowledge-presence">
          <span>TW</span>
          <span>YR</span>
          <span>+3</span>
          <button
            className="button secondary"
            onClick={() => workspaceId && void refresh(workspaceId, query)}
          >
            ↻ {wc(locale, "sync")}
          </button>
        </div>
      </section>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
      >
        <div className="dropzone-icon">↓</div>
        <div>
          <b>{wc(locale, "drop")}</b>
          <small>
            {wc(locale, "dropDetail")} · Markdown, Word, Excel, CSV, PDF, TXT
          </small>
        </div>
        <button
          className="button primary small"
          onClick={(event) => {
            event.stopPropagation();
            inputRef.current?.click();
          }}
        >
          {wc(locale, "choose")}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={onInputChange}
        />
      </div>

      {error && (
        <div className="api-error" role="alert">
          <b>{wc(locale, "apiUnavailable")}</b>
          <span>{error}</span>
          <button
            onClick={() => workspaceId && void refresh(workspaceId, query)}
          >
            {wc(locale, "retry")}
          </button>
        </div>
      )}

      {queue.length > 0 && (
        <section className="upload-queue">
          <div className="upload-summary">
            <div>
              <span className="eyebrow">INGEST RESULTS</span>
              <h2>{wc(locale, "results")}</h2>
              <p>{wc(locale, "resultDetail")}</p>
            </div>
            <div className="ingest-counts">
              <span>
                <b>
                  {queue.filter((item) => item.status === "COMPLETED").length}
                </b>{" "}
                {wc(locale, "stored")}
              </span>
              <span>
                <b>
                  {
                    queue.filter((item) => item.resolution === "NEW_VERSION")
                      .length
                  }
                </b>{" "}
                {wc(locale, "newVersion")}
              </span>
              <span>
                <b>
                  {queue.filter((item) => item.status === "DUPLICATE").length}
                </b>{" "}
                {wc(locale, "deduped")}
              </span>
            </div>
          </div>
          {queue.map((item) => {
            const result = resolutionCopy(item, locale);
            return (
              <div className={`upload-row result-${result.tone}`} key={item.id}>
                <span className="upload-result-icon">{result.icon}</span>
                <span className="upload-result-file">
                  <b>{item.fileName}</b>
                  <small>{result.detail}</small>
                </span>
                <span className="upload-result-state">
                  <strong>{result.label}</strong>
                  {item.versionId && (
                    <small className="mono">{item.versionId}</small>
                  )}
                </span>
              </div>
            );
          })}
        </section>
      )}

      <section className="knowledge-library">
        <div className="library-toolbar">
          <div>
            <span className="eyebrow">LIBRARY</span>
            <h2>
              {workspaceTab === "relations"
                ? wc(locale, "versions")
                : workspaceTab === "network"
                  ? wc(locale, "network")
                  : wc(locale, "files")}
            </h2>
          </div>
          <div className="library-tools">
            <div className="segmented library-view-switch">
              <button
                className={workspaceTab === "objects" ? "active" : ""}
                onClick={() => setWorkspaceTab("objects")}
              >
                {wc(locale, "files")}
              </button>
              <button
                className={workspaceTab === "network" ? "active" : ""}
                onClick={() => setWorkspaceTab("network")}
              >
                {wc(locale, "network")} <em>{objects.length}</em>
              </button>
              <button
                className={workspaceTab === "relations" ? "active" : ""}
                onClick={() => setWorkspaceTab("relations")}
              >
                {wc(locale, "versions")} <em>{graph?.edges.length ?? 0}</em>
              </button>
            </div>
            {workspaceTab === "objects" && (
              <form className="library-search" onSubmit={submitSearch}>
                <span>⌕</span>
                <input
                  aria-label="Search knowledge base"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={wc(locale, "searchPlaceholder")}
                />
                <button>{wc(locale, "search")}</button>
              </form>
            )}
          </div>
        </div>
        {workspaceTab === "objects" && (
          <div className="category-row">
            {categories.map((item) => (
              <button
                key={item.id}
                className={category === item.id ? "active" : ""}
                onClick={() => setCategory(item.id)}
              >
                {item.label}
                <em>
                  {item.id === "ALL"
                    ? objects.length
                    : objects.filter(
                        (object) => categoryFor(object) === item.id,
                      ).length}
                </em>
              </button>
            ))}
          </div>
        )}
        {workspaceTab === "objects" ? (
          <div
            className={`library-layout ${selectedObject ? "has-analysis" : ""}`}
          >
            <div className="file-collection">
              {loading ? (
                <div className="knowledge-empty">{wc(locale, "syncing")}</div>
              ) : visibleObjects.length === 0 ? (
                <button
                  className="knowledge-empty actionable"
                  onClick={() => inputRef.current?.click()}
                >
                  <img src="/brand/evidence-archivist.png" alt="Evidence Archivist" />
                  <b>{wc(locale, "emptyTitle")}</b>
                  <span>{wc(locale, "emptyDetail")}</span>
                </button>
              ) : (
                visibleObjects.map((item) => {
                  const source = sourceFromObject(item);
                  const itemCategory = categoryFor(item);
                  return (
                    <button
                      className={`knowledge-file ${selectedObjectId === item.object_id ? "selected" : ""}`}
                      key={item.object_id}
                      onClick={() => setSelectedObjectId(item.object_id)}
                    >
                      <i
                        className={`knowledge-file-icon kind-${itemCategory.toLowerCase()}`}
                      >
                        {source.formatKind.slice(0, 2)}
                      </i>
                      <span>
                        <b>{item.name}</b>
                        <small>
                          {itemCategory} · {readableBytes(source.sizeBytes)} ·{" "}
                          {item.version_count} {wc(locale, "fileVersions")}
                        </small>
                      </span>
                      <em>{formatDate(source.updatedAt)}</em>
                    </button>
                  );
                })
              )}
            </div>
            {selectedObject && (
              <aside className="quick-analysis">
                <div className="analysis-head">
                  <span>{wc(locale, "analysis")}</span>
                  <button
                    onClick={() => setSelectedObjectId(undefined)}
                    aria-label="Close analysis"
                  >
                    ×
                  </button>
                </div>
                <div className="analysis-file">
                  <i>
                    {selectedObject.current_version?.format_kind.slice(0, 2)}
                  </i>
                  <h3>{selectedObject.name}</h3>
                  <p className="mono">{selectedObject.object_id}</p>
                </div>
                <div className="analysis-summary">
                  <span>{wc(locale, "category")}</span>
                  <b>{categoryFor(selectedObject)}</b>
                  <p>
                    {selectedObject.current_version?.format_kind === "CSV" ||
                    selectedObject.current_version?.format_kind === "XLSX"
                      ? locale === "en" ? "Structured data ready for statistical and model analysis." : locale === "zh-TW" ? "結構化資料檔案，可用於後續統計與模型分析。" : "结构化数据文件，可用于后续统计与模型分析。"
                      : locale === "en" ? "Stored in team search and ready for thesis and evidence relations." : locale === "zh-TW" ? "已安全儲存並納入團隊搜尋，可繼續建立論題與證據關係。" : "已安全保存并纳入团队检索，可继续建立论题与证据关系。"}
                  </p>
                </div>
                <dl>
                  <dt>{wc(locale, "size")}</dt>
                  <dd>
                    {readableBytes(
                      selectedObject.current_version?.size_bytes ?? 0,
                    )}
                  </dd>
                  <dt>{wc(locale, "versions")}</dt>
                  <dd>{selectedObject.version_count}</dd>
                  <dt>{wc(locale, "fragments")}</dt>
                  <dd>{selectedObject.fragment_count}</dd>
                  <dt>{wc(locale, "status")}</dt>
                  <dd>{selectedObject.status}</dd>
                </dl>
                <button
                  className="button primary analysis-action"
                  onClick={() =>
                    window.dispatchEvent(
                      new CustomEvent("researchos:new-thesis", {
                        detail: { name: selectedObject.name },
                      }),
                    )
                  }
                >
                  {wc(locale, "useThesis")}
                </button>
              </aside>
            )}
          </div>
        ) : workspaceTab === "relations" ? (
          <div className="version-structure">
            <div className="lineage-legend">
              <span>
                <i className="current" />
                {wc(locale, "current")}
              </span>
              <span>
                <i />
                {wc(locale, "history")}
              </span>
              <span>
                <b>→</b> NEW_VERSION_OF
              </span>
              <small>{wc(locale, "deterministic")}</small>
            </div>
            {loading ? (
              <div className="knowledge-empty">{wc(locale, "loadingStructure")}</div>
            ) : lineageGroups.length === 0 ? (
              <div className="knowledge-empty">
                <b>{wc(locale, "noStructure")}</b>
                <span>{wc(locale, "firstVersion")}</span>
              </div>
            ) : (
              lineageGroups.map(({ object, nodes, edges }) => (
                <section className="lineage-row" key={object.object_id}>
                  <div className="lineage-object">
                    <i
                      className={`knowledge-file-icon kind-${categoryFor(object).toLowerCase()}`}
                    >
                      {object.current_version?.format_kind.slice(0, 2)}
                    </i>
                    <span>
                      <b>{object.name}</b>
                      <small>
                        {object.version_count} {wc(locale, "fileVersions")} · {edges.length} {wc(locale, "relations")}
                      </small>
                    </span>
                  </div>
                  <div className="lineage-chain">
                    {nodes.map((node, index) => (
                      <div className="lineage-step" key={node.node_id}>
                        <button
                          className={
                            node.ref.version_id === object.current_version_id
                              ? "current"
                              : ""
                          }
                          onClick={() => {
                            setSelectedObjectId(object.object_id);
                            setWorkspaceTab("objects");
                          }}
                        >
                          <span>
                            {node.ref.version_id === object.current_version_id
                              ? "CURRENT"
                              : "HISTORY"}
                          </span>
                          <b>{node.ref.version_id}</b>
                          <small>{formatDate(node.ref.created_at)}</small>
                        </button>
                        {index < nodes.length - 1 && (
                          <i className="lineage-link">
                            <span>NEW_VERSION_OF</span>→
                          </i>
                        )}
                      </div>
                    ))}
                  </div>
                  {edges.length === 0 && object.version_count > 1 && (
                    <span className="lineage-pending">{wc(locale, "syncing")}</span>
                  )}
                </section>
              ))
            )}
          </div>
        ) : (
          <div
            className={`knowledge-network ${selectedObject ? "has-selection" : ""}`}
          >
            <div className="network-map">
              <div className="network-root">
                <span>ResearchOS</span>
                <b>{wc(locale, "teamLibrary")}</b>
                <small>{objects.length} {wc(locale, "fileObjects")}</small>
              </div>
              {loading ? (
                <div className="network-empty">{wc(locale, "buildingNetwork")}</div>
              ) : objects.length === 0 ? (
                <button
                  className="network-empty actionable"
                  onClick={() => inputRef.current?.click()}
                >
                  {wc(locale, "firstNode")}
                </button>
              ) : (
                <div className="network-branches">
                  {objects.map((object) => (
                    <button
                      key={object.object_id}
                      className={`network-node kind-${categoryFor(object).toLowerCase()} ${selectedObjectId === object.object_id ? "selected" : ""}`}
                      onClick={() => setSelectedObjectId(object.object_id)}
                      aria-label={`查看 ${object.name} 的关联`}
                    >
                      <i>{object.current_version?.format_kind.slice(0, 2)}</i>
                      <span>
                        <b>{object.name}</b>
                        <small>
                          {object.version_count} {wc(locale, "versions")} · {object.fragment_count} {wc(locale, "fragments")}
                        </small>
                      </span>
                      <em>{object.version_count}</em>
                    </button>
                  ))}
                </div>
              )}
            </div>
            {selectedObject && (
              <aside className="network-inspector">
                <div className="analysis-head">
                  <span>{wc(locale, "nodeRelations")}</span>
                  <button
                    onClick={() => setSelectedObjectId(undefined)}
                    aria-label="Close network details"
                  >
                    ×
                  </button>
                </div>
                <div className="network-selected">
                  <i
                    className={`knowledge-file-icon kind-${categoryFor(selectedObject).toLowerCase()}`}
                  >
                    {selectedObject.current_version?.format_kind.slice(0, 2)}
                  </i>
                  <span>
                    <b>{selectedObject.name}</b>
                    <small className="mono">{selectedObject.object_id}</small>
                  </span>
                </div>
                <div className="network-facts">
                  <span>
                    <small>{wc(locale, "scope")}</small>
                    <b>{wc(locale, "sameLibrary")}</b>
                  </span>
                  <span>
                    <small>{wc(locale, "current")}</small>
                    <b className="mono">{selectedObject.current_version_id}</b>
                  </span>
                  <span>
                    <small>{wc(locale, "historicalRelations")}</small>
                    <b>
                      {graph?.edges.filter(
                        (edge) =>
                          edge.source_ref.startsWith(
                            `${selectedObject.object_id}@`,
                          ) ||
                          edge.target_ref.startsWith(
                            `${selectedObject.object_id}@`,
                          ),
                      ).length ?? 0}{" "}
                      {wc(locale, "relations")}
                    </b>
                  </span>
                  <span>
                    <small>{wc(locale, "fragments")}</small>
                    <b>{selectedObject.fragment_count}</b>
                  </span>
                </div>
                <div className="network-version-list">
                  <span>VERSION STRUCTURE</span>
                  {lineageGroups
                    .find(
                      (group) =>
                        group.object.object_id === selectedObject.object_id,
                    )
                    ?.nodes.map((node) => (
                      <button
                        key={node.node_id}
                        className={
                          node.ref.version_id ===
                          selectedObject.current_version_id
                            ? "current"
                            : ""
                        }
                        onClick={() => setWorkspaceTab("relations")}
                      >
                        <i />
                        <span>
                          <b>
                            {node.ref.version_id ===
                            selectedObject.current_version_id
                              ? wc(locale, "current")
                              : wc(locale, "history")}
                          </b>
                          <small className="mono">{node.ref.version_id}</small>
                        </span>
                        <em>→</em>
                      </button>
                    ))}
                </div>
                <button
                  className="button secondary network-detail-action"
                  onClick={() => setWorkspaceTab("relations")}
                >
                  {wc(locale, "fullChain")}
                </button>
              </aside>
            )}
          </div>
        )}
      </section>

      <div className="summary-strip api-summary">
        <div>
          <span>Research objects</span>
          <b>{loading ? "…" : objects.length}</b>
        </div>
        <div>
          <span>Versions</span>
          <b>{loading ? "…" : (state?.version_count ?? 0)}</b>
        </div>
        <div>
          <span>Parsed fragments</span>
          <b>{loading ? "…" : (state?.fragment_count ?? 0)}</b>
        </div>
        <div>
          <span>Semantic relations</span>
          <b className="quiet-value">Not in M1</b>
        </div>
      </div>

      <section className="table-section">
        <div className="section-title">
          <div>
            <h2>Research objects</h2>
            <p>Version-pinned source files from the live workspace.</p>
          </div>
          <div className="segmented">
            <button
              className={workspaceTab === "objects" ? "active" : ""}
              onClick={() => setWorkspaceTab("objects")}
            >
              Objects
            </button>
            <button
              className={workspaceTab === "relations" ? "active" : ""}
              onClick={() => setWorkspaceTab("relations")}
            >
              Relations
            </button>
            <button
              className={workspaceTab === "conflicts" ? "active" : ""}
              onClick={() => setWorkspaceTab("conflicts")}
            >
              Conflicts
            </button>
          </div>
        </div>
        <form className="filter-row" onSubmit={submitSearch}>
          <span className="table-search">
            <span>⌕</span>
            <input
              aria-label="Search objects"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter objects…"
            />
          </span>
          <button className="button primary small" type="submit">
            Search
          </button>
        </form>
        {workspaceTab === "objects" ? (
          loading ? (
            <div className="api-empty">Loading the live workspace…</div>
          ) : objects.length === 0 ? (
            <div className="api-empty">
              No assets yet. Drop a research file above to create the first
              object.
            </div>
          ) : (
            <div className="research-table">
              <div className="table-head">
                <span>Name</span>
                <span>Type</span>
                <span>State</span>
                <span>Version</span>
                <span>Updated</span>
              </div>
              {objects.map((item, index) => {
                const source = sourceFromObject(item);
                return (
                  <button
                    className="table-row"
                    key={item.object_id}
                    onClick={() => onSelect(source)}
                  >
                    <span className="name-cell">
                      <i className={`file-icon f${index % 4}`}>
                        {source.formatKind.slice(0, 1)}
                      </i>
                      <span>
                        <b>{source.name}</b>
                        <small className="mono">{source.id}</small>
                      </span>
                    </span>
                    <span>{source.type}</span>
                    <span>
                      <span className="badge badge-blue">{source.state}</span>
                    </span>
                    <span className="mono">{source.version}</span>
                    <span>{formatDate(source.updatedAt)}</span>
                  </button>
                );
              })}
            </div>
          )
        ) : workspaceTab === "relations" ? (
          <div className="api-empty">
            {graph?.edges.length ?? 0} deterministic NEW_VERSION_OF relations.
            Semantic relations arrive in M2.
          </div>
        ) : (
          <div className="api-empty">
            No unresolved deterministic ingest conflicts. Ambiguous logical
            identities remain separate assets.
          </div>
        )}
      </section>

      <section className="relations api-relations">
        <div className="section-title">
          <div>
            <h2>Version structure</h2>
            <p>
              Only deterministic version lineage is shown here. Semantic
              relations arrive in M2.
            </p>
          </div>
          <span className="badge badge-blue">
            {graph?.edges.length ?? 0} system edges
          </span>
        </div>
        {graph?.edges.length ? (
          <div className="api-edge-list">
            {graph.edges.map((edge) => (
              <div className="api-edge" key={edge.edge_id}>
                <span className="mono">{edge.source_ref}</span>
                <b>{edge.relation_type}</b>
                <span className="mono">{edge.target_ref}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="api-empty">No version lineage edges yet.</div>
        )}
      </section>
    </div>
  );
}
