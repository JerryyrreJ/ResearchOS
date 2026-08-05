# Git 协作与合并协议

## 1. 仓库

目标仓库：`https://github.com/JerryyrreJ/AIY_Project`

规划阶段无法读取该仓库内容，GitHub 接口返回 404。仓库可能是私有、尚未授权或路径尚未同步。因此每个 Codex 的第一项工作必须是仓库盘点，不能假设仓库为空或已按目标结构初始化。

## 2. 分支

```text
main                    只保存可发布版本
integration             四人集成分支
role/a-ontology         A
role/b-macrotrace       B
role/c-thesis           C
role/d-frontend         D
```

每个角色从同一个合同冻结提交创建分支。

推荐使用 `git worktree`，避免四个 Codex 操作同一工作目录：

```bash
git worktree add ../AIY_A role/a-ontology
git worktree add ../AIY_B role/b-macrotrace
git worktree add ../AIY_C role/c-thesis
git worktree add ../AIY_D role/d-frontend
```

## 3. 合并规则

- 所有角色 PR 目标为 `integration`；
- `main` 只接受从 `integration` 发起的 release PR；
- 禁止直接向 `main` 推送；
- 禁止 force push 到共享分支；
- 公共合同变更单独 PR；
- 统计模型和数据快照变更必须带结果哈希或测试；
- 前端 PR 必须基于冻结 Fixture 或真实 API。

## 4. 推荐合并顺序

1. `contracts-bootstrap`
2. A 的对象 API Skeleton
3. B 的 MacroTrace Tool Adapter Skeleton
4. C 的 Thesis Compiler Skeleton
5. D 的 Fixture UI
6. A/B 真实实现
7. C 真实编排
8. D E2E 和部署
9. Release PR

## 5. PR 模板

```markdown
## Role
A / B / C / D

## Scope
本 PR 完成什么。

## Owned paths changed
列出目录。

## Contract impact
NONE / L1 / L2 / L3

## Producer and consumers
谁生成，谁消费。

## Tests
命令和结果。

## Fixtures
新增或更新哪些 Fixture。

## Failure paths
验证了哪些失败和降级。

## Integration request
需要谁 review，下一步和谁联调。
```

## 6. MacroTrace 导入

推荐 B 使用 Git subtree 或完整 vendor snapshot，避免 submodule 在比赛现场失联。

优先：

```bash
git remote add macrotrace-upstream https://github.com/ZhenyuanPAN822/macrotrace.git
git fetch macrotrace-upstream
git subtree add --prefix services/macrotrace macrotrace-upstream main
```

如果目标仓库历史或权限不允许 subtree：

- 复制稳定版本到 `services/macrotrace/`；
- 写 `UPSTREAM_COMMIT`;
- 写 `UPSTREAM_LICENSE`;
- 禁止无记录改写上游核心。

## 7. 冻结

- H28：`feature-freeze`
- H32：`code-freeze`
- 最终：`demo-v1.0`

冻结后不进行目录重构、依赖升级或大规模格式化。
