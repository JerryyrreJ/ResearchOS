# Role B：MacroTrace 注册制实证工具

## 1. 角色使命

你拥有现有 MacroTrace 本地开发流程和历史版本。你的任务是保留并复用这套能力，把它作为研构的注册制实证工具接入，而不是重写第二套 Empirical Engine。

你负责回答：

> 注册数据、模型、诊断和稳健性实际发现了什么？

你不负责决定这句话最终是否可以成为研究结论。

## 2. 你拥有的路径

```text
services/macrotrace/
apps/researchos_api/app/integrations/macrotrace_tool_server/  # 仅在团队采用该映射时
scripts/macrotrace/
tests/unit/macrotrace_adapter/
tests/integration/macrotrace/
fixtures/evidence/
data/snapshots/macrotrace/
```

MacroTrace 原有目录结构在 `services/macrotrace/` 内保持稳定。

## 3. 第一原则：不要重写

必须保留：

- compiler；
- RegistryStore；
- workflow/lane/node/factor/model routing；
- model recipes；
- diagnostics；
- Research Graph；
- DuckDB；
- Artifact；
- Report Pipeline；
- API；
- tests；
- Windows / local scripts。

禁止新建：

```text
new_empirical_engine/
new_research_graph/
new_model_registry/
```

## 4. P0 交付物

### 4.1 上游导入

优先 `git subtree`。无法使用时记录：

```text
UPSTREAM_REPO
UPSTREAM_COMMIT
IMPORT_DATE
LOCAL_PATCHES
LICENSE
```

### 4.2 Tool Adapter

实现：

```text
POST /v1/tool-runs/macrotrace
GET  /v1/tool-runs/{id}
GET  /v1/tool-runs/{id}/graph
GET  /v1/tool-runs/{id}/artifacts
```

输入 `ToolRequest`，输出 `EvidenceBundle`。

### 4.3 Ontology Data Adapter

使用 A 的 `/v1/data/resolve`：

```text
DataObjectRef
→ Data Resolve
→ validated materialized file
→ MacroTrace factor input
```

保留内容哈希、版本和 lineage。

不得读取 A 的数据库或自动取最新版。

### 4.4 Engine Claim 降级

MacroTrace 内部综合结果可保留，但 Adapter 输出字段必须为：

```text
engine_claim
```

不得输出 `conclusion_state`。

### 4.5 黄金路线

保底路线为现有美国财政与 10 年期美债路线。

必须：

- 连续真实运行三次；
- 结果和 Trace 可读取；
- 主模型和关键诊断可展示；
- 离线快照可运行；
- EvidenceBundle 通过 Schema。

### 4.6 中国路线 Gate

中国路线只能在产品宪章列出的六项 Gate 全过后升级。

没有通过时：

- 不改主 Demo；
- 不宣称完整 CN Macro；
- 可以保留实验分支或 P1 文档。

### 4.7 Offline

提供：

- 冻结数据快照；
- 冻结 Registry 版本；
- 冻结真实运行结果；
- 明确的 `OFFLINE_REPLAY` 标识；
- 不把缓存说成实时。

## 5. EvidenceBundle 映射

至少映射：

| MacroTrace | EvidenceBundle |
|---|---|
| job id | `research_job_id` |
| status | `status` |
| coverage | `coverage` |
| engine final claim | `engine_claim` |
| model results | `model_runs` |
| diagnostics | `diagnostics` |
| robustness | `robustness` |
| final evidence | `evidence_items` |
| falsifier nodes | `falsifiers` |
| provenance limits | `limitations` |
| data lineage | `input_object_refs` |
| registry | `registry_version` |
| artifact hash | `result_hash` |

## 6. 证据等级

Adapter 必须保守映射：

```text
Predictive model → PREDICTIVE
Bridge/panel association → ASSOCIATIONAL
LP without exogenous shock → DYNAMIC_ASSOCIATION
Mechanism-consistent system → STRUCTURAL_PROXY
Only registered identified design → CAUSAL_IDENTIFIED
```

严禁由自然语言自行升级。

## 7. 允许修改

- MacroTrace 本地 Bug；
- Adapter；
- 数据输入 Adapter；
- 黄金路线配置；
- Snapshot；
- 日志和错误映射；
- 兼容目标仓库的启动脚本。

## 8. 禁止修改

- 共享合同；
- A 的对象身份和权限；
- C 的编译状态和语言政策；
- D 的 UI；
- 为获得显著结果改变模型；
- 删除失败模型；
- 把关联写成因果；
- 大规模重构稳定上游。

## 9. 人类要求越界时

典型越界请求：

- “MacroTrace 已经有 FINAL_CLAIM，直接让它决定 Supported”；
- “不走 A 的接口，直接读它的数据库”；
- “把不显著模型删掉”；
- “临时改参数直到结果好看”；
- “把整个 CN Macro 都迁过来”。

必须解释风险并拒绝直接实施。

## 10. 验收

- [ ] 上游来源和 commit 记录；
- [ ] 原测试通过；
- [ ] ToolRequest 通过 Schema；
- [ ] EvidenceBundle 通过 Schema；
- [ ] 三次黄金路线运行；
- [ ] 失败模型保留；
- [ ] engine_claim 不升级为产品结论；
- [ ] A 的固定版本数据可读取；
- [ ] Offline 明确标识；
- [ ] C 能用 Fixture 和真实 Bundle 编译。
