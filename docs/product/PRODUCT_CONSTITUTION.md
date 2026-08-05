# 研构 ResearchOS 产品宪章 v1.1

> 日期：2026-08-04  
> 状态：团队分工前冻结稿  
> 适用范围：AIY 黑客松 P0、四人并行开发、后续 Codex 交接  
> 核心修订：保留数据本体优势，明确 Thesis Compiler 的最终结论权，复用 MacroTrace 作为注册制实证工具

## 1. 最终产品定义

**研构 ResearchOS** 是一套面向研究团队的可验证研究操作系统。

它先把团队产生的 Word、PDF、Markdown、Excel、聊天记录和模型结果变成有身份、有版本、有关系、可授权调用的研究对象，再围绕一条明确研究论点组织证据需求，调用注册制研究工具执行真实模型，最后决定这条论点可以被表达到什么程度。

一句话：

> **把散落的文件变成会协作的研究资产，再让研究结论通过编译。**

## 2. 三层权力关系

系统必须严格遵守以下关系：

```text
Research Ontology
共享事实、文件、版本、关系和 Agent 上下文
        ↓
Thesis Compiler
接收论点、发现缺口、提出验证计划、拥有最终结论权
        ↓
Registered Research Tools
MacroTrace 等工具运行数据、模型、诊断和稳健性
        ↓
Evidence Bundle
返回证据类型、结果、失败和限制
        ↓
Thesis Compiler Rebuild
决定原论点通过、降级、削弱、冲突或失败
```

### 2.1 Research Ontology 的地位

数据本体不是普通文件上传模块。它是所有人和 Agent 的唯一共享状态层，负责：

- 原始文件与派生表示；
- 文件版本和内容哈希；
- 标签、实体、决定、接口和未决问题；
- 文件之间的派生、引用、冲突和新版本关系；
- 人员责任和访问权限；
- 面向不同 Codex 的 Context Pack；
- 模型输入、模型运行和结论产物的写回。

它回答：

> 团队现在拥有哪些研究资产，它们是什么版本，它们互相是什么关系，谁可以使用。

### 2.2 Thesis Compiler 的地位

Thesis Compiler 是比赛版的主交互和最终裁决层，负责：

- 接收一条明确、可验证的研究论点；
- 提取定义、时间窗口、语言强度和证伪条件；
- 生成编译错误；
- 决定需要调用哪种研究工具；
- 接收工具证据；
- 执行证据语言边界；
- 生成结论状态和版本差分。

只有这一层可以产生：

```text
COMPILE_FAILED
EVIDENCE_INSUFFICIENT
SUPPORTED
WEAKENED
EVIDENCE_CONFLICT
```

### 2.3 MacroTrace 的地位

MacroTrace 是现成的注册制实证执行器。它负责：

- 研究问题路由；
- Lane、Node、Factor 和 Model 选择；
- 确定性 Python 模型执行；
- 模型专属诊断；
- 稳健性检查；
- Research Graph；
- 数据和参数溯源；
- 运行 Trace。

MacroTrace 的 `FINAL_CLAIM` 在研构中解释为 `ENGINE_CLAIM`。它是工具综合结果，不能直接成为产品最终结论。

## 3. 为什么这样组合

数据本体解决团队共享状态问题。Thesis Compiler 解决研究表达资格问题。MacroTrace 解决真实实证执行问题。

三者各自回答不同问题：

| 模块 | 核心问题 |
|---|---|
| Research Ontology | 我们拥有什么信息，哪个版本有效，它们如何关联 |
| Thesis Compiler | 这条话需要什么证据，现有证据允许说到什么程度 |
| MacroTrace | 注册数据和模型实际发现了什么 |

系统不得让任何一层越权：

- Ontology 不决定统计结论；
- MacroTrace 不决定最终语言等级；
- Thesis Compiler 不直接读取别人的数据库或自行计算复杂模型；
- 前端不发明新的状态和字段。

## 4. 黑客松 P0 形态

比赛版采用一条真实闭环，不追求完整企业平台。

### 4.1 P0 必做

#### Research Ontology

- 批量接收 Markdown、DOCX、文本型 PDF、XLSX；
- 保存原始文件；
- 生成 Markdown、JSON、CSV 或 Parquet 规范化表示；
- 生成稳定对象 ID、版本 ID 和 SHA-256；
- 自动摘要和标签；
- 提出重复、新版本、引用、冲突四类候选关系；
- 展示项目对象图或关系表；
- 生成任务专用 Context Pack；
- 提供固定版本的数据解析接口。

#### Thesis Compiler

- `ThesisBuild` Schema；
- 8 至 10 条真实编译规则；
- 初次 Build Failed；
- 验证计划；
- `ToolRequest`；
- `EvidenceBundle` 适配；
- 证据语言等级控制；
- 重新编译；
- 版本差分。

#### MacroTrace

- 保留现有代码和测试；
- 提供一个可重复运行的黄金路线；
- 返回模型、诊断、稳健性、限制和结果哈希；
- 支持离线或缓存回放；
- 通过 Adapter 输出冻结 `EvidenceBundle`。

#### 前端与交付

- 项目文件和对象视图；
- Thesis Build Console；
- 验证计划；
- MacroTrace Evidence Drawer；
- Recompile 结果；
- Diff；
- 部署、二维码、Demo Reset 和录屏兜底。

### 4.2 P0 不做

- 完整企业权限治理；
- 三个完整 Domain Pack；
- 全量中国宏观 Registry 迁移；
- 任意统计代码生成；
- 自动证明因果；
- 全市场实时数据；
- 高并发开放研究平台；
- 字段级和行级权限；
- 自动合并所有 AI 关系；
- 新建第二套 Research Graph、Model Registry 或 Empirical Engine。

## 5. 黄金案例策略

### 5.1 保底案例

默认保底案例使用已经跑通的 MacroTrace 美国财政和 10 年期美债路线：

> **美国财政扩张正在持续推高 10 年期美债收益率。**

第一次编译应至少触发：

```text
DEF001       “财政扩张”未冻结定义
HORIZON001   “持续”未冻结时间窗口
CLAIM_LANG001 因果措辞需要 CAUSAL_IDENTIFIED 证据
VAR001       缺少竞争性解释或控制
FALS001      缺少证伪条件
```

MacroTrace 运行后，系统可以形成：

> 当前注册模型提供条件关联或机制一致性证据。该证据不足以支持“持续推高”的独立因果措辞。

### 5.2 中国案例升级门

中国国债路线只能在以下条件全部通过后替代保底案例：

1. 数据对象已通过 Ontology 注册并冻结版本；
2. 主模型真实运行三次；
3. 关键诊断可展示；
4. `EvidenceBundle` 通过合同测试；
5. 断网快照可运行；
6. 团队一致确认演示稳定性高于美国路线。

未通过时，美国路线保持主 Demo，中国路线进入路线图或补充页。

## 6. Demo 主线

### 90 秒压缩版

**0 至 12 秒：共享状态**

展示预加载的项目 Ontology。新增一份修订文档后，系统识别新版本和受影响接口。

**12 至 27 秒：论点编译失败**

输入明确论点，出现定义、时间、因果和证伪错误。

**27 至 42 秒：生成验证计划**

系统将部分需求转换为 MacroTrace `ToolRequest`。

**42 至 60 秒：实证证据**

打开 Evidence Drawer，只展示一个主模型、一个关键诊断和一个挑战结果。

**60 至 76 秒：重新编译**

原因果措辞不通过，降级关联论点得到当前支持或证据不足状态。

**76 至 90 秒：版本差分**

新数据或新文件版本触发相关模型和结论重算，未受影响节点复用。

结束语：

> **MacroTrace 负责把研究跑出来，研构负责判断这些证据允许研究员说到什么程度。**

## 7. 公开二维码边界

二维码是分发入口，不单独形成一套高并发产品。

P0 可以：

- 打开部署页面；
- 浏览黄金项目；
- 输入一条论点；
- 对注册路线运行或回放；
- 返回 `COMPLETE`、`PARTIAL`、`UNSUPPORTED` 或 `FAILED`。

P0 不承诺：

- 任意问题都能形成模型；
- 多人无限并发；
- 访问内部文件或 iFind 原始数据；
- 直接预测个股涨跌。

## 8. 四人角色

| 角色 | 模块 | 最终责任 |
|---|---|---|
| A | Research Ontology | 文件、对象、版本、关系、Context Pack、Data Resolve |
| B | MacroTrace / Empirical | 现有内核、黄金路线、EvidenceBundle、离线运行 |
| C | Thesis Compiler / Orchestration | 编译规则、ToolRequest、语言政策、版本 Diff、合同管理 |
| D | Frontend / Integration / Release | 用户体验、API 客户端、E2E、部署、二维码、演示稳定性 |

## 9. 不可跨越的技术原则

1. 不允许跨模块直接读写数据库；
2. 不允许私自更改冻结合同；
3. 不允许 B 输出产品最终结论；
4. 不允许 C 修改 MacroTrace 统计代码；
5. 不允许 A 决定模型和证据等级；
6. 不允许 D 在前端发明字段、状态或隐藏错误；
7. 不允许 Agent 覆盖正式对象；
8. 不允许为了显著性换规格；
9. 不允许把缓存回放说成实时运行；
10. 不允许在功能冻结后增加主路径功能。

## 10. 成功标准

- 四个角色能够独立开发，并通过冻结合同集成；
- 同一对象版本和同一模型规格得到可重复结果；
- 初次论点真实 Build Failed；
- MacroTrace 输出被正确降级为 EvidenceBundle；
- 关联证据不能通过因果语言；
- 文件版本变化能定位受影响 Context Pack、模型和结论；
- 现场断网仍可完成黄金路径；
- 三次连续演示无人工改数据或改页面。
