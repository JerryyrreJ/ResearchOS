# 四人团队启动步骤

## 1. 仓库管理员先完成

```bash
git clone <AIY_Project_URL>
cd AIY_Project
git checkout -b integration
git push -u origin integration

git branch role/a-ontology
git branch role/b-macrotrace
git branch role/c-thesis
git branch role/d-frontend

git push origin role/a-ontology role/b-macrotrace role/c-thesis role/d-frontend
```

将四位成员加入仓库 Collaborators，并保护 `main` 和 `integration`。

## 2. 导入共享文件

由一人创建 `contracts-bootstrap` PR，只导入：

- `AGENTS.md`；
- `contracts/v1/`；
- 合同 Fixtures；
- `docs/rfcs/ICR_TEMPLATE.md`；
- PR Template；
- 产品宪章和架构文件。

该 PR 合并后，四个角色都从同一提交同步。

## 3. 每位成员

1. 解压自己对应的 Handoff ZIP；
2. 将 ZIP 上传给自己的 Codex；
3. 把 `07_CODEX_MASTER_PROMPT.md` 作为第一条任务；
4. 要求 Codex 先输出 Repo Inventory；
5. 确认路径映射和第一 PR 计划；
6. Codex 才能开始改代码。

## 4. Worktree

```bash
git worktree add ../AIY_A role/a-ontology
git worktree add ../AIY_B role/b-macrotrace
git worktree add ../AIY_C role/c-thesis
git worktree add ../AIY_D role/d-frontend
```

每个 Codex 只操作一个 worktree。

## 5. 每四小时同步

每位成员报告：

```text
Role:
Branch:
Commit:
Completed:
Blocked:
Contract impact:
Need from other roles:
Next integration test:
```

阻断问题优先处理合同和 Fixture，避免等待真实服务。
