"use client";
/* eslint-disable @next/next/no-img-element -- transparent mascot is a pre-optimized static brand asset */

import { useEffect, useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { QRCodeSVG } from "qrcode.react";
import { localeNames, tx, type Locale } from "./i18n";
import RealWorkspace from "./real-workspace";
import LiveResearchFlow, { buildThesisPayload } from "./live-research-flow";
import ResearchOutputStudio from "./research-output-studio";
import DataConnectorSettings from "./data-connector-settings";
import type { WorkspaceSource } from "../lib/api-client";
import { researchosApi } from "../lib/api-client";

type View = "report-update" | "thesis" | "workspace" | "validation" | "macrotrace" | "recompile" | "versions";
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
  { id: "workspace", icon: "⌘", label: "研究助手", meta: "LIVE" },
  { id: "report-update", icon: "▤", label: "研究出品", meta: "报告" },
  { id: "thesis", icon: "◇", label: "论题编译", meta: "1" },
  { id: "validation", icon: "✓", label: "验证计划", meta: "2/2" },
  { id: "macrotrace", icon: "↳", label: "MacroTrace", meta: "已完成" },
  { id: "recompile", icon: "⇄", label: "重新编译" },
  { id: "versions", icon: "⑂", label: "版本差异", meta: "v2" },
];

const sources: SourceItem[] = [
  { type: "数据集", name: "10年期美国国债收益率样例快照", id: "DATA_US_TREASURY_10Y", version: "VER_DEMO_20260804", state: "CONFIRMED", origin: "fixture" },
  { type: "文档", name: "财政供给定义笔记", id: "DOC_PRODUCT_V2", version: "v2", state: "AI_PROPOSED", origin: "fixture" },
  { type: "论题", name: "美国财政扩张与10年期国债收益率", id: "THESIS_DEMO_001", version: "v2", state: "CONFIRMED", origin: "fixture" },
  { type: "证据", name: "MacroTrace 关联性证据包", id: "EVIDENCE_DEMO_001", version: "0.1.0", state: "CONFIRMED", origin: "fixture" },
];

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "green" | "amber" | "red" | "blue" | "purple" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function BrandMark({ inverse = false, large = false }: { inverse?: boolean; large?: boolean }) {
  return <span className={`researchos-mark ${inverse ? "inverse" : ""} ${large ? "large" : ""}`} aria-hidden="true"><i/><i/><i/><b/></span>;
}

function LocaleSwitcher({ locale, onChange, compact = false }: { locale: Locale; onChange: (locale: Locale) => void; compact?: boolean }) {
  return <label className={`locale-switcher ${compact ? "compact" : ""}`}><span className="sr-only">语言</span><select value={locale} onChange={e=>onChange(e.target.value as Locale)} aria-label="语言">{(Object.keys(localeNames) as Locale[]).map(key=><option value={key} key={key}>{localeNames[key]}</option>)}</select><i>⌄</i></label>;
}

function Topbar({ title, subtitle, onCommand, onInspector, onSettings, onPrimary, locale, onLocale, mode, workspace = false, reportUpdate = false }: { title: string; subtitle: string; onCommand: () => void; onInspector: () => void; onSettings: () => void; onPrimary: () => void; locale: Locale; onLocale: (locale: Locale) => void; mode: RuntimeMode; workspace?: boolean; reportUpdate?: boolean }) {
  return (
    <header className="topbar">
      <div className="breadcrumbs"><span>{workspace || reportUpdate ? (locale === "en" ? "International markets research" : "国际市场研究") : tx(locale,"Fiscal transmission study")}</span><i>/</i><strong>{tx(locale,title)}</strong></div>
      <div className="top-actions">
        <button className="mode-trigger" onClick={onSettings}><Badge tone={mode==="offline"?"blue":mode==="real"?"green":"amber"}>{mode==="offline"?"离线回放":mode==="real"?"真实接口 · A+B+C":"样例模式"}</Badge></button>
        <LocaleSwitcher locale={locale} onChange={onLocale} compact/>
        <button className="command-trigger" onClick={onCommand}><span>{tx(locale,"Search or command")}</span><kbd>⌘ K</kbd></button>
        <button className="inspector-trigger" onClick={onInspector} aria-label={tx(locale,"Inspector")}>⌘</button>
        <button className="avatar" onClick={onSettings} aria-label="设置与扩展">TW</button>
      </div>
      <div className="page-heading"><div><h1>{workspace ? (locale === "en" ? "Financial research copilot" : "金融研究助手") : tx(locale,title)}</h1><p>{workspace ? (locale === "en" ? "Discover public signals, verify them with data, and preserve every source." : "从公开资料发现线索，用市场数据核对判断，并保留完整引用。") : tx(locale,subtitle)}</p></div><div className="heading-actions"><button className="button secondary">{tx(locale,"Share")}</button><button className="button primary" onClick={onPrimary}>{workspace ? (locale === "en" ? "New research" : "新研究") : reportUpdate ? (locale === "en" ? "Update report" : "更新报告") : tx(locale,"Compile thesis")} <span>{workspace ? "+" : reportUpdate ? "→" : "⌘↵"}</span></button></div></div>
    </header>
  );
}

function Inspector({ selectedSource, locale }: { selectedSource?: SourceItem; locale: Locale }) {
  const item = selectedSource ?? sources[2];
  const isApi = item.origin === "api";
  return (
    <aside className="inspector">
      <div className="inspector-head"><span>{tx(locale,"Inspector")}</span><button aria-label="关闭检查器">×</button></div>
      <section className="inspector-section">
        <div className="object-mark">{item.type.slice(0, 2)}</div>
        <h3>{item.name}</h3><p className="mono quiet">{item.id}</p>
        <div className="inspector-badges"><Badge tone={isApi ? "blue" : item.state === "AI_PROPOSED" ? "purple" : "green"}>{item.state}</Badge><Badge>{item.type}</Badge></div>
      </section>
      <section className="inspector-section properties">
        <h4>{tx(locale,"Properties")}</h4>
        <dl><dt>版本</dt><dd>{item.version}</dd><dt>更新时间</dt><dd>{item.updatedAt ? new Date(item.updatedAt).toLocaleDateString() : "2026年8月4日"}</dd><dt>访问范围</dt><dd>工作空间</dd><dt>契约版本</dt><dd>{isApi ? "0.1.0-m1" : "0.1.0-frozen"}</dd></dl>
      </section>
      <section className="inspector-section"><h4>{tx(locale,"Traceability")}</h4><div className="trace-stack"><div><i className="trace-dot source"/><span>来源对象</span><small>{isApi ? `${item.versionCount ?? 1} 个版本 · ${item.formatKind ?? "未知格式"}` : "已固定版本"}</small></div>{isApi ? <div><i className="trace-line"/><span>已解析片段</span><small>{item.fragmentCount ?? 0} 个确定性片段</small></div> : <><div><i className="trace-line"/><span>证据包</span><small>关联性</small></div><div><i className="trace-dot thesis"/><span>已编译论题</span><small>表述强度已降低</small></div></>}</div></section>
      <section className="inspector-section"><h4>{tx(locale,"Provenance")}</h4><button className="source-link"><span>↗</span><div><b>{isApi ? "打开实时对象详情" : tx(locale,"Open frozen fixture")}</b><small>{isApi ? "M1 对象投影" : "sample_thesis_build.json"}</small></div></button></section>
    </aside>
  );
}

function InspectorDrawer({ open, onOpenChange, selectedSource, locale }: { open: boolean; onOpenChange: (open: boolean) => void; selectedSource?: SourceItem; locale: Locale }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="drawer-overlay"/><Dialog.Content className="drawer-content"><Dialog.Title className="sr-only">{tx(locale,"Inspector")}</Dialog.Title><Dialog.Close className="drawer-close" aria-label="关闭">×</Dialog.Close><Inspector selectedSource={selectedSource} locale={locale}/></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function SettingsCenter({ open, onOpenChange, theme, onTheme, locale, onLocale, reducedMotion, onReducedMotion, mode, onMode, scenario, onScenario, onReset }: { open: boolean; onOpenChange: (open: boolean) => void; theme: Theme; onTheme: (theme: Theme) => void; locale: Locale; onLocale: (locale: Locale) => void; reducedMotion: boolean; onReducedMotion: (value: boolean) => void; mode: RuntimeMode; onMode: (mode: RuntimeMode) => void; scenario: DemoScenario; onScenario: (scenario: DemoScenario) => void; onReset: () => void }) {
  const [tab, setTab] = useState<"appearance" | "demo" | "data" | "extensions" | "about">("appearance");
  const themes: { id: Theme; label: string }[] = [{id:"light",label:"浅色"},{id:"dark",label:"深色"},{id:"system",label:"跟随系统"},{id:"contrast",label:"高对比度"}];
  const extensions = [
    { mark:"MT", name:"MacroTrace", detail:"已注册的实证执行能力", state:"已启用", tone:"green" as const },
    { mark:"ZT", name:"Zotero", detail:"参考文献库连接器", state:"可申请", tone:"blue" as const },
    { mark:"OA", name:"OpenAlex", detail:"学术作品与引用连接器", state:"可申请", tone:"blue" as const },
    { mark:"IF", name:"iFind", detail:"机构受控数据源", state:"受限", tone:"amber" as const },
  ];
  const scenarios: { id: DemoScenario; label: string }[] = [{id:"complete",label:"已完成"},{id:"queued",label:"排队中"},{id:"running",label:"运行中"},{id:"partial",label:"部分完成"},{id:"failed",label:"失败"},{id:"cancelled",label:"已取消"},{id:"permission",label:"权限受阻"},{id:"timeout",label:"模型超时"},{id:"unknown",label:"未知状态"}];
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="settings-overlay"/><Dialog.Content className="settings-center"><Dialog.Title className="settings-title">设置</Dialog.Title><Dialog.Description className="settings-description">工作空间偏好、数据连接与已注册扩展</Dialog.Description><Dialog.Close className="settings-close" aria-label="关闭">×</Dialog.Close><div className="settings-layout"><nav className="settings-nav"><div className="settings-brand"><BrandMark/><span><b>ResearchOS</b><small>工作空间设置</small></span></div>{([['appearance','外观','◐'],['demo','演示与状态','▷'],['data','数据源','⌁'],['extensions','扩展','⌘'],['about','关于','◇']] as const).map(([id,label,icon])=><button key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}><i>{icon}</i>{label}{id==='data'&&<em>13</em>}{id==='extensions'&&<em>4</em>}</button>)}</nav><section className="settings-content">
    {tab==="appearance"&&<><div className="settings-head"><span>界面</span><h2>外观</h2><p>选择 ResearchOS 在此设备上的显示与交互方式。</p></div><div className="setting-block"><div><h3>颜色主题</h3><p>“跟随系统”会使用操作系统的外观偏好。</p></div><div className="theme-grid">{themes.map(item=><button key={item.id} className={`theme-choice theme-${item.id} ${theme===item.id?'selected':''}`} onClick={()=>onTheme(item.id)} aria-pressed={theme===item.id}><span><i/><i/><i/></span><b>{item.label}</b><em>{theme===item.id?'✓':''}</em></button>)}</div></div><div className="setting-row"><div><h3>语言</h3><p>简体中文、繁體中文与英语。</p></div><LocaleSwitcher locale={locale} onChange={onLocale}/></div><div className="setting-row"><div><h3>减少动态效果</h3><p>限制非必要的过渡动画与脉冲效果。</p></div><button className={`switch ${reducedMotion?'on':''}`} onClick={()=>onReducedMotion(!reducedMotion)} role="switch" aria-checked={reducedMotion}><i/></button></div></>}
    {tab==="extensions"&&<><div className="settings-head"><span>已注册能力</span><h2>扩展中心</h2><p>扩展只声明能力，安装过程不会修改已冻结的研究契约。</p></div><div className="extension-notice"><i>◇</i><span><b>目录预览</b><small>当前仅启用 MacroTrace；其他连接器需要经过审核的集成契约。</small></span></div><div className="extension-list">{extensions.map(ext=><div className="extension-row" key={ext.name}><span className="extension-mark">{ext.mark}</span><span><b>{ext.name}</b><small>{ext.detail}</small></span><Badge tone={ext.tone}>{ext.state}</Badge><button>{ext.state==="已启用"?'管理':'申请'}</button></div>)}</div></>}
    {tab==="demo"&&<><div className="settings-head"><span>交付控制</span><h2>演示与状态</h2><p>切换可信的数据模式，并检查各种异步失败状态。</p></div><div className="mode-grid"><button className={mode==="fixture"?"selected":""} onClick={()=>onMode("fixture")}><Badge tone="amber">样例</Badge><b>冻结契约</b><small>确定性的标准项目</small></button><button className={mode==="offline"?"selected":""} onClick={()=>onMode("offline")}><Badge tone="blue">离线回放</Badge><b>缓存样例回放</b><small>不声称调用实时接口</small></button><button className={mode==="real"?"selected":""} onClick={()=>onMode("real")}><Badge tone="green">真实接口</Badge><b>统一 A + B + C 接口</b><small>资产、编译器、MacroTrace、证据与版本差异</small></button></div><p className="integration-note"><b>已集成生产者接口：</b>A 数据基础、B MacroTrace 适配器与 C 论题编译器共用同一个浏览器接口。实证生产者启用前，MacroTrace 仍明确标记为样例。</p><div className="scenario-block"><h3>异步状态模拟器</h3><p>这些可见的质检控件不会修改契约样例。</p><div className="scenario-grid">{scenarios.map(item=><button key={item.id} className={scenario===item.id?"active":""} onClick={()=>onScenario(item.id)}>{item.label}</button>)}</div></div><div className="demo-tools"><div className="qr-card"><QRCodeSVG value="https://researchos-evidence-workspace.ztian9080.chatgpt.site/" size={92} bgColor="transparent" fgColor="currentColor" level="M"/><span><b>移动端演示入口</b><small>扫码打开私有部署页面。</small></span></div><button className="button secondary" onClick={onReset}>↻ 重置标准项目</button></div></>}
    {tab==="about"&&<><div className="settings-head"><span>产品定位</span><h2>让证据形成结构。</h2><p>ResearchOS 是证据驱动的金融研究工作台，而不是普通聊天面板。</p></div><div className="identity-card"><BrandMark large/><div><b>研构 · ResearchOS</b><small>契约样例 · 0.1.0-frozen</small></div></div><dl className="about-list"><dt>工作空间</dt><dd>国际市场研究</dd><dt>对象模型</dt><dd>论题 · 证据 · 来源 · 验证 · 模型运行 · 版本</dd><dt>构建版本</dt><dd className="mono">D-前端 / 2026.08</dd></dl></>}
    {tab==="data"&&<DataConnectorSettings locale={locale} active={tab==="data"}/>} 
  </section></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function RuntimeNotice({ mode, scenario, onRetry, onReset }: { mode: RuntimeMode; scenario: DemoScenario; onRetry: () => void; onReset: () => void }) {
  if (scenario==="complete" && mode==="fixture") return null;
  const copy: Record<DemoScenario,{title:string;detail:string;action?:string}> = {
    complete:{title:mode==="offline"?"离线回放已就绪":"运行完成",detail:mode==="offline"?"正在展示已固定的缓存结果，未发起实时请求。":"已完成已注册的样例流程。"},
    queued:{title:"运行已排队",detail:"请求已登记，正在等待执行资源。"},
    running:{title:"MacroTrace 正在运行",detail:"当前进度用于界面验证，冻结结果保持不变。"},
    partial:{title:"已有部分证据",detail:"已有一项产物，但诊断尚未完成，不能编译最终结论。",action:"检查部分结果"},
    failed:{title:"模型运行失败",detail:"未生成证据包，请检查诊断后重试。",action:"重试样例运行"},
    cancelled:{title:"运行已取消",detail:"证据生成前执行已停止，不会用旧结果替代。",action:"开始新运行"},
    permission:{title:"权限受阻",detail:"当前工作空间角色无权访问该来源，请向来源所有者申请。",action:"申请访问"},
    timeout:{title:"模型超时",detail:"MacroTrace 超过 180 秒限制，上次成功结果已标记为过期且不会复用。",action:"回放缓存运行"},
    unknown:{title:"不支持的后端状态",detail:"ResearchOS 收到未知状态并安全停止渲染该结果。",action:"复制诊断信息"},
  };
  const item=copy[scenario];
  return <div className={`runtime-notice state-${scenario}`} role={scenario==="failed"||scenario==="unknown"?"alert":"status"}><span className="runtime-icon">{scenario==="running"?"↻":scenario==="complete"?"✓":scenario==="queued"?"⋯":"!"}</span><span><b>{item.title}</b><small>{item.detail}</small></span>{item.action&&<button onClick={onRetry}>{item.action}</button>}<button className="notice-close" onClick={onReset} aria-label="重置状态">×</button></div>;
}

function ThesisView({ locale }: { locale: Locale }) {
  const [collapsed, setCollapsed] = useState(false);
  return <div className="workspace-scroll thesis-view">
    <section className="thesis-hero">
      <div className="eyebrow"><span className="status-dot red"/> 构建失败 <span className="mono">BUILD_DEMO_001</span></div>
      <blockquote>美国财政扩张正在持续推高<br/>10年期美债收益率。</blockquote>
      <div className="thesis-meta"><span>截止日期 <b>2026年8月4日</b></span><span>请求表述 <Badge tone="red">因果</Badge></span><span>版本 <b>THESIS_VER_001</b></span></div>
    </section>
    <section className="issues-section">
      <div className="section-title"><div><h2>{tx(locale,"Compile issues")}</h2><p>{tx(locale,"5 constraints prevent this thesis from compiling.")}</p></div><button className="text-button" onClick={()=>setCollapsed(value=>!value)}>{collapsed ? "全部展开" : tx(locale,"Collapse all")}</button></div>
      {!collapsed&&<div className="issue-list">
        {[
          ["DEF001", "Definition is not frozen", "“财政扩张”缺少可操作定义或来源引用。", "Define term", "error"],
          ["HORIZON001", "Time horizon is unresolved", "“持续”尚未指定起止日期或评估窗口。", "Set window", "error"],
          ["CLAIM_LANG001", "Evidence level cannot support causal wording", "当前缺少因果识别证据，现有证据仅支持关联性结论。", "Review language", "error"],
          ["VAR001", "Competing explanations are missing", "必须纳入货币条件与期限溢价等竞争性解释。", "Add controls", "warn"],
          ["FALS001", "Falsification criteria need confirmation", "已有三个候选证伪条件，但尚未确认。", "Confirm criteria", "warn"],
        ].map(([code,title,detail,action,tone], i) => <div className="issue-row" key={code}>
          <div className={`issue-icon ${tone}`}>{tone === "error" ? "!" : "·"}</div><div className="issue-body"><div><span className="mono issue-code">{code}</span><h3>{tx(locale,title)}</h3></div><p>{detail}</p></div><div className="issue-side"><Badge tone={i < 3 ? "red" : "amber"}>{tx(locale,i < 3 ? "BLOCKING" : "WARNING")}</Badge><button>{tx(locale,action)} →</button></div>
        </div>)}
      </div>}
    </section>
    <section className="validation-preview"><div><span className="eyebrow">{tx(locale,"NEXT REQUIRED ACTION")}</span><h2>{tx(locale,"Run the registered validation protocol")}</h2><p>冻结定义、执行 MacroTrace，再按照证据表述政策重新编译。</p></div><button className="button primary">{tx(locale,"Open validation plan")} →</button></section>
  </div>;
}

function WorkspaceView({ onSelect }: { onSelect: (item: SourceItem) => void }) {
  return <div className="workspace-scroll"><div className="summary-strip"><div><span>研究对象</span><b>12</b></div><div><span>关系</span><b>18</b></div><div><span>待解决冲突</span><b className="amber-text">2</b></div><div><span>上下文包</span><b>4</b></div></div>
    <section className="table-section"><div className="section-title"><div><h2>研究对象</h2><p>工作空间中可追溯版本的来源、主张与证据。</p></div><div className="segmented"><button className="active">对象</button><button>关系</button><button>冲突</button></div></div>
      <div className="filter-row"><button>全部类型⌄</button><button>全部状态⌄</button><span className="table-search">⌕ 筛选对象…</span><button className="button primary small">＋ 添加来源</button></div>
      <div className="research-table"><div className="table-head"><span>名称</span><span>类型</span><span>状态</span><span>版本</span><span>更新时间</span></div>{sources.map((s,i)=><button className="table-row" key={s.id} onClick={()=>onSelect(s)}><span className="name-cell"><i className={`file-icon f${i}`}>{s.type.slice(0,1)}</i><span><b>{s.name}</b><small className="mono">{s.id}</small></span></span><span>{s.type}</span><span><Badge tone={s.state === "AI_PROPOSED" ? "purple" : "green"}>{s.state === "AI_PROPOSED" ? "AI 建议" : "已固定"}</Badge></span><span className="mono">{s.version}</span><span>今天</span></button>)}</div>
    </section>
    <section className="relations"><div className="section-title"><div><h2>证据结构</h2><p>当前研究对象之间已确认与待确认的依赖关系。</p></div><button className="text-button">以表格查看 →</button></div><div className="relation-map"><div className="relation-node source-node"><small>来源</small><b>10年期美国国债</b><span>VER_DEMO_20260804</span></div><div className="relation-edge"><span>输入至</span></div><div className="relation-node model-node"><small>模型运行</small><b>M.BRIDGE_OLS.V1</b><span>成功</span></div><div className="relation-edge"><span>支持</span></div><div className="relation-node thesis-node"><small>论题</small><b>财政传导</b><span>已弱化</span></div></div></section>
  </div>;
}

function ValidationView() {
  const steps = [
    ["01","冻结研究定义","定义财政供给、评估窗口、竞争性解释与证伪条件。","COMPLETE"],
    ["02","固定来源版本","将国债收益率快照固定为 VER_DEMO_20260804。","COMPLETE"],
    ["03","运行已注册实证工具","使用冻结的工具请求执行 MacroTrace 利率传导流程。","COMPLETE"],
    ["04","应用证据表述政策","比较关联性输出与所请求的因果表述等级。","READY"],
    ["05","重新编译并生成差异","创建新的论题版本，不覆盖当前对象。","QUEUED"],
  ];
  return <div className="workspace-scroll protocol"><div className="protocol-intro"><div><span className="eyebrow">已注册协议 · VP-001</span><h2>财政供给 → 国债收益率</h2><p>从冻结定义到证据约束表述的确定性验证路径。</p></div><div className="progress-ring"><b>80%</b><span>已完成</span></div></div><div className="protocol-track">{steps.map(([n,title,desc,state],i)=><div className={`protocol-step ${state.toLowerCase()}`} key={n}><div className="step-rail"><span>{state === "COMPLETE" ? "✓" : n}</span>{i < steps.length-1 && <i/>}</div><div className="step-content"><div><h3>{title}</h3><p>{desc}</p></div><Badge tone={state === "COMPLETE" ? "green" : state === "READY" ? "blue" : "neutral"}>{state === "COMPLETE" ? "已完成" : state === "READY" ? "待执行" : "排队中"}</Badge>{i===2 && <div className="step-detail"><dl><dt>工具</dt><dd>MACROTRACE</dd><dt>请求</dt><dd className="mono">TOOL_REQ_DEMO_001</dd><dt>证据类型</dt><dd>关联性</dd><dt>超时限制</dt><dd>180 秒</dd></dl><button className="button secondary">检查运行 →</button></div>}</div></div>)}</div></div>;
}

function MacroTraceView() {
  return <div className="workspace-scroll macro-view"><div className="run-header"><div><span className="eyebrow"><span className="status-dot green"/> 运行完成</span><h2>利率传导</h2><p className="mono">JOB_FIXTURE_001 · M.BRIDGE_OLS.V1</p></div><div className="run-time"><span>耗时</span><b>02:14</b><button className="button secondary">↻ 回放运行</button></div></div>
    <div className="technical-tabs"><button className="active">结果</button><button>参数</button><button>诊断 <Badge tone="green">通过</Badge></button><button>产物</button></div>
    <section className="result-primary"><div><span className="eyebrow">引擎证据</span><h2>检测到条件关联</h2><p>当前注册模型仅返回关联性证据。本样例不包含真实实证结论，不能独立支持因果性表述。</p></div><div className="evidence-grade"><span>证据类型</span><b>关联性</b><small>表述上限</small><strong>仅支持关联</strong></div></section>
    <div className="technical-grid"><section><div className="section-kicker"><span>模型输出</span><Badge tone="green">成功</Badge></div><div className="terminal-output"><div><span>模型配方</span><b>M.BRIDGE_OLS.V1</b></div><div><span>注册表</span><b>macrotrace-fixture</b></div><div><span>覆盖范围</span><b>完整</b></div><div><span>结果哈希</span><b className="mono">22222222…2222</b></div></div></section><section><div className="section-kicker"><span>诊断</span><Badge tone="green">通过</Badge></div><div className="diagnostic"><div className="diag-line"><span>模型专项诊断</span><b>已通过</b></div><p>当前为样例结果，接入真实接口后将替换为实证诊断。</p><div className="metric-line"><span>是否阻断</span><b>否</b></div><div className="metric-line"><span>追踪编号</span><b className="mono">TRACE_FIXTURE_001</b></div></div></section></div>
    <section className="limitations"><div className="limit-icon">!</div><div><h3>证据边界</h3><ul><li>当前是契约样例，不包含真实实证结论。</li><li>关联性证据不能支持因果措辞。</li></ul></div><button className="text-button">打开证据包 →</button></section>
  </div>;
}

function RecompileView() {
  return <div className="workspace-scroll recompile"><section className="recompile-head"><span className="eyebrow">语义重新编译 · THESIS_VER_002</span><h2>证据改变了论题可以如何表述。</h2><p>保留证据支持的原始含义，移除无法获得支持的因果强度。</p></section><section className="semantic-diff"><div className="diff-labels"><span>修改前 · 因果</span><span>修改后 · 关联</span></div><div className="claim-before">美国财政扩张正在持续<del>推高</del>10年期美债收益率。</div><div className="diff-connector"><span>证据表述政策</span><i>↓</i></div><div className="claim-after">当前注册模型提供财政供给指标与10年期美债收益率的<ins>条件关联证据</ins>；现有证据<ins>不足以支持持续、独立的因果措辞</ins>。</div></section><section className="change-rationale"><div className="section-title"><div><h2>为什么表述发生变化</h2><p>每一处修改均可追溯到契约字段或编译问题。</p></div><Badge tone="green">已支持</Badge></div><div className="rationale-row"><span className="change-marker removed">−</span><div><h3>移除“推高”</h3><p>请求的<b>因果</b>等级超过证据包所能支持的<b>关联性</b>等级。</p></div><span className="mono">CLAIM_LANG001</span></div><div className="rationale-row"><span className="change-marker added">＋</span><div><h3>加入证据边界</h3><p>编译后的主张明确说明了获得支持的关联关系及其限制。</p></div><span className="mono">EVIDENCE_DEMO_001</span></div></section><div className="recompile-actions"><button className="button secondary">保留上一版本</button><button className="button primary">接受为新版本 →</button></div></div>;
}

function VersionView() {
  const groups = [["已变更","2","purple",["论题表述等级","规范化主张"]],["已重算","1","blue",["RUN_FIXTURE_001"]],["已复用","1","green",["DATA_US_TREASURY_10Y"]],["已失效","0","neutral",["没有对象失效"]]] as const;
  return <div className="workspace-scroll versions"><div className="version-header"><div><span className="eyebrow">版本比较</span><h2>THESIS_VER_001 <span>→</span> THESIS_VER_002</h2><p>加入关联性证据后，因果主张被调整为与证据等级相符的表述。</p></div><button className="button secondary">导出差异</button></div><div className="version-timeline"><span className="v-dot old">v1</span><i/><div><b>已加入 MacroTrace 证据</b><small>EVIDENCE_DEMO_001 · 关联性</small></div><i/><span className="v-dot new">v2</span></div><div className="diff-groups">{groups.map(([title,count,tone,items])=><section key={title} className={`diff-group ${tone}`}><div><span>{title}</span><b>{count}</b></div>{items.map((item)=><button key={item}><i>{title === "已变更" ? "△" : title === "已重算" ? "↻" : title === "已复用" ? "✓" : "—"}</i><span><b>{item}</b><small>{title === "已变更" ? "已在 THESIS_VER_002 中修改" : title === "已重算" ? "受新增证据影响" : title === "已复用" ? "固定版本未发生变化" : "没有下游影响"}</small></span><em>→</em></button>)}</section>)}</div><section className="impact-summary"><div><span>结论</span><b>已支持</b></div><div><span>重新计算的模型运行</span><b>1</b></div><div><span>发生变化的编译问题</span><b>1</b></div><div><span>复用对象</span><b>1</b></div></section></div>;
}

function LoginScreen({ onEnter, locale, onLocale }: { onEnter: () => void; locale: Locale; onLocale: (locale: Locale) => void }) {
  const [email, setEmail] = useState("");
  const [policyNotice, setPolicyNotice] = useState<string>();
  return <main className="login-shell">
    <section className="login-brand-panel">
      <div className="login-brand"><BrandMark inverse/><span>ResearchOS</span></div>
      <div className="login-statement"><span className="login-index">金融研究操作系统 · 01</span><h1>让证据<br/><em>形成</em><br/>结构。</h1><p>把散落的研究材料变成可追溯的证据结构，再让每一句结论通过编译。</p></div>
      <div className="evidence-field" aria-hidden="true">
        <img className="archivist-login" src="/brand/evidence-archivist.png" alt=""/>
        <div className="e-node n-source"><span>01</span><b>来源</b></div><i className="e-line l1"/><div className="e-node n-evidence"><span>02</span><b>证据</b></div><i className="e-line l2"/><div className="e-node n-thesis"><span>03</span><b>论题</b></div>
      </div>
      <div className="login-foot"><span>研构 · ResearchOS</span><span>v0.1 · 冻结契约</span></div>
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
      <div className="login-form-footer"><button onClick={()=>setPolicyNotice("研究数据始终保留在所选工作空间与部署边界内。")}>{tx(locale,"Privacy")}</button><button onClick={()=>setPolicyNotice("ResearchOS 输出在使用前需要完成证据与来源审核。")}>{tx(locale,"Terms")}</button><span>© 2026 ResearchOS</span></div>
      {policyNotice&&<div className="login-policy-notice" role="status">{policyNotice}<button onClick={()=>setPolicyNotice(undefined)} aria-label="关闭政策提示">×</button></div>}
    </section>
  </main>
}

export default function Home() {
  const [view, setView] = useState<View>("workspace");
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
  const [inspectorVisible, setInspectorVisible] = useState(false);
  const [newThesisOpen, setNewThesisOpen] = useState(false);
  const [draftClaim, setDraftClaim] = useState("");
  const [draftLanguage, setDraftLanguage] = useState("CAUSAL");
  const [creatingThesis, setCreatingThesis] = useState(false);
  const [activeThesis, setActiveThesis] = useState<{ id: string; claim: string; languageLevel: string }>();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  useEffect(()=>{ const key=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();setCommandOpen(v=>!v)} if(e.key==="Escape")setCommandOpen(false)}; addEventListener("keydown",key);return()=>removeEventListener("keydown",key)},[]);
  useEffect(()=>{const media=window.matchMedia("(prefers-color-scheme: dark)");const apply=()=>{const resolved=theme==="system"?(media.matches?"dark":"light"):theme;document.documentElement.dataset.theme=resolved;document.documentElement.style.colorScheme=resolved==="dark"?"dark":"light"};apply();media.addEventListener("change",apply);return()=>media.removeEventListener("change",apply)},[theme]);
  useEffect(()=>{document.documentElement.dataset.reducedMotion=reducedMotion?"true":"false"},[reducedMotion]);
  useEffect(()=>{const start=(event:Event)=>{const name=(event as CustomEvent<{name?:string}>).detail?.name;setDraftClaim(name?`基于「${name}」形成一个可验证的研究主张：`:"");setNewThesisOpen(true)};window.addEventListener("researchos:new-thesis",start);return()=>window.removeEventListener("researchos:new-thesis",start)},[]);
  useEffect(()=>{const openOutput=()=>{setView("report-update");window.setTimeout(()=>window.dispatchEvent(new Event("researchos:report-update")),0)};window.addEventListener("researchos:open-output",openOutput);return()=>window.removeEventListener("researchos:open-output",openOutput)},[]);
  useEffect(()=>{const openMacroTrace=()=>setView("macrotrace");window.addEventListener("researchos:open-macrotrace",openMacroTrace);return()=>window.removeEventListener("researchos:open-macrotrace",openMacroTrace)},[]);
  const current = useMemo(() => nav.find((n) => n.id === view)!, [view]);
  const subtitles: Record<View, string> = {
    "report-update": "按统一数据口径生成周报、月报与专题研究页面。",
    thesis: "依据冻结定义与证据表述政策编译研究主张。",
    workspace: "从公开信息发现线索，用结构化数据验证判断，并沉淀每一条来源。",
    validation: "从研究问题到证据约束结论的连续验证协议。",
    macrotrace: "执行已注册的实证模型，查看诊断与证据输出。",
    recompile: "检查证据如何约束论题的表述强度。",
    versions: "理解增量变化、重新计算与对象复用。",
  };
  const runtimeMode: RuntimeMode = mode;
  const projectSummary = mode === "real" ? `${liveObjectCount} 个对象 · M1 接口` : tx(locale, "4 sources · 1 thesis");
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
  return <main className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`} lang={locale} data-locale={locale} onClickCapture={handleShellClick}>
    <aside className="sidebar"><div className="brand"><BrandMark/><div><b>ResearchOS</b><span>{tx(locale,"Evidence workspace")}</span></div><button className="sidebar-toggle" onClick={()=>setSidebarCollapsed(value=>!value)} aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"} title={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}>{sidebarCollapsed ? "›" : "‹"}</button></div><button className="new-thesis" title="新建研究" onClick={()=>{setView("workspace");window.setTimeout(()=>window.dispatchEvent(new Event("researchos:new-research")),0)}}>＋ <span>新建研究</span><kbd>N</kbd></button><nav><span className="nav-label">{tx(locale,"Research")}</span>{nav.map(item=><button title={tx(locale,item.label)} key={item.id} className={view===item.id?"active":""} onClick={()=>setView(item.id)}><i>{item.icon}</i><span>{tx(locale,item.label)}</span>{(item.id === "workspace" ? "首页" : item.id === "thesis" && activeThesis ? "1" : item.meta)&&<em>{item.id === "workspace" ? "首页" : item.id === "thesis" && activeThesis ? "1" : item.meta}</em>}</button>)}</nav><div className="sidebar-project"><span className="nav-label">{tx(locale,"Active project")}</span><div className="project-card"><div className="project-icon">{view==="report-update"||view==="workspace"?"IM":"FT"}</div><div><b>{view==="report-update"||view==="workspace"?"国际市场研究":tx(locale,"Fiscal transmission")}</b><span>{view==="report-update"?"3 个数据集 · 周报出品":view==="workspace"?"公开资料 · 市场数据 · 内部资料":projectSummary}</span></div><button>···</button></div></div><div className="sidebar-bottom"><button title={tx(locale,"Activity")}><i>⌁</i><span>{tx(locale,"Activity")}</span><em>3</em></button><button title={tx(locale,"Help & shortcuts")}><i>?</i><span>{tx(locale,"Help & shortcuts")}</span></button><div className="sync-state"><span className="status-dot green"/><div><b>{tx(locale,"Workspace synced")}</b><small>{tx(locale,"Just now")}</small></div></div></div></aside>
    <section className="main-frame"><Topbar title={current.label} subtitle={subtitles[view]} onCommand={()=>setCommandOpen(true)} onInspector={()=>setInspectorVisible(value=>!value)} onSettings={()=>setSettingsOpen(true)} onPrimary={()=>view==="workspace"?window.dispatchEvent(new Event("researchos:new-research")):view==="report-update"?window.dispatchEvent(new Event("researchos:report-update")):runPrimaryFlow()} locale={locale} onLocale={setLocale} mode={runtimeMode} workspace={view==="workspace"} reportUpdate={view==="report-update"}/>{view !== "workspace" && view !== "report-update" && mode !== "real" && <RuntimeNotice mode={runtimeMode} scenario={scenario} onRetry={()=>setScenario("running")} onReset={()=>setScenario("complete")}/>}<div className={`content-frame ${inspectorVisible ? "" : "inspector-hidden"}`}>{view!=="workspace"&&view!=="report-update"&&mode==="real"&&<LiveResearchFlow view={view} locale={locale} thesisId={activeThesis?.id} claim={activeThesis?.claim} languageLevel={activeThesis?.languageLevel}/>} {view==="report-update"&&<ResearchOutputStudio/>} {view==="thesis"&&mode!=="real"&&<ThesisView locale={locale}/>} {view==="workspace"&&(mode === "real" ? <RealWorkspace onSelect={(item: WorkspaceSource)=>{setSelectedSource(item);setInspectorOpen(true)}} onObjectCount={setLiveObjectCount}/> : <WorkspaceView onSelect={(item)=>{setSelectedSource(item);setInspectorOpen(true)}}/>)} {view==="validation"&&mode!=="real"&&<ValidationView/>}{view==="macrotrace"&&mode!=="real"&&<MacroTraceView/>}{view==="recompile"&&mode!=="real"&&<RecompileView/>}{view==="versions"&&mode!=="real"&&<VersionView/>}{inspectorVisible&&<Inspector selectedSource={selectedSource} locale={locale}/>}</div></section>
    <InspectorDrawer open={inspectorOpen} onOpenChange={setInspectorOpen} selectedSource={selectedSource} locale={locale}/>
    <SettingsCenter open={settingsOpen} onOpenChange={setSettingsOpen} theme={theme} onTheme={setTheme} locale={locale} onLocale={setLocale} reducedMotion={reducedMotion} onReducedMotion={setReducedMotion} mode={mode} onMode={setMode} scenario={scenario} onScenario={setScenario} onReset={()=>{setView("thesis");setSelectedSource(undefined);setMode("fixture");setScenario("complete");setSettingsOpen(false)}}/>
    <Dialog.Root open={newThesisOpen} onOpenChange={setNewThesisOpen}><Dialog.Portal><Dialog.Overlay className="thesis-dialog-overlay"/><Dialog.Content className="thesis-dialog"><Dialog.Title>{locale === "en" ? "Create thesis" : locale === "zh-TW" ? "建立論題" : "新建论题"}</Dialog.Title><Dialog.Description>{locale === "en" ? "Define the claim first. Evidence will constrain its language during compilation." : "先定义可验证的研究主张，证据将在编译时约束其语言强度。"}</Dialog.Description><form onSubmit={createThesis}><label><span>{locale === "en" ? "Research claim" : "研究主张"}</span><textarea autoFocus required value={draftClaim} onChange={event=>setDraftClaim(event.target.value)} placeholder={locale === "en" ? "e.g. Fiscal expansion is associated with higher 10-year Treasury yields." : "例如：财政扩张与10年期美债收益率上升相关。"}/></label><label><span>{locale === "en" ? "Requested language" : "请求语言强度"}</span><select value={draftLanguage} onChange={event=>setDraftLanguage(event.target.value)}><option value="CAUSAL">CAUSAL · 因果</option><option value="ASSOCIATIONAL">ASSOCIATIONAL · 关联</option><option value="DESCRIPTIVE">DESCRIPTIVE · 描述</option></select></label><div className="thesis-dialog-note"><i>◇</i><span>{locale === "en" ? "The original claim is versioned. Recompile creates a new immutable build." : "原始主张将被版本化；重新编译会生成新的不可变构建。"}</span></div><div className="thesis-dialog-actions"><Dialog.Close type="button" className="button secondary">{locale === "en" ? "Cancel" : "取消"}</Dialog.Close><button className="button primary" disabled={creatingThesis || !draftClaim.trim()}>{creatingThesis ? (locale === "en" ? "Saving…" : "正在保存…") : (locale === "en" ? "Create thesis" : "创建论题")}</button></div></form></Dialog.Content></Dialog.Portal></Dialog.Root>
    {commandOpen&&<div className="command-overlay" onMouseDown={()=>setCommandOpen(false)}><div className="command" onMouseDown={e=>e.stopPropagation()}><div className="command-input"><span>⌕</span><input autoFocus placeholder={`${tx(locale,"Search or command")}…`}/><kbd>ESC</kbd></div><span className="command-label">功能导航</span>{nav.map(n=><button key={n.id} onClick={()=>{setView(n.id);setCommandOpen(false)}}><i>{n.icon}</i><span>{tx(locale,n.label)}</span><kbd>↵</kbd></button>)}</div></div>}
    {actionNotice&&<div className="action-toast" role="status"><i>✓</i><span>{actionNotice}</span></div>}
  </main>;
}
