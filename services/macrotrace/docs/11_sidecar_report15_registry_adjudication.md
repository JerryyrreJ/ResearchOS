# Report15 侧车批次 Registry 裁决

## 结论

`BATCH.REPORT15.20260805.SIDECAR` 包含 15 份报告、307 页、61 条研究路径、236 项变量定义和 76 条页码证据。侧车 Schema 审计通过，但没有任何方法完成美国数据复现，因此本轮只允许把 9 份宏观/市场研究来源登记为 `reviewed`。六份公司估值报告继续留在私有 `EVIDENCE_ONLY` 池；原 PDF、逐页文本和完整 records 不进入 Git。

登记来源不等于激活方法。下列方法裁决保存在 `report_pipeline/sidecar15/registry_adjudication.json`，运行平面不得绕过复现门。

## 优先方法裁决

| 方法组件 | 当前裁决 | 复用对象 | 新候选边界 | 激活前缺口 |
|---|---|---|---|---|
| 财政状态复合指标 | `REPRODUCTION_PENDING` | `US.FISCAL_TREASURY`、`MECH.FISCAL.BALANCE`、`N.FISCAL.BALANCE` | 新 Factor 与复合配方 | 用 Treasury/BEA/CBO 重建口径、vintage、等权/PCA 基准和滚动转折点验证 |
| 财政融资减现金余额代理 | `REPRODUCTION_PENDING` | 财政 Balance/Supply 与 `N.MONETARY.LIQUIDITY` | `F.FISCAL.NET_CASH_INJECTION.CANDIDATE` | TGA/净融资会计勾稽、符号与发布时间；禁止解释为财政乘数 |
| 贸易暴露与转口评分 | `REPRODUCTION_PENDING` | `US.TRADE`、`MECH.TRADE.EXTERNAL_DEMAND` | 新贸易节点和两个 Factor | 产品—行业映射、镜像贸易、原产地规则与替代权重；贸易泳道保持 blocked |
| 指数成分股平均相关性 | `REPRODUCTION_PENDING` | 仅复用 `US.FIN_STABILITY` | 新 market-cohesion mechanism/node/factor/recipe | 点时成分股历史、恒等式勾稽、直接两两相关基准、严格滚动样本外 |
| 银行资产负债重定价瀑布 | `REPRODUCTION_PENDING` | 金融稳定、货币与信用放大机制 | 新 bank-repricing mechanism/node/factor/recipe | 美国 Call Report 口径、存款 beta、提前还款、收益率曲线和组件加总检查 |
| REIT 资本化率与现金分派桥接 | `REPRODUCTION_PENDING` | 住房与货币泳道 | 新 REIT cash-flow mechanism/node/factor/recipe | 美国 REIT 会计口径、NOI→AFFO 勾稽、`r>g`、杠杆与再融资压力 |

两项映射被主审明确纠正：成分股相关性不能挂到跨泳道的 `N.ACTIVITY.TAIL_RISK`；REIT 估值不能塞进只研究 permits/starts 的 `N.HOUSING.CYCLE`。二者都需要独立候选节点。

## 降级与拒绝

- `RC.1FC594395298` 与 `RC.A8B571F4D9A8` 的月度拼图和高频看板只进入因子发现目录，不单独支撑综合结论。
- 关税 1.8% 粗略换算、中国银行 0.67% 净息差阈值、双边 HP 实时状态、KAMA、行业 Alpha、五次 GDP 外推和未来盈利窗口选择继续阻断。
- 六份公司估值报告只保留 DCF、DDM、NAV、EV/EBITDA 与 rNPV 方法证据；目标价、评级和买卖结论禁止进入美国宏观路由。

## 受控导入

本批次已由 changeset `CS.BATCH.REPORT15.20260805.SIDECAR.71DF2FEC79D8` 完成来源登记，精确 content hash 为 `5fd1e20849f984e815f60427ae2dab942bf13aa07b335dd92a325eca5fef3a72`。应用内容只有 9 个 `reports ADD → reviewed`；应用后 live Report Registry 为 20 份。六份公司估值报告仍留在私有 `EVIDENCE_ONLY` 池，全部候选 mechanism/node/factor/recipe 仍未进入 live Registry。

```powershell
Set-Location services\macrotrace

.\.venv\Scripts\python.exe scripts\import_sidecar_reverse_bundle.py `
  --records-jsonl <sidecar>\handoff\reverse_records.jsonl `
  --adjudication report_pipeline\sidecar15\registry_adjudication.json

# 仅生成 staged Registry，不修改 live Registry
.\.venv\Scripts\python.exe scripts\report_pipeline.py build-changeset `
  data\report_batches\BATCH.REPORT15.20260805.SIDECAR
```

应用仍需要 changeset 生成后的独立 `APPROVE_APPLY`，并在 apply 前核对精确 content hash。未复现的方法不会随来源登记而变成 active。
