# Agent Input · 已脱敏且已授权

只有同时满足以下条件的副本才能进入此目录：

- 已在 `SOURCE_INVENTORY.csv` 登记；
- `permission_status=approved`；
- `deidentified=yes`；
- `allowed_for_agent=yes`；
- 不属于 Holdout；
- 已确认允许通过指定 AI Endpoint 处理。

建议优先使用 TXT / MD，每位 Participant 一个文件。不要把原人工 Findings、Summary 或 Final Report 混入输入。
