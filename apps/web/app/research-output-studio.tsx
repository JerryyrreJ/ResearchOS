"use client";

import { useEffect, useMemo, useState } from "react";

type TemplateId = "weekly" | "overseas" | "reits";
type Dataset = { id:string; name:string; detail:string; asOf:string; state:"READY"|"STALE"; selected:boolean };

const templates = [
  { id:"weekly" as const, name:"国际市场周报", note:"市场总表、资产表现、估值比较、研究结论", sample:"创金合信国际市场周报" },
  { id:"overseas" as const, name:"海外市场月报", note:"权益、利率、汇率、资金流与风险提示", sample:"海外市场月报" },
  { id:"reits" as const, name:"REITs 市场月报", note:"规模估值、发行交易、分红与政策跟踪", sample:"REITs 市场月度报告" },
];

const initialDatasets: Dataset[] = [
  {id:"GLOBAL_ASSET_W",name:"全球大类资产周涨跌",detail:"股票、债券、商品与汇率",asOf:"2024-01-12",state:"READY",selected:true},
  {id:"INDEX_VALUATION",name:"主要市场估值",detail:"预测 PE / PB 与历史分位",asOf:"2024-01-12",state:"READY",selected:true},
  {id:"US_MACRO",name:"美国宏观与利率",detail:"CPI、经济意外指数、10年期美债",asOf:"2024-01-11",state:"READY",selected:true},
  {id:"MARKET_FLOW",name:"跨境资金流与成交",detail:"资金流、成交额与市场宽度",asOf:"2024-01-05",state:"STALE",selected:false},
];

const marketRows = [
  {region:"美国股市",name:"标普500指数",weekly:1.84,ytd:0.29,close:"4,783.83"},
  {region:"美国股市",name:"道琼斯指数",weekly:0.34,ytd:-0.26,close:"37,592.98"},
  {region:"美国股市",name:"纳斯达克指数",weekly:3.09,ytd:-0.26,close:"14,972.76"},
  {region:"香港股市",name:"恒生指数",weekly:-1.76,ytd:-4.71,close:"16,244.58"},
  {region:"香港股市",name:"恒生中国指数",weekly:-2.23,ytd:-4.97,close:"5,481.94"},
  {region:"欧洲、日本",name:"英国富时100指数",weekly:-0.84,ytd:-1.40,close:"7,624.93"},
  {region:"欧洲、日本",name:"德国DAX指数",weekly:0.66,ytd:-0.28,close:"16,704.56"},
  {region:"欧洲、日本",name:"法国CAC40指数",weekly:0.60,ytd:-1.03,close:"7,465.14"},
  {region:"欧洲、日本",name:"日本日经225指数",weekly:6.59,ytd:6.31,close:"35,577.11"},
  {region:"其他",name:"WTI原油期货",weekly:-1.53,ytd:1.44,close:"72.68"},
  {region:"其他",name:"黄金每盎司",weekly:0.18,ytd:-0.67,close:"2,049.06"},
  {region:"其他",name:"美国10年期国债收益率",weekly:-10.67,ytd:5.99,close:"3.94%",bp:true},
];

const chartAssets = marketRows.filter(item => ["标普500指数","纳斯达克指数","恒生指数","日本日经225指数","WTI原油期货","黄金每盎司"].includes(item.name));
const valuationRows = [
  {sector:"主要指数",cn:[11.6,1.3],hk:[10.0,1.1],us:[22.6,4.4]},
  {sector:"公用事业",cn:[14.5,1.8],hk:[7.8,0.9],us:[16.8,1.9]},
  {sector:"信息技术",cn:[31.2,2.8],hk:[17.8,1.7],us:[34.2,11.0]},
  {sector:"主要消费",cn:[25.4,5.2],hk:[20.2,3.1],us:[20.4,5.8]},
  {sector:"金融地产",cn:[6.0,0.6],hk:[4.1,0.4],us:[15.7,2.0]},
  {sector:"能源",cn:[8.7,1.2],hk:[6.2,0.8],us:[10.3,2.1]},
];

const formatMove = (value:number,bp=false) => `${value>0?"+":""}${value.toFixed(2)}${bp?" bp":"%"}`;
const heatTone = (value:number) => value >= 25 ? "heat-high" : value >= 15 ? "heat-mid" : value <= 8 ? "heat-low" : "heat-base";

export default function ResearchOutputStudio(){
  const [template,setTemplate]=useState<TemplateId>("weekly");
  const [datasets,setDatasets]=useState(initialDatasets);
  const [brief,setBrief]=useState("重点关注美股上涨的结构、主要市场估值水平及利率变化；结论必须注明数据截止日和可支持的表述范围。");
  const [generated,setGenerated]=useState(false);
  const [notice,setNotice]=useState<string>();
  const selectedCount=useMemo(()=>datasets.filter(item=>item.selected).length,[datasets]);
  const currentTemplate=templates.find(item=>item.id===template)!;
  const notify=(message:string)=>{setNotice(message);window.setTimeout(()=>setNotice(undefined),2600)};
  const generate=()=>{setGenerated(true);notify(`${currentTemplate.name} 已更新`)};
  const toggleDataset=(id:string)=>setDatasets(items=>items.map(item=>item.id===id?{...item,selected:!item.selected}:item));
  const exportBundle=()=>{
    const payload={schema:"researchos.research-publication.v2",report:currentTemplate.name,as_of:"2024-01-12",brief,datasets:datasets.filter(item=>item.selected).map(item=>({id:item.id,as_of:item.asOf})),sections:["market_table","asset_performance","valuation_comparison","research_conclusion"],review_state:"PENDING_REVIEW"};
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});
    const link=document.createElement("a");link.href=URL.createObjectURL(blob);link.download="international-market-weekly.json";link.click();URL.revokeObjectURL(link.href);notify("报告数据包已导出");
  };
  useEffect(()=>{const run=()=>generate();window.addEventListener("researchos:report-update",run);return()=>window.removeEventListener("researchos:report-update",run)});

  if(!generated) return <div className="workspace-scroll output-studio setup">
    <section className="output-intro"><div><span className="eyebrow"><span className="status-dot green"/> 研究出品</span><h2>按机构标准生成周报、月报与专题报告</h2><p>确定数据范围、报告结构和本期重点。系统按统一口径生成表格、图表、来源说明与研究结论，供研究员审阅定稿。</p></div><div className="output-route"><span>数据范围</span><i>→</i><span>报告结构</span><i>→</i><b>审阅发布</b></div></section>
    <div className="output-setup-grid">
      <section className="output-panel source-panel"><header><div><span>01 · 数据范围</span><h3>选择本期数据</h3></div><em>{selectedCount} 项已纳入</em></header><p className="panel-help">只有处于有效期内的数据会进入本期报告；过期数据需更新后才能使用。</p><div className="dataset-list">{datasets.map(item=><button key={item.id} className={item.selected?"selected":""} onClick={()=>toggleDataset(item.id)}><i>{item.selected?"✓":"＋"}</i><span><b>{item.name}</b><small>{item.detail}</small></span><time>{item.asOf}</time><em className={`badge badge-${item.state==="READY"?"green":"amber"}`}>{item.state==="READY"?"有效":"需更新"}</em></button>)}</div><button className="output-add-source" onClick={()=>notify("可返回研究助手补充数据和资料")}>＋ 补充数据或资料</button></section>
      <section className="output-panel template-panel"><header><div><span>02 · 报告结构</span><h3>选择出品类型</h3></div><em>机构报告模板</em></header><p className="panel-help">版式参照正式投研周报与月报，统一标题层级、图表规范、来源和页码。</p><div className="template-list">{templates.map(item=><button key={item.id} className={template===item.id?"selected":""} onClick={()=>setTemplate(item.id)}><i>{template===item.id?"●":"○"}</i><span><b>{item.name}</b><small>{item.note}</small><em>参考结构 · {item.sample}</em></span></button>)}</div></section>
      <section className="output-panel brief-panel"><header><div><span>03 · 本期重点</span><h3>确定研究范围与结论口径</h3></div><em>编辑说明</em></header><textarea value={brief} onChange={event=>setBrief(event.target.value)} aria-label="本期研究重点"/><div className="brief-suggestions"><button onClick={()=>setBrief("梳理全球大类资产周度表现，比较主要指数估值，并解释本周显著变化。")}>市场综述</button><button onClick={()=>setBrief("重点分析美股上涨的集中度、主要驱动行业及估值风险。")}>美股结构</button><button onClick={()=>setBrief("跟踪 REITs 发行、成交、分红与政策变化，形成月度结论。")}>REITs 跟踪</button></div><div className="generation-boundary"><i>✓</i><span><b>出品规范</b><small>所有图表均保留单位、统计区间、数据来源和截止日期；研究判断与原始数据分开呈现。</small></span></div><button className="button primary generate-output" disabled={!selectedCount||!brief.trim()} onClick={generate}>生成 {currentTemplate.name} <span>→</span></button></section>
    </div>{notice&&<div className="report-toast" role="status">✓ {notice}</div>}
  </div>;

  return <div className="workspace-scroll output-studio publication-mode">
    <section className="canvas-toolbar"><div><button onClick={()=>setGenerated(false)}>← 修改报告设置</button><span>国际市场周报 · 2024年第02期</span><em className="badge badge-amber">待审阅</em></div><div><button className="button secondary" onClick={()=>notify("草稿已保存为 v1")}>保存草稿</button><button className="button primary" onClick={exportBundle}>导出报告数据 ↓</button></div></section>
    <div className="publication-layout"><div className="publication-stack">
      <article className="publication-page">
        <header className="publication-head"><div><span className="publication-brand">研构 ResearchOS</span><small>国际市场研究</small></div><div><h2>海外观市 · 周评</h2><p>2024年第02期</p></div></header>
        <section className="publication-title"><span>一、全球市场</span><h1>国际市场周度跟踪</h1><p>统计区间：2024年1月8日 - 2024年1月12日</p></section>
        <section className="weekly-summary"><h3>本周摘要</h3><ul><li>美股主要指数收涨，纳斯达克指数周涨幅领先；上涨结构仍较集中。</li><li>日经225指数表现突出，香港市场继续承压；大类资产分化明显。</li><li>美国10年期国债收益率回落至3.94%，主要市场估值仍处于分化状态。</li></ul></section>
        <section className="publication-section"><div className="publication-section-title"><h3>1. 全球主要市场表现</h3><span>单位：%，国债收益率变动为 bp</span></div><table className="market-table"><thead><tr><th>区域</th><th>名称</th><th>周涨跌</th><th>年初至今</th><th>收盘</th></tr></thead><tbody>{marketRows.map((row,index)=><tr key={row.name}><td>{index===0||marketRows[index-1].region!==row.region?row.region:""}</td><td>{row.name}</td><td className={row.weekly>=0?"positive":"negative"}>{formatMove(row.weekly,row.bp)}</td><td className={row.ytd>=0?"positive":"negative"}>{formatMove(row.ytd,row.bp)}</td><td>{row.close}</td></tr>)}</tbody></table><p className="chart-source">数据来源：公开市场数据；数据截止日期：2024年1月12日。</p></section>
        <section className="publication-section"><div className="publication-section-title"><h3>2. 大类资产周度表现</h3><span>零轴比较</span></div><svg className="professional-bar-chart" viewBox="0 0 700 230" role="img" aria-label="全球主要资产周度涨跌柱状图"><line className="axis" x1="52" y1="178" x2="680" y2="178"/>{[-2,0,2,4,6].map(tick=><g key={tick}><line className="grid" x1="52" y1={178-tick*22} x2="680" y2={178-tick*22}/><text x="44" y={182-tick*22} textAnchor="end">{tick}%</text></g>)}{chartAssets.map((item,index)=>{const x=78+index*98;const height=Math.abs(item.weekly)*22;const y=item.weekly>=0?178-height:178;return <g key={item.name}><rect className={item.weekly>=0?"bar-up":"bar-down"} x={x} y={y} width="42" height={height}/><text className="bar-value" x={x+21} y={item.weekly>=0?y-6:y+height+13} textAnchor="middle">{formatMove(item.weekly)}</text><text className="category" x={x+21} y="201" textAnchor="middle">{item.name.replace("指数","")}</text></g>})}</svg><p className="chart-note">注：股票以主要市场指数表示，商品以对应期货或现货价格表示。不同资产收益率仅用于方向比较。</p><p className="chart-source">数据来源：公开市场数据；ResearchOS 整理。</p></section>
        <footer className="publication-foot"><span>仅供内部研究使用</span><span>数据截止：2024-01-12</span><b>1</b></footer>
      </article>

      <article className="publication-page">
        <header className="publication-head compact"><div><span className="publication-brand">研构 ResearchOS</span><small>国际市场研究</small></div><div><h2>海外观市 · 周评</h2><p>2024年第02期</p></div></header>
        <section className="publication-title small"><span>二、估值与宏观</span><h1>主要市场估值及宏观信号</h1></section>
        <section className="publication-section"><div className="publication-section-title"><h3>1. 中美港主要行业估值对比</h3><span>预测 PE / PB</span></div><table className="valuation-table"><thead><tr><th rowSpan={2}>行业</th><th colSpan={2}>沪深300</th><th colSpan={2}>香港</th><th colSpan={2}>美国</th></tr><tr><th>PE</th><th>PB</th><th>PE</th><th>PB</th><th>PE</th><th>PB</th></tr></thead><tbody>{valuationRows.map(row=><tr key={row.sector}><td>{row.sector}</td>{[...row.cn,...row.hk,...row.us].map((value,index)=><td key={index} className={heatTone(index%2===0?value:value*6)}>{value.toFixed(1)}</td>)}</tr>)}</tbody></table><div className="heat-legend"><span>估值较低</span><i/><i/><i/><i/><span>估值较高</span></div><p className="chart-source">数据来源：公开一致预期数据；数据截止日期：2024年1月12日。</p></section>
        <section className="publication-section"><div className="publication-section-title"><h3>2. 经济意外指数</h3><span>2018年1月 - 2024年1月</span></div><p className="section-intro">经济意外指数衡量实际公布数据相对市场预期的偏离程度。正值表示总体数据好于预期，负值表示不及预期。</p><svg className="professional-line-chart" viewBox="0 0 700 235" role="img" aria-label="中美经济意外指数趋势图">{[-100,-50,0,50,100].map((tick,index)=><g key={tick}><line className={tick===0?"axis":"grid"} x1="58" y1={34+index*38} x2="680" y2={34+index*38}/><text x="49" y={38+index*38} textAnchor="end">{100-index*50}</text></g>)}<polyline className="line-us" points="58,118 110,105 162,132 214,84 266,146 318,68 370,93 422,75 474,124 526,61 578,112 630,91 680,101"/><polyline className="line-cn" points="58,93 110,126 162,114 214,141 266,96 318,119 370,139 422,103 474,79 526,130 578,88 630,122 680,116"/>{["2018","2019","2020","2021","2022","2023","2024"].map((year,index)=><text className="year" key={year} x={58+index*103.5} y="223" textAnchor={index===0?"start":index===6?"end":"middle"}>{year}</text>)}</svg><div className="line-legend"><span><i className="us"/>美国经济意外指数</span><span><i className="cn"/>中国经济意外指数</span></div><p className="chart-source">数据来源：公开宏观数据库；ResearchOS 整理。</p></section>
        <section className="research-conclusion"><div><span>研究结论</span><em>审阅口径：描述性判断</em></div><h3>美股上涨延续，但估值与市场宽度提示结构性分化仍需关注。</h3><p>本周主要美股指数上涨，其中纳斯达克表现领先；当前数据支持“收益向少数高权重成长板块集中”的描述。估值比较显示，美国信息技术板块相对中港市场仍处高位。上述证据尚不足以单独推导风险偏好已全面改善，后续需结合盈利预期、市场宽度和资金流继续验证。</p><footer><span>关联数据：GLOBAL_ASSET_W · INDEX_VALUATION · US_MACRO</span><button onClick={()=>window.dispatchEvent(new CustomEvent("researchos:new-thesis",{detail:{name:"美股上涨主要由高权重成长板块驱动，市场宽度尚未全面改善"}}))}>建立验证任务 →</button></footer></section>
        <footer className="publication-foot"><span>仅供内部研究使用</span><span>研究员审阅后方可发布</span><b>2</b></footer>
      </article>
    </div><aside className="publication-inspector"><header><span>报告属性</span><b>国际市场周报</b></header><section><dl><dt>报告期</dt><dd>2024年第02期</dd><dt>数据截止</dt><dd>2024-01-12</dd><dt>统计频率</dt><dd>周度</dd><dt>页数</dt><dd>2 页</dd><dt>审阅状态</dt><dd className="pending">待审阅</dd></dl></section><section><span>数据完整性</span><div className="quality-row"><b>3 / 3</b><small>核心数据集有效</small></div><div className="quality-row"><b>12</b><small>市场指标已对齐</small></div><div className="quality-row"><b>0</b><small>缺失来源</small></div></section><section><span>报告操作</span><button onClick={()=>notify("图表口径说明已展开")}>查看图表口径</button><button onClick={()=>notify("全部数据来源已展开")}>查看数据来源</button><button onClick={()=>notify("审阅清单已创建")}>发起内部审阅</button></section><section className="publication-standard"><i>✓</i><p><b>出版检查通过</b>标题、单位、统计区间、来源、页码与风险边界均已包含。</p></section></aside></div>
    {notice&&<div className="report-toast" role="status">✓ {notice}</div>}
  </div>;
}
