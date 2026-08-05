# 美国市场混合路由与量化侧车融合记录

## 产品边界

当前版本只研究美国市场，覆盖美国宏观、利率与债券、宽基股票、行业背景、能源和商品。非美国市场问题必须返回 `UNSUPPORTED`，不得用美国数据代理执行。

## 混合路由合同

1. Registry 固定可用的工作流、泳道、研究节点、因子、模型和参数边界。
2. LLM 只负责识别问题领域，并在 Registry 白名单内排序和选择。
3. 每个工作流的核心泳道和核心节点由后端强制保留；LLM 不能删除，也不能创建新 ID、公式、代码或数值权重。
4. LLM 输出非法、超时或两次校验失败时，系统回退到确定性路由，继续执行已注册研究程序。
5. Python 使用真实数据执行模型、诊断和聚合；LLM 只解释结构化结果。

## 本轮侧车研究裁决

已纳入候选来源：

- `RC.7682F8E97EB4`：Time Series Momentum；
- `RC.E0533A62D4CC`：The Fundamentals of Commodity Futures Returns；
- `RC.25386D9CC68D`：Equilibrium Forward Curves for Commodities；
- `RC.FC5C3DFA15F0`：The Term Structure of Oil Futures Prices；
- `RC.0FA80A4AF119`：The Effect of the Federal Reserve on the Stock Market；
- `RC.75FA4CC97E50`：Forecasting Sector Stock Market Returns。

宏观能源传导保留在 `US.COMMODITY_ENERGY`；期货方向、库存、基差、便利收益和期限结构单独进入 `US.FUTURES_COMMODITY`，避免把宏观通胀传导与期货收益研究混为一谈。

## 当前可执行层

- 美国股票：S&P 500、Nasdaq、VIX、利率、美元、信用利差和金融条件；执行日频 AR、桥接回归和 VAR，并进行时间顺序样本外验证。
- 美国商品：WTI、Henry Hub、铜、综合商品指数、EIA 原油库存、美元和利率；执行价格方向、实物供需与宏观传导模型。
- FRED 连接增加连接失败重试；EIA 连接同时抓取 WTI 和 `WCESTUS1` 原油库存。

这里的 WTI、天然气等价格是免费官方现货或实物市场代理，不冒充经过换月处理的连续期货合约。

## 显示但暂不执行

以下节点保留在完整研究图中并标记 `BLOCKED`：

- 跨合约时间序列动量；
- 库存—基差—风险溢价；
- 储存均衡与便利收益；
- 原油期限结构斜率和曲率；
- FOMC 高频股票事件研究；
- 美国行业收益递归预测。

解锁条件分别包括：点时可得的连续期货收益、明确换月规则、单个到期合约曲线、基差序列、盘中事件时间戳、货币政策意外指标，以及可投资行业总收益面板。条件满足前，这些节点只展示研究能力边界，不进入结论。

## 前端表达

Research Graph 始终展示完整 Registry 节点宇宙：本题路由节点高亮，未路由节点置灰，缺数据或识别条件的节点显示阻断。市场二选一问题即使综合优势较弱，也给出“边际偏向上涨/下跌”的明确方向，同时在正文披露优势较弱、模型分歧和识别限制。
