# Benchmark Rubric

> **状态：** Draft / Proposed，需小样本试标后冻结。

## 评分维度

| 维度 | 需要判断什么 | 初始规则 |
|---|---|---|
| 事实准确性 | 输出是否与批准 Ground Truth 一致 | 关键事实错误单独标记 |
| Evidence 定位 | Claim 是否能打开正确来源和原文 | 位置错误视为未定位 |
| 关键遗漏 | Ground Truth 中重要内容是否缺失 | 按 priority 加权 |
| 类型正确 | fact / inference / recommendation 是否混淆 | 假设冒充事实为高风险错误 |
| 重复与冲突 | 是否合并重复、显式标记冲突 | 不得静默选择一方 |
| 人工修改 | Accept / Edit / Reject 及修改幅度 | 保留 AI Raw / Human Final |
| 时间 | Agent + Review 与人工基线的差异 | 先建立基线，不预承诺 ROI |

## 样本数量

先试标 10-15 条以稳定样本单位和评分口径。30-50 条是候选目标，不是已批准要求。
