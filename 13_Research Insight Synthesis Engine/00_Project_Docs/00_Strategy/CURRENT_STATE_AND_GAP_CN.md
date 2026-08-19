# Research Agent · 当前状态与战略缺口

> **版本：** V0.2｜**日期：** 2026-08-11｜**状态：** Audit Baseline  
> 本文区分已实现事实、高保真 Demo、已定义需求与平台方向。

> **范围决议（2026-08-11）：** 当前 Alpha / MVP 主线为已有录音、转写和项目材料进入 `Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery`。实时 AI 访谈、Participant Link、Streaming ASR 与 Researcher / Participant 实时双端均不进入 Alpha 或当前 MVP；MVP 完成后另行 Go / No-go，状态为 `Post-MVP TBC`。

## 交互架构决定（2026-08-11）

当前体验采用“对话式入口 + 受控工作流内核 + 项目 Artifact Workspace”，不再使用长表单作为主要交互，也不实现无限循环的通用聊天 Agent。

- Portfolio 首屏以项目卡片显示当前状态、来源数量和下一动作；
- 项目内按 Artifact Contract 组织 `背景资料来源 / Project Brief / 调研原始资料 / Research Plan / Evidence & Analysis / Human Review / Delivery`；
- 右侧对话受当前项目、文件夹、Gate 和 Research Agent 能力范围限制；
- 每一步结果必须沉淀为网页可读、人工可编辑的 Markdown / HTML Artifact，聊天记录不替代正式项目记忆；
- “用户想生成的任意内容”不进入当前 Alpha，只允许生成 Research Agent Contract 内定义的研究工件；
- 已实现 TXT、MD、CSV、JSON、DOCX、PPTX、XLSX 与 PDF 页级解析；图片/截图通过批准的 Live AI Endpoint 进行 OCR，音频/视频通过转写 Endpoint 生成 speaker + 时间码分段。图片和音视频在无 API Key 或 Endpoint 不支持相应模型时必须明确失败，不得降级为无定位文本；
- 项目背景与调研结果来源分区保存。只有经明确分类的项目背景进入 Brief / 问卷生成；未分类文件默认不进入 Agent 上下文。

## 1. 当前资产分类

| 能力 | 当前状态 | 处理建议 |
|---|---|---|
| 动态追问状态机 | Implemented / 测试通过 | Keep |
| Knowledge Card 轻量检索 | Implemented / 本地数据 | Keep + Enhance |
| Guardrail 与 Generic Fallback | Implemented / 测试通过 | Keep |
| Accept / Edit / Reject 与 Evaluation | Implemented / 测试通过 | Keep |
| Research Setup / Guide / Participant / Live / Evidence / Report UI | Experience Demo | Keep UI，逐模块接真实 API |
| Streaming ASR 与浏览器麦克风 | Not Implemented | Post-MVP TBC |
| Researcher / Participant 实时双端 | Not Implemented | Post-MVP TBC |
| Persistence / Run Recovery | Partial / 需按当前代码复核 | Alpha / MVP 分层补齐 |
| Evidence → Finding → Insight AI Pipeline | Implemented baseline / 质量未验证 | Alpha 以冰箱 Benchmark 验证 |
| 企业 Connector 与权限过滤 | Contract / Direction | Pilot；Alpha 仅本地/脱敏材料 |
| Skill / Knowledge / Memory / Learning 平台引擎 | Strategic Direction | 平台层另行定义 |
| Owner Portal / Marketplace / Credits / ROI Dashboard | Strategic Direction | 不进入当前 POC Must |

## 2. Keep

- Research Brief、Guide、Turn、Probe Decision、Review、Knowledge Card 等核心对象；
- Human-in-the-loop 与 AI Raw / Human Final 的分离方向；
- Generic 模式在无知识时仍能完成访谈；
- Source / Card / Probe 和 Turn / Evidence / Insight 两条追溯链；
- provider adapter、环境变量和不提交密钥的安全原则；
- 当前高保真 Demo 作为体验验证资产。

## 3. Enhance

- 将 Knowledge Card 补齐来源版本、有效期、权限、审核人与置信度；
- 将研究员修改记录转成 Experience Record，而不是只保存最终文本；
- 为每条 Insight 增加 Evidence Coverage、Confidence 和反向定位；
- 为 Research Brief 增加 Business Decision，确保研究回答真实决策；
- 为 Golden Set 增加 Generic / Knowledge 对照、盲评和回归版本；
- 建立 Capability Status Matrix，避免 Demo 被误读为已实现产品。

## 4. Conflict

### 文档权威冲突

正式 PRD 与代码目录 `PRD(3).md` 均具有 Source of Truth 表述。应统一为：母 PRD 管产品范围，Release PRD 管验收，代码和测试证明实现事实。

### 产品层级冲突

Research Insight Synthesis Engine、AI Research Copilot、Research Agent 与 Enterprise Intelligence Platform 目前混用。应使用 `research.project.md` 中的四级定义。

### Demo 与当前范围冲突

旧体验 Demo 覆盖 Participant、Live Interview 与 Voice 流程，但这些页面不属于当前 Alpha / MVP Must。对外演示必须显著说明：材料分析主线是当前范围；实时访谈体验仅为历史 Demo / Post-MVP Candidate。

### Knowledge Governance 冲突

用户贡献和系统学习不能直接修改正式知识或 Skill。所有候选必须经过 Owner 审批、版本发布和回滚机制。

## 5. Gap

### P0：验证资料

- 20–30 条 Golden Probe Cases；
- Generic vs Knowledge-enhanced 基线；
- Researcher Accept / Edit / Reject 原因；
- 已脱敏的 Research Brief、Interview Logic、Transcript 与 Final Report；
- Evidence → Insight 人工确认映射；
- Bad Case Taxonomy 与回归结果。

### P1：Vertical Alpha

- 完整 Project Brief 与 Track 决策；
- Source Registry、解析状态、版本与权限元数据；
- Evidence / Claim 原文定位与服务器校验；
- Evidence → Finding → Insight / Recommendation；
- AI Raw / Human Final 与 Review 记录；
- One-page Structured Delivery 与可重放 Run Manifest。

### P2：Research Intelligence

- Q+A Evidence Unit；
- Coding、Tag、Theme、Finding、Insight；
- 多场综合；
- AI Raw / Human Final 双层对象；
- 报告编辑、Evidence Coverage 与导出。

### P3：Enterprise Pilot

- 一个经批准的内部 Connector；
- Metadata / Permission Filtering；
- Knowledge Owner Workflow；
- Identity、基础 RBAC、Audit、Retention 与 Deletion；
- 企业批准模型 Endpoint。

### Platform backlog

- Product Strategy 与 Business Model；
- Skill / Knowledge / Memory / Learning Engine；
- Agent Marketplace；
- Owner Portal；
- Department / Workspace 模型；
- Credits、成本与 ROI Dashboard；
- Community Contribution 与 Governance；
- 三年 Roadmap 和其他 Agents。

### Post-MVP TBC

- 实时 AI 主持访谈；
- Participant Link、Consent 与 Mic Check；
- Streaming ASR、实时问题编排与双端同步；
- Researcher Live Override；
- 是否恢复 Probe Golden Set 作为独立产品验证主线。

## 6. 下一阶段建议

当前不建议立即重写所有页面。建议依次完成：

1. 统一命名、Owner、状态和文档权威关系；
2. 冻结冰箱材料、权限、Ground Truth 与 Benchmark 口径；
3. 验证 Evidence / Claim / Finding / Recommendation 白盒链路；
4. 跑通 Human Review 与 Structured Delivery；
5. 再将 Research Agent 接入最小 Knowledge / Learning / Governance；
6. MVP 完成后对实时 AI 访谈单独执行 Go / No-go。
