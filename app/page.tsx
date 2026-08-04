"use client";

import { useEffect, useMemo, useState } from "react";

type View = "thesis" | "workspace" | "validation" | "macrotrace" | "recompile" | "versions";

const nav: { id: View; icon: string; label: string; meta?: string }[] = [
  { id: "workspace", icon: "⌘", label: "Workspace", meta: "12" },
  { id: "thesis", icon: "◇", label: "Thesis Build", meta: "1" },
  { id: "validation", icon: "✓", label: "Validation Plan", meta: "2/2" },
  { id: "macrotrace", icon: "↳", label: "MacroTrace", meta: "Complete" },
  { id: "recompile", icon: "⇄", label: "Recompile" },
  { id: "versions", icon: "⑂", label: "Version Diff", meta: "v2" },
];

const sources = [
  { type: "DATASET", name: "10-year Treasury yield demo snapshot", id: "DATA_US_TREASURY_10Y", version: "VER_DEMO_20260804", state: "CONFIRMED" },
  { type: "DOCUMENT", name: "Fiscal supply definition notes", id: "DOC_PRODUCT_V2", version: "v2", state: "AI_PROPOSED" },
  { type: "THESIS", name: "US fiscal expansion and 10Y yield", id: "THESIS_DEMO_001", version: "v2", state: "CONFIRMED" },
  { type: "EVIDENCE", name: "MacroTrace associational bundle", id: "EVIDENCE_DEMO_001", version: "0.1.0", state: "CONFIRMED" },
];

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "green" | "amber" | "red" | "blue" | "purple" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function Topbar({ title, subtitle, onCommand }: { title: string; subtitle: string; onCommand: () => void }) {
  return (
    <header className="topbar">
      <div className="breadcrumbs"><span>Fiscal transmission study</span><i>/</i><strong>{title}</strong></div>
      <div className="top-actions">
        <Badge tone="amber">FIXTURE MODE</Badge>
        <button className="command-trigger" onClick={onCommand}><span>Search or command</span><kbd>⌘ K</kbd></button>
        <button className="avatar" aria-label="User menu">TW</button>
      </div>
      <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div><div className="heading-actions"><button className="button secondary">Share</button><button className="button primary">Compile thesis <span>⌘↵</span></button></div></div>
    </header>
  );
}

function Inspector({ selectedSource }: { selectedSource?: typeof sources[number] }) {
  const item = selectedSource ?? sources[2];
  return (
    <aside className="inspector">
      <div className="inspector-head"><span>Inspector</span><button aria-label="Close inspector">×</button></div>
      <section className="inspector-section">
        <div className="object-mark">{item.type.slice(0, 2)}</div>
        <h3>{item.name}</h3><p className="mono quiet">{item.id}</p>
        <div className="inspector-badges"><Badge tone={item.state === "AI_PROPOSED" ? "purple" : "green"}>{item.state}</Badge><Badge>{item.type}</Badge></div>
      </section>
      <section className="inspector-section properties">
        <h4>Properties</h4>
        <dl><dt>Version</dt><dd>{item.version}</dd><dt>As of</dt><dd>Aug 04, 2026</dd><dt>Access</dt><dd>Workspace</dd><dt>Contract</dt><dd>0.1.0-frozen</dd></dl>
      </section>
      <section className="inspector-section"><h4>Traceability</h4><div className="trace-stack"><div><i className="trace-dot source"/><span>Source object</span><small>Version pinned</small></div><div><i className="trace-line"/><span>Evidence bundle</span><small>Associational</small></div><div><i className="trace-dot thesis"/><span>Compiled thesis</span><small>Language weakened</small></div></div></section>
      <section className="inspector-section"><h4>Provenance</h4><button className="source-link"><span>↗</span><div><b>Open frozen fixture</b><small>sample_thesis_build.json</small></div></button></section>
    </aside>
  );
}

function ThesisView() {
  return <div className="workspace-scroll thesis-view">
    <section className="thesis-hero">
      <div className="eyebrow"><span className="status-dot red"/> BUILD FAILED <span className="mono">BUILD_DEMO_001</span></div>
      <blockquote>美国财政扩张正在持续推高<br/>10年期美债收益率。</blockquote>
      <div className="thesis-meta"><span>As of <b>Aug 04, 2026</b></span><span>Requested language <Badge tone="red">CAUSAL</Badge></span><span>Version <b>THESIS_VER_001</b></span></div>
    </section>
    <section className="issues-section">
      <div className="section-title"><div><h2>Compile issues</h2><p>5 constraints prevent this thesis from compiling.</p></div><button className="text-button">Collapse all</button></div>
      <div className="issue-list">
        {[
          ["DEF001", "Definition is not frozen", "“财政扩张” has no operational definition or source reference.", "Define term", "error"],
          ["HORIZON001", "Time horizon is unresolved", "“持续” does not specify a start date, end date, or evaluation window.", "Set window", "error"],
          ["CLAIM_LANG001", "Evidence level cannot support causal wording", "Required CAUSAL_IDENTIFIED evidence is not available. Current evidence is ASSOCIATIONAL.", "Review language", "error"],
          ["VAR001", "Competing explanations are missing", "Monetary conditions and term-premium controls must be addressed.", "Add controls", "warn"],
          ["FALS001", "Falsification criteria need confirmation", "Three candidate falsifiers are present but not yet confirmed.", "Confirm criteria", "warn"],
        ].map(([code,title,detail,action,tone], i) => <div className="issue-row" key={code}>
          <div className={`issue-icon ${tone}`}>{tone === "error" ? "!" : "·"}</div><div className="issue-body"><div><span className="mono issue-code">{code}</span><h3>{title}</h3></div><p>{detail}</p></div><div className="issue-side"><Badge tone={i < 3 ? "red" : "amber"}>{i < 3 ? "BLOCKING" : "WARNING"}</Badge><button>{action} →</button></div>
        </div>)}
      </div>
    </section>
    <section className="validation-preview"><div><span className="eyebrow">NEXT REQUIRED ACTION</span><h2>Run the registered validation protocol</h2><p>Freeze definitions, execute MacroTrace, then recompile under the evidence language policy.</p></div><button className="button primary">Open validation plan →</button></section>
  </div>;
}

function WorkspaceView({ onSelect }: { onSelect: (item: typeof sources[number]) => void }) {
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

export default function Home() {
  const [view, setView] = useState<View>("thesis");
  const [commandOpen, setCommandOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<typeof sources[number]>();
  useEffect(()=>{ const key=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();setCommandOpen(v=>!v)} if(e.key==="Escape")setCommandOpen(false)}; addEventListener("keydown",key);return()=>removeEventListener("keydown",key)},[]);
  const current = useMemo(()=>nav.find(n=>n.id===view)!,[view]);
  const subtitles: Record<View,string> = { thesis:"Compile a research claim against frozen definitions and evidence policy.",workspace:"Shared research state, versioned objects, and traceable relations.",validation:"A continuous protocol from question to evidence-bounded conclusion.",macrotrace:"Registered empirical execution, diagnostics, and evidence output.",recompile:"Review how evidence constrains the language of the thesis.",versions:"Understand incremental changes, recomputation, and reuse."};
  return <main className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><i/><i/><i/></div><div><b>ResearchOS</b><span>Evidence workspace</span></div><button>⌄</button></div><button className="new-thesis">＋ <span>New thesis</span><kbd>N</kbd></button><nav><span className="nav-label">Research</span>{nav.map(item=><button key={item.id} className={view===item.id?"active":""} onClick={()=>setView(item.id)}><i>{item.icon}</i><span>{item.label}</span>{item.meta&&<em>{item.meta}</em>}</button>)}</nav><div className="sidebar-project"><span className="nav-label">Active project</span><div className="project-card"><div className="project-icon">FT</div><div><b>Fiscal transmission</b><span>4 sources · 1 thesis</span></div><button>···</button></div></div><div className="sidebar-bottom"><button><i>⌁</i><span>Activity</span><em>3</em></button><button><i>?</i><span>Help & shortcuts</span></button><div className="sync-state"><span className="status-dot green"/><div><b>Workspace synced</b><small>Just now</small></div></div></div></aside>
    <section className="main-frame"><Topbar title={current.label} subtitle={subtitles[view]} onCommand={()=>setCommandOpen(true)}/><div className="content-frame">{view==="thesis"&&<ThesisView/>}{view==="workspace"&&<WorkspaceView onSelect={setSelectedSource}/>} {view==="validation"&&<ValidationView/>}{view==="macrotrace"&&<MacroTraceView/>}{view==="recompile"&&<RecompileView/>}{view==="versions"&&<VersionView/>}<Inspector selectedSource={selectedSource}/></div></section>
    {commandOpen&&<div className="command-overlay" onMouseDown={()=>setCommandOpen(false)}><div className="command" onMouseDown={e=>e.stopPropagation()}><div className="command-input"><span>⌕</span><input autoFocus placeholder="Search objects or run a command…"/><kbd>ESC</kbd></div><span className="command-label">Navigate</span>{nav.map(n=><button key={n.id} onClick={()=>{setView(n.id);setCommandOpen(false)}}><i>{n.icon}</i><span>{n.label}</span><kbd>↵</kbd></button>)}</div></div>}
  </main>;
}
