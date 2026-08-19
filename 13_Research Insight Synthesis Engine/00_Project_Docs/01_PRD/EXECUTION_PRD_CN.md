# Research Insight Synthesis Engine · Vertical Alpha 执行 PRD

**版本：** V2.0  
**日期：** 2026-08-11  
**状态：** Ready for Alpha Planning  
**文档定位：** 当前设计、开发与 Alpha 验收的权威子 PRD  
**母 PRD：** `PRD_CN.md`  
**集成规格：** `UXGS_Enterprise_Research_Platform_Spec_v0.2.docx`

> **范围决议：** 当前主线不做实时 AI 访谈。Participant Link、Consent、Mic Check、Streaming ASR、动态实时追问、Researcher / Participant 双端和 Live Override 均为 `Post-MVP TBC`。旧 V1.0 中将这些能力列为 POC Must 的条款自本版起失效。

---

## 1. Alpha 要证明什么

### 命题 A - Evidence-led Vertical Slice（Must）

> 能否使用已有录音、转写和项目材料，跑通 `Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery`，并让关键结论可回到原文证据？

### 命题 B - Benchmark 可验证性（Must）

> 能否以冰箱历史研究为 Benchmark，在不向 Agent 泄露保留答案的条件下，衡量事实准确性、证据定位、关键遗漏、人工修改和处理时间？

### Alpha 不证明

- 实时 AI 访谈或 Voice Agent 的客户价值；
- 生产级并发、SLA、SSO、完整 RBAC、灾难恢复；
- 真实 SharePoint / 内部数据库的生产接入；
- 完整 Owner Portal、Operations Dashboard、Marketplace 或 Credits；
- 自动学习、模型 Fine-tune 或无人审核的正式交付；
- `.docx` / `.pptx` 正式文件生成；Alpha 只输出结构化内容或 Markdown / HTML。

---

## 2. Alpha 输入与数据边界

### 2.1 必需输入

- 已批准的冰箱 Project Brief；
- Source Inventory：文件名、Owner、版本、日期、权限、数据等级；
- 已脱敏的录音转写、研究笔记、报告或其他项目材料；
- 由 Research Lead / Domain Expert 冻结的 Holdout Ground Truth；
- Benchmark Rubric 与停止条件。

### 2.2 数据原则

- 未脱敏姓名、联系方式、录音和敏感内部材料不得进入未批准服务；
- Agent 输入与 Holdout Reference 必须物理分离；
- 不确定或未授权内容标记 `TBC / Restricted`，不得猜测；
- Source 先登记权限和版本，再进入解析与分析；
- Benchmark Ground Truth 由人确认，不由 Agent 生成。

---

## 3. Scope 对照表

| 能力 | Alpha 处理 | 优先级 |
|---|---|---|
| Project Brief | 决策、问题、用户、范围、数据等级、交付与成功标准 | **Must** |
| Evidence-ready Research Plan | 从决策和研究问题反推 Evidence Needed、主问题、Probe Tree 与完成标准；不包含实时主持 | **Must** |
| Source Registry | Owner、版本、日期、权限、解析状态、校验值 | **Must** |
| 文档解析 | TXT / MD 优先；其他格式按当前解析能力使用 | **Must** |
| Evidence / Claim | 原子 Claim、原文片段、来源定位、类型与信心 | **Must** |
| Existing Feature Analysis | Finding、严重度、影响、Evidence Strength | **Must** |
| Recommendation | 关联 Finding，明确区分事实与建议 | **Must** |
| Human Review | Accept / Edit / Reject，保留 AI Raw / Human Final 与理由 | **Must** |
| Structured Delivery | One-page 内容、Evidence Pack、Machine-readable artifacts | **Must** |
| Run Manifest | 模型、Prompt/Policy、Skill、Schema、输入和时间 | **Must** |
| Conflict / Gap Detection | 标记冲突、重复、过期和覆盖缺口 | **Should** |
| 最小 Skill Runtime | 记录首批冻结 Skill 的 ID / 版本；不建完整 Portal | **Should** |
| 本地离线评测 | 与 Holdout 对比并输出结果表 | **Must** |
| Proposal Track | 仅在双氧水 Brief 完整后进入 Pilot | **Later** |
| Owner Portal / Dashboard | MVP 或后续 | **不做** |
| SharePoint / 企业 Connector | Pilot，需 Bosch 批准 | **不做** |
| 正式 Word / PPT 文件生成 | 结构化内容即可 | **不做** |
| 实时 AI 访谈全链路 | MVP 完成后单独 Go / No-go | **Post-MVP TBC** |

> 范围澄清：当前加入的是“访谈前的研究设计与输入质量 Gate”，不是恢复 Participant Link、ASR 或实时 AI 主持。已有研究材料仍是 Alpha 的主要执行输入；新 Research Plan 能力用于修复问卷过浅并建立可评测的上游 Evidence Contract。

---

## 4. 端到端流程与 Gate

| Gate | 操作 | 通过条件 | 责任人 |
|---|---|---|---|
| G0 Intake | 完成 Brief 与 Track | Sponsor、决策、范围、材料和成功标准明确 | Research Lead |
| G1 Data | 登记 Source | 权限、数据等级、Owner、版本和脱敏状态确认 | Project / Data Owner |
| G2 Benchmark | 冻结 Holdout | Ground Truth、Rubric、样本单位和争议记录确认 | Research Lead + Domain Expert |
| G2A Plan Quality | 审核研究计划与问卷 | 每个 RQ 已定义 Evidence Needed；关键问题具备中立 Probe Tree、完成标准和停止条件 | Research Lead |
| G3 Evidence | 解析并提取 Evidence / Claim | 关键 Claim 可定位原文；无定位内容不得成为 fact | Research Lead |
| G4 Synthesis | 生成 Finding / Recommendation | 事实、推断、建议分离；关键遗漏已检查 | Domain Reviewer |
| G5 Review | 人工审核与修改 | AI Raw、Human Final、动作和理由被保存 | Research Lead |
| G6 Delivery | 锁定输出 | Human View、Machine View、Evidence Pack 和 Run Manifest 完整 | Approver |

失败的 Gate 不得静默跳过。允许退回、修正和重跑，并保留运行历史。

---

## 5. 最小 Artifact Contract

| 对象 | 最小字段 |
|---|---|
| `Project` | id, name, track, owner, scope, status, data_classification |
| `Brief` | decision, goals, research_questions, users, constraints, delivery, success |
| `Source` | id, title, owner, version, date, permission, checksum, parse_status |
| `Evidence` | id, source_id, locator, verbatim_text, context, access_scope |
| `Claim` | id, statement, claim_type, evidence_ids, confidence, review_status |
| `Finding` | id, statement, evidence_ids, impact, severity, confidence |
| `Recommendation` | id, finding_ids, proposal, rationale, status |
| `Review` | id, artifact_id, action, ai_raw, human_final, reason, reviewer, timestamp |
| `Run` | id, inputs, model, skill_versions, prompt_policy, schema_version, status |
| `Delivery` | id, audience, version, artifacts, permissions, approved_at |

规则：`fact` 必须至少绑定一条有效 Evidence；Recommendation 不得伪装成 Finding；未审核自动输出不得标记为 Approved。

---

## 6. 首批 Skill 范围

建议 Alpha 只冻结 4-6 个 Skill：

1. `validate-project-brief`
2. `design-evidence-ready-interview`
3. `ingest-and-register-source`
4. `extract-evidence-and-claims`
5. `analyze-existing-feature`
6. `generate-reviewed-delivery`

`detect-evidence-conflicts` 暂作为 `extract-evidence-and-claims` 的质量检查步骤；Contract 稳定后再拆成独立 Skill。

每个 Skill 最少包含 ID、版本、Owner、输入、输出、禁止项、测试和失败行为。完整 Registry、发布审批 UI、回滚与退役运营进入 MVP。

---

## 7. Alpha 验收

### Must

- [ ] 冰箱 Brief、Source Inventory 和 Holdout Ground Truth 由责任人确认；
- [ ] 至少一份 Research Plan 能将每个 RQ 映射到 Evidence Needed、Probe Tree 与 Completion Criteria；
- [ ] 问卷质量评测证明新方案相较旧方案降低关键证据缺口；
- [ ] Agent 未接触 Holdout Reference；
- [ ] 至少一组脱敏材料完成端到端处理；
- [ ] 核心 Artifact 通过 Schema 校验；
- [ ] 每个已批准的事实 Claim 均可打开正确来源和定位；
- [ ] Finding 与 Recommendation 不混淆；
- [ ] Review 保存 AI Raw、Human Final、动作和理由；
- [ ] 输出 Human View、Machine View、Evidence Pack 和 Run Manifest；
- [ ] 评测报告记录命中、遗漏、错误、人工修改和耗时；
- [ ] 不处理未批准的生产敏感数据。

### 建议指标（Proposed，Benchmark 冻结后确认）

| 指标 | 初始建议 |
|---|---:|
| Schema 有效率 | ≥99% |
| 关键 Claim 引用可定位率 | ≥95% |
| 无依据事实率 | ≤2%；高风险事实 0 |
| Benchmark 关键事实准确率 | ≥95% |
| 关键遗漏率 | ≤5% |
| 权限违规 | 0 |
| 人工时间变化 | 建立真实基线，不预先承诺 ROI |

指标在 Ground Truth 和样本单位确认前只是 Proposed Target，不得作为已达成结果对外传播。

---

## 8. 进入 MVP 的条件

满足以下条件后才进入 Governed MVP：

1. 冰箱 Benchmark 的事实准确性、遗漏和证据定位达到已批准阈值；
2. 真实用户完成 Alpha Review，并记录主要修改和失败；
3. Artifact Schema、首批 Skills 与 Review Contract 稳定；
4. 数据分类、保留、删除和批准模型边界有明确 Owner；
5. 团队确认后端、身份、安全与运维资源。

MVP 完成后，另行评估实时 AI 访谈。是否立项取决于客户需求、研究价值、隐私与同意、实时系统成本、ASR质量及团队资源；不自动恢复为 Must。

---

## 9. 立即行动

1. 建立冰箱 Benchmark 材料包；
2. 完成 Project Brief 与 Source Inventory；
3. 冻结 Ground Truth 与 Rubric；
4. 确认最小 Artifact Schema；
5. 选择首批 4-6 个 Skills；
6. 先试标 10-15 条样本，稳定口径后再扩展；
7. 跑通一组脱敏材料的 Vertical Alpha。
