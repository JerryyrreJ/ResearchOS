# 研构 ResearchOS 协作与技术架构 v1.1

## 1. 推荐仓库结构

```text
AIY_Project/
├── AGENTS.md
├── README.md
├── contracts/
│   └── v1/
├── apps/
│   ├── researchos_api/
│   │   └── app/
│   │       ├── objects/             # A
│   │       ├── canonicalizers/      # A
│   │       ├── ontology/            # A
│   │       ├── search/              # A
│   │       ├── context_builder/     # A
│   │       ├── thesis/              # C
│   │       ├── orchestration/       # C
│   │       ├── integrations/        # C
│   │       └── api/                 # A/C 按路由所有权拆分
│   └── web/                          # D
├── services/
│   └── macrotrace/                   # B，保留上游结构
├── fixtures/
│   ├── contracts/
│   ├── ontology/
│   ├── evidence/
│   └── demo/
├── tests/
│   ├── contract/
│   ├── integration/
│   └── e2e/
├── infra/                            # D
├── scripts/                          # 按所有权分目录
└── docs/
    ├── product/
    ├── architecture/
    ├── interfaces/
    ├── handoffs/
    ├── demo/
    └── rfcs/
```

如果现有仓库结构不同，Codex 必须先完成 Repo Inventory，再将角色所有权映射到等价目录。禁止为了匹配本手册而大规模移动已有稳定代码。

## 2. 运行拓扑

黑客松推荐两进程：

```text
Browser
   ↓
Nginx / single public origin
   ├── /api/* → ResearchOS API
   └── /       → Web
                  │
ResearchOS API ───┼── Object / Ontology / Thesis
                  │
                  └── localhost MacroTrace Tool API
```

MacroTrace 保持独立可运行。ResearchOS API 通过冻结 `ToolRequest` 和 `EvidenceBundle` 调用它。

## 3. 模块边界

### A：Ontology

对外只暴露对象 API、Ontology API、Context Pack API 和 Data Resolve API。A 的数据库是 A 的实现细节。

### B：MacroTrace

对外只暴露 Tool Run API 和 Evidence Bundle。B 的 DuckDB、Registry 和模型代码是 B 的实现细节。

### C：Thesis

对外暴露 Thesis Build、Compile、Verify 和 Diff API。C 不直接读取 A 或 B 数据库。

### D：Frontend

只通过 OpenAPI 或冻结 Fixtures 消费后端。D 不在 UI 内复制业务状态机。

## 4. 集成接口

| Producer | Consumer | 合同 |
|---|---|---|
| A | B | `DataObjectRef`, `DataResolveRequest`, `DataResolveResponse` |
| A | C | `DataObjectRef`, `ContextPack`, `OntologyRelation` |
| C | B | `ToolRequest` |
| B | C | `EvidenceBundle` |
| C | D | `ThesisBuild`, `CompileResult`, `JobEvent`, `VersionDiff` |
| A | D | Object Summary、Ontology Graph、Context Pack |
| B | D | 只读 Research Graph，通过 C 代理或冻结 URL |

## 5. 数据所有权

- 原始文件和规范化表示：A；
- MacroTrace 官方数据快照：B；
- Thesis Build 和 Compile Result：C；
- UI 本地状态：D；
- 共享合同和 Fixture：团队冻结；
- 模型产物写回 Ontology 时，A 保存对象，B/C 提供内容与元数据。

## 6. 禁止直接耦合

以下行为视为破坏集成：

- B 直接打开 A 的 SQLite/PostgreSQL；
- C 直接查询 B 的 DuckDB；
- D 直接读取文件系统或 DuckDB；
- A 在对象服务中导入 MacroTrace 统计模块；
- B 改写 Thesis Compiler 状态；
- C 将 MacroTrace 内部类作为公共合同；
- 任一角色通过复制字段绕过冻结 Schema。

## 7. 合同变更等级

### L0：本地实现

不改变公共字段、枚举、端点或语义。角色可自行修改。

### L1：向后兼容增加

增加可选字段或新内部端点。需要提交 ICR，并由至少一个消费者角色确认。

### L2：破坏性变更

重命名字段、改变枚举、删除字段、改变状态语义、改变端点。需要 A、B、C、D 全部批准，并提升合同版本。

### L3：架构变更

改变模块所有权、绕过 Adapter、合并/拆分服务。需要团队会议、迁移计划和回滚方案。

## 8. 集成顺序

1. C 提交合同和 Skeleton；
2. A、B、C、D 从同一合同提交创建分支；
3. A 提供 Object/Data Resolve Fixtures；
4. B 提供 EvidenceBundle Fixture；
5. C 使用 Fixtures 完成 Compile 流程；
6. D 使用 Fixtures 完成 UI；
7. A/B 替换 Fixture 为真实接口；
8. C 完成真实编排；
9. D 运行 E2E；
10. 功能冻结后只修阻断 Bug。

## 9. 时间门

| 时间 | 门槛 |
|---|---|
| H0-H2 | 仓库盘点、合同冻结、分支创建 |
| H2-H8 | 四个角色独立完成可测试骨架 |
| H8-H14 | 第一条 Fixture Vertical Slice |
| H14-H22 | 真实 Ontology + MacroTrace + Compiler 集成 |
| H22-H28 | Demo、离线、部署、降级 |
| H28 | Feature Freeze |
| H28-H32 | E2E、红队、稳定性 |
| H32 | Code Freeze |
| H32-H36 | 路演、录屏、发布 |

## 10. 合同测试

每个公共 JSON 必须同时通过：

- JSON Schema 校验；
- Producer 序列化测试；
- Consumer 反序列化测试；
- Fixture Snapshot；
- 未知必需字段拒绝；
- 未知枚举拒绝；
- 合同版本检查。

CI 任何合同测试失败时，不允许合并到 `integration`。
