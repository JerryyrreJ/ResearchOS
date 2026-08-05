# Role D：前端、端到端集成、部署与演示

## 1. 角色使命

你负责让评委和用户在一个连贯产品中看懂：

1. 团队文件已经形成共同研究状态；
2. 一条论点为什么 Build Failed；
3. 系统为什么调用 MacroTrace；
4. 模型证据如何限制结论语言；
5. 新版本为什么只更新一部分内容。

你同时负责部署、二维码、E2E 和 Demo 兜底。

## 2. 你拥有的路径

```text
apps/web/
infra/
tests/e2e/
docs/demo/
scripts/demo/
fixtures/ui/
.github/workflows/  # 与团队确认后
```

你不拥有后端合同和业务状态机。

## 3. P0 页面

### 3.1 Workspace / Ontology

展示：

- 文件；
- 作者；
- 版本；
- 标签；
- 关系；
- 冲突；
- Context Pack。

P0 不需要复杂图编辑。关系图失败时切换表格。

### 3.2 Thesis Build Console

这是产品首页的主交互。

展示：

- 原论点；
- as-of；
- language level；
- Build 状态；
- 编译错误；
- 定位和修复操作；
- Compile Thesis 按钮。

### 3.3 Validation Plan

展示定义、窗口、控制、实证工具和证伪条件步骤。

### 3.4 MacroTrace Evidence Drawer

复用 B 的 Research Graph Artifact 或现有 renderer。

只需突出：

- 一个主模型；
- 一个关键诊断；
- 一个挑战或稳健性；
- Evidence Type；
- Limitations。

不得新建第二套研究图。

### 3.5 Recompile

展示：

```text
原论点：因果措辞未通过
降级论点：关联证据当前支持
```

同时显示原因和 EvidenceBundle。

### 3.6 Version Diff

展示：

- Changed；
- Reused；
- Model runs recomputed；
- Compile issues changed；
- Conclusion changed。

## 4. 开发策略

### Fixture First

在 A/B/C 真实接口完成前，使用 `shared/fixtures/contracts`。

前端类型必须由 JSON Schema / OpenAPI 生成或严格映射。

不得手工添加后端不存在的字段。

### API Client

集中在一个目录，统一错误处理：

```text
apps/web/src/api/
```

### 状态

服务器状态来自后端。前端只保存：

- 当前页面；
- 选中节点；
- 图布局；
- 展开状态；
- 本地表单草稿。

## 5. 部署

推荐：

- Nginx；
- HTTPS；
- Web 静态构建；
- ResearchOS API systemd；
- MacroTrace systemd；
- 环境变量；
- health checks；
- 日志；
- demo reset。

二维码指向部署页面。

## 6. Offline / Demo

必须提供：

- 一键加载黄金项目；
- `OFFLINE_REPLAY` 标识；
- 真实缓存结果；
- Demo reset；
- 静态关系表；
- 模型超时提示；
- 录屏。

不能把缓存说成实时。

## 7. E2E 黄金路径

```text
打开项目
→ 查看 Ontology
→ 打开 Thesis
→ Compile Failed
→ 查看 Validation Plan
→ Run MacroTrace / Replay
→ Evidence Drawer
→ Recompile
→ 查看降级结论
→ 加载新版本
→ Diff
```

## 8. 允许修改

- 组件；
- Layout；
- CSS；
- 图渲染；
- API client 内部；
- 本地 UI state；
- 部署脚本；
- E2E；
- 可访问性和性能。

## 9. 禁止修改

- JSON Schema；
- API 状态语义；
- 后端枚举；
- A/B/C 数据库；
- MacroTrace 模型；
- Compile 规则；
- 隐藏失败；
- 伪造实时；
- 在 UI 中写死未经真实生成的统计结果。

## 10. 人类要求越界时

典型越界请求：

- “后端还没做，前端先把 Supported 写死”；
- “把错误折叠掉，让画面好看”；
- “直接从 DuckDB 读结果”；
- “EvidenceBundle 多加一个字段，不用通知 C/B”；
- “复制一张新的 Research Graph”。

必须停止并提供 Fixture 或 ICR 路线。

## 11. 验收

- [ ] 五个 P0 页面可用；
- [ ] Fixture 和真实 API 可切换；
- [ ] 未知状态有明确错误；
- [ ] 失败节点可见；
- [ ] Evidence Type 和语言上限可见；
- [ ] Ontology 关系可回链；
- [ ] E2E 黄金路径通过；
- [ ] 部署 health check；
- [ ] QR 可访问；
- [ ] Offline 明确标识；
- [ ] 连续三次演示；
- [ ] 录屏与产品一致。
