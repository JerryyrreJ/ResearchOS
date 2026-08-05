"use client";
/* eslint-disable @next/next/no-img-element -- source favicons are remote evidence metadata */

import { useCallback, useEffect, useRef, useState } from "react";
import { researchosApi, type ObjectSummary, type WorkspaceSource } from "../lib/api-client";

type QueueStatus = "QUEUED" | "UPLOADING" | "COMPLETED" | "DUPLICATE" | "FAILED";
type QueueItem = { id:string; fileName:string; status:QueueStatus; detail?:string };
type ResearchState = "idle" | "running" | "complete";
type SourceTab = "all" | "web" | "data" | "local";
type RealWorkspaceProps = { onSelect:(item:WorkspaceSource)=>void; onObjectCount:(count:number)=>void };

const publicSources = [
  {id:"WEB_01",kind:"web" as const,mark:"FED",title:"美联储 · 货币政策与数据发布",detail:"官方政策与数据发布",meta:"公开 · 官方",url:"https://www.federalreserve.gov/"},
  {id:"WEB_02",kind:"web" as const,mark:"BLS",title:"美国劳工统计局 · CPI",detail:"通胀数据与发布时间表",meta:"公开 · 官方",url:"https://www.bls.gov/cpi/"},
  {id:"WEB_03",kind:"web" as const,mark:"新闻",title:"美股上涨集中度与市场宽度讨论",detail:"新闻与市场观点聚类",meta:"12 个相关链接",url:"#"},
];
const dataSources = [
  {id:"DATA_01",kind:"data" as const,mark:"接口",title:"标普 500 与成分股贡献",detail:"指数收益、权重与贡献率",meta:"截止 2024-01-12",url:"#"},
  {id:"DATA_02",kind:"data" as const,mark:"FRED",title:"10 年期美国国债固定期限利率",detail:"DGS10 · 日频",meta:"已固定版本",url:"https://fred.stlouisfed.org/series/DGS10"},
  {id:"DATA_03",kind:"data" as const,mark:"模型",title:"MacroTrace · 市场宽度模型设定",detail:"回归设定、诊断与稳健性检查",meta:"待运行",url:"#"},
];
const samplePrompts = ["本周美股上涨是否主要由少数科技龙头驱动？","近期利率变化对 REITs 二级市场表现有什么影响？","结合政策与数据，寻找本周值得跟踪的宏观研究线索。"];

function sourceFromObject(item:ObjectSummary):WorkspaceSource{
  const current=item.current_version;
  return {type:"SOURCE_FILE",name:item.name,id:item.object_id,version:current?.version_id??"—",state:item.status,origin:"api",formatKind:current?.format_kind??"UNKNOWN",sizeBytes:current?.size_bytes??0,fragmentCount:item.fragment_count,versionCount:item.version_count,updatedAt:current?.created_at??item.created_at};
}
function readableBytes(value:number){if(value<1024)return`${value} B`;if(value<1024*1024)return`${(value/1024).toFixed(1)} KB`;return`${(value/1024/1024).toFixed(1)} MB`}
function queueLabel(item:QueueItem){
  if(item.status==="DUPLICATE")return"重复文件 · 已跳过";
  if(item.status==="COMPLETED"&&item.detail==="NEW_VERSION")return"已建立新版本";
  if(item.status==="COMPLETED"&&item.detail==="NEW_ASSET")return"已加入资料库";
  return{QUEUED:"等待上传",UPLOADING:"上传中",COMPLETED:"已完成",DUPLICATE:"重复文件",FAILED:"上传失败"}[item.status];
}

export default function RealWorkspace({onSelect,onObjectCount}:RealWorkspaceProps){
  const inputRef=useRef<HTMLInputElement>(null);
  const questionRef=useRef<HTMLTextAreaElement>(null);
  const dragDepthRef=useRef(0);
  const onObjectCountRef=useRef(onObjectCount);
  const [workspaceId,setWorkspaceId]=useState<string>();
  const [objects,setObjects]=useState<ObjectSummary[]>([]);
  const [queue,setQueue]=useState<QueueItem[]>([]);
  const [question,setQuestion]=useState(samplePrompts[0]);
  const [submittedQuestion,setSubmittedQuestion]=useState("");
  const [researchState,setResearchState]=useState<ResearchState>("idle");
  const [sourceTab,setSourceTab]=useState<SourceTab>("all");
  const [selectedSource,setSelectedSource]=useState("WEB_03");
  const [dragging,setDragging]=useState(false);
  const [error,setError]=useState<string>();
  const [notice,setNotice]=useState<string>();

  useEffect(()=>{onObjectCountRef.current=onObjectCount},[onObjectCount]);
  const refresh=useCallback(async(id:string)=>{const nextObjects=await researchosApi.listObjects(id);setObjects(nextObjects);onObjectCountRef.current(nextObjects.length)},[]);
  useEffect(()=>{let cancelled=false;void(async()=>{try{let workspaces=await researchosApi.listWorkspaces();if(!workspaces.length)workspaces=[await researchosApi.createWorkspace("Financial research workspace")];if(cancelled)return;setWorkspaceId(workspaces[0].id);await refresh(workspaces[0].id)}catch(caught){if(!cancelled)setError(caught instanceof Error?caught.message:"Unable to load workspace")}})();return()=>{cancelled=true}},[refresh]);
  useEffect(()=>{const choose=()=>inputRef.current?.click();const focus=()=>{setResearchState("idle");requestAnimationFrame(()=>questionRef.current?.focus())};window.addEventListener("researchos:choose-files",choose);window.addEventListener("researchos:new-research",focus);return()=>{window.removeEventListener("researchos:choose-files",choose);window.removeEventListener("researchos:new-research",focus)}},[]);

  const notify=(message:string)=>{setNotice(message);window.setTimeout(()=>setNotice(undefined),2600)};
  const acceptFiles=async(incoming:File[])=>{
    if(!workspaceId||!incoming.length)return;
    const initial=incoming.map((file,index)=>({id:`${file.name}-${file.lastModified}-${index}`,fileName:file.name,status:"QUEUED" as const}));setQueue(initial);
    try{const batch=await researchosApi.createBatch(workspaceId);for(const[index,file]of incoming.entries()){const itemId=initial[index].id;setQueue(current=>current.map(item=>item.id===itemId?{...item,status:"UPLOADING"}:item));try{const outcome=await researchosApi.uploadFile(batch.id,file,workspaceId);setQueue(current=>current.map(item=>item.id===itemId?{...item,status:outcome.status==="DUPLICATE"?"DUPLICATE":"COMPLETED",detail:outcome.resolution_status??undefined}:item))}catch(caught){setQueue(current=>current.map(item=>item.id===itemId?{...item,status:"FAILED",detail:caught instanceof Error?caught.message:"Upload failed"}:item))}}await researchosApi.finalizeBatch(batch.id);await refresh(workspaceId);notify("内部资料已加入本次研究的证据范围")}catch(caught){setError(caught instanceof Error?caught.message:"Unable to upload files")}
  };
  const onDrop=(event:React.DragEvent<HTMLDivElement>)=>{event.preventDefault();dragDepthRef.current=0;setDragging(false);void acceptFiles(Array.from(event.dataTransfer.files))};
  const submitResearch=(event:React.FormEvent)=>{event.preventDefault();if(!question.trim())return;setSubmittedQuestion(question.trim());setResearchState("running");window.setTimeout(()=>setResearchState("complete"),850)};
  const localSources=objects.map(item=>({id:item.object_id,kind:"local" as const,mark:(item.current_version?.format_kind??"文件").slice(0,4),title:item.name,detail:`${readableBytes(item.current_version?.size_bytes??0)} · ${item.version_count} 个版本`,meta:"内部工作空间",url:"#",object:item}));
  const allSources=[...publicSources,...dataSources,...localSources];
  const visibleSources=allSources.filter(item=>sourceTab==="all"||item.kind===sourceTab);

  return <div className={`workspace-scroll financial-research ${dragging?"is-dragging":""}`} onDragEnter={event=>{event.preventDefault();if(event.dataTransfer.types.includes("Files")){dragDepthRef.current+=1;setDragging(true)}}} onDragOver={event=>event.preventDefault()} onDragLeave={event=>{event.preventDefault();dragDepthRef.current=Math.max(0,dragDepthRef.current-1);if(!dragDepthRef.current)setDragging(false)}} onDrop={onDrop}>
    {dragging&&<div className="workspace-drop-overlay" role="status"><img src="/brand/evidence-archivist.png" alt=""/><b>加入本次研究</b><span>松开后作为内部证据保存，不会覆盖公开来源</span></div>}
    <div className="financial-research-grid">
      <main className="research-chat">
        {researchState==="idle"&&<section className="research-welcome"><span className="eyebrow"><span className="status-dot green"/> 国际市场研究</span><h2>从一个研究问题开始</h2><p>检索公开资料、核对市场数据并引用内部文件。所有结论均保留来源、数据截止日期和适用范围。</p><div className="research-capabilities"><span><i>⌕</i><b>公开资料</b><small>新闻 · 政策 · 公告 · 财报</small></span><span><i>↳</i><b>市场数据</b><small>行情 · 宏观 · 估值 · 实证检验</small></span><span><i>◇</i><b>内部资料</b><small>团队文件 · 历史报告 · 研究底稿</small></span></div><div className="prompt-suggestions">{samplePrompts.map(item=><button key={item} onClick={()=>setQuestion(item)}>{item}<span>→</span></button>)}</div></section>}
        {researchState!=="idle"&&<section className="research-conversation">
          <article className="user-query"><div>LY</div><p>{submittedQuestion}</p></article>
          <article className="assistant-research"><header><div className="assistant-mark">研</div><div><b>研究结果</b><span>{researchState==="running"?"正在检索并核对数据…":"资料与数据已汇总"}</span></div><em>2 类信息源</em></header>
            <div className="research-plan"><span>检索范围</span><p>先核对公开资料中对“上涨集中度”的讨论，再使用指数成分贡献、市场宽度和估值数据验证其方向与强度。</p></div>
            <div className="dual-route">
              <section className={researchState==="complete"?"complete":"running"}><header><i>⌕</i><div><b>公开资料</b><span>新闻、政策、公告与市场评论</span></div><em>{researchState==="complete"?"已汇总":"检索中"}</em></header><div className="route-line"><span/><p>覆盖政策、公司公告、机构观点与市场新闻</p></div><div className="route-line"><span/><p>{researchState==="complete"?"28 个来源归纳为 6 个相关主题":"正在补充宏观与行业相关资料…"}</p></div>{researchState==="complete"&&<footer><b>资料共识</b><p>“指数上涨但市场宽度有限”在多个独立来源中重复出现。</p></footer>}</section>
              <section className={researchState==="complete"?"complete":"running"}><header><i>↳</i><div><b>市场数据</b><span>指数、成分、估值与利率</span></div><em>{researchState==="complete"?"可检验":"核对中"}</em></header><div className="route-line"><span/><p>核对指数收益、成分股贡献与利率数据</p></div><div className="route-line"><span/><p>{researchState==="complete"?"统计口径已对齐，可进入实证检验":"正在检查频率、截止日期与缺失值…"}</p></div>{researchState==="complete"&&<footer><b>检验方案</b><p>比较头部权重股贡献率、等权指数与市值加权指数差异。</p></footer>}</section>
            </div>
            {researchState==="complete"&&<div className="research-answer"><div className="answer-label"><span>研究结论（初稿）</span><em>证据等级：关联性</em></div><h3>美股上涨具有较明显的头部集中现象，但尚不足以判断市场风险偏好已全面改善。</h3><p>公开资料与当前市场数据在方向上相互支持：指数上涨主要由少数大型科技公司贡献，而等权表现与市场宽度相对较弱。该结论目前属于<strong>描述性与关联性判断</strong>；是否构成持续性的结构变化，仍需补充更长时间窗口并完成实证检验。</p><div className="claim-evidence"><span><b>6</b>相关主题</span><span><b>3</b>有效数据集</span><span><b>1</b>待检验问题</span><span><b>0</b>缺失来源</span></div><footer><button className="button secondary" onClick={()=>window.dispatchEvent(new CustomEvent("researchos:open-macrotrace",{detail:{question:submittedQuestion}}))}>开始实证检验 ↳</button><button className="button secondary" onClick={()=>window.dispatchEvent(new CustomEvent("researchos:new-thesis",{detail:{name:"美股上涨主要由少数科技龙头集中驱动，而非市场宽度全面改善"}}))}>加入验证计划 ◇</button><button className="button primary" onClick={()=>window.dispatchEvent(new Event("researchos:open-output"))}>形成周报页面 →</button></footer></div>}
          </article>
        </section>}
        <form className="research-composer" onSubmit={submitResearch}><textarea ref={questionRef} value={question} onChange={event=>setQuestion(event.target.value)} aria-label="输入金融研究问题" placeholder="输入需要研究的问题…"/><div><span><button type="button" className="composer-tool active">⌕ 公开资料</button><button type="button" className="composer-tool active">↳ 市场数据</button><button type="button" className="composer-tool" onClick={()=>inputRef.current?.click()}>＋ 内部资料</button></span><button className="composer-send" disabled={!question.trim()||researchState==="running"} aria-label="开始研究">↑</button></div></form>
        <input ref={inputRef} type="file" multiple hidden onChange={event=>{void acceptFiles(Array.from(event.target.files??[]));event.target.value=""}}/>
      </main>

      <aside className="evidence-drawer"><header><div><span>当前研究</span><h3>资料与数据</h3></div><button onClick={()=>inputRef.current?.click()}>＋ 添加</button></header><nav><button className={sourceTab==="all"?"active":""} onClick={()=>setSourceTab("all")}>全部 <em>{allSources.length}</em></button><button className={sourceTab==="web"?"active":""} onClick={()=>setSourceTab("web")}>公开资料 <em>{publicSources.length}</em></button><button className={sourceTab==="data"?"active":""} onClick={()=>setSourceTab("data")}>市场数据 <em>{dataSources.length}</em></button><button className={sourceTab==="local"?"active":""} onClick={()=>setSourceTab("local")}>内部资料 <em>{localSources.length}</em></button></nav><div className="evidence-drawer-list">{visibleSources.map(item=><button key={item.id} className={selectedSource===item.id?"selected":""} onClick={()=>{setSelectedSource(item.id);if("object" in item)onSelect(sourceFromObject(item.object));else if(item.url!=="#")window.open(item.url,"_blank","noopener,noreferrer")}}><i className={`source-mark ${item.kind}`}>{item.mark}</i><span><b>{item.title}</b><small>{item.detail}</small><em>{item.meta}</em></span><strong>↗</strong></button>)}</div><section className="evidence-drawer-foot"><div><span className="status-dot green"/><b>已归入当前研究</b></div><p>引用过的链接、数据和内部文件统一保存在这里，便于复核和继续写作。</p><button onClick={()=>inputRef.current?.click()}>添加内部资料</button></section>{queue.length>0&&<section className="compact-upload"><span>上传队列</span>{queue.map(item=><div key={item.id}><b>{item.fileName}</b><em>{queueLabel(item)}</em></div>)}</section>}{error&&<div className="research-api-note"><b>内部资料暂不可用</b><span>公开资料与市场数据仍可正常检索。</span></div>}</aside>
    </div>{notice&&<div className="report-toast" role="status">✓ {notice}</div>}
  </div>;
}
