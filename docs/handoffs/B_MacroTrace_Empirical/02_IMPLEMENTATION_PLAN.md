# Role B 实施计划与测试

## H0-H2

- 仓库和本地 MacroTrace 版本盘点；
- 记录 upstream commit；
- 跑现有测试；
- 创建分支。

## H2-H6

- 导入 MacroTrace；
- 修复目标环境运行；
- 保持现有 Demo 可用。

## H6-H10

- ToolRequest validator；
- EvidenceBundle mapper；
- Fixture endpoint。

## H10-H14

- A Data Resolve Adapter；
- 固定对象版本；
- lineage 和 hash。

## H14-H18

- 美国黄金路线；
- 主模型、诊断、限制；
- 三次运行。

## H18-H22

- C 真实联调；
- 错误和超时；
- Artifact 和 Graph。

## H22-H28

- Offline；
- 快照；
- Demo reset；
- 可选中国 Gate。

## 测试目标

```bash
pytest -q
pytest tests/contract -q
pytest tests/integration/macrotrace -q
```

## 关键测试

1. 不合法 ToolRequest；
2. 缺少数据对象；
3. Schema mismatch；
4. 模型成功；
5. 模型失败；
6. 阻断诊断；
7. 关联证据映射；
8. 结果 hash；
9. offline replay 标记；
10. C 反序列化。
