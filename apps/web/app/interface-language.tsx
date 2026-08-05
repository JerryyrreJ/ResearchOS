"use client";

import { useEffect } from "react";
import type { Locale } from "./i18n";

// Compatibility catalog for legacy/static surfaces. Contract codes, object IDs,
// filenames, and backend-produced research content intentionally remain raw.
const interfaceTerms = [
  ["Settings", "设置", "設定"], ["Workspace settings", "工作区设置", "工作區設定"],
  ["Appearance", "外观", "外觀"], ["Color theme", "颜色主题", "色彩主題"],
  ["System follows your operating-system preference.", "跟随操作系统的外观偏好。", "跟隨作業系統的外觀偏好。"],
  ["Language", "语言", "語言"], ["Reduce motion", "减少动态效果", "減少動態效果"],
  ["Limits non-essential transitions and pulses.", "减少非必要的过渡与脉冲动画。", "減少非必要的轉場與脈衝動畫。"],
  ["Extension Center", "扩展中心", "擴充中心"], ["Catalog preview", "插件目录预览", "外掛目錄預覽"],
  ["Demo & status", "演示与状态", "展示與狀態"], ["Frozen contracts", "冻结契约", "凍結契約"],
  ["Deterministic golden project", "确定性标准项目", "確定性標準專案"],
  ["Cached fixture replay", "缓存样例回放", "快取範例重播"], ["No live API claims", "不声明实时接口结果", "不宣稱即時介面結果"],
  ["Unified A + B + C API", "统一 A+B+C 接口", "統一 A+B+C 介面"],
  ["Async state simulator", "异步状态模拟器", "非同步狀態模擬器"], ["Mobile demo entry", "移动端演示入口", "行動端展示入口"],
  ["Workspace", "工作空间", "工作空間"], ["Fiscal transmission study", "财政传导研究", "財政傳導研究"],
  ["Object model", "对象模型", "物件模型"], ["Build", "构建", "建置"], ["Version", "版本", "版本"],
  ["Updated", "更新时间", "更新時間"], ["Access", "访问范围", "存取範圍"], ["Contract", "契约", "契約"],
  ["Source object", "来源对象", "來源物件"], ["Parsed fragments", "解析片段", "解析片段"],
  ["Evidence bundle", "证据包", "證據包"], ["Compiled thesis", "编译论题", "編譯論題"],
  ["Language weakened", "语言强度已降低", "語言強度已降低"], ["Research objects", "研究对象", "研究物件"],
  ["Relations", "关系", "關係"], ["Open conflicts", "待处理冲突", "待處理衝突"], ["Context packs", "上下文包", "情境包"],
  ["Objects", "对象", "物件"], ["Conflicts", "冲突", "衝突"], ["All types", "全部类型", "全部類型"], ["All states", "全部状态", "全部狀態"],
  ["Name", "名称", "名稱"], ["Type", "类型", "類型"], ["State", "状态", "狀態"], ["Today", "今天", "今天"],
  ["Evidence structure", "证据结构", "證據結構"], ["View as table", "以表格查看", "以表格檢視"],
  ["Tool", "工具", "工具"], ["Request", "请求", "請求"], ["Evidence", "证据", "證據"], ["Timeout", "超时", "逾時"],
  ["Inspect run", "检查运行", "檢查執行"], ["Duration", "耗时", "耗時"], ["Results", "结果", "結果"],
  ["Parameters", "参数", "參數"], ["Artifacts", "产物", "產物"], ["Evidence type", "证据类型", "證據類型"],
  ["Language ceiling", "语言上限", "語言上限"], ["Association only", "仅支持关联", "僅支援關聯"],
  ["Model output", "模型输出", "模型輸出"], ["Diagnostic", "诊断", "診斷"], ["Passed", "已通过", "已通過"],
  ["Blocking", "是否阻断", "是否阻斷"], ["No", "否", "否"], ["Trace", "追踪记录", "追蹤紀錄"],
  ["Evidence boundary", "证据边界", "證據邊界"], ["Open Evidence Bundle", "打开证据包", "開啟證據包"],
  ["Evidence changed what the thesis may claim.", "证据改变了论题可以使用的表述。", "證據改變了論題可以使用的表述。"],
  ["Before", "之前", "之前"], ["After", "之后", "之後"], ["Evidence language policy", "证据语言政策", "證據語言政策"],
  ["Why the language changed", "语言为何改变", "語言為何改變"],
  ["Each edit is traceable to a contract value or compile issue.", "每项修改都可追溯到契约值或编译问题。", "每項修改都可追溯到契約值或編譯問題。"],
  ["Evidence boundary added", "已增加证据边界", "已新增證據邊界"],
  ["Keep previous version", "保留上一版本", "保留上一版本"], ["Accept as new version", "接受为新版本", "接受為新版本"],
  ["Version comparison", "版本比较", "版本比較"], ["Export diff", "导出差异", "匯出差異"],
  ["MacroTrace evidence added", "已加入 MacroTrace 证据", "已加入 MacroTrace 證據"],
  ["Conclusion", "结论", "結論"], ["Model runs recomputed", "已重新计算的模型运行", "已重新計算的模型執行"],
  ["Compile issues changed", "已变化的编译问题", "已變更的編譯問題"], ["Objects reused", "复用对象", "重用物件"],
  ["Run full validation", "运行完整验证链", "執行完整驗證鏈"], ["Run again", "重新运行", "重新執行"],
  ["Retry", "重试", "重試"], ["Running…", "正在执行…", "正在執行…"],
  ["End-to-end research compilation", "端到端研究编译", "端到端研究編譯"],
  ["Waiting for a live compile result.", "等待实时编译结果。", "等待即時編譯結果。"],
  ["No MacroTrace run yet.", "尚无 MacroTrace 运行。", "尚無 MacroTrace 執行。"],
  ["Changed", "已变更", "已變更"], ["Reused", "已复用", "已重用"],
  ["Recomputed by Thesis Compiler", "由论题编译器重新计算", "由論題編譯器重新計算"],
  ["Pinned reference unchanged", "固定引用未变化", "固定引用未變更"], ["Integration failed", "集成失败", "整合失敗"],
  ["Navigate", "导航", "導覽"], ["Cancel", "取消", "取消"], ["Create thesis", "创建论题", "建立論題"],
  ["Research claim", "研究主张", "研究主張"], ["Requested language", "请求语言强度", "要求語言強度"],
] as const;

const localeIndex: Record<Locale, number> = { en: 0, "zh-CN": 1, "zh-TW": 2 };

export default function InterfaceLanguageBridge({ locale }: { locale: Locale }) {
  useEffect(() => {
    const target = localeIndex[locale];
    const lookup = new Map<string, string>();
    for (const terms of interfaceTerms) for (const term of terms) lookup.set(term, terms[target]);
    const translate = (value: string) => {
      const trimmed = value.trim();
      const suffix = trimmed.endsWith(" →") ? " →" : "";
      const base = suffix ? trimmed.slice(0, -2) : trimmed;
      const translated = lookup.get(base) ?? lookup.get(trimmed);
      return translated ? value.replace(trimmed, `${translated}${suffix}`) : value;
    };
    const apply = (root: ParentNode) => {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while ((node = walker.nextNode())) if (node.nodeValue?.trim()) node.nodeValue = translate(node.nodeValue);
      if (root instanceof Element) for (const element of [root, ...root.querySelectorAll("[placeholder],[title],[aria-label]")]) {
        for (const attribute of ["placeholder", "title", "aria-label"]) {
          const value = element.getAttribute(attribute); if (value) element.setAttribute(attribute, translate(value));
        }
      }
    };
    apply(document.body);
    const observer = new MutationObserver((records) => records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) apply(node as Element);
      else if (node.nodeType === Node.TEXT_NODE && node.nodeValue) node.nodeValue = translate(node.nodeValue);
    })));
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale]);
  return null;
}
