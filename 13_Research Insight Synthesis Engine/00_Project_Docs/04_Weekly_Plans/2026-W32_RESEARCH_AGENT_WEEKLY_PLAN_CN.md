# Research Agent · 本周执行计划

> **周期：** 2026-08-03（周一）— 2026-08-07（周五）  
> **制定时间：** 2026-08-03 11:15 CST  
> **版本：** V1.0  
> **状态：** Ready to Execute  
> **本周类型：** 历史项目盲测 + ROI 可行性验证  
> **团队：** Product Owner（你）+ UX 2人 + AI 实习生 1人 + Codex

## 1. 本周唯一目标

本周不继续扩建平台功能，也不制作正式 Gold Set。只回答一个问题：

> **现有 v0.5 Research Agent 能否利用一个历史研究项目的脱敏采访，在较少 UX 投入下生成有原文证据、可审核的 Findings 与 Insights，并显示出至少 50% 的人工时间节省潜力？**

本周结果只能用于决定“是否值得继续迭代”，不能证明产品已达到生产质量，也不能据此对外宣称 ROI 已成立。

## 2. 为什么本周这样做

当前已具备：

- v0.5 Multi-Interview Research Agent；
- Research Project、批量文本导入与 SQLite 存储；
- Bosch AI Endpoint 接入；
- Evidence → Finding → Insight 结构化输出；
- Quote 必须逐字存在于对应 Transcript 的服务器校验；
- 已有历史采访和人工总结，可作为不泄露给 Agent 的参考答案。

当前尚不具备：

- 经验证的分析质量；
- 正式 Gold Set；
- 多项目 ROI 数据；
- 稳定的两阶段 Evidence → Cross-interview Synthesis 工作流；
- 生产级数据治理与权限。

因此，本周应先验证真实价值，而不是继续增加页面、Voice、Marketplace、Knowledge Engine 或完整平台能力。

## 3. 本周不做

- 不做正式 20–30 条 Gold Set；
- 不做实时语音、ASR 或 Participant Link；
- 不接 OneDrive / SharePoint 自动读取；
- 不做 SSO、Credits、Marketplace 或完整 Owner Portal；
- 不重新设计全部 UI；
- 不制作正式双语 PRD 或管理层大 PPT；
- 不把人工 Summary、Final Report、Findings 或 Insights作为 Agent 输入；
- 不使用未脱敏的姓名、联系方式、录音或敏感内部材料；
- 除非阻断测试，不新增功能。

## 4. 本周需要准备的材料

选择 **1个** 历史项目，必须满足：

- 已完成且团队熟悉；
- 有明确 Research Goal 与 Research Questions；
- 有 3–10 份可脱敏 Transcript；
- 有研究团队认可的最终 Summary / Findings / Report；
- 项目范围不依赖大量图片、视频或未解析附件；
- 数据允许在当前批准的 Bosch AI Endpoint 中处理。

本周建议只使用 `.txt` 或 `.md`，每位 Participant 一个文件：

```text
P01.txt
P02.txt
P03.txt
...
```

本周不优先使用 CSV / JSON。虽然页面支持上传，但当前版本会把每个文件整体当成一份 Transcript，TXT / MD 更容易检查 Participant 与原文关系。

### 输入包

```text
Blind_Test_Input/
├── RESEARCH_BRIEF.md
└── Transcripts/
    ├── P01.txt
    ├── P02.txt
    └── ...
```

### 保留答案包（不上传）

```text
Holdout_Reference/
├── FINAL_SUMMARY.*
├── FINAL_FINDINGS.*
└── FINAL_REPORT.*
```

`Holdout_Reference` 只在 Agent 完成分析后打开，用于比较，防止把原答案泄露给模型。

## 5. 人员投入上限

| 角色 | 本周投入上限 | 只负责什么 |
|---|---:|---|
| Product Owner（你） | 3–4小时 | 选项目、确认合规、设定目标、做继续/停止决策 |
| UX 1（Research Quality） | 2小时 | 审核 Evidence、Findings、Insights 与遗漏 |
| UX 2（Product Experience） | 1–1.5小时 | 观察操作阻力、记录页面与工作流问题 |
| AI 实习生 | 2–3个工作日 | 准备环境、运行 POC、修复阻断问题、整理结果 |
| Codex | 按需 | 生成测试表、对比、统计、修复代码和整理报告 |

两位 UX 不从头重做研究分析，不手工制作完整标准答案；只基于已有报告进行判断。

## 6. 每日执行计划

## 周一 8月3日｜冻结项目与输入

### Product Owner

1. 从历史项目中选择一个作为 Blind Test。
2. 确认该材料是否允许通过当前 Bosch AI Endpoint 处理。
3. 写下原项目的：
   - Research Goal；
   - Research Questions；
   - Target Users；
   - 原人工分析大约耗时；
   - 最终报告由谁认可。
4. 将 Final Summary / Findings / Report 单独保存为 Holdout，不给 Agent。

### AI 实习生 + Codex

1. 检查 POC 可以启动并显示 `Live AI`。
2. 将每份 Transcript 转成单独 TXT / MD。
3. 只做脱敏和格式清理，不重写受访者原话。
4. 建立测试记录：开始时间、上传时间、AI运行时间、错误和版本。

### 当日完成定义

- 1个历史项目被冻结；
- 3–10份脱敏 Transcript 准备完成；
- Holdout Reference 被隔离；
- POC 显示 Live AI；
- 原人工耗时已记录，未知则标记 `TBC`。

## 周二 8月4日｜第一次盲测

### 操作步骤

1. 打开 `http://127.0.0.1:8000/agent.html`。
2. 创建新的 Research Project。
3. 按历史项目填写 Research Goal、Research Questions 和 Target Users。
4. 批量上传 Transcript。
5. 检查 Participant ID、文件数量和文本预览。
6. 点击“运行跨访谈 Research Agent”。
7. 保存页面结果和运行时间。
8. 在结果保存前不要打开 Holdout Reference。

### AI 实习生只修复 P0 阻断

可修复：

- 项目无法创建；
- 文件无法上传；
- API无法调用；
- 引用校验导致错误但原因可定位；
- 结果无法保存或重新打开。

本日不修复内容质量，不边看答案边调整 Prompt。

### 当日完成定义

- 至少完成1次独立 Blind Run；
- AI结果与运行时间已保存；
- 技术错误与研究质量问题分开记录。

## 周三 8月5日｜最小人工审核

### UX 1：60–90分钟质量审核

先看 AI 输出，再打开 Holdout Reference。对每条结果标记：

#### Evidence

- `Exact`：原文逐字存在且未断章取义；
- `Context issue`：原文存在但解释错误或缺失上下文；
- `Invalid`：Participant、Quote 或含义不成立。

#### Finding

- `Accept`：可以直接使用；
- `Edit`：小幅修改后可用；
- `Reject`：不成立或价值很低；
- `Missing`：原报告的重要 Finding 被遗漏。

#### Insight

- 是否被 Findings 支持；
- 是否过度推断；
- 是否有业务决策价值；
- 是否只是重复描述。

### UX 2：30–45分钟体验观察

只记录：

- 哪一步看不懂；
- 哪一步需要人工搬运；
- 哪个状态不可信；
- 哪种信息难以审核；
- 是否愿意用它处理下一个项目。

### 当日完成定义

- 所有 AI Findings 已标记 Accept / Edit / Reject；
- Holdout 中的核心 Findings 已标记 Covered / Missing；
- UX实际审核时间已记录；
- 不要求 UX 重写完整报告。

## 周四 8月6日｜只修最高价值问题

将问题分成：

| 类别 | 示例 | 本周处理 |
|---|---|---|
| P0 Evidence Risk | 引用错误、Participant错误、结论无证据 | 必须修 |
| P0 Technical Blocker | 无法上传、无法保存、API失败 | 必须修 |
| P1 Quality | Finding太泛、遗漏核心模式 | 只修最高频1–2项 |
| P2 Experience | 排版、视觉、次要交互 | 下周候选 |
| Platform Backlog | Knowledge、Memory、Marketplace、Credits | 不进入本周 |

如果修改 Prompt 或 Agent 规则：

1. 保存第一次运行结果；
2. 记录修改原因；
3. 重新使用完全相同的输入运行；
4. 比较 Evidence Risk 是否下降；
5. 不为了贴合某个最终报告而硬编码答案。

### 当日完成定义

- P0问题已解决或形成明确阻断结论；
- 如有第二次运行，Run 1与Run 2均保留；
- 修改内容、原因和影响已记录。

## 周五 8月7日｜ROI与继续/停止决策

### 计算本周指标

```text
人工节省比例
=
(历史人工分析时间 - AI辅助后的人工审核时间)
÷ 历史人工分析时间
```

同时记录：

- AI运行时间；
- 技术准备时间；
- UX审核时间；
- Evidence Context Accuracy；
- Finding Accept + Edit比例；
- 核心 Finding Coverage；
- Reject数量；
- Missing数量；
- 是否存在伪造 Quote 或无证据结论。

### 本周建议继续 Gate

以下阈值是本周决策标准，不是正式产品 KPI：

| 指标 | 继续条件 |
|---|---:|
| Quote逐字存在 | 100%（服务端硬校验） |
| Evidence上下文正确 | ≥90% |
| Finding Accept + Edit | ≥60% |
| 核心 Finding Coverage | ≥60% |
| 人工时间节省潜力 | ≥50% |
| 伪造引语 / 无证据正式结论 | 0 |
| UX是否愿意用于第二个项目 | 至少1人愿意 |

### 决策

#### Continue

若大部分 Gate 达到：下周选择第2–3个历史项目，开始形成轻量评测集。

#### Iterate

若证据链可靠但 Finding质量不足：保留产品方向，只改 Evidence → Synthesis 工作流，不扩页面。

#### Stop / Reframe

若审核时间接近原人工分析、重要结论大量遗漏或证据不可信：停止扩建，重新定义目标，不进入平台化。

## 7. 本周交付物

周五只需要以下六项：

1. 一份脱敏 Blind Test Input；
2. 一次完整 AI Draft；
3. 一份 UX轻量审核表；
4. 一份 Covered / Missing 对照；
5. 一页 ROI Validation Summary；
6. 一个明确决策：Continue / Iterate / Stop。

不需要大规模 PRD、Figma 或管理层汇报包。

## 8. 最小审核记录模板

| ID | Type | AI Output | Evidence IDs | Review | Issue | Human Time |
|---|---|---|---|---|---|---:|
| TBC | Evidence / Finding / Insight | TBC | TBC | Accept / Edit / Reject / Missing | TBC | TBC |

## 9. 本周风险控制

- **答案泄露：** Final Report不进入Agent输入。
- **数据风险：** 只使用脱敏材料；当前 SQLite 默认位于 OneDrive 项目目录，可能被同步。
- **范围膨胀：** 新想法进入 Backlog，不在本周直接开发。
- **过度证明：** 一个项目只能证明可行性，不能证明普遍 ROI。
- **迎合旧报告：** 原报告是参考，不一定是真理；AI发现新模式也必须由 Evidence 支持。
- **技术与质量混淆：** API失败和研究结论不好分别记录。

## 10. 下周触发条件

只有本周得到 `Continue` 或 `Iterate`，下周才进行：

- 增加第2–3个历史项目；
- 将真实审核记录沉淀为轻量 Gold Set；
- 设计两阶段 Agent：单份 Evidence → 跨访谈 Synthesis；
- 增加 Human Review 数据保存；
- 形成更可靠的 ROI 范围。

Marketplace、Skill Engine、Knowledge Evolution、Credits 和其他 Agents 继续保留在平台战略中，但不由一次历史项目测试提前触发开发。

