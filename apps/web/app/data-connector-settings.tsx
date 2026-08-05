"use client";

import { useEffect, useMemo, useState } from "react";
import type { Locale } from "./i18n";
import { DATA_CONNECTORS } from "../lib/connector-catalog";
import {
  researchosApi,
  type DataPlugin,
  type DataPluginDataset,
} from "../lib/api-client";

const copy = {
  "zh-CN": { title:"数据连接器", intro:"目录展示可接入的数据源；只有后端已注册的插件才能进入版本化研究资产。", enable:"启用", disable:"停用", sample:"检查数据目录", docs:"官方文档", bridge:"需要桥接服务", licensed:"需要机构授权", configured:"后端已配置", unavailable:"后端未配置", security:"密钥由 ResearchOS 后端环境管理，不返回浏览器，也不会写入 Git。", rows:"个数据集" },
  "zh-TW": { title:"資料連接器", intro:"目錄展示可接入的資料源；只有後端已註冊的外掛才能進入版本化研究資產。", enable:"啟用", disable:"停用", sample:"檢查資料目錄", docs:"官方文件", bridge:"需要橋接服務", licensed:"需要機構授權", configured:"後端已設定", unavailable:"後端未設定", security:"密鑰由 ResearchOS 後端環境管理，不返回瀏覽器，也不會寫入 Git。", rows:"個資料集" },
  en: { title:"Data connectors", intro:"The catalog shows possible sources; only backend-registered plugins can create versioned research assets.", enable:"Enable", disable:"Disable", sample:"Inspect catalog", docs:"Documentation", bridge:"Bridge required", licensed:"License required", configured:"Backend configured", unavailable:"Backend not configured", security:"Credentials are managed by the ResearchOS backend environment, never returned to the browser, and never written to Git.", rows:"datasets" },
};

export default function DataConnectorSettings({ locale, active }: { locale: Locale; active: boolean }) {
  const words=copy[locale];
  const [plugins,setPlugins]=useState<DataPlugin[]>([]);
  const [selectedId,setSelectedId]=useState(DATA_CONNECTORS[0]?.id);
  const [busy,setBusy]=useState<string>();
  const [message,setMessage]=useState<string>();
  const [sample,setSample]=useState<DataPluginDataset[]>([]);

  const pluginMap=useMemo(()=>new Map(plugins.map(item=>[item.plugin_id,item])),[plugins]);
  const selected=DATA_CONNECTORS.find(item=>item.id===selectedId);
  const selectedPlugin=selected?pluginMap.get(selected.id):undefined;

  const refresh=async()=>setPlugins(await researchosApi.listDataPlugins());
  useEffect(()=>{
    if(!active)return;
    let cancelled=false;
    void researchosApi.listDataPlugins()
      .then(result=>{if(!cancelled)setPlugins(result)})
      .catch(error=>{if(!cancelled)setMessage(error instanceof Error?error.message:"Data plugin catalog unavailable")});
    return()=>{cancelled=true};
  },[active]);

  const toggle=async()=>{
    if(!selectedPlugin)return;
    setBusy("toggle");setMessage(undefined);setSample([]);
    try{
      await researchosApi.setDataPluginEnabled(selectedPlugin.plugin_id,!selectedPlugin.enabled);
      await refresh();
    }catch(error){setMessage(error instanceof Error?error.message:"Data plugin update failed")}
    finally{setBusy(undefined)}
  };
  const inspect=async()=>{
    if(!selectedPlugin)return;
    setBusy("sample");setMessage(undefined);setSample([]);
    try{
      const result=await researchosApi.listDataPluginDatasets(selectedPlugin.plugin_id,undefined,8);
      setSample(result);setMessage(`${result.length} ${words.rows}`);
    }catch(error){setMessage(error instanceof Error?error.message:"Dataset catalog unavailable")}
    finally{setBusy(undefined)}
  };

  const backendStatus=selectedPlugin
    ? selectedPlugin.enabled?"已启用":selectedPlugin.configured&&selectedPlugin.available?words.configured:words.unavailable
    : selected?.runtime==="licensed"?words.licensed:words.bridge;

  return <><div className="settings-head"><span>FINANCIAL DATA LAYER</span><h2>{words.title}</h2><p>{words.intro}</p></div><div className="connector-security"><i>⌁</i><span><b>ResearchOS backend policy</b><small>{words.security}</small></span></div><div className="connector-console"><div className="connector-list">{DATA_CONNECTORS.map(item=>{const plugin=pluginMap.get(item.id);return <button key={item.id} className={selectedId===item.id?"active":""} onClick={()=>{setSelectedId(item.id);setMessage(undefined);setSample([])}}><i>{item.mark}</i><span><b>{item.name}</b><small>{item.category} · {item.institution}</small></span><em className={plugin?.enabled?"connected":""}>{plugin?.enabled?"●":"○"}</em></button>})}</div><div className="connector-detail">{selected&&<><div className="connector-detail-head"><span className="extension-mark">{selected.mark}</span><span><h3>{selected.name}</h3><small>{selected.coverage}</small></span><b>{backendStatus}</b></div>{selected.legalNote&&<p className="connector-legal">{selected.legalNote}</p>}{selectedPlugin?<><div className="connector-keyless">{selectedPlugin.configured&&selectedPlugin.available?"✓":"!"} {selectedPlugin.description}</div><div className="connector-actions"><button className="button primary" disabled={!!busy||!selectedPlugin.configured||!selectedPlugin.available} onClick={()=>void toggle()}>{selectedPlugin.enabled?words.disable:words.enable}</button><button className="button" disabled={!!busy||!selectedPlugin.available} onClick={()=>void inspect()}>{words.sample}</button></div>{!selectedPlugin.configured&&<p className="connector-unavailable">{selectedPlugin.credential_kind==="FRED_API_KEY"?"请在后端设置 FRED_API_KEY。":"请安装并配置对应的 ResearchOS 数据插件。"}</p>}</>:<p className="connector-unavailable">该来源目前仅存在于连接器目录，尚未注册到 B 的版本化数据插件系统，因此不会声称可执行。</p>}<a className="connector-docs" href={selected.docsUrl} target="_blank" rel="noreferrer">{words.docs} ↗</a>{message&&<p className="connector-message">{message}</p>}{sample.length>0&&<div className="connector-sample"><span>BACKEND DATASET CATALOG</span>{sample.slice(0,5).map(item=><small key={item.dataset_id}><b>{item.name}</b> · {item.description}</small>)}</div>}</>}</div></div></>;
}
