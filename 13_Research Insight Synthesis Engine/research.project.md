# Research Insight Synthesis Engine · Project Configuration

## Project identity

- **Project folder:** `13_Research Insight Synthesis Engine`
- **Current product role:** UXGS Enterprise Intelligence Platform 下的首个 Research Agent / Research Intelligence 能力验证项目
- **Current implementation:** `WIP/AI-UX-Research-/AI_Research_Copilot_v0/`
- **Default language:** 简体中文；需要正式跨区域评审时再生成中英双语版本
- **Current phase:** Vertical Alpha / Prototype，尚非生产系统
- **Current scope decision (2026-08-11):** 当前主线为已有录音、转写和项目材料进入 `Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery`。实时 AI 访谈不进入 Alpha 或当前 MVP，MVP 完成后另行 Go / No-go，状态为 `Post-MVP TBC`。

## Product hierarchy

```text
UXGS Enterprise Intelligence Platform
└── Research Agent
    ├── Research Insight Synthesis Engine
    └── AI Research Copilot Experience
```

- **Platform** 定义跨 Agent 的 Skill、Knowledge、Memory、Learning、Governance、Marketplace 与 Analytics。
- **Research Agent** 是平台上的第一个 Agent，负责研究规划、访谈、综合、证据链与报告。
- **Research Insight Synthesis Engine** 是 Research Agent 的核心研究智能与证据综合能力。
- **AI Research Copilot** 是当前面向研究员和受访者的体验 / POC 名称，不等同于完整平台。

> 范围说明：上述“访谈”是 Research Agent 的长期能力域，不代表当前 Release 承诺实时 AI 主持、Participant Link、Streaming ASR 或 Researcher / Participant 双端。

## Source priority

发生冲突时按以下顺序判断：

1. 用户在当前任务中的明确指令；
2. 本文件与仓库 `AGENTS.md`；
3. `00_Project_Docs/00_Strategy/PLATFORM_PRODUCT_CONTEXT_CN.md` 中的长期方向；
4. `00_Project_Docs/01_PRD/PRD_CN.md` 中的 Research Agent 立项范围；
5. `00_Project_Docs/01_PRD/EXECUTION_PRD_CN.md` 中的当前 Release 验收范围；
6. `output/doc/UXGS_Enterprise_Research_Platform_Spec_v0.2.docx` 作为集成系统规格；若与前述范围文件冲突，以前述文件为准并进入合并清单；
7. 代码、测试与 README 作为实际完成状态的证据；
8. 历史 ChatGPT 对话和旧 POC 仅作为背景与候选方向，不自动视为已批准需求。

## Working principles

### Product intent controls feature input

用户在讨论中提出的新页面、功能、技术或商业想法，默认作为 `Product Hypothesis`，不自动覆盖既有产品方向。主 Agent 必须先检查它是否：

- 强化 Research Agent 的明确客户价值；
- 符合 Evidence-first、Human-in-control 与企业治理原则；
- 与 Platform → Agent → Engine → Experience 的产品层级一致；
- 在当前团队和 Release 范围内可验证；
- 不会为了未来平台能力牺牲当前 vertical slice；
- 不会把 Demo、Mock 或候选知识表述成已实现或已批准能力。

若输入与长期方向冲突，主 Agent 应明确指出冲突、解释风险、提出更符合产品原则的替代方案，而不是机械执行。

### Evolution, not rebuild

现有 POC 是基础，新想法用于增强。任何改动先执行：

1. **Keep**：保留已验证流程、交互、代码、数据结构与客户认可部分；
2. **Enhance**：补足证据、知识、治理、学习与平台连接；
3. **Conflict**：指出与现有架构、合规、权限、商业模式或路线图的冲突；
4. **Gap**：标记缺失能力及其优先级，不将缺口伪装成已完成功能。

### Evidence rules

- 聊天中形成的产品设想必须标记为 `Strategic Direction`、`Hypothesis` 或 `TBC`。
- 只有代码、测试、真实材料或正式验收记录支持的能力才能标记为 `Implemented`。
- 高保真页面但未接后端时标记为 `Experience Demo`。
- 本地规则、Mock、Synthetic 数据不得表述为真实 AI 质量或客户研究结果。

## Current focus

当前优先顺序：

1. 统一产品层级、命名、文档权威关系与真实完成状态；
2. 冻结冰箱 Benchmark 的材料清单、权限、Ground Truth 与评测口径；
3. 跑通 `Brief → Source → Evidence → Analysis → Human Review → Structured Delivery` vertical slice；
4. 修复研究输入质量：建立 `Decision → Unknown → Evidence Needed → Question → Probe Tree → Completion Criteria`，避免浅层问卷导致后续综合失真；
5. 用 Benchmark 同时验证问卷 Evidence Readiness、事实准确性、证据可定位率、关键遗漏与人工修改；
6. 在 MVP 建设最小 Knowledge / Learning / Governance；
7. MVP 完成后再决定是否立项实时 AI 访谈；
8. 再扩展 Marketplace、完整 Owner Portal、Dashboard、Credits 与其他 Agents。

## Review format

产品、页面或文档评审默认包含：

- Keep
- Enhance
- Conflict
- Gap
- UX / AI / Scalability / Business Value / Technical Feasibility 评分
- 建议进入的 Release
- Owner、风险和下一步
