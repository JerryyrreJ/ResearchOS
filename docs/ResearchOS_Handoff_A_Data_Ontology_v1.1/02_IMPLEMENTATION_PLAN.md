# Role A 实施计划与测试

## H0-H2

- 仓库盘点；
- 运行测试；
- 校验合同哈希；
- 建 `role/a-ontology`；
- 输出路径映射。

## H2-H6

- Object / Version / Representation；
- 文件存储；
- SHA-256；
- batch upload；
- exact duplicate。

## H6-H10

- Markdown / DOCX Canonicalizer；
- PDF / XLSX 最小支持；
- Manifest；
- Parser failure。

## H10-H14

- 标签和候选关系；
- Project State；
- Ontology Graph JSON。

## H14-H18

- Context Pack；
- Data Resolve；
- 与 B/C Fixture 联调。

## H18-H22

- 影响传播；
- 权限最小实现；
- D 所需 API；
- 集成测试。

## H22-H28

- 性能、离线、Demo 数据；
- 失败降级；
- 文档和发布 Fixture。

## 测试命令目标

```bash
pytest tests/unit/ontology -q
pytest tests/integration/ontology -q
pytest tests/contract -q
```

## 关键测试

1. 同一字节文件两次上传；
2. 同名不同内容；
3. 新版本不覆盖旧版本；
4. DOCX 表格；
5. PDF 页码；
6. Excel 多 Sheet；
7. Parser failure；
8. 无权限读取；
9. Data Resolve 缺字段；
10. Context Pack 锁定版本。
