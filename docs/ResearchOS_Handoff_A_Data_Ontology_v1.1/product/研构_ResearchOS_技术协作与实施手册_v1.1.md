# 研构 ResearchOS 技术、协作与实施手册

> 版本：v1.1 四人 Codex 并行开发冻结稿  
> 合同版本：0.1.0-frozen

## 1. 技术目标

系统需要交付两条可运行闭环。

### 1.1 文件到共享研究状态

```text
Upload
→ Original Object
→ Canonical Representation
→ AI Enrichment
→ Ontology Relations
→ Project State
→ Context Pack
```

### 1.2 论点到可验证结论

```text
ThesisBuild
→ Compile Issues
→ Validation Plan
→ ToolRequest
→ MacroTrace
→ EvidenceBundle
→ Language Policy
→ CompileResult
→ VersionDiff
```

## 2. 权力边界

- A 拥有对象身份、版本、关系和数据解析；
- B 拥有统计模型、诊断和 engine evidence；
- C 拥有编译规则、工具编排、语言政策和最终状态；
- D 拥有呈现、E2E、部署和演示；
- 共享合同由团队冻结，C 负责 Steward 流程；
- 任一模块不得直接读取其他模块数据库。

## 3. 推荐仓库结构

```text
AIY_Project/
├── AGENTS.md
├── contracts/v1/
├── apps/
│   ├── researchos_api/app/
│   │   ├── objects/             # A
│   │   ├── canonicalizers/      # A
│   │   ├── ontology/            # A
│   │   ├── search/              # A
│   │   ├── context_builder/     # A
│   │   ├── thesis/              # C
│   │   ├── orchestration/       # C
│   │   └── integrations/        # C
│   └── web/                      # D
├── services/macrotrace/          # B
├── fixtures/
├── tests/
├── infra/                        # D
├── scripts/
└── docs/
```

现有仓库结构优先保留。四个 Codex 必须先完成 Repo Inventory，再映射所有权。

## 4. 运行拓扑

```text
Browser
  ↓
Nginx
  ├── /        → Web
  └── /api/*   → ResearchOS API
                    ├── A: Object and Ontology
                    ├── C: Thesis and Orchestration
                    └── localhost Tool Request
                              ↓
                         MacroTrace API
                              ↓
                         EvidenceBundle
```

MacroTrace 保持独立运行。ResearchOS API 通过冻结合同调用它。

## 5. 共享合同

### 5.1 DataObjectRef

固定对象版本、表示、Schema、许可和内容哈希。

### 5.2 DataResolve

A 为 B 解析固定版本数据，返回任务物化路径、Schema、lineage 和 hash。

### 5.3 ContextPack

A 为任务装配对象、接口、决定、问题、禁止改动和版本映射。

### 5.4 ThesisBuild

C 保存原论点、规范化论点、语言等级、定义、证据要求、Falsifier 和输入对象。

### 5.5 ToolRequest

C 请求 B 运行 MacroTrace。它不能携带任意 Python 或新公式。

### 5.6 EvidenceBundle

B 返回 engine_claim、证据等级、模型、诊断、稳健性、局限、对象引用、Registry 版本和哈希。

### 5.7 CompileResult

C 返回唯一产品结论状态、编译问题、Validation Plan、语言政策、受影响节点和复用节点。

### 5.8 VersionDiff

C 汇总版本差异，A/B 提供对象和模型影响信息。

## 6. 合同变更等级

| 等级 | 含义 | 审批 |
|---|---|---|
| L0 | 模块内部修改，不改变公共语义 | 角色自行决定 |
| L1 | 向后兼容增加可选字段或内部端点 | Producer 和至少一个 Consumer |
| L2 | 重命名、删除字段、改变枚举或状态 | A、B、C、D 全部批准并升版本 |
| L3 | 改变模块所有权或绕过 Adapter | 团队会议、迁移和回滚方案 |

## 7. Git 工作流

```text
main
integration
role/a-ontology
role/b-macrotrace
role/c-thesis
role/d-frontend
```

每个角色从同一合同冻结提交创建分支。推荐使用 worktree。所有角色 PR 目标为 `integration`。`main` 只接受 Release PR。

## 8. 集成顺序

1. 导入共享合同和 Fixtures；
2. A 提供 Object 和 Data Resolve Fixtures；
3. B 提供 EvidenceBundle Fixture；
4. C 使用 Fixture 完成 Compile；
5. D 使用 Fixture 完成 UI；
6. A/B 替换 Fixture 为真实服务；
7. C 完成真实编排；
8. D 完成 E2E 和部署；
9. 功能冻结；
10. Release。

## 9. Role A 实施边界

### 负责

- ObjectRecord、ObjectVersion、Representation；
- MD、DOCX、文本 PDF、XLSX 规范化；
- SHA-256、重复和版本；
- AI 候选标签、决定、问题和关系；
- Project State；
- Context Pack；
- Data Resolve。

### 禁止

- 选择统计模型；
- 生成 CompileResult；
- 改变 Evidence Type；
- 让消费者绕过 version_id；
- 修改 B/C/D 的内部代码。

## 10. Role B 实施边界

### 负责

- 保留 MacroTrace 上游；
- ToolRequest Adapter；
- Ontology Data Adapter；
- 模型运行和诊断；
- EvidenceBundle；
- 黄金路线和 Offline Snapshot。

### 禁止

- 开发第二套 Empirical Engine；
- 让 MacroTrace 决定 `conclusion_state`；
- 为结果表现修改规格；
- 直接读取 A 的数据库；
- 隐藏失败模型。

## 11. Role C 实施边界

### 负责

- ThesisBuild；
- 编译规则；
- Validation Plan；
- ToolRequest；
- EvidenceBundle 消费；
- Language Policy；
- CompileResult；
- VersionDiff；
- Orchestration 和合同 Steward。

### 禁止

- 直接运行统计模型；
- 读取 A/B 数据库；
- 单方面改变 L2/L3 合同；
- 降低因果语言规则以通过 Demo；
- 删除失败证据。

## 12. Role D 实施边界

### 负责

- Workspace and Ontology；
- Thesis Build Console；
- Validation Plan；
- Evidence Drawer；
- Recompile；
- Diff；
- API Client；
- E2E；
- Nginx、服务、QR、Offline 和录屏。

### 禁止

- 在 UI 中复制状态机；
- 写死未经生成的 Supported 或统计结果；
- 直接访问文件系统和 DuckDB；
- 修改公共 Schema；
- 隐藏失败和局限。

## 13. 越界请求协议

Codex 收到越界要求时必须停止，并返回：

```text
该修改会改变冻结边界：<合同/目录/状态>。
受影响角色：<A/B/C/D>。
直接实施风险：<接口、数据、状态或 Demo 风险>。
非破坏性方案：<Adapter、可选字段、Fixture 或本地实现>。
所需流程：ICR L1/L2/L3。
```

Codex 可以生成 ICR，不得在批准前实施 L2/L3。

## 14. Contract Test

每个公共 JSON 同时通过：

- JSON Schema；
- Producer Serialization；
- Consumer Parsing；
- Fixture Snapshot；
- 合同版本；
- 未知必需字段拒绝；
- 未知枚举拒绝。

合同测试失败时不得合并。

## 15. 失败和降级

### Ontology

解析失败保留原件和失败状态。AI 不可用时返回空候选关系。

### MacroTrace

Tool 不支持、Partial、模型失败和超时都映射为正式 EvidenceBundle 状态。

### Thesis Compiler

缺少证据或阻断诊断不能被 UI 或人工静默跳过。

### Frontend

图组件失败时显示关系表。模型服务不可用时显示 Offline Replay。录屏只能作为兜底并明确标识。

## 16. 时间计划

| 时间 | 目标 |
|---|---|
| H0 至 H2 | 仓库盘点、合同冻结、分支和 worktree |
| H2 至 H8 | 四个角色完成可测试 Skeleton |
| H8 至 H14 | Fixture Vertical Slice |
| H14 至 H22 | 真实 Ontology、MacroTrace 和 Compiler 集成 |
| H22 至 H28 | 前端、部署、Offline 和 Demo |
| H28 | Feature Freeze |
| H28 至 H32 | E2E、红队和稳定性 |
| H32 | Code Freeze |
| H32 至 H36 | 路演、录屏和 Release |

## 17. 完成定义

每个角色完成必须满足：

- 单元测试；
- 合同测试；
- Fixture；
- 失败路径；
- README；
- PR 合同影响说明；
- 无越界文件修改；
- 下一消费者完成联调。

## 18. 仓库访问说明

规划阶段无法读取 `JerryyrreJ/AIY_Project`，GitHub 接口返回 404。每个 Codex 的第一项工作必须是读取本地仓库、现有 AGENTS、README、依赖、测试和目录结构，生成 `repo_inventory_<ROLE>.md`。现有稳定代码优先复用，禁止按本手册强行重构目录。

## 19. 技术冻结结论

> **A 管理研究对象和版本，B 管理真实实证执行，C 管理结论资格和系统编排，D 管理用户体验和交付。公共合同连接四者，任何人都不能通过直接数据库访问绕过合同。**
