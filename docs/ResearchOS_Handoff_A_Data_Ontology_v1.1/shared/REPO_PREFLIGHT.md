# Repo Preflight：所有 Codex 的第一项任务

在写代码之前执行：

```bash
git status --short --branch
git branch --show-current
git log -5 --oneline
find . -maxdepth 3 -type f | sort | sed -n '1,240p'
```

读取：

```text
AGENTS.md
README.md
pyproject.toml / requirements*
package.json / lockfile
已有 docs
已有 contracts
已有 CI
```

输出 `docs/handoffs/repo_inventory_<ROLE>.md`，至少包含：

- 当前分支和 HEAD；
- 目录树；
- 现有技术栈；
- 与目标架构对应关系；
- 本角色可复用代码；
- 路径冲突；
- 不能删除的现有资产；
- 需要团队确认的结构问题。

规则：

1. 仓库有代码时，不得直接重新初始化；
2. 有现有 API 时，优先加 Adapter；
3. 有现有测试时，先跑测试；
4. 发现另一个角色已经修改共享文件时，停止并同步；
5. 发现合同缺失时，只能使用包内冻结合同，不得自创。
