# 研构 ResearchOS 完整产品书

> 版本：v1.1 四人协作冻结稿  
> 日期：2026-08-04  
> 用途：统一产品叙事、系统权力关系、黑客松范围、接口边界和 Codex 并行开发

## 0. 执行摘要

### 0.1 产品定义

研构 ResearchOS 是面向研究团队的可验证研究操作系统。它将团队和 Agent 产生的 Word、PDF、Markdown、Excel、聊天记录、数据快照和模型结果转换为有身份、有版本、有关系、可授权调用的研究对象，再围绕一条明确研究论点组织验证需求，调用 MacroTrace 等注册研究工具执行真实模型，最后生成受证据等级约束的结论版本。

### 0.2 一句话

> **把散落的文件变成会协作的研究资产，再让研究结论通过编译。**

### 0.3 产品三层权力关系

```text
Research Ontology
共享文件、版本、关系、权限和 Agent Context
        ↓
Thesis Compiler
接收论点、产生错误、组织验证、拥有最终结论权
        ↓
Registered Research Tools
MacroTrace 运行注册数据、模型、诊断和稳健性
        ↓
Evidence Bundle
返回证据等级、结果、失败、局限和哈希
        ↓
Thesis Compiler Rebuild
通过、降级、削弱、冲突或失败
```

### 0.4 核心分工

| 模块 | 回答的问题 |
|---|---|
| Research Ontology | 团队拥有哪些对象，哪个版本有效，它们如何关联，谁可以调用 |
| Thesis Compiler | 一条论点缺什么证据，现有证据允许说到什么程度 |
| MacroTrace | 注册数据和模型实际发现了什么 |
| Frontend and Release | 用户如何看懂整条链路，现场如何稳定运行 |

## 1. 问题背景

### 1.1 AI 产出速度已经超过团队整理速度

一个四人团队分别使用 ChatGPT、Claude、Codex 或其他 Agent，很快会产生几十份文档、数据表和代码说明。文件分散后，团队需要手工完成寻找、去重、版本判断、汇总、冲突处理和上下文重建。

### 1.2 现有工具缺少共同研究状态

研究过程通常分布在：

- 群聊；
- 本地文件夹；
- 网盘；
- Git；
- Notebook；
- Word 和 PPT；
- 不同 Agent 会话。

研究员很难快速确认：

- 最新决定；
- 未决问题；
- 依赖接口；
- 文件版本；
- 数据来源；
- 模型输入；
- 结论影响。

### 1.3 研究表达也缺少可执行约束

大模型可以生成流畅论述，但不会稳定地因为定义模糊、时间窗口缺失、因果证据不足或关键诊断失败而停止。研究团队需要一套允许 Build Failed 的机制。

## 2. Research Ontology 的产品优势

### 2.1 文件是入口

支持：

- Markdown；
- DOCX；
- 文本型 PDF；
- XLSX 和 CSV；
- JSON；
- 网页归档；
- 聊天记录导出；
- 模型产物。

### 2.2 原始文件完整保留

系统生成三层对象：

```text
Original
原始 PDF、DOCX、XLSX、MD

Canonical Representation
content.md、document.json、tables/*.csv、manifest.json

Semantic Objects
主题、决定、接口、任务、风险、数据集、模型规格和论点
```

### 2.3 对象拥有稳定身份

每个对象至少记录：

- object_id；
- version_id；
- SHA-256；
- 创建者和负责人；
- 来源和许可；
- 状态；
- 标签；
- 规范化表示；
- 父对象和派生对象；
- 被哪些 Context Pack、模型和结论引用。

### 2.4 关系形成研究本体

P0 关系包括：

```text
DERIVED_FROM
NEW_VERSION_OF
DUPLICATES
REFERENCES
ABOUT
CONTRADICTS
DEPENDS_ON
AFFECTS
USED_BY
PRODUCED_BY
```

AI 先提出候选关系。确认后的关系形成项目状态。

### 2.5 相较于本地文件夹

文件夹按路径组织。Research Ontology 按对象含义、版本、关系和影响组织。它能够回答“改动会影响什么”，并为不同 Agent 选择固定版本材料。

### 2.6 相较于群聊

群聊保存时间流。Research Ontology 保存决定、问题、接口和文件版本。新成员可以直接读取当前项目状态。

### 2.7 相较于 Git

Git 提供文件历史。Research Ontology增加跨格式规范化、语义对象、责任关系、权限、许可、Context Pack、模型运行和结论影响。

### 2.8 相较于普通 RAG

RAG 主要检索文本块。Research Ontology 继续保存原件、版本、关系、使用记录和正式状态。回答必须绑定对象版本和位置。

## 3. Context Pack

### 3.1 目标

四名成员分别使用自己的 Codex。系统需要保证：

- 每个 Codex 获得任务相关材料；
- 所有人使用同一合同版本；
- 已废弃对象不会进入默认上下文；
- 未决冲突和禁止修改项会进入 Prompt；
- Context Pack 可以复现和比较。

### 3.2 内容

```text
Task
Required Objects
Frozen Interfaces
Confirmed Decisions
Open Questions
Forbidden Changes
Version Map
Token Budget
Pack Hash
```

### 3.3 价值

Context Pack 将数据本体直接转化为多 Agent 协作能力。它减少重复解释，限制 Codex 越界修改，并保留每个任务使用的上下文版本。

## 4. Thesis Compiler

### 4.1 主交互

用户提交明确论点：

> 美国财政扩张正在持续推高 10 年期美债收益率。

Thesis Compiler 先进行静态检查，再决定是否调用研究工具。

### 4.2 P0 编译规则

| 错误码 | 含义 |
|---|---|
| DEF001 | 核心概念没有操作化定义 |
| HORIZON001 | 时间窗口或“持续”未定义 |
| TIME001 | 来源或数据晚于 as_of_date |
| VAR001 | 必需变量或竞争解释缺失 |
| FALS001 | 关键论点缺少证伪条件 |
| TOOL001 | 需要的注册工具路线不存在 |
| EVIDENCE001 | 证据覆盖不足 |
| DIAG001 | 阻断诊断失败 |
| CLAIM_LANG001 | 证据等级不足以支持措辞 |
| PERM001 | 输入对象无权访问 |

### 4.3 验证计划

编译错误转为用户可执行步骤：

```text
定义财政扩张
明确时间窗口
加入竞争性解释
运行注册研究工具
添加证伪条件
重新编译
```

### 4.4 最终状态

```text
COMPILE_FAILED
EVIDENCE_INSUFFICIENT
SUPPORTED
WEAKENED
EVIDENCE_CONFLICT
```

只有 Thesis Compiler 可以产生这些状态。

## 5. MacroTrace

### 5.1 定位

MacroTrace 直接复用为注册制实证工具。现有研究路由、Registry、模型、诊断、Research Graph、DuckDB、Artifact、API 和测试应尽量保持稳定。

### 5.2 输入

C 通过 `ToolRequest` 请求研究：

- thesis_id；
- question；
- as_of_date；
- requested_evidence_type；
- workflow_hint；
- 固定版本 DataObjectRef；
- falsifier_requirements；
- timeout。

### 5.3 输出

B 返回 `EvidenceBundle`：

- engine_claim；
- evidence_type；
- model_runs；
- diagnostics；
- robustness；
- evidence_items；
- falsifiers；
- limitations；
- input_object_refs；
- registry_version；
- result_hash；
- artifacts。

### 5.4 证据等级

```text
DESCRIPTIVE
PREDICTIVE
ASSOCIATIONAL
DYNAMIC_ASSOCIATION
STRUCTURAL_PROXY
CAUSAL_IDENTIFIED
```

MacroTrace 的内部 Final Claim 在研构中映射为 `engine_claim`。产品最终结论仍由 C 编译。

## 6. 用户完整路径

### 6.1 项目文件进入

团队批量投入文件。A 创建对象、规范化表示、候选关系和项目状态。

### 6.2 项目问答

用户查询决定、冲突和接口，答案回到对象版本。

### 6.3 创建论点

用户从项目对象或自然语言创建 ThesisBuild。

### 6.4 初次编译

系统显示 Build Failed 和验证计划。

### 6.5 研究工具执行

C 产生 ToolRequest。B 通过 A 的 Data Resolve 读取固定版本数据，运行 MacroTrace。

### 6.6 Evidence Bundle

模型结果、失败、诊断和局限返回 C。

### 6.7 Recompile

C 执行语言政策和证据规则，产生最终状态。

### 6.8 写回

模型运行、Evidence Package 和 Claim Version 写回 Ontology。

### 6.9 Diff

新文件或新数据版本激活后，系统定位受影响 Context Pack、模型运行和论点版本。

## 7. 产品页面

1. Workspace and Ontology；
2. Thesis Build Console；
3. Validation Plan；
4. MacroTrace Evidence Drawer；
5. Recompile Result；
6. Version Diff。

Evidence Drawer 复用现有 MacroTrace Research Graph，不开发第二张同义研究图。

## 8. 黑客松 P0

### 8.1 Research Ontology

- 批量上传 MD、DOCX、文本 PDF、XLSX；
- 原始文件和哈希；
- 规范化表示；
- 对象版本；
- 摘要和标签；
- 重复、新版本、引用和冲突候选；
- 项目关系图或关系表；
- Context Pack；
- Data Resolve。

### 8.2 Thesis Compiler

- ThesisBuild；
- 8 至 10 条规则；
- Validation Plan；
- ToolRequest；
- EvidenceBundle 消费；
- Language Policy；
- CompileResult；
- Diff。

### 8.3 MacroTrace

- 上游版本记录；
- Tool Adapter；
- Ontology Adapter；
- 黄金路线；
- EvidenceBundle；
- Offline Snapshot。

### 8.4 Frontend and Release

- 六个页面；
- Fixture First；
- E2E；
- Nginx 和服务部署；
- QR；
- Demo Reset；
- Offline Replay；
- 录屏。

## 9. P0 暂缓

- 完整企业权限；
- 字段级权限；
- 三个完整 Domain Pack；
- 全量中国宏观迁移；
- 任意统计代码生成；
- 自动证明因果；
- 全市场实时数据；
- 个股涨跌预测；
- 无限并发；
- 第二套 Empirical Engine、Research Graph 或 Model Registry。

## 10. 黄金案例

### 10.1 保底路线

使用现有 MacroTrace 美国财政和 10 年期美债路线，保证真实、稳定和离线可回放。

### 10.2 中国路线升级条件

中国国债路线需要全部通过：

1. Ontology 数据版本冻结；
2. 主模型连续运行三次；
3. 关键诊断可展示；
4. EvidenceBundle 合同通过；
5. Offline Snapshot 通过；
6. 团队确认稳定性更高。

## 11. 90 秒 Demo

| 时间 | 画面 |
|---|---|
| 0 至 12 秒 | 项目 Ontology、文件版本和接口影响 |
| 12 至 27 秒 | 明确论点初次 Build Failed |
| 27 至 42 秒 | Validation Plan 和 ToolRequest |
| 42 至 60 秒 | 一个主模型、一个诊断和一个挑战结果 |
| 60 至 76 秒 | 原因果措辞失败，降级论点重新编译 |
| 76 至 90 秒 | 新版本触发局部重算和 Diff |

结束语：

> **MacroTrace 负责把研究跑出来，研构负责判断这些证据允许研究员说到什么程度。**

## 12. 四人协作

### A：Research Ontology

拥有对象、规范化、关系、搜索、Context Pack 和 Data Resolve。

### B：MacroTrace

拥有现有 MacroTrace、Tool Adapter、Ontology Adapter、EvidenceBundle、黄金路线和 Snapshot。

### C：Thesis Compiler

拥有 ThesisBuild、规则、Validation Plan、ToolRequest、EvidenceBundle 编译、Language Policy、最终状态、Diff 和合同治理。

### D：Frontend and Release

拥有前端、E2E、部署、二维码、Demo、Offline 和发布。

## 13. 核心接口

| Producer | Consumer | Contract |
|---|---|---|
| A | B | DataObjectRef、DataResolveRequest、DataResolveResponse |
| A | C | DataObjectRef、ContextPack、OntologyRelation |
| C | B | ToolRequest |
| B | C | EvidenceBundle |
| C | D | ThesisBuild、CompileResult、JobEvent、VersionDiff |
| A | D | Object Summary、Ontology Graph、Context Pack |

公共合同版本为 `0.1.0-frozen`。破坏性变更需要四人批准并提升版本。

## 14. 验收标准

### 14.1 Ontology

- 混合文件可批量上传；
- 原件和规范化表示可回链；
- exact duplicate 不重复存储；
- 修改创建新版本；
- Context Pack 固定版本和哈希；
- Data Resolve 不自动取最新。

### 14.2 MacroTrace

- 上游来源和 commit 有记录；
- ToolRequest 和 EvidenceBundle 通过 Schema；
- 黄金路线连续运行三次；
- 失败模型保留；
- Offline 明确标识；
- engine_claim 不越权成为产品结论。

### 14.3 Thesis Compiler

- 初次论点触发真实错误；
- Validation Plan 可执行；
- 证据等级限制措辞；
- 阻断诊断影响状态；
- 降级论点可生成；
- Diff 正确。

### 14.4 Frontend

- Fixture 与真实 API 可切换；
- 失败节点可见；
- 未知状态有错误；
- E2E 黄金路径通过；
- QR 可访问；
- 连续三次演示；
- 录屏与实际产品一致。

## 15. 商业化方向

### 第一阶段

项目研究工作区、批量文件、Ontology、Context Pack 和单一注册研究工具。

### 第二阶段

多工作区、审批、iFind/Wind/内部数据库连接、行业模板和团队研究资产库。

### 第三阶段

企业 Research API、大规模研报逆向、多工具 Registry 和受控 Agent 基础设施。

## 16. 最终定位

Research Ontology 是共享状态和长期数据资产基础。Thesis Compiler 是用户形成和更新论点的主交互。MacroTrace 是已经成熟的实证执行工具。三者形成从文件到证据、从证据到结论、从结论到版本的完整闭环。

> **让团队和 Agent 共享同一份研究状态，让每条结论都能回到文件、数据和模型。**
