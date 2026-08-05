# ResearchOS M1：确定性资产基座

这是 ResearchOS v0.3 的第一阶段实现。目标是在完全不依赖 AI 的情况下完成：

- 文件格式与基础元数据检测；
- 流式 SHA-256 和内容寻址 Blob 存储；
- Asset 与不可变 AssetVersion；
- 整文件去重；
- Representation 与精确 Fragment；
- Markdown、DOCX、XLSX、CSV、文本型 PDF 解析；
- IngestBatch、失败隔离和审计；
- 版本历史与基础 API。

AI 分类、语义关系、ContextPack、ImpactSet 和选择性重建将在后续里程碑接入。

## 本地启动

~~~bash
cp .env.example .env
uv sync --dev
uv run alembic upgrade head
uv run uvicorn researchos.api.main:app --reload
~~~

默认使用 SQLite 和本地内容寻址存储，便于开发和测试。生产目标为 PostgreSQL 与
S3 兼容对象存储。

API 文档：http://127.0.0.1:8000/docs

## 测试

~~~bash
uv run pytest
uv run ruff check .
~~~

## 确定性优先

以下能力必须由代码完成，不能交给模型猜测：

- MIME、大小、Hash 和文件结构；
- 文档可确定元数据；
- Blob 去重；
- 显式 Asset 更新；
- 稳定来源标识对应的新版本；
- Parser 和 VersionDiff。

AI 以后只能为研究阶段、材料角色和不确定的逻辑身份生成可审核候选。

