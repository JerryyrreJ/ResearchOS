"use client";

import { useEffect, useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { QRCodeSVG } from "qrcode.react";
import { localeNames, tx, type Locale } from "./i18n";
import RealWorkspace from "./real-workspace";
import LiveResearchFlow, { buildThesisPayload } from "./live-research-flow";
import type { WorkspaceSource } from "../lib/api-client";
import { researchosApi } from "../lib/api-client";

type View = "thesis" | "workspace" | "validation" | "macrotrace" | "recompile" | "versions";
type Theme = "light" | "dark" | "system" | "contrast";
type RuntimeMode = "fixture" | "offline" | "real";
type DemoScenario = "complete" | "queued" | "running" | "partial" | "failed" | "cancelled" | "permission" | "timeout" | "unknown";
type SourceItem = {
  type: string;
  name: string;
  id: string;
  version: string;
  state: string;
  origin?: "fixture" | "api";
  formatKind?: string;
  sizeBytes?: number;
  fragmentCount?: number;
  versionCount?: number;
  updatedAt?: string;
};

const nav: { id: View; icon: string; label: string; meta?: string }[] = [
  { id: "workspace", icon: "⌘", label: "Workspace", meta: "12" },
  { id: "thesis", icon: "◇", label: "Thesis Build", meta: "1" },
  { id: "validation", icon: "✓", label: "Validation Plan", meta: "2/2" },
  { id: "macrotrace", icon: "↳", label: "MacroTrace", meta: "Complete" },
  { id: "recompile", icon: "⇄", label: "Recompile" },
  { id: "versions", icon: "⑂", label: "Version Diff", meta: "v2" },
];

const sources: SourceItem[] = [
  { type: "DATASET", name: "10-year Treasury yield demo snapshot", id: "DATA_US_TREASURY_10Y", version: "VER_DEMO_20260804", state: "CONFIRMED", origin: "fixture" },
  { type: "DOCUMENT", name: "Fiscal supply definition notes", id: "DOC_PRODUCT_V2", version: "v2", state: "AI_PROPOSED", origin: "fixture" },
  { type: "THESIS", name: "US fiscal expansion and 10Y yield", id: "THESIS_DEMO_001", version: "v2", state: "CONFIRMED", origin: "fixture" },
  { type: "EVIDENCE", name: "MacroTrace associational bundle", id: "EVIDENCE_DEMO_001", version: "0.1.0", state: "CONFIRMED", origin: "fixture" },
];

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "green" | "amber" | "red" | "blue" | "purple" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function BrandMark({ inverse = false, large = false }: { inverse?: boolean; large?: boolean }) {
  return <span className={`researchos-mark ${inverse ? "inverse" : ""} ${large ? "large" : ""}`} aria-hidden="true"><i/><i/><i/><b/></span>;
}

function LocaleSwitcher({ locale, onChange, compact = false }: { locale: Locale; onChange: (locale: Locale) => void; compact?: boolean }) {
  return <label className={`locale-switcher ${compact ? "compact" : ""}`}><span className="sr-only">Language</span><select value={locale} onChange={e=>onChange(e.target.value as Locale)} aria-label="Language">{(Object.keys(localeNames) as Locale[]).map(key=><option value={key} key={key}>{localeNames[key]}</option>)}</select><i>⌄</i></label>;
}

function Topbar({ title, subtitle, onCommand, onInspector, onSettings, locale, onLocale, mode }: { title: string; subtitle: string; onCommand: () => void; onInspector: () => void; onSettings: () => void; locale: Locale; onLocale: (locale: Locale) => void; mode: RuntimeMode }) {
  return (
    <header className="topbar">
      <div className="breadcrumbs"><span>{tx(locale,"Fiscal transmission study")}</span><i>/</i><strong>{tx(locale,title)}</strong></div>
      <div className="top-actions">
        <button className="mode-trigger" onClick={onSettings}><Badge tone={mode==="offline"?"blue":mode==="real"?"green":"amber"}>{mode==="offline"?"OFFLINE REPLAY":mode==="real"?"REAL API · A+B+C":"FIXTURE MODE"}</Badge></button>
        <LocaleSwitcher locale={locale} onChange={onLocale} compact/>
        <button className="command-trigger" onClick={onCommand}><span>{tx(locale,"Search or command")}</span><kbd>⌘ K</kbd></button>
        <button className="inspector-trigger" onClick={onInspector} aria-label={tx(locale,"Inspector")}>⌘</button>
        <button className="avatar" onClick={onSettings} aria-label="Settings and extensions">TW</button>
      </div>
      <div className="page-heading"><div><h1>{tx(locale,title)}</h1><p>{tx(locale,subtitle)}</p></div><div className="heading-actions"><button className="button secondary">{tx(locale,"Share")}</button><button className="button primary">{tx(locale,"Compile thesis")} <span>⌘↵</span></button></div></div>
    </header>
  );
}

function Inspector({ selectedSource, locale }: { selectedSource?: SourceItem; locale: Locale }) {
  const item = selectedSource ?? sources[2];
  const isApi = item.origin === "api";
  return (
    <aside className="inspector">
      <div className="inspector-head"><span>{tx(locale,"Inspector")}</span><button aria-label="Close inspector">×</button></div>
      <section className="inspector-section">
        <div className="object-mark">{item.type.slice(0, 2)}</div>
        <h3>{item.name}</h3><p className="mono quiet">{item.id}</p>
        <div className="inspector-badges"><Badge tone={isApi ? "blue" : item.state === "AI_PROPOSED" ? "purple" : "green"}>{item.state}</Badge><Badge>{item.type}</Badge></div>
      </section>
      <section className="inspector-section properties">
        <h4>{tx(locale,"Properties")}</h4>
        <dl><dt>Version</dt><dd>{item.version}</dd><dt>Updated</dt><dd>{item.updatedAt ? new Date(item.updatedAt).toLocaleDateString() : "Aug 04, 2026"}</dd><dt>Access</dt><dd>Workspace</dd><dt>Contract</dt><dd>{isApi ? "0.1.0-m1" : "0.1.0-frozen"}</dd></dl>
      </section>
      <section className="inspector-section"><h4>{tx(locale,"Traceability")}</h4><div className="trace-stack"><div><i className="trace-dot source"/><span>Source object</span><small>{isApi ? `${item.versionCount ?? 1} version(s) · ${item.formatKind ?? "UNKNOWN"}` : "Version pinned"}</small></div>{isApi ? <div><i className="trace-line"/><span>Parsed fragments</span><small>{item.fragmentCount ?? 0} deterministic fragments</small></div> : <><div><i className="trace-line"/><span>Evidence bundle</span><small>Associational</small></div><div><i className="trace-dot thesis"/><span>Compiled thesis</span><small>Language weakened</small></div></>}</div></section>
      <section className="inspector-section"><h4>{tx(locale,"Provenance")}</h4><button className="source-link"><span>↗</span><div><b>{isApi ? "Open live asset details" : tx(locale,"Open frozen fixture")}</b><small>{isApi ? "M1 object projection" : "sample_thesis_build.json"}</small></div></button></section>
    </aside>
  );
}

function InspectorDrawer({ open, onOpenChange, selectedSource, locale }: { open: boolean; onOpenChange: (open: boolean) => void; selectedSource?: SourceItem; locale: Locale }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="drawer-overlay"/><Dialog.Content className="drawer-content"><Dialog.Title className="sr-only">{tx(locale,"Inspector")}</Dialog.Title><Dialog.Close className="drawer-close" aria-label="Close">×</Dialog.Close><Inspector selectedSource={selectedSource} locale={locale}/></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function SettingsCenter({ open, onOpenChange, theme, onTheme, locale, onLocale, reducedMotion, onReducedMotion, mode, onMode, scenario, onScenario, onReset }: { open: boolean; onOpenChange: (open: boolean) => void; theme: Theme; onTheme: (theme: Theme) => void; locale: Locale; onLocale: (locale: Locale) => void; reducedMotion: boolean; onReducedMotion: (value: boolean) => void; mode: RuntimeMode; onMode: (mode: RuntimeMode) => void; scenario: DemoScenario; onScenario: (scenario: DemoScenario) => void; onReset: () => void }) {
  const [tab, setTab] = useState<"appearance" | "demo" | "extensions" | "about">("appearance");
  const themes: { id: Theme; label: string }[] = [{id:"light",label:"Light"},{id:"dark",label:"Dark"},{id:"system",label:"System"},{id:"contrast",label:"High contrast"}];
  const extensions = [
    { mark:"MT", name:"MacroTrace", detail:"Registered empirical execution", state:"ENABLED", tone:"green" as const },
    { mark:"ZT", name:"Zotero", detail:"Reference library connector", state:"AVAILABLE", tone:"blue" as const },
    { mark:"OA", name:"OpenAlex", detail:"Scholarly works and citations", state:"AVAILABLE", tone:"blue" as const },
    { mark:"IF", name:"iFind", detail:"Institution-controlled data source", state:"RESTRICTED", tone:"amber" as const },
  ];
  const scenarios: { id: DemoScenario; label: string }[] = [{id:"complete",label:"Complete"},{id:"queued",label:"Queued"},{id:"running",label:"Running"},{id:"partial",label:"Partial"},{id:"failed",label:"Failed"},{id:"cancelled",label:"Cancelled"},{id:"permission",label:"Permission blocked"},{id:"timeout",label:"Model timeout"},{id:"unknown",label:"Unknown state"}];
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="settings-overlay"/><Dialog.Content className="settings-center"><Dialog.Title className="settings-title">Settings</Dialog.Title><Dialog.Description className="settings-description">Workspace preferences, demo controls, and registered extensions</Dialog.Description><Dialog.Close className="settings-close" aria-label="Close">×</Dialog.Close><div className="settings-layout"><nav className="settings-nav"><div className="settings-brand"><BrandMark/><span><b>ResearchOS</b><small>Workspace settings</small></span></div>{([['appearance','Appearance','◐'],['demo','Demo & status','▷'],['extensions','Extensions','⌘'],['about','About','◇']] as const).map(([id,label,icon])=><button key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}><i>{icon}</i>{label}{id==='extensions'&&<em>4</em>}</button>)}</nav><section className="settings-content">
    {tab==="appearance"&&<><div className="settings-head"><span>INTERFACE</span><h2>Appearance</h2><p>Choose how ResearchOS looks and behaves on this device.</p></div><div className="setting-block"><div><h3>Color theme</h3><p>System follows your operating-system preference.</p></div><div className="theme-grid">{themes.map(item=><button key={item.id} className={`theme-choice theme-${item.id} ${theme===item.id?'selected':''}`} onClick={()=>onTheme(item.id)} aria-pressed={theme===item.id}><span><i/><i/><i/></span><b>{item.label}</b><em>{theme===item.id?'✓':''}</em></button>)}</div></div><div className="setting-row"><div><h3>Language</h3><p>简体中文、繁體中文 and English.</p></div><LocaleSwitcher locale={locale} onChange={onLocale}/></div><div className="setting-row"><div><h3>Reduce motion</h3><p>Limits non-essential transitions and pulses.</p></div><button className={`switch ${reducedMotion?'on':''}`} onClick={()=>onReducedMotion(!reducedMotion)} role="switch" aria-checked={reducedMotion}><i/></button></div></>}
    {tab==="extensions"&&<><div className="settings-head"><span>REGISTERED CAPABILITIES</span><h2>Extension Center</h2><p>Extensions declare capabilities; installation never changes frozen research contracts.</p></div><div className="extension-notice"><i>◇</i><span><b>Catalog preview</b><small>Only MacroTrace is active. Other connectors require a reviewed integration contract.</small></span></div><div className="extension-list">{extensions.map(ext=><div className="extension-row" key={ext.name}><span className="extension-mark">{ext.mark}</span><span><b>{ext.name}</b><small>{ext.detail}</small></span><Badge tone={ext.tone}>{ext.state}</Badge><button>{ext.state==="ENABLED"?'Manage':'Request'}</button></div>)}</div></>}
    {tab==="demo"&&<><div className="settings-head"><span>DELIVERY CONTROL</span><h2>Demo & status</h2><p>Switch between honest data modes and verify every asynchronous failure state.</p></div><div className="mode-grid"><button className={mode==="fixture"?"selected":""} onClick={()=>onMode("fixture")}><Badge tone="amber">FIXTURE</Badge><b>Frozen contracts</b><small>Deterministic golden project</small></button><button className={mode==="offline"?"selected":""} onClick={()=>onMode("offline")}><Badge tone="blue">OFFLINE REPLAY</Badge><b>Cached fixture replay</b><small>No live API claims</small></button><button className={mode==="real"?"selected":""} onClick={()=>onMode("real")}><Badge tone="green">REAL API</Badge><b>Unified A + B + C API</b><small>Assets, compiler, MacroTrace, evidence and version diff</small></button></div><p className="integration-note"><b>Integrated producer APIs:</b> A asset foundation, B MacroTrace adapter, and C Thesis Compiler now share one browser API. MacroTrace still identifies itself as FIXTURE until its producer enables empirical execution.</p><div className="scenario-block"><h3>Async state simulator</h3><p>Visible QA controls; these never alter contract fixtures.</p><div className="scenario-grid">{scenarios.map(item=><button key={item.id} className={scenario===item.id?"active":""} onClick={()=>onScenario(item.id)}>{item.label}</button>)}</div></div><div className="demo-tools"><div className="qr-card"><QRCodeSVG value="https://researchos-evidence-workspace.ztian9080.chatgpt.site/" size={92} bgColor="transparent" fgColor="currentColor" level="M"/><span><b>Mobile demo entry</b><small>Scan to open the private production route.</small></span></div><button className="button secondary" onClick={onReset}>↻ Reset golden project</button></div></>}
    {tab==="about"&&<><div className="settings-head"><span>PRODUCT IDENTITY</span><h2>Evidence becomes structure.</h2><p>ResearchOS is an evidence-driven research IDE, not a conversational dashboard.</p></div><div className="identity-card"><BrandMark large/><div><b>研构 · ResearchOS</b><small>Contract fixture · 0.1.0-frozen</small></div></div><dl className="about-list"><dt>Workspace</dt><dd>Fiscal transmission study</dd><dt>Object model</dt><dd>Thesis · Evidence · Source · Validation · Model Run · Version</dd><dt>Build</dt><dd className="mono">D-FRONTEND / 2026.08</dd></dl></>}
  </section></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function RuntimeNotice({ mode, scenario, onRetry, onReset }: { mode: RuntimeMode; scenario: DemoScenario; onRetry: () => void; onReset: () => void }) {
  if (scenario==="complete" && mode==="fixture") return null;
  const copy: Record<DemoScenario,{title:string;detail:string;action?:string}> = {
    complete:{title:mode==="offline"?"Offline replay ready":"Run complete",detail:mode==="offline"?"Showing a pinned cached result. No live request was made.":"The registered fixture completed."},
    queued:{title:"Run queued",detail:"The request is registered and waiting for an execution slot."},
    running:{title:"MacroTrace is running",detail:"Live progress is simulated for UI validation; the frozen result remains unchanged."},
    partial:{title:"Partial evidence available",detail:"One artifact is available, but diagnostics are incomplete. Do not compile a final conclusion.",action:"Inspect partial result"},
    failed:{title:"Model run failed",detail:"No evidence bundle was produced. Review diagnostics before retrying.",action:"Retry fixture run"},
    cancelled:{title:"Run cancelled",detail:"Execution stopped before evidence generation. Previous results are not substituted.",action:"Start new run"},
    permission:{title:"Permission blocked",detail:"Your workspace role cannot access this source. Request access from the source owner.",action:"Request access"},
    timeout:{title:"Model timeout",detail:"MacroTrace exceeded the 180 second limit. The last successful result is marked stale and is not reused.",action:"Replay cached run"},
    unknown:{title:"Unsupported backend state",detail:"ResearchOS received an unknown enum and stopped rendering this result safely.",action:"Copy diagnostic"},
  };
  const item=copy[scenario];
  return <div className={`runtime-notice state-${scenario}`} role={scenario==="failed"||scenario==="unknown"?"alert":"status"}><span className="runtime-icon">{scenario==="running"?"↻":scenario==="complete"?"✓":scenario==="queued"?"⋯":"!"}</span><span><b>{item.title}</b><small>{item.detail}</small></span>{item.action&&<button onClick={onRetry}>{item.action}</button>}<button className="notice-close" onClick={onReset} aria-label="Reset status">×</button></div>;
}

function ThesisView({ locale }: { locale: Locale }) {
  const [collapsed, setCollapsed] = useState(false);
  return <div className="workspace-scroll thesis-view">
    <section className="thesis-hero">
      <div className="eyebrow"><span className="status-dot red"/> BUILD FAILED <span className="mono">BUILD_DEMO_001</span></div>
      <blockquote>美国财政扩张正在持续推高<br/>10年期美债收益率。</blockquote>
      <div className="thesis-meta"><span>As of <b>Aug 04, 2026</b></span><span>Requested language <Badge tone="red">CAUSAL</Badge></span><span>Version <b>THESIS_VER_001</b></span></div>
    </section>
    <section className="issues-section">
      <div className="section-title"><div><h2>{tx(locale,"Compile issues")}</h2><p>{tx(locale,"5 constraints prevent this thesis from compiling.")}</p></div><button className="text-button" onClick={()=>setCollapsed(value=>!value)}>{collapsed ? "Expand all" : tx(locale,"Collapse all")}</button></div>
      {!collapsed&&<div className="issue-list">
        {[
          ["DEF001", "Definition is not frozen", "“财政扩张” has no operational definition or source reference.", "Define term", "error"],
          ["HORIZON001", "Time horizon is unresolved", "“持续” does not specify a start date, end date, or evaluation window.", "Set window", "error"],
          ["CLAIM_LANG001", "Evidence level cannot support causal wording", "Required CAUSAL_IDENTIFIED evidence is not available. Current evidence is ASSOCIATIONAL.", "Review language", "error"],
          ["VAR001", "Competing explanations are missing", "Monetary conditions and term-premium controls must be addressed.", "Add controls", "warn"],
          ["FALS001", "Falsification criteria need confirmation", "Three candidate falsifiers are present but not yet confirmed.", "Confirm criteria", "warn"],
        ].map(([code,title,detail,action,tone], i) => <div className="issue-row" key={code}>
          <div className={`issue-icon ${tone}`}>{tone === "error" ? "!" : "·"}</div><div className="issue-body"><div><span className="mono issue-code">{code}</span><h3>{tx(locale,title)}</h3></div><p>{detail}</p></div><div className="issue-side"><Badge tone={i < 3 ? "red" : "amber"}>{tx(locale,i < 3 ? "BLOCKING" : "WARNING")}</Badge><button>{tx(locale,action)} →</button></div>
        </div>)}
      </div>}
    </section>
    <section className="validation-preview"><div><span className="eyebrow">{tx(locale,"NEXT REQUIRED ACTION")}</span><h2>{tx(locale,"Run the registered validation protocol")}</h2><p>Freeze definitions, execute MacroTrace, then recompile under the evidence language policy.</p></div><button className="button primary">{tx(locale,"Open validation plan")} →</button></section>
  </div>;
}

function WorkspaceView({ onSelect }: { onSelect: (item: SourceItem) => void }) {
  return <div className="workspace-scroll"><div className="summary-strip"><div><span>Research objects</span><b>12</b></div><div><span>Relations</span><b>18</b></div><div><span>Open conflicts</span><b className="amber-text">2</b></div><div><span>Context packs</span><b>4</b></div></div>
    <section className="table-section"><div className="section-title"><div><h2>Research objects</h2><p>Versioned sources, claims, and evidence in this workspace.</p></div><div className="segmented"><button className="active">Objects</button><button>Relations</button><button>Conflicts</button></div></div>
      <div className="filter-row"><button>All types⌄</button><button>All states⌄</button><span className="table-search">⌕ Filter objects…</span><button className="button primary small">＋ Add source</button></div>
      <div className="research-table"><div className="table-head"><span>Name</span><span>Type</span><span>State</span><span>Version</span><span>Updated</span></div>{sources.map((s,i)=><button className="table-row" key={s.id} onClick={()=>onSelect(s)}><span className="name-cell"><i className={`file-icon f${i}`}>{s.type.slice(0,1)}</i><span><b>{s.name}</b><small className="mono">{s.id}</small></span></span><span>{s.type}</span><span><Badge tone={s.state === "AI_PROPOSED" ? "purple" : "green"}>{s.state}</Badge></span><span className="mono">{s.version}</span><span>Today</span></button>)}</div>
    </section>
    <section className="relations"><div className="section-title"><div><h2>Evidence structure</h2><p>Confirmed and proposed dependencies among active research objects.</p></div><button className="text-button">View as table →</button></div><div className="relation-map"><div className="relation-node source-node"><small>SOURCE</small><b>Treasury 10Y</b><span>VER_DEMO_20260804</span></div><div className="relation-edge"><span>INPUT TO</span></div><div className="relation-node model-node"><small>MODEL RUN</small><b>M.BRIDGE_OLS.V1</b><span>SUCCESS</span></div><div className="relation-edge"><span>SUPPORTS</span></div><div className="relation-node thesis-node"><small>THESIS</small><b>Fiscal transmission</b><span>WEAKENED</span></div></div></section>
  </div>;
}

function ValidationView() {
  const steps = [
    ["01","Freeze research definitions","Define fiscal supply, evaluation window, competing explanations, and falsifiers.","COMPLETE"],
    ["02","Resolve pinned source versions","Lock the Treasury yield snapshot to VER_DEMO_20260804.","COMPLETE"],
    ["03","Run registered empirical tool","Execute MacroTrace workflow RATES_TRANSMISSION using the frozen ToolRequest.","COMPLETE"],
    ["04","Apply evidence language policy","Compare ASSOCIATIONAL output against the requested CAUSAL language level.","READY"],
    ["05","Recompile and produce diff","Create a new thesis version without overwriting the active object.","QUEUED"],
  ];
  return <div className="workspace-scroll protocol"><div className="protocol-intro"><div><span className="eyebrow">REGISTERED PROTOCOL · VP-001</span><h2>Fiscal supply → Treasury yield</h2><p>A deterministic validation path from frozen definitions to evidence-bounded language.</p></div><div className="progress-ring"><b>80%</b><span>complete</span></div></div><div className="protocol-track">{steps.map(([n,title,desc,state],i)=><div className={`protocol-step ${state.toLowerCase()}`} key={n}><div className="step-rail"><span>{state === "COMPLETE" ? "✓" : n}</span>{i < steps.length-1 && <i/>}</div><div className="step-content"><div><h3>{title}</h3><p>{desc}</p></div><Badge tone={state === "COMPLETE" ? "green" : state === "READY" ? "blue" : "neutral"}>{state}</Badge>{i===2 && <div className="step-detail"><dl><dt>Tool</dt><dd>MACROTRACE</dd><dt>Request</dt><dd className="mono">TOOL_REQ_DEMO_001</dd><dt>Evidence</dt><dd>ASSOCIATIONAL</dd><dt>Timeout</dt><dd>180 sec</dd></dl><button className="button secondary">Inspect run →</button></div>}</div></div>)}</div></div>;
}

function MacroTraceView() {
  return <div className="workspace-scroll macro-view"><div className="run-header"><div><span className="eyebrow"><span className="status-dot green"/> RUN COMPLETE</span><h2>RATES_TRANSMISSION</h2><p className="mono">JOB_FIXTURE_001 · M.BRIDGE_OLS.V1</p></div><div className="run-time"><span>Duration</span><b>02:14</b><button className="button secondary">↻ Replay run</button></div></div>
    <div className="technical-tabs"><button className="active">Results</button><button>Parameters</button><button>Diagnostics <Badge tone="green">PASS</Badge></button><button>Artifacts</button></div>
    <section className="result-primary"><div><span className="eyebrow">ENGINE EVIDENCE</span><h2>Conditional association detected</h2><p>The registered model returns associational evidence only. This fixture asserts no empirical value and cannot support independent causal language.</p></div><div className="evidence-grade"><span>Evidence type</span><b>ASSOCIATIONAL</b><small>Language ceiling</small><strong>Association only</strong></div></section>
    <div className="technical-grid"><section><div className="section-kicker"><span>Model output</span><Badge tone="green">SUCCESS</Badge></div><div className="terminal-output"><div><span>recipe</span><b>M.BRIDGE_OLS.V1</b></div><div><span>registry</span><b>macrotrace-fixture</b></div><div><span>coverage</span><b>FULL</b></div><div><span>result hash</span><b className="mono">22222222…2222</b></div></div></section><section><div className="section-kicker"><span>Diagnostic</span><Badge tone="green">PASS</Badge></div><div className="diagnostic"><div className="diag-line"><span>Model-specific diagnostic</span><b>Passed</b></div><p>Fixture only; replace with real diagnostic output.</p><div className="metric-line"><span>Blocking</span><b>No</b></div><div className="metric-line"><span>Trace</span><b className="mono">TRACE_FIXTURE_001</b></div></div></section></div>
    <section className="limitations"><div className="limit-icon">!</div><div><h3>Evidence boundary</h3><ul><li>This is a contract fixture and contains no real empirical conclusion.</li><li>Associational evidence cannot support causal wording.</li></ul></div><button className="text-button">Open Evidence Bundle →</button></section>
  </div>;
}

function RecompileView() {
  return <div className="workspace-scroll recompile"><section className="recompile-head"><span className="eyebrow">SEMANTIC RECOMPILE · THESIS_VER_002</span><h2>Evidence changed what the thesis may claim.</h2><p>The original meaning is preserved where supported; unsupported causal force is removed.</p></section><section className="semantic-diff"><div className="diff-labels"><span>BEFORE · CAUSAL</span><span>AFTER · ASSOCIATIONAL</span></div><div className="claim-before">美国财政扩张正在持续<del>推高</del>10年期美债收益率。</div><div className="diff-connector"><span>Evidence language policy</span><i>↓</i></div><div className="claim-after">当前注册模型提供财政供给指标与10年期美债收益率的<ins>条件关联证据</ins>；现有证据<ins>不足以支持持续、独立的因果措辞</ins>。</div></section><section className="change-rationale"><div className="section-title"><div><h2>Why the language changed</h2><p>Each edit is traceable to a contract value or compile issue.</p></div><Badge tone="green">SUPPORTED</Badge></div><div className="rationale-row"><span className="change-marker removed">−</span><div><h3>“推高” removed</h3><p>Requested level <b>CAUSAL</b> exceeds the bundle&apos;s <b>ASSOCIATIONAL</b> evidence type.</p></div><span className="mono">CLAIM_LANG001</span></div><div className="rationale-row"><span className="change-marker added">＋</span><div><h3>Evidence boundary added</h3><p>The compiled claim now states the supported association and its explicit limitation.</p></div><span className="mono">EVIDENCE_DEMO_001</span></div></section><div className="recompile-actions"><button className="button secondary">Keep previous version</button><button className="button primary">Accept as new version →</button></div></div>;
}

function VersionView() {
  const groups = [["Changed","2","purple",["Thesis language level","Normalized claim"]],["Recomputed","1","blue",["RUN_FIXTURE_001"]],["Reused","1","green",["DATA_US_TREASURY_10Y"]],["Invalidated","0","neutral",["No objects invalidated"]]] as const;
  return <div className="workspace-scroll versions"><div className="version-header"><div><span className="eyebrow">VERSION COMPARISON</span><h2>THESIS_VER_001 <span>→</span> THESIS_VER_002</h2><p>The causal claim was downgraded after associational evidence was added.</p></div><button className="button secondary">Export diff</button></div><div className="version-timeline"><span className="v-dot old">v1</span><i/><div><b>MacroTrace evidence added</b><small>EVIDENCE_DEMO_001 · ASSOCIATIONAL</small></div><i/><span className="v-dot new">v2</span></div><div className="diff-groups">{groups.map(([title,count,tone,items])=><section key={title} className={`diff-group ${tone}`}><div><span>{title}</span><b>{count}</b></div>{items.map((item)=><button key={item}><i>{title === "Changed" ? "△" : title === "Recomputed" ? "↻" : title === "Reused" ? "✓" : "—"}</i><span><b>{item}</b><small>{title === "Changed" ? "Modified in THESIS_VER_002" : title === "Recomputed" ? "Affected by new evidence" : title === "Reused" ? "Pinned version unchanged" : "No downstream impact"}</small></span><em>→</em></button>)}</section>)}</div><section className="impact-summary"><div><span>Conclusion</span><b>SUPPORTED</b></div><div><span>Model runs recomputed</span><b>1</b></div><div><span>Compile issues changed</span><b>1</b></div><div><span>Objects reused</span><b>1</b></div></section></div>;
}

function LoginScreen({ onEnter, locale, onLocale }: { onEnter: () => void; locale: Locale; onLocale: (locale: Locale) => void }) {
  const [email, setEmail] = useState("");
  const [policyNotice, setPolicyNotice] = useState<string>();
  return <main className="login-shell">
    <section className="login-brand-panel">
      <div className="login-brand"><BrandMark inverse/><span>ResearchOS</span></div>
      <div className="login-statement"><span className="login-index">RESEARCH OPERATING SYSTEM · 01</span><h1>Evidence<br/><em>becomes</em><br/>structure.</h1><p>把散落的研究材料变成可追溯的证据结构，再让每一句结论通过编译。</p></div>
      <div className="evidence-field" aria-hidden="true">
        <div className="e-node n-source"><span>01</span><b>Source</b></div><i className="e-line l1"/><div className="e-node n-evidence"><span>02</span><b>Evidence</b></div><i className="e-line l2"/><div className="e-node n-thesis"><span>03</span><b>Thesis</b></div>
      </div>
      <div className="login-foot"><span>研构 · ResearchOS</span><span>v0.1 · Frozen contracts</span></div>
    </section>
    <section className="login-form-panel" lang={locale}>
      <div className="login-locale"><LocaleSwitcher locale={locale} onChange={onLocale}/></div>
      <div className="login-form-wrap">
        <span className="form-overline">{tx(locale,"PRIVATE RESEARCH WORKSPACE")}</span>
        <h2>{tx(locale,"Enter your research workspace")}</h2>
        <p className="form-intro">{tx(locale,"Continue to Fiscal transmission study. Object versions, evidence sources, and compile history remain traceable.")}</p>
        <label className="auth-field"><span>{tx(locale,"Work email")}</span><input value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@organization.com" type="email"/></label>
        <button className="auth-primary" onClick={onEnter}><span>{tx(locale,"Continue to ResearchOS")}</span><i>→</i></button>
        <div className="auth-separator"><span>{tx(locale,"or")}</span></div>
        <button className="auth-secondary" onClick={onEnter}><span className="openai-mark">◌</span><span>{tx(locale,"Continue with ChatGPT")}</span></button>
        <p className="auth-note"><i>◇</i> {tx(locale,"Demo workspace entry. Authentication is provided by the deployment environment; this page never stores passwords.")}</p>
      </div>
      <div className="login-form-footer"><button onClick={()=>setPolicyNotice("Research data remains inside the selected workspace and deployment boundary.")}>{tx(locale,"Privacy")}</button><button onClick={()=>setPolicyNotice("ResearchOS outputs require evidence and provenance review before use.")}>{tx(locale,"Terms")}</button><span>© 2026 ResearchOS</span></div>
      {policyNotice&&<div className="login-policy-notice" role="status">{policyNotice}<button onClick={()=>setPolicyNotice(undefined)} aria-label="Close policy notice">×</button></div>}
    </section>
  </main>
}

export default function Home() {
  const [view, setView] = useState<View>("thesis");
  const [commandOpen, setCommandOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<SourceItem>();
  const [entered, setEntered] = useState(false);
  const [locale, setLocale] = useState<Locale>("zh-CN");
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>("system");
  const [reducedMotion, setReducedMotion] = useState(false);
  const [mode, setMode] = useState<RuntimeMode>("real");
  const [scenario, setScenario] = useState<DemoScenario>("complete");
  const [liveObjectCount, setLiveObjectCount] = useState(0);
  const [actionNotice, setActionNotice] = useState<string>();
  const [inspectorVisible, setInspectorVisible] = useState(true);
  const [newThesisOpen, setNewThesisOpen] = useState(false);
  const [draftClaim, setDraftClaim] = useState("");
  const [draftLanguage, setDraftLanguage] = useState("CAUSAL");
  const [creatingThesis, setCreatingThesis] = useState(false);
  const [activeThesis, setActiveThesis] = useState<{ id: string; claim: string; languageLevel: string }>();
  useEffect(()=>{ const key=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();setCommandOpen(v=>!v)} if(e.key==="Escape")setCommandOpen(false)}; addEventListener("keydown",key);return()=>removeEventListener("keydown",key)},[]);
  useEffect(()=>{const media=window.matchMedia("(prefers-color-scheme: dark)");const apply=()=>{const resolved=theme==="system"?(media.matches?"dark":"light"):theme;document.documentElement.dataset.theme=resolved;document.documentElement.style.colorScheme=resolved==="dark"?"dark":"light"};apply();media.addEventListener("change",apply);return()=>media.removeEventListener("change",apply)},[theme]);
  useEffect(()=>{document.documentElement.dataset.reducedMotion=reducedMotion?"true":"false"},[reducedMotion]);
  const current = useMemo(() => nav.find((n) => n.id === view)!, [view]);
  const subtitles: Record<View, string> = {
    thesis: "Compile a research claim against frozen definitions and evidence policy.",
    workspace: "Shared research state, versioned objects, and traceable relations.",
    validation: "A continuous protocol from question to evidence-bounded conclusion.",
    macrotrace: "Registered empirical execution, diagnostics, and evidence output.",
    recompile: "Review how evidence constrains the language of the thesis.",
    versions: "Understand incremental changes, recomputation, and reuse.",
  };
  const runtimeMode: RuntimeMode = mode;
  const workspaceMeta = mode === "real" ? String(liveObjectCount) : "12";
  const projectSummary = mode === "real" ? `${liveObjectCount} objects · M1 API` : tx(locale, "4 sources · 1 thesis");
  const notify = (message: string) => { setActionNotice(message); window.setTimeout(() => setActionNotice(undefined), 3200); };
  const createThesis = async (event: React.FormEvent) => {
    event.preventDefault();
    const claim = draftClaim.trim();
    if (!claim) return;
    setCreatingThesis(true);
    try {
      const thesisId = `THESIS_${crypto.randomUUID().replaceAll("-", "").slice(0, 12).toUpperCase()}`;
      await researchosApi.createThesis(buildThesisPayload(thesisId, claim, draftLanguage));
      setActiveThesis({ id: thesisId, claim, languageLevel: draftLanguage });
      setNewThesisOpen(false);
      setDraftClaim("");
      setView("thesis");
      notify(locale === "en" ? "Thesis created and saved" : "论题已创建并保存");
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : "论题创建失败");
    } finally {
      setCreatingThesis(false);
    }
  };
  const runPrimaryFlow = () => { setView("thesis"); window.setTimeout(() => (document.querySelector(".live-flow-header .button") as HTMLButtonElement | null)?.click(), 0); };
  const downloadDiff = () => { const blob = new Blob([JSON.stringify({ thesis: "THESIS_DEMO_001", from: "THESIS_VER_001", to: "THESIS_VER_002", evidence: "ASSOCIATIONAL" }, null, 2)], { type: "application/json" }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "researchos-version-diff.json"; link.click(); URL.revokeObjectURL(link.href); notify("Version diff exported"); };
  const handleShellClick = (event: React.MouseEvent<HTMLElement>) => {
    const button = (event.target as HTMLElement).closest("button");
    if (!button || button.disabled) return;
    const label = (button.textContent ?? "").replace(/\s+/g, " ").trim();
    if (label === "分享" || label === "Share") { void navigator.clipboard.writeText(window.location.href).then(() => notify("Workspace link copied")); }
    else if (label.includes("编译论题") || label.includes("Compile thesis")) runPrimaryFlow();
    else if (label === "×" && button.getAttribute("aria-label") === "Close inspector") setInspectorVisible(false);
    else if (label.includes("New thesis") || label.includes("新建论题")) setNewThesisOpen(true);
    else if (label === "⌄") setSettingsOpen(true);
    else if (label === "···") { setSettingsOpen(true); notify("Project controls opened"); }
    else if (label.includes("Activity") || label.includes("活动")) notify("3 recent events · compile, evidence, and version update");
    else if (label.includes("Help") || label.includes("帮助")) { setCommandOpen(true); notify("Use ⌘K / Ctrl+K to navigate"); }
    else if (label.includes("Open validation plan") || label.includes("打开验证计划")) setView("validation");
    else if (label.includes("Inspect run")) setView("macrotrace");
    else if (label.includes("Open Evidence Bundle")) { setView("macrotrace"); notify("EvidenceBundle provenance is shown below the run"); }
    else if (label.includes("Export diff")) downloadDiff();
    else if (label.includes("Accept as new version")) { setView("versions"); notify("New immutable thesis version accepted"); }
    else if (label.includes("Keep previous version")) { setView("versions"); notify("Previous thesis version remains active"); }
    else if (label.includes("Replay run")) { notify("Replay requested in Fixture mode"); setScenario("running"); }
    else if (["Results", "Parameters", "Artifacts"].includes(label) || label.startsWith("Diagnostics")) notify(`${label} panel selected`);
    else if (label.includes("View as table")) notify("Relationship table view opened");
    else if (label.includes("Add source")) { setView("workspace"); notify(mode === "real" ? "Use Choose files to upload a source" : "Switch to Real API to upload a source"); }
    else if (label.includes("All types") || label.includes("All states")) notify(`${label.replace("⌄", "")} filter is ready`);
    else if (["Objects", "Relations", "Conflicts"].includes(label)) notify(`${label} workspace selected`);
    else if (label.includes("Collapse all")) notify("Compile issues collapsed");
    else if (label.endsWith("→") && (label.includes("Define") || label.includes("Set") || label.includes("Review") || label.includes("Add") || label.includes("Confirm"))) notify(`${label.replace("→", "").trim()} editor opened`);
    else if (label.includes("Open live asset details") || label.includes("Open frozen fixture") || label.includes("打开冻结样例")) notify("Pinned provenance details opened");
    else if (label === "隐私" || label === "Privacy") notify("Research data stays within the selected workspace and deployment boundary.");
    else if (label === "使用条款" || label === "Terms") notify("ResearchOS outputs require evidence and provenance review before use.");
    else if (label === "Manage") { setView("macrotrace"); setSettingsOpen(false); notify("MacroTrace capability opened"); }
    else if (label === "Request") notify("Integration request recorded for contract review");
    else if (button.closest(".diff-group")) { setInspectorOpen(true); notify(`Diff detail: ${label.replace("→", "").trim()}`); }
  };
  if (!entered) return <LoginScreen onEnter={() => { setEntered(true); requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "auto" })); }} locale={locale} onLocale={setLocale} />;
  return <main className="app-shell" lang={locale} data-locale={locale} onClickCapture={handleShellClick}>
    <aside className="sidebar"><div className="brand"><BrandMark/><div><b>ResearchOS</b><span>{tx(locale,"Evidence workspace")}</span></div><button>⌄</button></div><button className="new-thesis" onClick={()=>setNewThesisOpen(true)}>＋ <span>{tx(locale,"New thesis")}</span><kbd>N</kbd></button><nav><span className="nav-label">{tx(locale,"Research")}</span>{nav.map(item=><button key={item.id} className={view===item.id?"active":""} onClick={()=>setView(item.id)}><i>{item.icon}</i><span>{tx(locale,item.label)}</span>{(item.id === "workspace" ? workspaceMeta : item.id === "thesis" && activeThesis ? "1" : item.meta)&&<em>{item.id === "workspace" ? workspaceMeta : item.id === "thesis" && activeThesis ? "1" : item.meta}</em>}</button>)}</nav><div className="sidebar-project"><span className="nav-label">{tx(locale,"Active project")}</span><div className="project-card"><div className="project-icon">FT</div><div><b>{tx(locale,"Fiscal transmission")}</b><span>{projectSummary}</span></div><button>···</button></div></div><div className="sidebar-bottom"><button><i>⌁</i><span>{tx(locale,"Activity")}</span><em>3</em></button><button><i>?</i><span>{tx(locale,"Help & shortcuts")}</span></button><div className="sync-state"><span className="status-dot green"/><div><b>{tx(locale,"Workspace synced")}</b><small>{tx(locale,"Just now")}</small></div></div></div></aside>
    <section className="main-frame"><Topbar title={current.label} subtitle={subtitles[view]} onCommand={()=>setCommandOpen(true)} onInspector={()=>setInspectorVisible(value=>!value)} onSettings={()=>setSettingsOpen(true)} locale={locale} onLocale={setLocale} mode={runtimeMode}/>{view !== "workspace" && mode !== "real" && <RuntimeNotice mode={runtimeMode} scenario={scenario} onRetry={()=>setScenario("running")} onReset={()=>setScenario("complete")}/>}<div className={`content-frame ${inspectorVisible ? "" : "inspector-hidden"}`}>{view!=="workspace"&&mode==="real"&&<LiveResearchFlow view={view} locale={locale} thesisId={activeThesis?.id} claim={activeThesis?.claim} languageLevel={activeThesis?.languageLevel}/>} {view==="thesis"&&mode!=="real"&&<ThesisView locale={locale}/>} {view==="workspace"&&(mode === "real" ? <RealWorkspace onSelect={(item: WorkspaceSource)=>{setSelectedSource(item);setInspectorOpen(true)}} onObjectCount={setLiveObjectCount}/> : <WorkspaceView onSelect={(item)=>{setSelectedSource(item);setInspectorOpen(true)}}/>)} {view==="validation"&&mode!=="real"&&<ValidationView/>}{view==="macrotrace"&&mode!=="real"&&<MacroTraceView/>}{view==="recompile"&&mode!=="real"&&<RecompileView/>}{view==="versions"&&mode!=="real"&&<VersionView/>}{inspectorVisible&&<Inspector selectedSource={selectedSource} locale={locale}/>}</div></section>
    <InspectorDrawer open={inspectorOpen} onOpenChange={setInspectorOpen} selectedSource={selectedSource} locale={locale}/>
    <SettingsCenter open={settingsOpen} onOpenChange={setSettingsOpen} theme={theme} onTheme={setTheme} locale={locale} onLocale={setLocale} reducedMotion={reducedMotion} onReducedMotion={setReducedMotion} mode={mode} onMode={setMode} scenario={scenario} onScenario={setScenario} onReset={()=>{setView("thesis");setSelectedSource(undefined);setMode("fixture");setScenario("complete");setSettingsOpen(false)}}/>
    <Dialog.Root open={newThesisOpen} onOpenChange={setNewThesisOpen}><Dialog.Portal><Dialog.Overlay className="thesis-dialog-overlay"/><Dialog.Content className="thesis-dialog"><Dialog.Title>{locale === "en" ? "Create thesis" : locale === "zh-TW" ? "建立論題" : "新建论题"}</Dialog.Title><Dialog.Description>{locale === "en" ? "Define the claim first. Evidence will constrain its language during compilation." : "先定义可验证的研究主张，证据将在编译时约束其语言强度。"}</Dialog.Description><form onSubmit={createThesis}><label><span>{locale === "en" ? "Research claim" : "研究主张"}</span><textarea autoFocus required value={draftClaim} onChange={event=>setDraftClaim(event.target.value)} placeholder={locale === "en" ? "e.g. Fiscal expansion is associated with higher 10-year Treasury yields." : "例如：财政扩张与10年期美债收益率上升相关。"}/></label><label><span>{locale === "en" ? "Requested language" : "请求语言强度"}</span><select value={draftLanguage} onChange={event=>setDraftLanguage(event.target.value)}><option value="CAUSAL">CAUSAL · 因果</option><option value="ASSOCIATIONAL">ASSOCIATIONAL · 关联</option><option value="DESCRIPTIVE">DESCRIPTIVE · 描述</option></select></label><div className="thesis-dialog-note"><i>◇</i><span>{locale === "en" ? "The original claim is versioned. Recompile creates a new immutable build." : "原始主张将被版本化；重新编译会生成新的不可变构建。"}</span></div><div className="thesis-dialog-actions"><Dialog.Close type="button" className="button secondary">{locale === "en" ? "Cancel" : "取消"}</Dialog.Close><button className="button primary" disabled={creatingThesis || !draftClaim.trim()}>{creatingThesis ? (locale === "en" ? "Saving…" : "正在保存…") : (locale === "en" ? "Create thesis" : "创建论题")}</button></div></form></Dialog.Content></Dialog.Portal></Dialog.Root>
    {commandOpen&&<div className="command-overlay" onMouseDown={()=>setCommandOpen(false)}><div className="command" onMouseDown={e=>e.stopPropagation()}><div className="command-input"><span>⌕</span><input autoFocus placeholder={`${tx(locale,"Search or command")}…`}/><kbd>ESC</kbd></div><span className="command-label">Navigate</span>{nav.map(n=><button key={n.id} onClick={()=>{setView(n.id);setCommandOpen(false)}}><i>{n.icon}</i><span>{tx(locale,n.label)}</span><kbd>↵</kbd></button>)}</div></div>}
    {actionNotice&&<div className="action-toast" role="status"><i>✓</i><span>{actionNotice}</span></div>}
  </main>;
}
