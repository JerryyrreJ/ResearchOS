# B MacroTrace Empirical Handoff v1.1

    ## 用法

    1. 解压本包；
    2. 将整个目录上传给该成员的 Codex；
    3. 让 Codex 先读 `00_START_HERE.md`；
    4. 将 `07_CODEX_MASTER_PROMPT.md` 作为第一条执行任务；
    5. Codex 必须先做仓库盘点，不得立即重构；
    6. 团队确认 Repo Inventory 和 First PR Plan 后再写代码。

    ## 分支

    `role/b-macrotrace`

    ## 角色拥有范围

    - services/macrotrace
- macrotrace adapter
- snapshots

    ## 冻结规则

    - `shared/contracts/v1` 不得私改；
    - 越界请求按 `03_HUMAN_CHANGE_PROTOCOL.md` 处理；
    - 目标仓库在规划阶段无法读取，必须执行 `shared/REPO_PREFLIGHT.md`；
    - 真实仓库已有代码优先复用；
    - PR 只提交本角色路径和批准的共享文件。
