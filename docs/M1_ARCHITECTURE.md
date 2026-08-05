# M1 确定性资产基座

## 决策

M1 不使用 AI。系统先通过代码形成可信、稳定、可调用的资产接口，M2 的 AI
只能消费这些接口并生成可审核候选。

### 必须由代码完成

- 文件流读取和大小限制；
- SHA-256；
- 内容寻址 Blob；
- 格式和 MIME 检测；
- DOCX、XLSX、CSV、Markdown、文本 PDF 的确定性元数据；
- Asset 与 AssetVersion 身份；
- 原始和规范化 Representation；
- Fragment Locator；
- 精确重复检测；
- 明确 Asset 或稳定 source_key 对应的新版本；
- 失败状态和审计。

### AI 以后可以做

- 研究阶段和材料角色分类；
- 主题识别；
- 不确定的逻辑材料身份候选；
- 候选语义对象和关系。

AI 不得直接合并 Asset、修改权限、覆盖版本或确认高风险关系。

## 写入流程

~~~mermaid
flowchart TD
    A["上传流"] --> B["大小限制 + SHA-256 + Blob"]
    B --> C["格式检测 + 确定性元数据"]
    C --> D["Asset 身份解析 + AssetVersion"]
    D --> E["原始 Representation"]
    E --> F["Parser + 规范化 Representation"]
    F --> G["Fragment + ParseRun + AuditEvent"]
~~~

物理 Blob 可以去重，但逻辑 Asset 不会因为 Hash 相同而自动合并。

## 身份解析顺序

1. 请求显式提供 asset_id：在该 Asset 下创建版本；
2. 请求提供稳定 source_key，且已绑定 Asset：在该 Asset 下创建版本；
3. 同一 Workspace、同一原文件名和同一 Hash：视为精确重复；
4. 其他情况：创建新 Asset；
5. force_new_asset 可以明确创建共享同一 Blob 的另一个逻辑 Asset。

文件名相似但没有稳定来源时，M1 不自动认定为新版本。M2 可以提出候选，但必须
保持可审核。

## 不变量

- AssetVersion 创建后不可修改；
- current_version_id 只是便利指针；
- 持久化引用不得使用 latest；
- 每个 Fragment 固定 version_id、representation_id 和 locator；
- Parser 失败不删除原始文件或 AssetVersion；
- 一个 IngestItem 失败不回滚同批次其他文件；
- 不支持的格式产生可审计的 UNSUPPORTED ParseRun；
- 用户文件名只作为显示元数据，不参与存储路径。

## 存储

M1 使用完整 Blob + 整文件去重。LocalContentAddressedBlobStore 实现 BlobStore
协议，保存路径由 SHA-256 决定。

后续 S3、MinIO 或分块存储必须实现相同协议，不能改变 AssetVersion 的“完整不可变
版本”语义。Storage Chunk 不能替代 Fragment。

## 数据库

正式目标为 PostgreSQL；测试和快速本地开发支持 SQLite。Alembic 是唯一迁移入口。

核心表：

- workspaces；
- blobs；
- assets；
- asset_versions；
- representations；
- fragments；
- ingest_batches；
- ingest_items；
- parse_runs；
- audit_events。

## API

~~~text
POST /api/v1/workspaces
POST /api/v1/workspaces/{workspace_id}/ingest-batches
POST /api/v1/ingest-batches/{batch_id}/items
POST /api/v1/ingest-batches/{batch_id}/finalize
GET  /api/v1/ingest-batches/{batch_id}
GET  /api/v1/workspaces/{workspace_id}/assets
GET  /api/v1/assets/{asset_id}
GET  /api/v1/asset-versions/{version_id}
~~~

版本详情接口返回确定性元数据、Representation、Fragment 和 ParseRun，供人类界面
与后续 AI 通过同一合同消费。

## M1 不包含

- ClassificationAssertion；
- SemanticNode；
- RelationAssertion；
- ContextPack；
- VersionDiff；
- ImpactSet；
- 选择性重建；
- Commit、Branch、Merge、WorkspaceRevision；
- 块级增量存储；
- OCR；
- 异步队列的独立 Worker 部署。

这些对象按 v0.3 开发顺序继续实现，不得提前污染资产基座合同。

