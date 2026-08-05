"use client";

import { useEffect, useRef, useState } from "react";

export type MacroTraceContext = {
  question?: string;
  thesisId?: string;
  workspaceId?: string;
};

type MacroTraceEvent = {
  type: "researchos:macrotrace-ready" | "researchos:macrotrace-run-complete";
  payload?: { jobId?: string; status?: string; question?: string };
};

function configuredMacroTraceUrl() {
  const configured = process.env.NEXT_PUBLIC_MACROTRACE_UI_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  // `start.ps1` deliberately starts the original B product on this address.
  return "http://127.0.0.1:8000";
}

export default function MacroTraceWorkbench({ context, onBack, onRunComplete }: {
  context?: MacroTraceContext;
  onBack: () => void;
  onRunComplete?: (event: Required<Pick<MacroTraceEvent, "payload">>["payload"]) => void;
}) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);
  const [frameError, setFrameError] = useState(false);
  const baseUrl = configuredMacroTraceUrl();
  const expectedOrigin = new URL(baseUrl).origin;
  const url = new URL(baseUrl);
  url.searchParams.set("embed", "1");
  if (typeof window !== "undefined") url.searchParams.set("parent_origin", window.location.origin);
  if (context?.question) url.searchParams.set("question", context.question);
  if (context?.thesisId) url.searchParams.set("thesis_id", context.thesisId);
  if (context?.workspaceId) url.searchParams.set("workspace_id", context.workspaceId);
  const source = url.toString();

  useEffect(() => {
    const receive = (event: MessageEvent<MacroTraceEvent>) => {
      if (event.origin !== expectedOrigin || event.source !== frame.current?.contentWindow) return;
      if (event.data?.type === "researchos:macrotrace-ready") setReady(true);
      if (event.data?.type === "researchos:macrotrace-run-complete") {
        onRunComplete?.(event.data.payload ?? {});
      }
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, [expectedOrigin, onRunComplete]);

  return <section className="macrotrace-workbench" aria-label="MacroTrace original workbench">
    <header className="macrotrace-bridge-bar">
      <div>
        <span className="macrotrace-bridge-label">B · ORIGINAL MACROTRACE</span>
        <strong>实证研究工作台</strong>
        <small>{ready ? "已连接 B 的原始研究图与诊断界面" : "正在连接 B 的原始研究图与诊断界面…"}</small>
      </div>
      <div className="macrotrace-bridge-actions">
        {context?.thesisId && <span className="macrotrace-context">论题 {context.thesisId}</span>}
        <button className="button secondary" onClick={onBack}>← 返回研究助手</button>
      </div>
    </header>
    {frameError && <div className="macrotrace-frame-error" role="alert"><b>无法载入 MacroTrace 原始工作台。</b><span>请确认 B 后端已在 {baseUrl} 启动，然后刷新此页。</span></div>}
    <iframe
      ref={frame}
      className="macrotrace-original-frame"
      title="MacroTrace original research workbench"
      src={source}
      onLoad={() => setFrameError(false)}
      onError={() => setFrameError(true)}
      allow="clipboard-write"
    />
  </section>;
}
