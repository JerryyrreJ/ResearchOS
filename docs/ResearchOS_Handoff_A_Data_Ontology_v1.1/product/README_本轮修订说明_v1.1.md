# 研构 ResearchOS v1.1 修订说明

> 日期：2026-08-04  
> 状态：四人分工与 Codex 交接前冻结稿

## 1. 本轮解决的核心问题

上一版已经充分表达 Research Ontology 的价值，但比赛版产品权力关系仍容易被理解成“四个并列模块”。本轮将产品收敛为一条明确链路：

```text
Research Ontology
共享文件、版本、关系和 Agent 上下文
        ↓
Thesis Compiler
接收论点、发现缺口、提出验证计划
        ↓
MacroTrace
运行注册模型、诊断和稳健性
        ↓
Evidence Bundle
返回证据等级和局限
        ↓
Thesis Compiler Rebuild
产生最终结论状态和版本差分
```

## 2. 保留的产品核心

Research Ontology 继续承担底层核心能力：

- Word、PDF、Markdown、Excel 和聊天记录统一进入项目空间；
- 原始文件完整保留；
- 生成 Markdown、JSON、CSV 或 Parquet 规范化表示；
- 自动标签、版本、引用、冲突和责任关系；
- 为不同 Codex 生成固定版本的 Context Pack；
- 记录模型输入、运行结果和结论产物。

## 3. 调整的产品主交互

舞台主交互由“开放问题后直接跑模型”调整为“明确论点先编译”。

示例：

> 美国财政扩张正在持续推高 10 年期美债收益率。

系统先返回定义、时间窗口、因果措辞、竞争解释和证伪条件错误。用户确认验证计划后，系统调用 MacroTrace。MacroTrace 的综合解释作为 `ENGINE_CLAIM` 进入编译器。最终 `SUPPORTED`、`WEAKENED`、`EVIDENCE_INSUFFICIENT`、`EVIDENCE_CONFLICT` 或 `COMPILE_FAILED` 只能由 Thesis Compiler 产生。

## 4. Empirical 部分的处理

现有 MacroTrace 直接作为注册制实证工具接入。团队不再开发第二套 Empirical Engine、Research Graph 或 Model Registry。

本轮新增内容集中在：

1. ThesisBuild；
2. 编译规则；
3. ToolRequest；
4. EvidenceBundle Adapter；
5. 证据语言政策；
6. Build Console；
7. Recompile；
8. Version Diff；
9. Offline Demo。

## 5. Demo 策略

美国财政与 10 年期美债路线是保底真实路线。中国国债路线只有在数据版本、模型运行、诊断、合同、离线快照和三次演示全部通过后，才替代保底案例。

## 6. 四人分工

| 角色 | 核心模块 | 最终责任 |
|---|---|---|
| A | Research Ontology | 文件对象、规范化、版本、关系、Context Pack、Data Resolve |
| B | MacroTrace | 现有实证内核、Ontology Adapter、EvidenceBundle、黄金路线 |
| C | Thesis Compiler | 编译规则、验证计划、工具编排、语言边界、最终结论、合同治理 |
| D | Frontend and Release | 前端、E2E、部署、二维码、离线演示、发布 |

## 7. 冻结结论

> **Research Ontology 让团队和 Agent 拥有同一份研究状态。MacroTrace 负责把研究跑出来。Thesis Compiler 决定证据允许研究员说到什么程度。**
