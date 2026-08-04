# MacroTrace 首批扩展语料：30 份来源目录

本批次固定为 10 份机构 PDF、10 个官方研究网页、10 份基础论文 PDF。机器可读、可复抓取的唯一目录是
[`report_pipeline/corpus30/source_catalog.json`](../report_pipeline/corpus30/source_catalog.json)。原始文件不进入仓库；本地抓取会记录最终 URL、时间、字节数和 SHA-256。

## 选择目的

- 机构报告覆盖美国通胀、增长、就业、货币政策、财政、金融稳定、银行、外部平衡、能源、家庭信用和制造业。
- 网页来源不是泛泛评论，而是 GDPNow、Inflation Nowcasting、GSCPI、Trimmed Mean PCE、NFCI、ADS、Outlook-at-Risk 等可以拆成数据与模型节点的官方方法页面。
- 基础论文补齐 Dynamic Factor、实时 nowcast/news、Local Projection、Growth-at-Risk、BVAR、FAVAR、新凯恩斯机制、结构性通胀、金融加速器和 SVAR 长期约束。

## Codex 原生逆向协议

每份材料都经过以下语义阅读，而不是词频或自动摘要：

1. **定位阅读**：识别原始研究问题、结论边界、目录、图表、公式、附录和数据说明。
2. **机制阅读**：还原“冲击/状态 → 机制 → 中间命题 → 结果”的因果或预测链。
3. **实证阅读**：记录 estimand、因变量、自变量、控制、样本、频率、变换、识别、模型、诊断和稳健性。
4. **产品映射**：映射为 Question → Lane → Mechanism → Node → Factor → Dataset/Transform → Model → Diagnostic → Evidence → Aggregation。
5. **冲突检查**：与 R01–R11 和当前 Registry 对照，决定新增、合并、仅证据或阻塞；不因名称不同制造重复模块。
6. **独立复核**：由不同 `review_run_id` 的第二遍 Codex 阅读核对页码、公式、变量定义和 Registry 边界。Codex 不被伪装成人工 reviewer，但它是本流程的正式研究 reviewer。

抓取脚本只做来源保存：

```powershell
python scripts/fetch_reverse_corpus.py --strict
```

抓取结束后，`scripts/report_pipeline.py` 负责指纹、逐页文本映射、记录校验和 changeset 门控。未经复现的模型或方法最多进入 `candidate/reviewed`，不能自动变成运行时 `active`。
