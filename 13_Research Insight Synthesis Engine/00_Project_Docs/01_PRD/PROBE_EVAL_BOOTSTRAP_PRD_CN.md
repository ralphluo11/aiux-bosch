# Research Insight Synthesis Engine · 追问评测与逻辑推导 PRD

**文档名：** Probe Evaluation & Logic Bootstrap PRD  
**版本：** V1.0  
**日期：** 2026-07-29  
**状态：** Active Method Track — 当前先验证访谈前设计；实时执行仍为 Post-MVP TBC  
**文档定位：** 专项子 PRD（不替代母 PRD / 执行 PRD）  
**母文档：** `PRD_CN.md`、`EXECUTION_PRD_CN.md`  
**对应 POC 能力：** Generic / Knowledge Probe、Human Review、Evaluation JSON、Guardrail  

> **一句话：** 先把「业务决策 → Evidence Needed → 问题 → Probe Tree → 完成标准」显式化，再用少量人工标注种子验证追问质量；实时自动追问在 Post-MVP Go / No-go 前只做离线评测。  
> **明确不做：** 本阶段不做模型 Fine-tune / 权重训练。

---

## 1. 背景与要解决的问题

POC 的核心体验是「用户答一句 → AI 决定追问还是跳下一主问」。若完全靠模型临场发挥：

- 追问风格不稳定（有时诱导、有时过技术）
- 问卷覆盖逻辑不清晰（何时够深、何时该跳题）
- 无法向客户证明「为什么这个问题更好」
- 无法系统对比 Generic vs Knowledge-enhanced

团队已形成共识：

1. **先不训练模型**（执行 PRD 明确不做 Fine-tuning）
2. **用 3–5 条人工标注启动**，再让系统对未标注样本自动推导
3. 推导结果必须 **可审核、可回溯、可进 Golden Set**

本 PRD 定义这一闭环的目标、数据规格、流程、以及 **UX 与 AI 各自交付物**。

---

## 2. 目标与非目标

### 2.1 目标（POC 内）

| ID | 目标 | 成功标准 |
|----|------|----------|
| G1 | 冻结一份「追问逻辑说明书」 | UX + AI 共用同一份 Guide Intent / 跳题规则 |
| G2 | 产出可复用的种子标注 | ≥3 条 Good + ≥2 条 Bad（建议 5 条起） |
| G3 | 未标注回答可自动出候选 | 同场景新回答能生成 1 条候选追问 + 理由 |
| G4 | 人工抽检形成评测集 | POC 结束前 Golden Set ≥20 条（种子扩写） |
| G5 | 可对比两种模式 | 至少 5 条同时有 Generic / Knowledge 结果 |

### 2.2 非目标

- 不做 SFT / RLHF / 私有模型训练
- 不追求统计显著的 USP 提升证明
- 不替代研究员 Live Override（推导结果仍是「建议」）
- 不在本专项内做完整 ASR / Summary 方案（见执行 PRD）

---

## 3. 核心概念（先对齐词）

| 术语 | 含义 |
|------|------|
| **问卷逻辑（Interview Logic）** | 主问题顺序、每题 intent、最多追问轮次、何时下一题/结束、禁止项 |
| **种子标注（Seed Labels）** | 人工写的 3–5 条「输入→期望追问/拒绝理由」 |
| **自动推导（Bootstrap Inference）** | 模型 + 规则对未标注回答生成候选下一问 |
| **抽检（Human Spot-check）** | 人对自动结果做 Accept / Edit / Reject |
| **Golden Set** | 通过审核的评测样本集，用于回归与演示 |
| **Bad Case** | 明确不该发出的追问（诱导、双重问题、术语泄露等） |
| **Few-shot** | 把种子样例放进 Prompt，让模型模仿，**不是训练权重** |
| **Evidence Needed** | 为回答某个研究问题必须获得的事件、情境、行为、原因、影响、频率、替代方式等证据槽位 |
| **Probe Tree** | 按证据缺口选择追问的分支，不是必须逐条念完的固定题单 |
| **Completion Criteria** | 关键 Evidence 已获得，或明确无法获得、继续追问会重复/诱导、达到时间或安全边界 |

### 3.2 当前质量原则

- Question coverage 不等于 Evidence coverage；每个 RQ 至少有一组明确的 Evidence Needed。
- `max_followups` 只是时间护栏，不能单独代表“已经问深”。
- 追问优先补齐单一证据缺口：真实事件、触发情境、行为过程、判断原因、影响、频率、替代方式或成功标准。
- 访谈/问卷结束后输出 `ready / partial / insufficient / conflicted`，不足时不得强行形成高置信度总结。

### 3.1 推导依赖什么（重要）

```text
问卷逻辑（显式规则）
    +
Knowledge Cards（可选）
    +
种子标注（Few-shot 示例）
    +
当前用户回答
        ↓
自动候选追问 + 理由 + 引用 Card
        ↓
人工 Accept / Edit / Reject
        ↓
写入 Golden Set / Bad Case
```

**仅有 3–5 条标注，不足以单独“学会”整份问卷。**  
种子负责「示范好坏」；逻辑说明书 + Guide/Card 负责「推导边界」。

---

## 4. 数据规格

### 4.1 种子标注单条字段（Must）

| 字段 | 说明 | 示例 |
|------|------|------|
| `case_id` | 唯一 ID | `SEED-001` |
| `guide_question_id` | 所属主问题 | `gq-2` |
| `guide_question_text` | 主问题原文 | 冷藏室里哪里温度不满意？ |
| `participant_answer` | 用户最终回答 | 后面菜会冻，门边饮料不够冷… |
| `should_probe` | 是否该追问 | `yes` / `no`（no 则应下一主问） |
| `good_probe` | 期望好追问（中性、单缺口） | 方便再说一下，是后壁附近更容易结冰，还是整层不均匀？ |
| `bad_probe` | 至少 1 个反例 | 是不是风道设计有问题导致结霜？ |
| `bad_reason` | 反例为何坏 | 诱导 + 工程术语 |
| `signal` | 检测到的用户信号 | 后壁结冰 / 门边不冷 |
| `information_gap` | 还缺什么信息 | 空间分布是否不均匀 |
| `knowledge_card_ids` | 若增强模式应引用的 Card | `KC-airflow-01` 或空 |
| `scores` | 可选 1–5：相关/深度/中性/依据/不重复 | `4,4,5,4,5` |
| `notes` | UX/研究备注 | 演示优先用这条 |

### 4.2 完整示例（可直接当 Seed-001）

**输入**

- 主问题：冰箱冷藏室里，你觉得哪里温度不满意？
- 用户回答：后面的菜经常冻住，但是门边饮料不够冷，而且塞满东西时更明显。

**人工标注**

- 是否追问：是  
- 好追问：方便再说一下，是后壁附近更容易结冰，还是整层都不均匀？  
- 坏追问：是不是因为风道设计有问题导致结霜？  
- 坏因：诱导归因 + 内部工程术语  
- 信号：后壁结冰、门边偏暖、满载加重  
- 信息缺口：空间分布 / 装载条件  
- 可引用 Card：`KC-door-airflow`（若有）

**再备 4 类种子（建议组合）**

| Seed | 类型 | 目的 |
|------|------|------|
| 002 | 频繁开门 / 恢复慢 | 覆盖另一机制 |
| 003 | 含糊回答「就是不太方便」 | 测澄清型追问 |
| 004 | 信息已够，应跳下一主问 | 测「不追问」逻辑 |
| 005 | Bad：双重问题 / 泄露内部名 | 测 Guardrail |

### 4.3 自动推导输出字段（系统生成）

与现有 ProbeDecision / Evaluation 对齐：

- `action`: `probe` | `next_guide_question`
- `proposed_question`
- `probe_intent` / `detected_signal` / `information_gap`
- `candidate_hypotheses`
- `grounded_card_ids`
- `rationale`
- `generation_mode`: `llm` | `deterministic`
- `guardrail_result`（通过 / 拦截原因）

### 4.4 Golden Set 扩写目标（POC）

| 阶段 | 数量 | 来源 |
|------|------|------|
| Day 0 | 3–5 | UX 手写种子 |
| Day 2–3 | → 10–15 | 自动推导 + UX/AI 抽检 |
| POC 验收前 | ≥20 | 继续抽检；含 ≥5 条双模式对比 |

---

## 5. 端到端流程（要做的步骤）

### Phase A — 冻结逻辑（0.5–1 天）

1. 选定 POC 场景（如冰箱冷藏体验，或 Kennel 后客户场景）
2. 写出 **Interview Logic Sheet**（见 §6.1）
3. 确认 Guide 主问题 5–8 条及每题 `intent` / `max_followups`
4. （Stretch）确认 5–10 张 Knowledge Card 的 signal → probe 映射

### Phase B — 种子标注（0.5 天）

1. UX 按 §4.1 填写 3–5 条种子（含 ≥2 Bad）
2. AI 检查字段完整性、与 Guardrail 规则一致
3. 种子入库：表格 +（可选）写入 Prompt few-shot 区 / `evaluations` 目录

### Phase C — 自动推导（可重复）

1. 准备未标注回答池（手工编 10 条 **或** 真实试访 transcript）
2. 系统对每条生成候选（Generic；有 Card 时再跑 Knowledge）
3. 导出结果表 / Evaluation JSON
4. **不自动视为正确**，进入抽检

### Phase D — 抽检与回流（持续）

对每条自动结果，标注人只做三选一：

| 动作 | 含义 | 回流 |
|------|------|------|
| **Accept** | 可发给受访者 | 进 Golden Set |
| **Edit** | 改几个字后可用 | 进 Golden Set（保留 AI 原文 + 终稿） |
| **Reject** | 不可用 | 进 Bad Case，并写原因标签 |

原因标签建议固定枚举：

`leading` | `double_question` | `jargon` | `internal_leak` | `off_topic` | `redundant` | `too_vague` | `should_not_probe`

### Phase E — 迭代（每轮几小时）

1. AI 根据 Bad Case 改 Prompt / Guardrail / 检索规则（**不改模型权重**）
2. 用 Golden Set 回归：同一输入再跑，看 Accept 率是否上升
3. UX 更新 Logic Sheet（若发现问卷逻辑本身有洞）

---

## 6. 交付物与模板

### 6.1 Interview Logic Sheet（UX 主笔，AI 共建）

最少包含：

```text
场景：…
业务决策：…
研究目标：…
Evidence Needed：event / context / behavior / rationale / impact / frequency / workaround / success criteria
主问题列表：
  Q1 intent=context  probe_tree=[event, context, behavior]  完成标准=…
  Q2 intent=pain     probe_tree=[impact, frequency, workaround]  完成标准=…
  …
跳题规则：关键证据缺口关闭 → 下一主问；达到时间护栏但证据不足 → 标记 partial / insufficient
结束规则：主问题全部覆盖或时长到
禁止：诱导归因、双问题、未批准工程术语、内部项目名
Knowledge 开关：Generic 必可完成；Enhanced 仅用 approved Card
```

### 6.2 种子 / Golden Set 表（建议 CSV 列）

`case_id, source(seed|bootstrap|live), guide_question_id, participant_answer, should_probe, good_probe, ai_proposed, human_final, review(accept|edit|reject), bad_reason_tags, card_ids, mode(generic|knowledge), scores, notes`

### 6.3 Demo Script 片段（验收用）

1. 展示 1 条种子如何约束风格  
2. 输入 1 条**未标注**新回答 → 自动出题  
3. Researcher Accept/Edit  
4. 展示 Bad Case 被 Guardrail 或人工 Reject  
5. （Stretch）同一回答 Generic vs Knowledge 对比  

---

## 7. 角色分工

### 7.1 UX 要做什么

| # | 任务 | 产出 | 完成定义 |
|---|------|------|----------|
| U1 | 定 POC 场景与用户表述口径 | 场景一页纸 | Kennel 前后冻结一版 |
| U2 | 写 Interview Logic Sheet | 逻辑说明书 | AI 可据此配置 Guide |
| U3 | 手写 3–5 条种子标注 | Seed 表 | 字段齐全，含 Bad |
| U4 | 设计抽检体验预期 | 审题交互说明 | Accept/Edit/Reject + 原因标签 |
| U5 | 抽检自动推导结果 | 标注后的表 | 每轮至少审 10 条 |
| U6 | 维护「什么叫好追问」标准 | 评分口径 / 示例 | 与研究规范一致 |
| U7 | 组织 1 场短试访（可选） | 真实回答素材 | 补未标注池 |
| U8 | 验收演示叙事 | Demo script 中 UX 部分 | 能讲清「为何可信」 |

**UX 不做：** 配 API、改 Prompt 工程细节、训模型、写检索代码。

### 7.2 AI（你）要做什么

| # | 任务 | 产出 | 完成定义 |
|---|------|------|----------|
| A1 | 把 Logic Sheet 落成 Guide / 状态机参数 | 配置或代码 | `max_followups`、跳题规则生效 |
| A2 | 设计/维护 Probe Prompt + Schema | Prompt 版本 | 强制结构化输出 |
| A3 | 接入主 LLM（Key / Base URL / Model） | 可跑 Live | `/api/health` 显示 LLM |
| A4 | 将 3–5 种子注入 few-shot 或评测夹具 | 种子可被调用 | 同输入可复现 |
| A5 | 实现/接通「未标注 → 批量推导」 | 脚本或 API 批跑 | 导出 CSV/JSON |
| A6 | Guardrail 规则与 Bad 标签对齐 | 拦截记录 | 高风险类可拦或可标 |
| A7 | （Stretch）Knowledge Card 检索与引用约束 | 仅 approved Card | 无命中则 Generic fallback |
| A8 | 搭建回归：Golden Set 重跑对比 | 评测报告 | Accept 率 / 违规率可看 |
| A9 | 根据 Bad Case 迭代 Prompt/规则 | 变更说明 | 每轮写清改了什么 |
| A10 | 文档：已知限制 + Phase 1 是否才考虑训练 | 一页限制说明 | 与执行 PRD 一致 |

**AI 不做：** 独自定义「好研究问题」口径（需 UX/研究确认）；替代 Live 人工 Override。

### 7.3 协作节奏（建议）

| 节点 | UX | AI |
|------|----|----|
| Kickoff（0.5h） | 带场景与好/坏例子 | 带现有 Decision Schema |
| Day 0 结束 | Logic Sheet + 5 种子 | Prompt 接入种子 + 试跑 3 条 |
| 每日站会（15min） | 反馈抽检里最烦的 3 类错 | 当天改规则/Prompt |
| Gate / 验收前 | 确认 Demo 叙事与口径 | Golden Set≥20 + 导出包 |

---

## 8. 系统行为要求（给实现）

1. **同一输入可复现**：记录 model 名、prompt 版本、knowledge_mode、card 命中  
2. **保留双轨文本**：`ai_proposed_question` 与 `human_final_question` 必须都存  
3. **失败可降级**：LLM 失败 → deterministic / offline probe，不丢 Turn  
4. **未抽检不得称为 Golden**：自动结果默认 `review_status=pending`  
5. **Generic 必须可独立跑完**：关闭 Knowledge 不能断访谈  

与执行 PRD 对齐的验收钩子：

- P0-06 Generic Adaptive Probe  
- P0-07 Override 保留 AI vs 最终题  
- P0-10 / P0-11 Stretch：Knowledge + Guardrail  
- Evaluations / Golden Set 原始输入（现有 PoC 已具备导出方向）

---

## 9. 验收标准（本专项）

### Must

- [ ] Interview Logic Sheet 已冻结一版  
- [ ] ≥5 条种子（含 ≥2 Bad）字段完整  
- [ ] 对 ≥10 条未标注回答完成自动推导  
- [ ] 抽检后 Golden Set ≥20（Accept/Edit 合计）  
- [ ] 至少演示 1 次：新回答 → 自动题 → 人工 Accept/Edit  
- [ ] Bad Case 有原因标签，并能指出 Prompt/规则改动点  

### Stretch

- [ ] 同 5 条输入的 Generic vs Knowledge 对比表  
- [ ] Guardrail 自动拦截记录 ≥3  
- [ ] 一键从 Evaluation JSON 导入抽检表  

### 明确失败信号

- 只有种子、没有逻辑说明书，却声称「模型已学会问卷」  
- 自动结果未抽检就用于对外承诺准确率  
- 开始 Fine-tune 却挤占 Must 闭环（ASR / Live / Summary）排期  

---

## 10. 工作量粗估（POC 并行，不阻塞主路径）

| 工作包 | UX | AI | 合计感 |
|--------|----|----|--------|
| Logic Sheet + 5 种子 | 0.5–1 天 | 0.5 天接入 | ~1 天对齐 |
| 首轮 10 条推导+抽检 | 0.5 天审 | 0.5 天批跑 | ~1 天 |
| 扩到 20 + 1 轮迭代 | 0.5 天 | 0.5–1 天 | ~1 天 |
| Demo 叙事打磨 | 0.5 天 | 配合导出 | 0.5 天 |

**相对训练：** 以上是「天」级；Fine-tune 是「周–月」级且 POC 不做。

---

## 11. 与主 POC 排期的关系

```text
主路径 Must（执行 PRD）
  Setup → Guide → Link → ASR → Probe → Override → Summary

本专项（并行加强可信度）
  Logic → Seed → Bootstrap → Spot-check → Golden Set
```

优先级建议：

1. **不阻塞** ASR / 双端闭环  
2. 本专项保证「追问为什么可信」的演示与回归  
3. Kennel 后若换客户场景：Logic Sheet + 种子重做一版，流水线复用  

---

## 12. 开放问题

1. POC 场景最终是冰箱 Demo，还是 Kennel 客户场景？  
2. 抽检是否进产品 UI（Evaluations 页），还是 POC 阶段用表格即可？  
3. 种子与 Golden Set 存放：仅 `WIP/` 表格，还是进仓库 `evaluations/`？  
4. 中文主模型最终选 `gpt-5.4-mini` 还是 `qwen3.7-plus`？（影响 few-shot 表现，不改流程）

---

## Document Control

| 字段 | 值 |
|------|-----|
| **Version** | 1.0 |
| **Last Updated** | 2026-07-29 |
| **Parent** | `PRD_CN.md` V2.0 / `EXECUTION_PRD_CN.md` V1.0 |
| **Owner** | UX 负责人（口径）+ AI 负责人（推导与评测管线）共同 |
| **Next** | UX 填 Logic Sheet + 5 种子；AI 接 LLM 并批跑首轮推导 |
