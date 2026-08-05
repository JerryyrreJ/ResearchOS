# MacroTrace 公开网站部署交接

## 1. 交接目标

本仓库是 MacroTrace 当前成品的单仓库交接版本。目标是在一台可信云服务器上运行 Python 后端，并由同一服务提供前端页面：

`浏览器 → HTTPS / Nginx → FastAPI → Research Compiler / Empirical Models → DuckDB + Artifacts`

前端只提交问题、读取进度、研究图和结构化结果。真实观测数据、模型运行、任务记录和生成的 artifact 全部留在服务器端。

## 2. 已包含的内容

- 当前前端与手机、安卓、iPhone、iPad、笔记本和桌面响应式样式；
- FastAPI 后端、分层问题编译、受注册表约束的路由、真实模型与诊断；
- Lane、Mechanism、Node、Factor、Model、Route 与研报逆向注册表；
- 当前官方美国市场观测数据和原始快照；
- 已清空个人提问、运行历史和研究 artifact 的种子 DuckDB；
- Windows 本地启动脚本；
- Docker、生产 Compose、Nginx 反向代理示例；
- 中英文产品文档、测试和数据/代码完整性清单。

## 3. 不包含的内容

公开 GitHub 仓库不包含真实 API Key、账号或密码。原因是公开提交会永久进入 Git 历史，任何人都能复制并产生费用。仓库已包含全部变量名、申请入口和注入位置；真实值必须由服务器负责人通过安全渠道放入服务器的 `.env.production`，不能再提交回 Git。

需要注入的变量：

- `DEEPSEEK_API_KEY`
- `FRED_API_KEY`
- `BLS_API_KEY`
- `BEA_API_KEY`
- `CENSUS_API_KEY`
- `EIA_API_KEY`
- `MACROTRACE_SYNC_ADMIN_KEY`（如开放远程数据同步）

## 4. 最短服务器部署步骤

```bash
git clone https://github.com/ZhenyuanPAN822/macrotrace-researchos.git
cd macrotrace-researchos
cp .env.production.example .env.production
# 编辑 .env.production：填入域名和通过安全渠道收到的密钥
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml ps
curl http://127.0.0.1:8000/v1/health
```

第一次启动时，容器会把只读种子数据库复制到 `runtime/macrotrace.duckdb`。后续重新构建镜像不会覆盖服务器的运行历史和 artifact。

## 5. 域名与 HTTPS

1. 把域名 A 记录指向服务器公网 IP。
2. 将 `deploy/nginx/macrotrace.conf.example` 复制到 Nginx 配置目录并替换 `YOUR_DOMAIN`。
3. 检查并重载 Nginx。
4. 使用 Certbot 或云厂商证书配置 HTTPS。
5. 把 `.env.production` 的 `MACROTRACE_ALLOWED_HOSTS` 和 `MACROTRACE_CORS_ORIGINS` 改成真实域名后重启容器。

同源部署是第一版最稳妥的方案：FastAPI 同时提供页面和 API，不需要维护第二套前端构建服务器，也不会产生跨域配置漂移。

## 6. 数据与持久化

- `data/macrotrace.duckdb`：公开的干净种子数据库，只包含观测值和数据同步沿革。
- `data/raw/`：官方来源的原始快照，供复核与重新构造。
- `runtime/macrotrace.duckdb`：服务器首次启动后生成的可写数据库。
- `runtime/artifacts/`：回归表、图、诊断和结构化结果。

上线前备份 `runtime/`；升级镜像时不要删除这个目录。公开前端不得直接下载 DuckDB 或 raw 文件，所有数据读取只能经过后端白名单 API。

## 7. 生产配置建议

- 只运行 1 个 Uvicorn worker。当前任务队列和 DuckDB 写入都在单进程内协调，多 worker 会造成状态分裂。
- 服务器大内存不等于无限并发。首发保留 `MACROTRACE_MAX_JOB_WORKERS=1`、`MACROTRACE_MAX_QUEUED_JOBS=3`。
- 公网默认关闭数据同步：`MACROTRACE_ALLOW_DATA_SYNC=false`。需要更新数据时，使用维护窗口或设置高强度 `MACROTRACE_SYNC_ADMIN_KEY`。
- Nginx 保留 600 秒读取超时；模型节点自身仍应使用注册表的超时与规模上限。
- 公开前增加云防火墙、HTTPS、访问日志轮转、磁盘告警和每日 `runtime/` 备份。

## 8. 验收清单

- `/v1/health` 返回成功；
- 首页在 360、390、820、1280 和 1440 像素宽度下无页面横向溢出；
- 研究来源在手机单列、平板双列、桌面侧栏显示；
- 能提交问题、看到任务进度、Research Graph、模型详情和完整研究报告；
- 任一模型节点能追溯变量、规格、结果、诊断与 provenance；
- 浏览器网络响应与页面源码中不存在 API Key；
- 重启容器后旧任务和 artifact 仍在；
- 同一个请求受到速率与队列限制；
- `git status` 不出现 `.env.production` 或 `runtime/`。

## 9. 当前边界

- 当前是美国市场研究系统，覆盖宏观、利率、股票指数和商品相关路径；
- 当前任务队列不是 Redis/Celery 式分布式队列，首发保持单实例；
- 公开网站如果需要用户账户、计费、跨实例调度或多人权限，需要下一阶段增加数据库与鉴权层；
- LLM 只负责结构化选择和证据解释，不允许生成任意执行代码、SQL、公式或注册表修改。

## 10. 故障回滚

```bash
docker compose -f docker-compose.production.yml logs --tail=300 macrotrace
docker compose -f docker-compose.production.yml down
git checkout <last-known-good-commit>
docker compose -f docker-compose.production.yml up -d --build
```

不要回滚或覆盖 `runtime/`。如数据库损坏，先复制整个 `runtime/` 留档，再从最近备份恢复。
