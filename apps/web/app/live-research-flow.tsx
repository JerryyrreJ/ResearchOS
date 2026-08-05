"use client";

import { useState } from "react";
import {
  researchosApi,
  type CompileEnvelope,
  type CompileResult,
  type VersionDiff,
} from "../lib/api-client";
import type { Locale } from "./i18n";

type LiveView = "thesis" | "validation" | "recompile" | "versions";
type Phase = "idle" | "creating" | "compiling" | "running" | "verifying" | "complete" | "failed";

export function buildThesisPayload(thesisId: string, rawClaim: string, languageLevel = "CAUSAL") {
  return {
  contract_version: "0.1.0-frozen",
  thesis_id: thesisId,
  project_id: "PROJ_DEMO",
  version_id: "THESIS_VER_001",
  parent_version_id: null,
  raw_claim: rawClaim,
  normalized_claim: rawClaim,
  as_of_date: "2026-08-04",
  language_level: languageLevel,
  scope: { subject: "US fiscal supply and 10-year Treasury yield", geography: "United States", start_date: null, end_date: "2026-08-04", horizon_text: "持续，尚未定义" },
  definitions: [
    { term: "财政扩张", definition: null, status: "AMBIGUOUS", source_refs: [] },
    { term: "持续", definition: null, status: "MISSING", source_refs: [] },
  ],
  required_evidence_types: ["CAUSAL_IDENTIFIED"],
  falsifier_requirements: ["加入货币条件后关系明显消失", "替换财政供给定义后方向不稳定", "不同估计窗口下结果不稳健"],
  input_object_refs: [{
    contract_version: "0.1.0-frozen", object_id: "DATA_US_TREASURY_10Y", version_id: "VER_DEMO_20260804",
    object_type: "DATASET", name: "10-year Treasury yield demo snapshot", representation: "PARQUET",
    schema_version: "1.0.0", content_hash: "0".repeat(64), license_policy: "PUBLIC", access_scope: "WORKSPACE:WS_DEMO",
    content_uri: "objects/DATA_US_TREASURY_10Y/VER_DEMO_20260804/data.parquet", as_of_date: "2026-08-04",
    data_schema: { time_key: "date", entity_keys: [], value_fields: ["ust10"], frequency: "D", units: { ust10: "percent" }, field_types: { date: "date", ust10: "float64" } },
    lineage_refs: ["SRC_PUBLIC_DEMO"], metadata: { fixture_only: true },
  }],
  metadata: { fixture_only: true },
  };
}

function statusTone(status: string) {
  return status === "COMPLETE" || status === "SUCCESS" || status === "PASS" ? "green" : status === "WARNING" || status === "PARTIAL" ? "amber" : "red";
}

export default function LiveResearchFlow({ view, locale, thesisId = "THESIS_DEMO_001", claim = "美国财政扩张正在持续推高10年期美债收益率。", languageLevel = "CAUSAL" }: { view: LiveView; locale: Locale; thesisId?: string; claim?: string; languageLevel?: string }) {
  const zh = locale !== "en";
  const [phase, setPhase] = useState<Phase>("idle");
  const [compiled, setCompiled] = useState<CompileEnvelope>();
  const [verified, setVerified] = useState<CompileResult>();
  const [versions, setVersions] = useState<CompileResult[]>([]);
  const [diff, setDiff] = useState<VersionDiff>();
  const [error, setError] = useState<string>();
  const thesisPayload = buildThesisPayload(thesisId, claim, languageLevel);

  const runFlow = async () => {
    setError(undefined);
    try {
      setPhase("creating");
      await researchosApi.createThesis(thesisPayload);
      await researchosApi.getThesis(thesisId);
      setPhase("compiling");
      const first = await researchosApi.compileThesis(thesisId);
      setCompiled(first);
      if (first.job_id) await researchosApi.getJobEvents(first.job_id);
      setPhase("running");
      const toolRun = await researchosApi.runMacroTrace(first.tool_request);
      const resolvedToolRun = await researchosApi.getToolRun(toolRun.tool_run_id);
      await Promise.all([
        researchosApi.getToolGraph(toolRun.tool_run_id),
        researchosApi.getToolArtifacts(toolRun.tool_run_id),
      ]);
      setPhase("verifying");
      const verification = await researchosApi.verifyThesis(thesisId, resolvedToolRun.evidence_bundle);
      setVerified(verification.compile_result);
      if (verification.job_id) {
        await researchosApi.getJobEvents(verification.job_id);
      }
      const nextVersions = await researchosApi.listThesisVersions(thesisId);
      setVersions(nextVersions);
      if (nextVersions.length >= 2) {
        setDiff(await researchosApi.getVersionDiff(nextVersions[0].build_id, nextVersions[nextVersions.length - 1].build_id));
      }
      setPhase("complete");
    } catch (caught) {
      setPhase("failed");
      setError(caught instanceof Error ? caught.message : "端到端研究流程执行失败");
    }
  };

  const action = <button className="button primary" disabled={!["idle", "complete", "failed"].includes(phase)} onClick={() => void runFlow()}>{phase === "idle" ? (zh ? "运行完整验证链" : "Run full validation") : phase === "complete" ? (zh ? "重新运行" : "Run again") : phase === "failed" ? (zh ? "重试" : "Retry") : (zh ? "正在执行…" : "Running…")}</button>;
  const header = <section className="live-flow-header"><div><span className="eyebrow"><span className="status-dot green"/> 真实接口 · A + B + C</span><h2>{zh ? "端到端研究编译" : "End-to-end research compilation"}</h2><p>{zh ? "真实接口串联论题编译器、MacroTrace、证据验证与版本差异。" : "Live REST calls connect Thesis Compiler, MacroTrace, evidence verification, and version diff."}</p></div>{action}</section>;
  const progress = <div className="live-progress" aria-label="研究流程进度">{["creating", "compiling", "running", "verifying", "complete"].map((step, index) => <span key={step} className={phase === "complete" || ["creating", "compiling", "running", "verifying", "complete"].indexOf(phase) >= index ? "done" : ""}>{index + 1}<small>{["建立论题", "编译", "MacroTrace", "验证", "差异"][index]}</small></span>)}</div>;

  let body;
  if (view === "thesis") body = <><section className="live-thesis"><span className="eyebrow">论题 · 请求等级 {languageLevel}</span><h1>{claim}</h1><p>{verified?.compiled_claim ?? compiled?.compile_result.compiled_claim ?? (zh ? "尚未编译。运行验证后，证据会约束这里的语言。" : "Not compiled yet. Evidence will constrain this language after validation.")}</p></section><section className="live-issue-list">{(verified ?? compiled?.compile_result)?.issues.map(issue => <div key={issue.code}><span className={`badge badge-${issue.blocking ? "red" : "amber"}`}>{issue.code}</span><b>{issue.message}</b><small>{issue.suggested_actions[0]}</small></div>) ?? <div className="api-empty">{zh ? "等待真实编译结果。" : "Waiting for a live compile result."}</div>}</section></>;
  if (view === "validation") body = <section className="live-protocol">{(verified ?? compiled?.compile_result)?.validation_plan.map((step, index) => <div key={step.step_id}><i>{String(index + 1).padStart(2, "0")}</i><span><b>{step.label}</b><small className="mono">{step.step_id}</small></span><em className={`badge badge-${statusTone(step.status)}`}>{step.status}</em></div>) ?? <div className="api-empty">{zh ? "运行后载入后端生成的验证计划。" : "Run the flow to load the backend validation plan."}</div>}</section>;
  if (view === "recompile") body = <section className="semantic-diff"><div><span>修改前</span><p>{compiled?.compile_result.original_claim ?? thesisPayload.raw_claim}</p></div><i>→</i><div className="after"><span>修改后 · {verified?.language_policy.allowed_level ?? "待验证"}</span><p>{verified?.compiled_claim ?? (zh ? "等待证据包…" : "Waiting for EvidenceBundle…")}</p></div></section>;
  if (view === "versions") body = <><section className="version-header"><div><span className="eyebrow">实时版本差异</span><h2>{versions[0]?.build_id ?? "—"} <span>→</span> {versions.at(-1)?.build_id ?? "—"}</h2><p>{diff?.summary ?? (zh ? "运行后生成不可变编译版本差异。" : "Run to generate the immutable build diff.")}</p></div></section><div className="diff-groups"><section className="diff-group changed"><div><span>已变更</span><b>{diff?.changed_objects.length ?? 0}</b></div>{diff?.changed_objects.map(item => <button key={item.field}><i>△</i><span><b>{item.field}</b><small>由论题编译器重新计算</small></span><em>→</em></button>)}</section><section className="diff-group reused"><div><span>已复用</span><b>{diff?.reused_refs.length ?? 0}</b></div>{diff?.reused_refs.map(item => <button key={item}><i>✓</i><span><b>{item}</b><small>固定引用未发生变化</small></span></button>)}</section></div></>;

  return <div className="workspace-scroll live-research-flow">{header}{progress}{error && <div className="api-error" role="alert"><b>流程连接失败</b><span>{error}</span></div>}{body}</div>;
}
