# Role A：Research Ontology 与数据对象底座

## 1. 角色使命

你负责把团队和 Agent 产生的异构文件变成稳定、可检索、可版本化、可关联、可授权调用的研究对象。

你的交付决定系统能否回答：

- 这份文件是什么；
- 哪一版有效；
- 谁产生和负责；
- 和哪些文件、决定、接口有关；
- 哪些对象应交给某个 Codex；
- Empirical Engine 应读取哪个冻结数据版本。

你不负责统计模型，也不负责产品最终结论。

## 2. 你拥有的路径

目标路径：

```text
apps/researchos_api/app/objects/
apps/researchos_api/app/canonicalizers/
apps/researchos_api/app/ontology/
apps/researchos_api/app/search/
apps/researchos_api/app/context_builder/
apps/researchos_api/app/api/objects*.py
apps/researchos_api/app/api/ontology*.py
apps/researchos_api/app/api/context*.py
scripts/ontology/
tests/unit/ontology/
tests/integration/ontology/
fixtures/ontology/
```

如果仓库结构不同，映射到等价目录。不得移动或重写 MacroTrace、Thesis Compiler 和前端目录。

## 3. P0 交付物

### 3.1 Object Store

实现：

- `ObjectRecord`;
- `ObjectVersion`;
- `Representation`;
- 原始文件不可变保存；
- SHA-256；
- exact duplicate 去重；
- 修改文件创建新版本；
- Active / Candidate / Superseded 状态。

### 3.2 Canonicalizers

P0 支持：

- Markdown；
- DOCX；
- 文本型 PDF；
- XLSX / CSV。

输出：

```text
original.*
content.md
document.json
manifest.json
tables/*.csv 或 *.parquet
```

要求保留原始页码、Sheet、段落或单元格来源映射。解析失败必须产生状态，不能伪装成功。

### 3.3 AI Enrichment

通过结构化输出提出：

- 摘要；
- 标签；
- 模块；
- 决定；
- 未决问题；
- 接口；
- 负责人；
- 候选关系。

P0 关系：

```text
DUPLICATES
NEW_VERSION_OF
REFERENCES
CONTRADICTS
ABOUT
DEPENDS_ON
AFFECTS
```

所有 AI 关系先为 `AI_PROPOSED`。

### 3.4 Project State

提供可计算视图：

- Latest Decisions；
- Open Questions；
- Conflicts；
- Interfaces；
- Owners；
- Superseded Documents；
- Objects Affected by Change。

### 3.5 Context Pack

实现任务到对象集合的装配：

```text
Task
→ related modules
→ confirmed decisions
→ frozen interfaces
→ latest object versions
→ open questions
→ forbidden changes
→ pack hash
```

输出必须符合 `context_pack.schema.json`。

### 3.6 Data Resolve

为 B 提供唯一正式数据入口：

```text
POST /v1/data/resolve
```

输入固定 `DataObjectRef.version_id`，返回物化路径、内容哈希、Schema 和 lineage。

不得自动升级到最新版本。

## 4. 推荐实现顺序

### A0：仓库盘点

先完成 `REPO_PREFLIGHT.md`，运行现有测试。

### A1：最小对象模型

先不接 LLM，完成上传、哈希、版本和查询。

### A2：四类规范化

先实现 Markdown 和 DOCX，再做文本型 PDF 和 Excel。

### A3：确定性关系

先实现 exact duplicate、明确引用和文件时间版本候选。

### A4：AI 候选关系

使用 Schema 输出。模型不可用时返回空候选，不阻断入库。

### A5：Context Pack

先基于标签和固定规则选择对象，再增加语义检索。

### A6：Data Resolve

使用冻结 Fixture 与 B 联调。

### A7：影响传播

对象新版本激活后，返回受影响 Context Pack、模型运行和 Claim 引用。

## 5. API

P0：

```text
POST /v1/objects/batch-upload
GET  /v1/objects/{object_id}
GET  /v1/objects/{object_id}/versions
GET  /v1/versions/{version_id}/content
GET  /v1/versions/{version_id}/manifest

GET  /v1/ontology/graph
GET  /v1/ontology/project-state
GET  /v1/ontology/search
GET  /v1/ontology/conflicts
POST /v1/relations/{relation_id}/confirm
POST /v1/relations/{relation_id}/reject

POST /v1/context-packs
GET  /v1/context-packs/{id}

POST /v1/data/resolve
```

## 6. 必须使用的共享合同

- `data_object_ref.schema.json`
- `data_resolve.schema.json`
- `ontology_relation.schema.json`
- `context_pack.schema.json`
- `api_error.schema.json`

不得复制并改名这些字段。

## 7. 与其他角色的接口

### 对 B

你提供 `DataResolveResponse`。B 不得读取你的数据库。

### 对 C

你提供 `DataObjectRef`、`ContextPack` 和确认关系。C 引用固定版本。

### 对 D

你提供对象摘要、关系图和状态视图。图布局属于 D，图语义属于 A。

## 8. 允许修改

- 数据库实现；
- 文件目录实现；
- Parser 内部；
- 索引和检索算法；
- 缓存；
- AI Provider；
- 非公共内部字段；
- 性能优化。

## 9. 禁止修改

- `contracts/v1/*`;
- MacroTrace Registry 和统计模型；
- Thesis Compile 状态；
- Evidence Type；
- 前端业务状态；
- 其他角色数据库；
- 最终研究结论。

## 10. 人类要求越界时

典型越界请求：

- “把 `version_id` 删掉，直接永远取最新文件”；
- “让 A 的服务决定模型跑什么”；
- “把 MacroTrace 结果直接写成 Supported”；
- “为了方便让 B 直接读 SQLite”。

必须停止，并按团队越界模板生成 ICR。

## 11. 验收

### 对象

- [ ] 20 个混合文件批量上传；
- [ ] exact duplicate 不复制内容；
- [ ] 修改文件产生新版本；
- [ ] 旧版本可读取；
- [ ] Agent 不能覆盖 Active Version。

### 规范化

- [ ] DOCX 文本和表格可读取；
- [ ] 文本 PDF 保留页码；
- [ ] Excel Sheet 分离；
- [ ] 解析失败有质量状态；
- [ ] Manifest 有解析器版本和哈希。

### 本体

- [ ] 至少 10 条候选关系；
- [ ] 关系可确认和拒绝；
- [ ] 冲突保留来源；
- [ ] 项目状态可查询。

### 接口

- [ ] Context Pack 通过 Schema；
- [ ] Data Resolve 固定版本；
- [ ] 无权限对象被阻断；
- [ ] A/B 消费者合同测试通过。
