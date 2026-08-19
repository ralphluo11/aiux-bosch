# Source Inventory 使用说明

每个候选文件占一行。文件进入 Agent Input 前，以下字段必须明确：

- `owner`
- `permission_status`
- `data_classification`
- `contains_personal_data`
- `deidentified`
- `allowed_for_agent`
- `holdout_only`

不确定就填 `TBC` 或 `pending`，不要自行推断授权。
