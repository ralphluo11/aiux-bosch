# 冰箱 Benchmark 材料包

> **状态：** 待填充  
> **用途：** 为 Research Agent Vertical Alpha 准备可审计的输入、人工 Ground Truth、评测样本和交付记录。  
> **数据原则：** 未脱敏姓名、联系方式、录音、设备 ID 或其他敏感信息不得放入 `04_Agent_Input_Deidentified/`。

## 最重要的边界

```text
可给 Agent 的材料
01_Project_Brief
02_Source_Inventory
04_Agent_Input_Deidentified
07_Benchmark_Samples/Input

不可在分析前给 Agent 的答案
05_Holdout_Reference_DO_NOT_GIVE_TO_AGENT
06_Ground_Truth
07_Benchmark_Samples/Expected
```

运行前由人工确认输入清单。Agent 完成分析并锁定 Run 后，才允许打开 Holdout / Ground Truth 进行对比。

## 文件夹说明

| 文件夹 | 放什么 | 谁来填 |
|---|---|---|
| `01_Project_Brief/` | 业务决策、研究目标、研究问题、用户、边界、材料、交付、成功标准 | Joe / Business Sponsor / Research Lead，未知写 TBC |
| `02_Source_Inventory/` | 每个来源的文件名、Owner、版本、日期、权限、数据等级、脱敏和是否可给 Agent | 项目材料负责人 |
| `03_Raw_Materials_RESTRICTED/` | 原始转写、报告、PPT、研究笔记、指标和其他原材料；默认受限 | 项目材料负责人；不要直接给 Agent |
| `04_Agent_Input_Deidentified/` | 从原始材料复制并完成脱敏、权限确认后的 Agent 输入 | Data Owner / Research Lead 审批 |
| `05_Holdout_Reference_DO_NOT_GIVE_TO_AGENT/` | 原人工 Summary、Findings、Report、优先级等保留答案 | Research Lead；分析前隔离 |
| `06_Ground_Truth/` | 人工冻结的关键事实、Evidence、Finding、Priority、可接受建议和争议 | Research Lead + Domain Expert |
| `07_Benchmark_Samples/` | 单条评测输入、Expected、禁错样本和 Rubric | UX / Research Lead |
| `08_Evaluation_Runs/` | 每次运行的模型/Skill/Prompt版本、输出、评分和耗时 | AI / Evaluator |
| `09_Review_and_Delivery/` | AI Raw、Human Final、Review理由、One-pager和最终评测报告 | Research Lead / Approver |
| `10_Permissions_and_Compliance/` | 数据分类、允许的 AI Endpoint、脱敏检查、保留与删除要求 | Data Owner / IT / Security |

## 建议命名

- Transcript：`P01_transcript_deidentified.txt`
- Report：`YYYY-MM-DD_report_title_v01.pdf`
- Presentation：`YYYY-MM-DD_deck_title_v01.pptx`
- Research note：`YYYY-MM-DD_note_topic_author-role.md`
- Benchmark run：`RUN_YYYYMMDD_01/`

Participant 仅使用编号，不在文件名中写真实姓名。

## 你可以怎么把内容交给我

1. 直接把文件放到对应文件夹，我读取后补清单和模板；或
2. 在对话中逐项告诉我 Brief 信息，我代填 `PROJECT_BRIEF_CN.md`；或
3. 把材料一次放进 `00_Inbox_To_Classify/`，我只在本项目范围内帮你分类。敏感材料仍需先确认权限与脱敏要求。

## 开始前的最低完成条件

- [ ] `PROJECT_BRIEF_CN.md` 关键字段完成或标 TBC；
- [ ] `SOURCE_INVENTORY.csv` 列出全部候选材料；
- [ ] `DATA_PERMISSION_CHECKLIST_CN.md` 确认允许处理的范围；
- [ ] 至少 3 份脱敏材料进入 `04_Agent_Input_Deidentified/`；
- [ ] Holdout 与 Agent Input 完全分离；
- [ ] Research Lead 确认 Ground Truth Owner 和争议处理方式。
