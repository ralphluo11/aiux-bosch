# UXGS Enterprise Intelligence Platform · 产品战略上下文

> **版本：** V0.1  
> **日期：** 2026-08-03  
> **状态：** Strategic Direction — 待管理层、业务、Data 与 IT/Security 评审  
> **来源：** 用户与 ChatGPT 的产品探索对话 + 当前 Research POC 审计  
> **用途：** 保留平台级产品意图，指导 Research Agent 演进；不替代正式 PRD 或批准记录

## 1. 核心判断

当前项目不应只被理解为一个自动访谈或研究总结工具。长期方向是建立：

> **UXGS Enterprise Intelligence Platform：把 UXGS 方法、Bosch 知识、部门记忆和真实使用经验转化为可治理、可复用、可持续学习的企业智能能力。**

Research 是第一个 Agent，而不是平台的全部。未来可逐步扩展 Design、Requirement、Power BI、Presentation 等 Agent，但共享同一套企业智能底座。

## 2. 为什么不是普通 ChatGPT、Cursor 或 Skill Library

通用 AI 工具能够生成内容，但无法天然提供：

- Bosch 内部知识与部门语境；
- 经审批的方法和知识版本；
- 企业权限、审计、保留与删除；
- 从人工修改和使用行为中形成的组织学习；
- 跨项目、跨团队但受控的记忆；
- 对 Agent 输出质量、成本和业务价值的持续运营。

平台价值不在于保存更多 Prompt，而在于把 AI 能力变成受治理的企业工作系统。

## 3. 产品层级

```text
UXGS Enterprise Intelligence Platform
├── Experience Layer
│   ├── Home
│   ├── Agent Marketplace
│   ├── Research
│   ├── Knowledge
│   ├── Learning
│   ├── Dashboard
│   └── Owner Portal
├── Agent Layer
│   ├── Research Agent（首个）
│   ├── Design Agent（方向）
│   ├── Requirement Agent（方向）
│   ├── Power BI Agent（方向）
│   └── Presentation Agent（方向）
├── Intelligence Layer
│   ├── Skill Engine
│   ├── Knowledge Engine
│   ├── Memory Engine
│   └── Learning / Experience Engine
└── Enterprise Foundation
    ├── Governance
    ├── Identity / SSO / RBAC
    ├── Audit / Retention / Deletion
    ├── MCP / Connectors
    ├── Analytics / ROI
    └── Credits / Cost Control
```

## 4. 四类核心智能资产

### 4.1 Skill：怎么做

Skill 定义 Agent 的专业方法、步骤、判断规则与输出结构，例如如何进行 Coding、Theme 聚类、Insight 形成和报告组织。

- 主要 Owner：UXGS AI / 方法团队
- 更新频率：低，按版本评审
- 客户权限：默认调用能力，不直接下载内部 Skill 或系统提示
- 关键要求：版本、审批、测试、发布、回滚、弃用

### 4.2 Knowledge：知道什么

Knowledge 包含部门术语、产品机制、规范、模板、历史研究和经批准的外部资料。

- 主要 Owner：UXGS + 业务部门 Knowledge Owner
- 更新频率：高，可持续贡献
- 进入正式使用前：权限过滤、来源追溯、有效期与 Owner 审批
- 用户上传首先形成 `Knowledge Candidate`，不直接成为正式知识

### 4.3 Memory：记住什么

Memory 保存经授权且对未来任务有价值的稳定上下文，例如部门偏好、项目术语、利益相关者关系和输出风格。

- 与 Knowledge 的区别：Knowledge 是可引用事实或正式资产；Memory 是特定部门、项目或用户的持续上下文
- 必须明确作用域：User / Project / Department / Enterprise
- 必须支持查看、更正、过期与删除
- 未确认信息不得自动沉淀为组织事实

### 4.4 Experience / Learning：从使用中学到什么

Experience 记录 AI 原始输出、人工终稿、Accept / Edit / Reject、追问、补充材料、常见错误和反馈。

学习闭环：

```text
Agent Usage
→ Human Modification / Feedback
→ Experience Record
→ Pattern & Knowledge Gap Detection
→ Knowledge / Skill Candidate
→ Owner Review
→ Approved Version
→ Controlled Release
```

系统不能因为频繁修改就自动改变生产 Skill；它只能形成建议，最终由 Owner 审批。

## 5. 平台护城河

长期护城河不是单一模型、Prompt 或 Skill 文件，而是：

```text
Governance
+ Bosch Knowledge
+ Organizational Memory
+ Learning from Experience
+ Community Contribution
+ Embedded Workflow
```

模型可以替换，工作流可以模仿，但长期积累、经过审批且能持续演进的企业知识与经验难以复制。

## 6. Research Agent 在平台中的位置

Research Agent 是平台第一个可验证的 vertical slice：

```text
Business Need
→ Research Setup
→ Interview / Source Collection
→ Transcript / Raw Evidence
→ Coding
→ Theme / Finding
→ Traceable Insight
→ Report
→ Human Review
→ Experience Record
→ Knowledge Gap / Improvement Candidate
```

当前 `Research Insight Synthesis Engine` 重点验证：

- 动态专业追问；
- Evidence-first 分析；
- Finding / Insight 的原文追溯；
- AI Raw 与 Human Final 分离；
- Knowledge-enhanced 与 Generic 的对照；
- 使用反馈进入 Owner 审批闭环。

Research Agent 不应直接修改正式 Knowledge，也不应向客户暴露或下载内部 Skill。

## 7. 关键产品模块

### Agent Marketplace

不是简单文件下载页，而是受控的 Agent Capability Marketplace。用户发现、申请和调用能力；平台管理适用范围、版本、Owner、成本和权限。

### Knowledge Center

支持 Source、Knowledge Card、Candidate、审批、版本、有效期、权限和引用追溯。

### Learning Center

展示质量趋势、常见修改、Bad Case、知识缺口、改进候选和发布后的效果，不等同于自动训练模型。

### Owner Portal

Owner 审批 Knowledge / Skill Candidate，管理版本、权限、风险、发布和回滚，并查看使用影响。

### Dashboard

至少覆盖采用率、任务量、输出质量、人工修改率、节省时间、Token / Credits 成本、知识命中率和业务 ROI。

## 8. 商业模式假设

以下仅为待验证方向：

- Department Subscription
- Usage Credits
- Professional Service
- Knowledge Package
- Agent Package

正式商业模式必须进一步验证客户、预算 Owner、成本结构、价值衡量和内部结算方式。

## 9. 产品演进原则

1. **Evolution, not rebuild**：保留已验证 POC，逐步增强。
2. **Strategy before PRD**：先统一 Vision、Positioning、Architecture 和 IA，再冻结详细需求。
3. **Human in control**：AI 提议，人审批并保留差异。
4. **Evidence before insight**：无证据不形成正式结论。
5. **Governance by design**：知识、记忆和学习从第一天就有边界。
6. **Provider replaceability**：平台逻辑不绑定单一模型。
7. **Version everything**：Skill、Knowledge、Prompt、Model、Schema 和输出均可追溯。

## 10. 建议产品库

```text
01 Vision
02 Product Strategy
03 Business Model
04 User Journey
05 Information Architecture
06 System Architecture
07 Skill Engine
08 Knowledge Engine
09 Memory Engine
10 Learning Engine
11 Research Agent
12 Other Agents
13 Owner Portal
14 Dashboard
15 Roadmap
16 PRD
17 Figma
18 Development
```

本 Research 项目不需要立即承载全部目录。平台级文档成熟后，可迁移到独立的平台主库；本项目保留 Research Agent 专属材料及平台引用。

## 11. 分阶段交付

### V0.1：产品战略

统一 Why、Vision、Positioning、Moat、用户、价值与范围。

### V0.2：系统架构与 IA

确认平台层、Agent 层、四类智能资产、治理和主要页面。

### V0.3：Research Agent

确认第一个 MVP、真实 vertical slice、评测与 Pilot。

### V0.4：核心 Engines

定义 Skill / Knowledge / Memory / Learning 的对象、生命周期、Owner 和接口。

### V1.0：完整产品方案

形成 PRD、Technical Blueprint、Implementation Guide、Roadmap 和 Figma。

## 12. 当前待确认事项

| 事项 | 状态 |
|---|---|
| 正式平台名称：Bosch 或 UXGS Enterprise Intelligence Platform | TBC |
| Research Agent、Engine 与 Copilot 的正式命名 | TBC |
| 平台主库是否从本 Research 项目拆分 | 建议拆分，TBC |
| 首个试点客户、Sponsor 与预算 Owner | TBC |
| 内部 AI Endpoint、数据分类与托管边界 | TBC |
| Knowledge / Memory 的部门 Owner 与审批 SLA | TBC |
| Credits 与内部结算模式 | Hypothesis |
| Marketplace 的首批 Agent 范围 | Hypothesis |

