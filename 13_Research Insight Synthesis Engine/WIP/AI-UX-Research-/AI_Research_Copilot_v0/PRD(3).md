# AI Research Copilot｜产品需求文档

**版本：** V3.0  
**日期：** 2026-07-28  
**状态：** Ready for Codex Development  
**产品阶段：** v0.3 已完成；本文定义后续 Prototype 与完整产品方向  
**文档定位：** 项目唯一产品要求来源（Product Source of Truth）

---

## 0. Codex 使用说明

Codex 在修改本项目之前，必须依次阅读：

1. 本文件 `PRD.md`；
2. `README.md`；
3. `tests/` 中的现有测试；
4. 与本次任务直接相关的源代码。

执行规则：

- 先确认本次需求属于哪个 Release，不得默认一次实现完整 PRD。
- 保留现有 v0.3 的可运行能力、API contract、离线回退和测试。
- 每次只完成一个可验证的 vertical slice，并补齐自动化测试。
- 新能力必须保留 AI 原始输出、人工最终输出和两者之间的修改记录。
- 不得把 API Key、Token、内部 endpoint 或真实 Bosch 数据提交到代码仓库。
- 不得在个人 OpenAI endpoint 上处理真实 Bosch transcript、录音或内部资料。
- 模型、语音和 Embedding 必须通过 provider adapter 与环境变量接入，不能写死供应商。
- 若 PRD、README 和现有代码冲突：以本 PRD 为产品目标，以测试和当前代码为已实现事实；先报告冲突，再做最小必要修改。
- 完成一次迭代后，更新 README 的“已完成 / 未完成 / 启动方式”，并报告测试结果。

---

## 1. 产品定义

AI Research Copilot 是一个面向企业 UX Research、产品和业务团队的 AI 用户研究平台。

完整产品从研究问题开始，覆盖：

```text
Business Need
→ Research Setup
→ Interview Guide
→ Participant Interview
→ Real-time Transcript
→ Dynamic Probe
→ Evidence Extraction
→ Cross-interview Synthesis
→ Traceable Insight
→ Editable Report
→ Research Memory
```

它不是一个“上传 transcript 后自动写报告”的黑盒总结器，也不只是一个语音聊天壳。核心目标是让 AI 承担高耗时、可结构化、可检查的研究工作，同时让研究员保留研究判断和最终审批权。

### 1.1 一句话定位

> AI Research Copilot 是一个以实时语音访谈为入口、以可追溯研究证据为核心，并利用企业产品与工程知识生成更专业、更中性的深度追问的白盒研究副驾驶。

### 1.2 核心 USP

通用 AI 通常只能根据回答继续问“为什么”或“能举例吗”。本产品利用经过审核的产品、工程、设计和市场知识，完成：

```text
Product / Engineering Mechanism
→ User-observable Signal
→ Candidate Hypothesis
→ Missing Discriminating Evidence
→ Neutral Participant-facing Probe
```

> 普通 AI 知道如何继续问；AI Research Copilot 知道为什么值得问，以及下一问应该验证哪个产品或设计假设。

---

## 2. 背景与问题

当前企业用户研究存在以下问题：

- 访谈设计依赖研究员个人经验，研究逻辑难以复用。
- 访谈、录音、转录、编码、洞察和汇报分散在不同工具中。
- 通用 LLM 缺少产品机制知识，动态追问容易停留在表层。
- 直接让 LLM 总结长 transcript 会跳过中间证据，产生无法解释的结论。
- 产品、工程和售后资料没有被转化为可用于研究的问题与假设。
- AI 原始判断和研究员最终判断通常没有分别保存，无法评测或迭代。
- 多个研究项目产生的 Evidence、Tag、Theme 和 Insight 没有形成可复用资产。

产品机会不是“把更多资料塞进 RAG”，而是把企业知识转化成受访者能够回答、不会被诱导、并能区分假设的研究问题。

---

## 3. 产品原则

1. **Human in control**  
   AI 提供建议；研究员可以接受、修改、拒绝、覆盖和回溯。

2. **Evidence before insight**  
   没有 Evidence 不生成 Insight；没有原文定位不输出直接引语。

3. **Q + A 是基本分析单元**  
   每个 Evidence Unit 必须保留主持人问题与受访者完整回答，不能只保存脱离语境的句子。

4. **Traceability is a hard requirement**  
   Insight 必须能回到 Evidence；Evidence 必须能回到 Interview Turn；知识增强追问必须能回到 Knowledge Card 与 Source。

5. **Neutral by design**  
   候选工程假设只用于内部判断，不能作为事实暗示给受访者。

6. **Modular intermediate outputs**  
   Brief、Guide、Turn、Transcript、Evidence、Tag、Theme、Insight、Report 都应独立保存、导出和复用。

7. **Safe fallback**  
   知识检索或模型失败不能中断访谈；系统必须回退到 Generic Probe 或下一主问题。

8. **Provider replaceability**  
   产品逻辑不依赖单一模型、单一 API 或单一供应商。

9. **Evaluation by design**  
   每次 AI 输出、人工操作和失败原因都要成为可评测数据。

---

## 4. 产品目标与非目标

### 4.1 产品目标

- 在同一产品中完成研究设计、访谈、分析和报告。
- 根据研究目标、Guide、当前回答、覆盖缺口和知识生成动态追问。
- 允许研究员在访谈中实时接受、修改或覆盖下一问。
- 建立 `Source → Knowledge Card → Hypothesis → Probe → Answer` 追问链路。
- 建立 `Interview Turn → Evidence → Tag → Theme → Insight → Report` 洞察链路。
- 将 AI 原始结果与 Human-reviewed 结果分别保存。
- 用 Golden Set 证明产品相较 Generic AI 的稳定质量增益。
- 为后续内部知识库、多 BU、权限和企业治理预留稳定接口。

### 4.2 非目标

- 不替代专业研究员做最终战略判断。
- 不把未经审核的 AI 结论自动当作企业事实。
- 不把 Knowledge Card 中的工程假设直接告诉受访者。
- 不做故障诊断、维修建议或医学判断。
- 不在当前 Prototype 做多 BU、生产级 SSO/RBAC 或大规模并发。
- 不在当前 Prototype 做自由打断、重叠说话的全双工 Voice Agent。
- 不在真实访谈流程中混入 Synthetic User。
- 不通过 fine-tuning 解决可以由 workflow、schema、retrieval 和 evaluation 解决的问题。

---

## 5. 用户与核心场景

| 用户 | 核心任务 | 核心价值 |
|---|---|---|
| UX Researcher | 创建研究、审核 Guide、监控访谈、干预下一问、审核 Evidence/Insight | 提升效率和深度，同时保留控制权 |
| Product Manager / BU Owner | 提供业务问题、产品范围和假设，消费研究结果 | 更快获得与决策相关的证据 |
| Product / Engineering Expert | 审核机制知识、Knowledge Card 和候选假设 | 将专业知识可靠地转为研究能力 |
| Participant | 通过链接完成实时语音访谈 | 低门槛、自然表达真实经历 |
| Knowledge / Data Owner | 管理数据源、权限、版本和有效期 | 保证知识可用、可控、可追溯 |
| Business Reader | 查看结论、证据和建议 | 快速判断结论是否可信 |
| Administrator | 管理账号、权限、模型、审计、保留和删除 | 满足企业治理要求 |

核心场景：

1. 产品或功能探索性访谈；
2. 用户旅程与使用情境研究；
3. 产品机制或设计假设验证；
4. 新概念、原型或功能评价；
5. 售后问题和用户反馈的原因探索；
6. 多场访谈的 Evidence、Theme 和 Insight 综合；
7. 已批准研究资产的跨项目复用。

---

## 6. 端到端用户流程

### 6.1 Researcher Flow

1. 创建 Study。
2. 输入 Business Decision、Research Goal、Target User、Research Questions、Product Scope、Candidate Hypotheses、Duration 和 Language。
3. 选择本研究允许使用的知识源。
4. AI 生成 Interview Guide 与 Coverage Map。
5. 研究员修改、排序并发布 Guide。
6. 生成 Participant Link 并配置 consent。
7. 研究员打开 Live View。
8. Participant 语音回答，系统形成实时 transcript。
9. 系统根据当前回答和研究缺口生成候选下一问。
10. 研究员接受、修改、拒绝或覆盖下一问。
11. 访谈结束后，系统生成 Evidence、Tag、Theme 和候选 Insight。
12. 研究员审核分析结果并输出可编辑报告。
13. 已批准对象进入 Research Memory。

### 6.2 Participant Flow

1. 打开邀请链接。
2. 阅读研究说明并确认 consent。
3. 完成麦克风检查。
4. 查看当前问题。
5. 语音回答并看到 interim transcript。
6. 回答结束后形成 final transcript；必要时可修正。
7. 接收下一主问题或动态追问。
8. 完成访谈并退出。

### 6.3 Human Review Flow

每个 AI 对象均保留：

```text
AI Raw Output
→ Researcher Accept / Edit / Reject
→ Human Final Output
→ Review Reason
→ Timestamp / Reviewer / Model / Prompt Version
```

---

## 7. 当前代码基线：v0.3

截至 2026-07-28，当前代码已经实现：

- 固定 Research Brief 与 Guide；
- 本地 JSON 格式 Approved Knowledge Cards；
- keyword / lightweight hybrid retrieval；
- LLM Probe Planner adapter；
- Structured JSON 输出；
- Knowledge Card 引用白名单校验；
- 中性、重复、双重问题和内部信息 Guardrail；
- LLM 或知识失败时的 deterministic fallback；
- Interview Session / Turn 状态机；
- Researcher 对候选追问执行 Accept / Edit / Reject；
- Relevance、Depth、Neutrality、Grounding、Non-redundancy 五维评分；
- Evaluation JSON 导出；
- Participant 与 Researcher 共用的本地调试页面；
- 无第三方 Python 依赖的本地运行；
- 16 项自动化测试。

当前 API：

| Method | Path | 当前用途 |
|---|---|---|
| `GET` | `/api/health` | 查看模型与运行状态 |
| `GET` | `/api/study` | 获取固定 Brief 与 Guide |
| `POST` | `/api/sessions` | 创建 Session |
| `GET` | `/api/sessions/{id}` | 获取 Session 状态 |
| `POST` | `/api/sessions/{id}/answers` | 提交 final transcript 并生成下一问 |
| `POST` | `/api/sessions/{id}/reviews` | 接受、修改、拒绝并评分 |
| `GET` | `/api/sessions/{id}/evaluation` | 导出 Evaluation JSON |

### 7.1 v0.3 尚未实现

- 可编辑的 Research Setup；
- AI Guide Builder 与 Guide Review；
- 浏览器麦克风和 Streaming ASR；
- 真正分离的 Participant / Researcher 双端同步；
- Participant Link、consent 和 device check；
- 数据库持久化；
- Embedding / Vector Retrieval；
- 企业数据 Connector 和权限过滤；
- Evidence → Tag → Theme → Insight；
- 单场 Summary 与多场综合；
- PPT / Word 报告；
- 企业身份、审计、保留和删除。

---

## 8. Release 计划与优先级

### Release v0.4｜Probe Intelligence Validation

**目标：** 在增加语音复杂度前，证明动态追问本身有价值。

**P0**

- 建立 20–30 条 Golden Probe Cases；
- 同一输入分别生成 Generic 与 Knowledge-enhanced 问题；
- 支持盲评和批量 Evaluation 导出；
- 增加 Discriminating Power、Answerability、Source Fidelity；
- 建立 Bad Case Taxonomy；
- 修复高频 Prompt、Retrieval 和 Guardrail 问题；
- 所有现有能力保持可运行。

**完成条件**

- 20–30 个案例可以一键运行；
- 每个案例保留输入、检索命中、模型原始输出、最终问题和评分；
- Knowledge-enhanced 在 Depth 或 Discriminating Power 上表现出明确正向趋势；
- Neutrality 不低于 Generic Baseline；
- Knowledge Card 越权引用和内部信息泄露为 0。

### Release v0.5｜End-to-End Voice Vertical Slice

**目标：** 跑通从 Study Setup 到单场语音访谈结束的真实体验。

**P0**

- Research Setup；
- Guide 生成、人工编辑和发布；
- Participant Link；
- Consent 与麦克风检查；
- Streaming ASR；
- Participant / Researcher 双端状态同步；
- Researcher 实时修改下一问；
- Session 持久化与断开保护；
- 单场基础 Summary；
- Summary quote 回到 Interview Turn。

**明确妥协**

- Participant 点击“回答完成”后提交 final transcript；
- 不做自由打断和多人重叠语音；
- 问题先以文字显示，TTS 为 Stretch；
- 内部数据库继续使用 Connector stub；
- 只支持一个 Pilot 场景和少量 Study。

**完成条件**

- 10–15 分钟访谈可以从创建到 Summary 完整跑通；
- 3 场 Pilot 中至少 2 场无需开发者手工修复；
- ≥90% 回合形成可用 final transcript；
- ASR finalization + next question P95 < 8 秒；
- Researcher intervention success = 100%；
- Summary direct quote traceability = 100%。

### Release v0.6｜Evidence & Insight

**目标：** 将单场和多场 transcript 转成白盒、可审核的研究结果。

**P0**

- Q+A adjacency pair 切分；
- Evidence Unit；
- `primary_tag` 与 `secondary_tags`；
- exact quote 与 source offsets；
- AI raw / human final 双层对象；
- Theme 聚合；
- 候选 Insight；
- 点击 Insight 回到 Evidence 和 transcript；
- Markdown / HTML 报告；
- 多场 Study synthesis。

**完成条件**

- 每条 direct quote 是原 transcript 的精确子串，或有明确 fuzzy-match 修正记录；
- 每条 Insight 至少关联一条 Evidence；
- 研究员可以 Accept / Edit / Reject Evidence、Tag、Theme 和 Insight；
- AI 原始版本不会因人工修改而丢失；
- 报告中所有引用可反向定位。

### Release v0.7｜Pilot Integration

**目标：** 接入一个真实、获批的内部数据源并支持一个 BU Pilot。

**P0**

- 至少一个真实 Connector；
- Permission / metadata filtering；
- Knowledge Card 专家审核；
- Embedding / hybrid retrieval；
- Prompt、Model、Knowledge 和 Review audit；
- 基础角色与项目隔离；
- retention / deletion policy；
- approved enterprise model endpoints。

### Enterprise Release

- 多 BU Workspace；
- SSO / RBAC；
- 完整审计、保留、删除、导出与数据驻留；
- 标准化 Knowledge Engineering；
- Research Memory；
- 多模板报告与 PPT；
- Dashboard 和企业工作流集成；
- 更自然的实时 Voice Agent；
- 生产级稳定性、并发和 SLA。

---

## 9. 功能需求

### FR-01｜Research Setup

输入：

- Business Decision；
- Research Goal；
- Target User / Segment；
- Research Questions；
- Product / Feature Scope；
- Candidate Hypotheses；
- Interview Duration；
- Language；
- Evidence Rule；
- Interpretation Rule；
- Knowledge Scope。

要求：

- 支持创建、编辑、复制、归档 Study；
- 必填项缺失时给出明确提示；
- 保存版本；
- Interview Guide、Probe Planner 和 Analysis Pipeline 使用同一个 Brief；
- 当前 Prototype 可先使用本地持久化，但接口应可迁移至数据库。

### FR-02｜Guide Builder

每个 Guide Question 至少包含：

```yaml
id:
text:
intent:
research_question_id:
expected_observable_signal:
candidate_probe_direction:
order:
max_followups:
status:
version:
```

要求：

- AI 可生成 5–8 个主问题；
- Researcher 可编辑、删除、排序和发布；
- Participant 只能看到发布版本；
- 每个问题可回到 Research Question；
- Knowledge-enhanced 问题必须显示其内部来源，但来源不展示给 Participant。

### FR-03｜Interview Orchestrator

系统需要维护：

- 当前 Guide 位置；
- 已覆盖 / 未覆盖 Research Questions；
- 当前话题追问深度；
- 剩余时间与 fatigue budget；
- Participant 回答历史；
- 已使用问题；
- Researcher intervention；
- Generic / Knowledge-enhanced mode；
- Probe / Next Guide / Skip / End 决策。

每轮状态：

```text
Ask Question
→ Receive Answer
→ Finalize Transcript
→ Interpret Answer
→ Retrieve Knowledge
→ Generate Candidate Probe
→ Guardrail
→ Researcher Review
→ Ask / Next Guide / End
```

### FR-04｜Answer Interpreter

只解释受访者原话，不生成或补全“用户答案”。

结构化输出：

```yaml
product_or_feature:
usage_context:
user_behavior:
observable_signal:
impact:
emotion:
ambiguity:
contradiction:
missing_detail:
research_question_relevance:
potential_knowledge_query:
confidence:
```

### FR-05｜Knowledge Source 与 Knowledge Card

支持的来源类型：

- internal database；
- SharePoint / approved document repository；
- file upload；
- curated external source；
- approved historical research asset。

原始来源保存为 `SourceDocument` 和 `SourceChunk`。研究可用知识保存为 `KnowledgeCard`。

Knowledge Card 最小结构：

```yaml
card_id:
source_ids:
product_scope:
feature_or_component:
mechanism:
observable_user_signals:
trigger_or_context:
candidate_hypotheses:
discriminating_evidence:
neutral_probe_seeds:
confidence:
valid_from:
valid_to:
access_level:
review_status:
reviewer:
```

规则：

- 只有 `approved` Card 能进入正式访谈；
- Card 必须能回到 Source；
- 过期、越权、产品型号不匹配的 Card 不得被检索；
- AI 可以起草 Card，但正式使用前需要专家审核。

### FR-06｜Retrieval

输入：

```text
Current Answer
+ Research Goal
+ Product Scope
+ Coverage Gap
+ Access Context
```

流程：

```text
Query Planning
→ Permission / Metadata Filter
→ Keyword + Vector Retrieval
→ Re-ranking
→ Context Package
```

每次检索保存：

- query；
- filters；
- candidate hits；
- final hits；
- score；
- source / card version；
- selected / rejected reason；
- fallback reason。

无可靠命中时必须进入 Generic Probe，不能强行套用知识。

### FR-07｜Probe Planner

Planner 每轮必须：

1. 判断回答是否已经充分；
2. 识别 observable signal；
3. 检索相关 Knowledge Cards；
4. 形成内部 candidate hypotheses；
5. 找到区分假设所缺少的信息；
6. 选择一个 probe intent；
7. 生成一个简短、中性、受访者可回答的问题；
8. 输出一个 action：`probe`、`next_guide_question` 或 `end`。

最小输出：

```json
{
  "action": "probe",
  "question_source": "knowledge",
  "proposed_question": "这种情况通常发生在冰箱的哪个位置？",
  "probe_intent": "differentiate_context",
  "detected_signal": "uneven cooling",
  "information_gap": "location",
  "candidate_hypotheses": ["placement", "airflow", "usage_context"],
  "grounded_card_ids": ["KC-014"],
  "rationale": "需要补足发生位置以区分使用情境。",
  "confidence": 0.81
}
```

### FR-08｜Question Guardrail

每个问题至少检查：

- 是否诱导或预设原因；
- 是否将 candidate hypothesis 当成事实；
- 是否使用受访者无法理解的内部术语；
- 是否一次询问多个问题；
- 是否重复；
- 是否偏离 Research Goal；
- 是否泄露内部或保密信息；
- 是否超过追问深度与时间预算；
- 是否能根据个人经历回答；
- 是否引用了未检索或未批准的 Card。

被拦截问题必须保存 flags 与 fallback reason。

### FR-09｜Researcher Live View

显示：

- 当前问题；
- interim / final transcript；
- 会话进度；
- 剩余时间；
- AI candidate probe；
- probe intent；
- knowledge references；
- guardrail state。

操作：

- Accept；
- Edit；
- Reject；
- Override；
- Skip；
- End Interview；
- 对候选问题评分并记录备注。

Researcher 修改后的问题必须同步给 Participant，并保存 original 与 final 两个版本。

### FR-10｜Voice Runtime

- Browser microphone；
- Streaming ASR；
- interim transcript；
- final transcript；
- Participant 可在提交前修正；
- ASR 失败可重录或文字输入；
- 断开时保存已完成 Turns；
- 音频是否保存由 Study policy 决定；
- Prototype 使用“点击完成本轮”，不要求自动 VAD；
- TTS 不是 P0。

### FR-11｜Evidence Pipeline

分析基本单元：

```text
Moderator Question
+ Participant Full Answer
= Q+A Adjacency Pair
```

`EvidenceUnit` 最小字段：

```yaml
evidence_id:
session_id:
turn_id:
question_text:
full_answer:
exact_quote:
start_index:
end_index:
primary_tag:
secondary_tags:
extraction_reason:
ai_raw:
human_final:
review_action:
reviewer:
schema_version:
model_version:
prompt_version:
created_at:
```

要求：

- `exact_quote` 必须是 transcript 的精确子串；
- 若模型返回文本不完全匹配，后端可以 fuzzy match，但必须记录匹配方法和修正；
- Primary Tag 表示该 Evidence 的主要研究含义；
- Secondary Tags 补充情境、行为、影响和产品范围；
- 不能只保留 Tag，必须保留 Q+A 与 exact quote。

### FR-12｜Theme、Insight 与 Report

层级：

```text
Interview Turn
→ Evidence Unit
→ Tag
→ Theme
→ Insight
→ Recommendation
→ Report
```

要求：

- Theme 可合并、拆分、重命名；
- Insight 必须关联 Evidence；
- Recommendation 必须关联 Insight；
- AI raw 与 human final 分开；
- 点击 Theme / Insight 可回到所有支撑 Evidence；
- 点击 Evidence 可定位到 transcript；
- 报告可编辑；
- Prototype 先导出 Markdown / HTML，PPT 在后续 Release 实现。

### FR-13｜Golden Set 与 Evaluation

每条 Golden Case 至少包含：

```yaml
case_id:
research_brief:
guide_question:
conversation_history:
participant_answer:
knowledge_cards:
expected_information_gap:
forbidden_patterns:
generic_output:
knowledge_output:
retrieval_trace:
guardrail_flags:
reviewer_ratings:
reviewer_preference:
bad_case_type:
notes:
```

评价维度：

- Relevance；
- Depth；
- Neutrality；
- Grounding；
- Non-redundancy；
- Discriminating Power；
- Answerability；
- Source Fidelity。

Bad Case Taxonomy：

- generic / shallow；
- irrelevant；
- repetitive；
- leading；
- double-barreled；
- unsupported knowledge；
- wrong card；
- confidential leakage；
- jargon-heavy；
- unanswerable；
- premature diagnosis；
- missed probe opportunity；
- unnecessary probe；
- malformed structured output；
- latency / timeout。

### FR-14｜Persistence 与 Export

必须结构化保存：

- Study；
- Guide；
- Session；
- Turn；
- Retrieval Trace；
- Probe Decision；
- Review Action；
- Evidence；
- Tag；
- Theme；
- Insight；
- Report；
- Evaluation；
- Audit Event。

支持导出：

- Session JSON；
- Transcript；
- Evaluation JSON / CSV；
- Evidence JSON / CSV；
- Report Markdown / HTML。

### FR-15｜Governance

Pilot / Enterprise 阶段要求：

- SSO；
- RBAC；
- BU / Project 隔离；
- consent；
- data residency；
- audit；
- retention；
- deletion；
- sensitive data handling；
- approved model / endpoint configuration；
- Prompt、Model、Knowledge 和 Human Review 版本记录。

---

## 10. 核心数据对象

| 对象 | 作用 |
|---|---|
| `Workspace` | BU / 团队隔离与配置 |
| `Project` | 持续研究项目 |
| `ResearchBrief` | 决策、目标、用户、问题、范围和假设 |
| `GuideQuestion` | 主问题、意图、覆盖目标和版本 |
| `Participant` | 受访者、consent 和研究属性 |
| `InterviewSession` | 会话状态、策略和时间 |
| `InterviewTurn` | 问题、回答、transcript 和决策 |
| `SourceDocument` | 原始知识资料与权限 |
| `SourceChunk` | 可检索原文片段 |
| `KnowledgeCard` | 机制—信号—假设—证据—追问结构 |
| `RetrievalTrace` | query、filters、hits 和使用结果 |
| `ProbeDecision` | 是否追问、缺口、问题和依据 |
| `ReviewAction` | 人工接受、修改、拒绝与原因 |
| `EvidenceUnit` | Q+A、exact quote、tag 和定位 |
| `Theme` | 多条 Evidence 的归类 |
| `Insight` | 由 Evidence / Theme 支持的研究结论 |
| `Recommendation` | 与 Insight 关联的行动建议 |
| `Report` | 单场或多场研究输出 |
| `EvaluationCase` | Golden Case、评分和 Bad Case |
| `AuditEvent` | 模型、Prompt、权限和操作记录 |

每个对象必须使用稳定独立 ID；不得只保存整段 transcript 和最终报告。

---

## 11. 模型与 API 接入要求

### 11.1 公司环境假设

公司按“一个模型 / deployment 对应一套 API 授权”管理。不同能力不能假设共享同一 Key、Base URL、API Version 或 deployment name。

代码必须使用逻辑能力槽位，而不是把公开模型名写死在业务逻辑中：

| 能力槽位 | 必要性 | 用途 | 必须支持 |
|---|---:|---|---|
| Main Reasoning LLM | 当前必须 | 动态追问、结构化判断、Guide、Insight | JSON Schema / Structured Output |
| Live Transcription | v0.5 必须 | 麦克风实时转录 | Streaming WebSocket 或等价接口 |
| Diarized Transcription | v0.6 建议 | 会后高精度重转录和说话人区分 | File transcription + diarization |
| Embedding | v0.7 必须 | Knowledge Card / Source 检索与聚类 | Multilingual embeddings |
| Batch Text LLM | 可选 | 大批量 Evidence、Tag、Summary | 低成本结构化输出 |
| Evaluation LLM | 可选 | Golden Set 辅助评测与高质量报告 | 与生产模型独立配置 |

申请公司 API 时，对每个槽位确认：

- Base URL；
- API Key / Token；
- internal deployment name；
- model name；
- API version；
- request / response schema；
- Structured Outputs 支持；
- streaming / WebSocket 支持；
- rate limit；
- timeout；
- data retention / logging policy；
- allowed data classification。

### 11.2 环境变量 contract

Main LLM：

```bash
AI_UX_LLM_API_KEY=
AI_UX_LLM_BASE_URL=
AI_UX_LLM_MODEL=
AI_UX_LLM_DEPLOYMENT=
AI_UX_LLM_API_VERSION=
AI_UX_LLM_TIMEOUT_SECONDS=
```

Live ASR：

```bash
AI_UX_ASR_API_KEY=
AI_UX_ASR_BASE_URL=
AI_UX_ASR_MODEL=
AI_UX_ASR_DEPLOYMENT=
AI_UX_ASR_API_VERSION=
```

Diarized ASR：

```bash
AI_UX_DIARIZE_API_KEY=
AI_UX_DIARIZE_BASE_URL=
AI_UX_DIARIZE_MODEL=
AI_UX_DIARIZE_DEPLOYMENT=
AI_UX_DIARIZE_API_VERSION=
```

Embedding：

```bash
AI_UX_EMBEDDING_API_KEY=
AI_UX_EMBEDDING_BASE_URL=
AI_UX_EMBEDDING_MODEL=
AI_UX_EMBEDDING_DEPLOYMENT=
AI_UX_EMBEDDING_API_VERSION=
```

Batch / Evaluation：

```bash
AI_UX_BATCH_API_KEY=
AI_UX_BATCH_BASE_URL=
AI_UX_BATCH_MODEL=

AI_UX_EVAL_API_KEY=
AI_UX_EVAL_BASE_URL=
AI_UX_EVAL_MODEL=
```

若多个能力实际共享同一 endpoint，配置层可以复用值，但业务代码仍保持独立 adapter。

### 11.3 Provider Adapter

建议接口：

```python
class ProbeGenerator(Protocol): ...
class GuideGenerator(Protocol): ...
class EvidenceExtractor(Protocol): ...
class InsightGenerator(Protocol): ...
class LiveTranscriber(Protocol): ...
class BatchTranscriber(Protocol): ...
class Embedder(Protocol): ...
class Evaluator(Protocol): ...
```

业务逻辑只依赖 Protocol，不直接依赖 OpenAI、Azure OpenAI 或其他供应商 SDK。

---

## 12. 目标 API

现有 API contract 应向后兼容。新增 API 可按 Release 分批实现。

### Study / Guide

| Method | Path | 用途 |
|---|---|---|
| `POST` | `/api/studies` | 创建 Study |
| `GET` | `/api/studies/{id}` | 获取 Study |
| `PATCH` | `/api/studies/{id}` | 修改 Study |
| `POST` | `/api/studies/{id}/guide/generate` | 生成 Guide |
| `PATCH` | `/api/studies/{id}/guide` | 编辑 Guide |
| `POST` | `/api/studies/{id}/guide/publish` | 发布 Guide |

### Participant / Session

| Method | Path | 用途 |
|---|---|---|
| `POST` | `/api/studies/{id}/participant-links` | 创建 Participant Link |
| `POST` | `/api/participant-links/{token}/consent` | 保存 consent |
| `POST` | `/api/sessions` | 创建 Session |
| `GET` | `/api/sessions/{id}` | 获取 Session |
| `POST` | `/api/sessions/{id}/answers` | 提交 final transcript |
| `POST` | `/api/sessions/{id}/reviews` | Review 下一问 |
| `POST` | `/api/sessions/{id}/end` | 结束 Session |

### Analysis / Evaluation

| Method | Path | 用途 |
|---|---|---|
| `POST` | `/api/sessions/{id}/analysis` | 生成 Evidence / Theme / Insight |
| `GET` | `/api/sessions/{id}/evidence` | 获取 Evidence |
| `PATCH` | `/api/evidence/{id}` | Review Evidence |
| `GET` | `/api/studies/{id}/insights` | 获取跨访谈 Insight |
| `POST` | `/api/studies/{id}/reports` | 生成 Report |
| `GET` | `/api/sessions/{id}/evaluation` | 导出单场 Evaluation |
| `POST` | `/api/evaluations/batch` | 批量运行 Golden Set |

### Knowledge

| Method | Path | 用途 |
|---|---|---|
| `POST` | `/api/knowledge/sources` | 新增 Source |
| `GET` | `/api/knowledge/cards` | 获取 Cards |
| `PATCH` | `/api/knowledge/cards/{id}` | Review Card |
| `POST` | `/api/knowledge/retrieve` | 调试检索 |

---

## 13. 非功能要求

### 13.1 Reliability

- 模型、Retrieval 或 ASR 单点失败不能破坏已保存的 Session；
- 每个外部调用有 timeout、明确错误类型和一次受控重试；
- 失败后进入 safe fallback；
- 所有状态变更具备稳定 ID 和时间戳；
- 重复请求不能无意创建重复 Turn。

### 13.2 Performance

- ASR interim transcript 应接近实时；
- ASR finalization + candidate next question P95 < 8 秒；
- Researcher 修改必须在问题发给 Participant 前生效；
- 10–15 分钟访谈不需要开发者手动修复状态。

### 13.3 Traceability

- direct quote 精确定位率 = 100%，或明确标记无法定位；
- Knowledge-grounded probe 的有效 Card 引用率 = 100%；
- Insight 至少关联一条 Evidence；
- AI raw、human final、model、prompt、schema 和 knowledge version 可查询。

### 13.4 Security

- 所有 secrets 只通过环境变量或 approved secret store；
- 浏览器不得获得长期 API Key；
- 浏览器实时语音若需要临时凭证，由后端签发短期 token；
- 不在日志中输出完整 Key、敏感原文或内部机密；
- 真实 Bosch 数据只发送到 approved endpoint；
- 权限过滤必须发生在检索上下文交给模型之前。

### 13.5 Portability

- 本地开发应支持 Mac 和 Windows；
- 无模型 Key 时保持 Offline Rules 模式；
- 当前标准库实现可以逐步引入依赖，但必须提供可复现安装方式；
- 数据 schema、provider adapter 和业务状态机保持解耦。

---

## 14. 成功指标

### 产品与流程

- End-to-End Completion Rate；
- Study Setup Time；
- Participant Completion Rate；
- Time from Last Interview to Reviewed Report；
- Researcher Intervention Rate；
- Report Export / Share Rate。

### 追问质量

- Relevance；
- Depth；
- Neutrality；
- Grounding；
- Non-redundancy；
- Discriminating Power；
- Answerability；
- Source Fidelity；
- Researcher Acceptance / Edit / Reject Rate；
- New Information Gain。

### Evidence 与报告

- Exact Quote Match Rate；
- Evidence Traceability；
- Insight Traceability；
- Unsupported Claim Rate；
- Time to Reviewed Insight；
- Human Edit Distance / Edit Rate。

### 建议正式目标

- ≥90% 已启动访谈能够完成并生成结果；
- ≥95% Insight 可回溯到原始 Evidence；
- 100% direct quote 可回到原始 transcript；
- 100% Knowledge-grounded probe 可回到有效 Card，或明确标记 Generic；
- 高风险诱导、未经依据的工程判断或内部信息泄露为 0；
- Mechanism-aware 在盲评中持续优于 Generic Baseline。

具体阈值在 v0.4 与 v0.5 Pilot 后根据真实基线调整。

---

## 15. Prototype 团队与交付假设

计划基线：

- 3 名 Core Members；
- 约 35–40 Person-Days；
- 产品 / 用研 Driver 负责研究逻辑、Golden Set 和验收；
- AI / Backend 负责模型 adapter、Orchestrator、Retrieval、Trace 和 Evaluation；
- Full-stack / UX 负责 Researcher、Participant、Voice 和 Review 体验；
- 产品 / 工程专家短时审核 Knowledge Cards 与关键案例。

Prototype 的核心交付不是功能数量，而是：

1. 一条真实可运行的端到端链路；
2. 一套能证明追问质量的 Golden Set；
3. 一条可追溯的 Evidence / Insight 链路；
4. 一组能替换为 Bosch approved endpoint 的稳定 adapter；
5. 一份明确的 Bad Case 和下一阶段接入清单。

---

## 16. 风险与产品回应

| 风险 | 产品回应 |
|---|---|
| 工程知识导致诱导 | 假设只在内部使用，Participant 只看到中性问题 |
| 知识过期或产品不匹配 | 产品、型号、市场、版本、有效期 metadata filter |
| 模型编造 Card | Card ID 白名单和后端校验 |
| RAG 无命中 | Generic Fallback |
| 模型输出格式错误 | Strict schema、解析校验和 fallback |
| 自动总结产生幻觉 | Evidence-first；direct quote 精确对齐 |
| 研究员修改覆盖 AI 原始值 | AI raw 与 human final 分层保存 |
| 语音开发吞噬全部时间 | v0.4 先验证 intelligence；v0.5 使用按轮次提交 |
| 公司 API 各模型配置不同 | 独立 capability adapter 与环境变量 |
| 内部资料泄露 | approved endpoint、permission filter、guardrail、audit |
| Prototype 过度建设 | 按 Release Gate 开发；Stretch 不阻塞 P0 |

---

## 17. 完整产品完成定义

完整产品只有在以下条件同时满足时才视为可交付：

1. Researcher 可以创建、执行、分析多场 Study；
2. Participant 可以通过链接完成稳定的实时语音访谈；
3. AI 能根据 Guide、会话、Coverage 和知识生成中性动态追问；
4. Researcher 能实时干预，并在访谈后审核分析对象；
5. 至少一个真实内部数据源已接入并受权限控制；
6. Knowledge-grounded probe 可回到 Knowledge Card 与 Source；
7. Insight / Summary / Report 可回到 Evidence 与 Interview Turn；
8. RAG 和模型不可用时有安全 fallback；
9. 具备企业身份、权限、审计、保留和删除能力；
10. Golden Set 证明产品相较 Generic AI 有稳定质量增益。

---

## 18. Codex 当前下一步

若用户没有另外指定，本项目下一步默认执行 **v0.4：Probe Intelligence Validation**，不要直接跳到语音。

建议实现顺序：

1. 定义 `EvaluationCase` 与 Golden Set JSON schema；
2. 加入 20–30 条代表性案例的目录与示例；
3. 实现 Generic / Knowledge-enhanced batch runner；
4. 保存 Retrieval、Raw Output、Guardrail 与 Latency；
5. 实现盲评输入与 Evaluation CSV / JSON 导出；
6. 扩充八维评分和 Bad Case Taxonomy；
7. 补齐单元测试与端到端测试；
8. 更新 README，并记录 v0.4 已完成和仍未完成项。

在开始 v0.5 之前，必须先展示：

- Golden Set 可重复运行；
- Dynamic Probe 会随回答变化；
- Knowledge-enhanced 的价值可被研究员评分；
- 无 Card 命中时安全回退；
- 不存在越权 Card 引用或内部信息泄露。

