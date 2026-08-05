# MacroTrace 本地模型与数据源配置

MacroTrace 的公开分发版本采用 BYOK（Bring Your Own Key）模式：项目不附带作者的模型密钥或数据源密钥，使用者在本地启动服务后，通过首页的 `API & data` 配置中心接入自己的服务。

这套配置只面向本地应用。配置接口拒绝来自非本机客户端或非本机网页 Origin 的请求，不能直接作为公网密钥管理服务使用。

## 一、从前端完成配置

1. 启动 MacroTrace，并打开 `http://127.0.0.1:8000`。
2. 点击顶部导航中的 `API & data`，或首页的 `LOCAL PROVIDERS` 卡片。
3. 在 `01 Model service` 中选择模型供应商、模型、Endpoint 与 API Key。
4. 选择密钥存储方式：
   - `仅本次运行`：只保存在当前 Python 进程内，服务停止后消失。
   - `保存在本机`：写入被 Git 忽略的 `data/private/provider-config.json`。
5. 点击“保存配置”，再点击“测试连接”。
6. 在 `02 Macro data` 中依次配置 FRED、BLS 与 EIA；Treasury 和 New York Fed 当前无需密钥。
7. 每个数据源先单独测试，通过后再点击“同步已配置数据源”。

模型下拉框只是经过验证的常用选项。供应商发布新模型后，可以选择“自定义模型 ID”，无需修改前端代码。

## 二、模型供应商

| 供应商 | 默认 Endpoint | 配置能力 |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | 官方模型或自定义模型 ID |
| DeepSeek | `https://api.deepseek.com` | 官方模型或自定义模型 ID |
| Anthropic / Claude | `https://api.anthropic.com` | Anthropic Messages API |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | Google 官方 OpenAI-compatible 接口 |
| Custom | 使用者填写 | 任意 OpenAI-compatible `/chat/completions` 服务 |

配置中心内置官方申请入口和逐步说明。模型名称可能随供应商更新而变化；以供应商文档和账户中实际可调用的模型 ID 为准。

自定义 Endpoint 的约束：

- 公网地址必须使用 HTTPS。
- HTTP 只允许 `localhost`、`127.0.0.1` 或 `::1`。
- URL 不能包含用户名或密码。
- 可以填写 API Base URL，也可以填写以 `/chat/completions` 结尾的完整 Endpoint。

## 三、美国宏观数据源

| 数据源 | 是否需要 Key | 当前覆盖 |
| --- | --- | --- |
| FRED / ALFRED | 是 | 利率、通胀、增长、金融条件、州级面板与部分 vintage |
| BLS Public Data API | 是 | CPI、就业、失业率、工资、JOLTS 与行业劳动力指标 |
| EIA Open Data | 是 | 原油、天然气、电力与能源价格 |
| U.S. Treasury Fiscal Data | 否 | 联邦债务与财政数据 |
| New York Fed Markets API | 否 | SOFR 等参考利率 |

申请步骤和官方链接直接显示在每个数据源卡片内。FRED 使用还必须保留以下声明：

> This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

## 四、密钥安全合同

- API Key 不写入浏览器 `localStorage`、任务历史或 URL。
- 后端状态接口只返回 `********`，永不把完整密钥回传给前端。
- Pydantic 使用 `SecretStr` 接收密钥，错误信息不会包含供应商响应正文。
- LLM trace、研究图、artifact、日志和截图不得记录密钥。
- `data/`、`.env.local`、`artifacts/` 与 `release/` 均在 `.gitignore` 中。
- “保存在本机”只适用于单用户电脑；多人共用电脑时应使用“仅本次运行”。
- 如果密钥来自 `.env.local`，前端的“清除本地配置”不会修改环境文件；需要手动删除对应变量并重启服务。

不要把本地设置接口暴露到公网。未来如果改为多人部署，必须换成用户身份认证、加密凭据存储、对象级授权和服务端 Secret Manager。

## 五、设置 API

前端使用以下本地端点：

```text
GET    /v1/settings/catalog
GET    /v1/settings/status
PUT    /v1/settings/llm
POST   /v1/settings/llm/test
DELETE /v1/settings/llm

PUT    /v1/settings/data-sources/{source_id}
POST   /v1/settings/data-sources/{source_id}/test
DELETE /v1/settings/data-sources/{source_id}
```

这些端点只负责本地配置与连接测试。研究执行仍通过 Registry 约束的研究任务 API 完成，模型供应商不能借此修改 Python 统计代码、公式或白名单参数。

## 六、让 Codex 或 Claude Code 添加新数据源

首页 `03 Add new source` 提供了可复制的任务模板。添加连接器时应至少完成：

1. 新增官方 API 客户端，并配置 timeout、重试、频率限制和错误分类。
2. 将密钥加入本地凭据层，而不是写入源码或前端。
3. 在 Dataset Registry 中登记来源、许可、频率、单位、发布时间、修订与 vintage 属性。
4. 在 Factor Registry 中登记经济定义、变换、滞后、适用机制与失效条件。
5. 建立原始字段到标准观测表的映射，保留 source、series、as-of 和抓取批次。
6. 增加连接测试、同步测试、无密钥错误测试、未来数据泄漏测试和 Registry 兼容性测试。
7. 在配置中心增加申请步骤、官方文档链接、密钥状态与同步状态。
8. 运行完整测试和浏览器验收，不得用 mock 结果冒充真实数据同步。

推荐交给本地编码代理的说明：

```text
请在 MacroTrace 中新增一个官方数据连接器：[数据源名称]。
先阅读 docs/12_local_provider_configuration.md、现有 connector、
Dataset Registry、Factor Registry 和测试。实现官方 API 客户端、
本地密钥配置、连接测试、增量同步、字段标准化、vintage/release
元数据、因子映射、失败降级和前端申请指南。不得把密钥写入源码、
浏览器存储、日志、trace、artifact、截图或 Git。不得生成新的统计
模型代码绕过 Registry。完成后运行全量 pytest、compileall、
node --check 和桌面/手机浏览器验收，并列出新增数据集、因子、
覆盖范围、限制与官方来源。
```

## 七、代码位置

- 供应商与数据源目录：`backend/app/provider_catalog.py`
- 本地密钥存储：`backend/app/credentials.py`
- 连接测试：`backend/app/connection_service.py`
- 请求 Schema：`backend/app/connection_schemas.py`
- 设置端点：`backend/app/main.py`
- 动态 LLM 客户端：`backend/app/llm.py`
- 数据同步入口：`backend/app/sync.py`
- 前端配置中心：`frontend/index.html`、`frontend/app.js`、`frontend/styles.css`
- 安全与功能测试：`tests/test_local_provider_settings.py`

