# C 端仓库盘点

- 日期：2026-08-05
- 分支：`role/c-thesis`
- 初始状态：交接 ZIP 仅含冻结契约、fixtures 与协作规范，没有可复用应用代码。
- 契约：`contracts/v1` 共 12 个 schema，哈希全部匹配 `contract_manifest.json`，版本 `0.1.0-frozen`。
- C 所有路径：`apps/researchos_api/app/{thesis,orchestration,integrations}`、C API、C tests、fixtures/demo/thesis、docs/interfaces、docs/rfcs。
- 风险：团队远程仓库当前未提供；本仓库作为可合并的独立 C 分支，不修改 A/B/D 路径。
- 集成原则：只消费冻结 JSON 契约；不访问 A/B 数据库；先用合同 fixture 验证。
- 首个纵切：创建论点 → 首次编译 → 生成 ToolRequest → 摄取 EvidenceBundle → 重编译 → 版本差异/SSE。
- 验证命令：`pytest`；运行命令：`uvicorn apps.researchos_api.app.main:app --port 8000`。
