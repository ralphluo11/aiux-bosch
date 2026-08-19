# Research Insight Synthesis Engine · 产品 PRD（立项与对齐）

**产品名：** Research Insight Synthesis Engine（研究洞察综合引擎）  
**项目编号：** 13（UXGS Internal）  
**文档定位：** **立项、资源对齐、阶段决策**（母 PRD）  
**执行文档：** `EXECUTION_PRD_CN.md`（设计 / 开发 / Vertical Alpha 验收用）

> **版本：** V2.1｜**日期：** 2026-08-11｜**状态：** Draft — Vertical Alpha 范围已更新

> **正式范围决议（2026-08-11）：** 当前主线为已有录音、转写和项目材料进入 `Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery`。实时 AI 访谈、Participant Link、Streaming ASR、动态实时追问和双端 Live View 不进入 Alpha 或当前 MVP；MVP 完成后另行 Go / No-go，状态为 `Post-MVP TBC`。本文中仍出现的实时访谈描述仅代表长期候选能力，不构成当前 Release 承诺；当前验收以 V2.0 `EXECUTION_PRD_CN.md` 为准。

---

## 01 | Project Overview


| 项         | 内容                                      |
| --------- | --------------------------------------- |
| **产品名**   | Research Insight Synthesis Engine       |
| **产品类型**  | Enterprise AI Research Intelligence / Evidence Synthesis 产品 |
| **产品阶段**  | Vertical Alpha；验证已有研究材料的证据综合与审核交付            |
| **核心链路**  | **Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery** |
| **产品负责人** | TBC（Data 负责人 + UX 负责人共同推进客户与 data 信息收集） |
| **读者**    | 业务 Sponsor、Data / UX 负责人、Eng、试点客户方      |




### 近期关键节点（POC 以本表为准；Kennel 后可微调）


| 节点                | 日期（约）            | 说明            |
| ----------------- | ---------------- | ------------- |
| 客户定义 + 收集 data 信息 | **2026-07-31**   | Data + UX 负责人 |
| Kennel 对齐         | **2026-07-31**   | 排期锚点；之后可调整    |
| **POC 结束**        | **约 2026-08-05** | **周期约一周半**    |
| Phase 1 启动        | Kennel 后         | 见路线图          |




### 文档体系


| 文档                      | 用途                               |
| ----------------------- | -------------------------------- |
| **本 PRD**               | 立项、对齐、范围与路线决策                    |
| **EXECUTION_PRD_CN.md** | 页面 / API / 验收 / Gate / 数据模型等执行细节 |
| `WIP/`                  | POC 演示、Pilot 记录、客户与 data 收集结果    |


---



## 02 | Background & Objectives



### 2.1 要解决的问题

- 采访大纲依赖个人经验，**专家结构与既有题库**难复用
- 采访、转录、分析、报告分散在多个工具，信息反复搬运
- 通用 AI 能动态追问，但缺少**产品 / 工程机制层面**的判断  
- 内部资料、外部资料与真实客户回答之间**缺少可追溯连接**  
- 总结难与**博世语境**对齐；外部 SaaS 无法深度对接内部数据



### 2.2 产品目标

1. **Evidence-led 闭环**：已有材料从登记、分析走到可审核交付，同一产品内完成。
2. **Human accountable**：AI 生成 Evidence、Finding 与 Recommendation 候选，人审核、修改、批准并保留差异。
3. **专家结构可复用**：研究方法、Artifact Contract 与 Benchmark 形成版本化资产。
4. **双 Track 能力**：既有功能研究输出 Finding / Recommendation；Proposal 研究输出 Assumption / Opportunity / Validation Plan。
5. **Post-MVP decision**：实时 AI 访谈只有在 MVP 完成后通过单独 Go / No-go 才可能立项。



### 2.3 产品原则

1. **End-to-end first** — 研究从创建走到报告，不拆断链。
2. **Human in control** — 研究员保留最终判断权。
3. **Knowledge grounded** — 知识辅助提问与总结，不替受访者生成答案。
4. **Evidence traceable** — 结论与增强追问均可回溯来源。
5. **Neutral by design** — 内部假设不直接作为事实告知受访者。
6. **Modular outputs** — Guide、Transcript、Evidence、Theme、Insight、Report 独立保存、可复用。



### 2.4 成功标准（决策层）

**Vertical Alpha：**

- 冻结冰箱 Project Brief、Source Inventory、Ground Truth 与 Benchmark Rubric；
- 使用已脱敏的已有录音转写、研究笔记、报告和项目材料；
- 生成可定位的 Evidence / Claim，并综合 Finding / Recommendation；
- Research Lead 执行 Accept / Edit / Reject，保留 AI Raw / Human Final；
- 输出 Human View、Machine View、Evidence Pack 与 Run Manifest；
- 使用 Holdout Reference 评估准确性、遗漏、人工修改和时间。

**完整产品方向：**

- 多项目、权限、≥1 类真实内部数据源  
- 大纲与总结的**博世语境**可配置  
- 知识库、跨项目复用、多 BU

---



## 03 | 核心价值主张（双 USP）



### USP-A｜数据层：内部 ↔ 外部关联 + 博世语境

> 博世内部数据可与外部采集数据关联；在**采访大纲生成**与**总结报告**阶段做外部工具无法等价的「博世语境」调整。


| 阶段   | 大纲                          | 总结               |
| ---- | --------------------------- | ---------------- |
| POC  | 专家结构 + 库；Connector **接口预留** | 基础摘要 + 引用回溯      |
| 完整产品 | 内部 / 外部源参与 Guide；语境规则可配置    | 语气、框架、证据链按博世语境输出 |




### USP-B｜追问层：Mechanism-aware 深度追问

> 普通 AI 知道怎么追问；我们的 AI 知道**为什么值得追问**，以及下一问应验证哪个**产品 / 设计假设**。

利用 Bosch 产品、工程、设计知识与精选外部资料：

```text
Engineering / Product Mechanism
→ User-observable Signal
→ Candidate Hypothesis
→ Discriminating Evidence
→ Neutral Customer-facing Probe
```


| 阶段   | 能力                                                         |
| ---- | ---------------------------------------------------------- |
| POC  | Generic 自适应追问 **Must**；Knowledge Pack + 机制感知追问 **Stretch** |
| 完整产品 | Knowledge Cards、RAG、Guardrail、Research Memory 体系化          |


**非目标：** 不做「上传文件做普通 RAG」即视为完整差异；不把未经审核的 AI 结论当作企业事实。

---



## 04 | Users & Customer



### 4.1 客户状态


| 项              | 状态                                      |
| -------------- | --------------------------------------- |
| 试点客户 / Sponsor | **定义中** — **2026-07-31 前**定稿并收集 data 信息 |
| 责任人            | Data + UX 负责人                           |
| POC 策略         | 客户未定前按**通用场景**推进                        |




### 4.2 角色


| 角色                               | 价值                                           |
| -------------------------------- | -------------------------------------------- |
| **UX Researcher / Research Lead** | 创建项目、确认材料、审核 Evidence / Finding、批准交付 |
| **Participant / 受访者** | 当前 Alpha 不直接使用；已有脱敏转写可作为 Source。实时参与属于 Post-MVP TBC |
| **Product / Engineering Expert** | 审核 Knowledge Cards、机制与假设（完整产品 / POC Stretch） |
| **Data / Knowledge Owner**       | 数据源、权限、同步（Phase 1+）                          |
| **Business Reader**              | 消费摘要与证据                                      |
| **System Admin**                 | 空间、角色、合规（Phase 2）                            |


---



## 05 | 端到端体验

```text
Project Brief → Source Registry → Evidence / Claim
→ Finding / Recommendation → Human Review
→ Structured Delivery → Benchmark Evaluation
```



### 5.1 Project Brief 与 Research Plan

定义业务决策、研究问题、用户、边界、材料、数据等级、交付和成功标准。当前 Alpha 使用已有研究材料，不生成 Participant Link。

### 5.2 实时 AI 访谈（Post-MVP TBC）

不进入 Alpha 或当前 MVP。MVP 完成后再根据客户需求、隐私与同意、ASR质量、实时成本和团队资源单独决策。

### 5.3 总结报告

POC：单场 Themes、要点、Quotes、基础导出。  
完整产品：Evidence 链、博世语境、多场聚合、模板库。

### 5.4 证据链（完整产品目标）

```text
Interview Turn → Transcript → Evidence → Theme → Insight → Report
```

每条 Insight 须可回到：来源用户 → 问题 → 原话 → 时间 / 片段。

---



## 06 | Scope & Roadmap



### 6.1 Vertical Alpha — **当前范围以本表为准**


| 纳入                                  | 不纳入                                   |
| ----------------------------------- | ------------------------------------- |
| 冰箱 Project Brief、Source Inventory 与 Holdout Ground Truth | 实时 AI 访谈、Participant Link、ASR、Live View |
| 已有脱敏转写、研究笔记、报告和项目材料 | 真实内部库生产接入 |
| Evidence / Claim 原文定位与校验 | 多项目 / 多 BU |
| Finding / Recommendation 与 Human Review | SSO / 完整 RBAC / 完整审计平台 |
| Human View、Machine View、Evidence Pack、Run Manifest | Owner Portal / Dashboard / Marketplace |
| 本地离线 Benchmark Evaluation | 正式 PPT / Word 文件生成 |


**最短验收闭环：**  
1 份批准 Brief → 1 组脱敏材料 → Evidence / Finding → 人工审核 → 1 份结构化交付 + Benchmark 结果。

> 功能级验收、Gate、P0 清单见 **EXECUTION_PRD_CN.md**。



### 6.2 Phase 1 — 首个可推广版本

- 多项目管理与权限  
- **≥1 类**真实内部数据源 + 外部精选资料  
- USP-A：大纲 / 总结博世语境规则  
- USP-B：Knowledge Cards、轻量 RAG、Guardrail、机制感知追问稳定化  
- Evidence 审核工作台、报告导出增强  
- 一个 BU 内多 Study / 多 Session



### 6.3 Phase 2 — 企业化

- 知识库、跨项目 Research Memory  
- 多 BU 租户、SSO、审计、数据治理  
- 内外部数据关联深化（USP-A 完整态）  
- 模板库、评测、运营看板



### 6.4 Phase 3（愿景）

跨产品 / 市场信号关联、趋势与知识空白、Synthetic User 单独评估。

---



## 07 | 能力蓝图（完整产品 · 战略视图）

> 开发优先级与 POC 裁剪见执行 PRD。


| 模块                          | 说明                 | POC     | Phase 1 |
| --------------------------- | ------------------ | ------- | ------- |
| Project / Study 管理          | 目标、假设、状态           | 单 Study | 多项目     |
| Research Plan              | Brief、方法、范围与 Gate | ✅ | ✅ |
| Participant Link & Consent  | 链接、同意、设备检查 | Post-MVP TBC | Post-MVP TBC |
| Real-Time Voice + ASR       | 语音、转录、轮次提交 | Post-MVP TBC | Post-MVP TBC |
| Interview Orchestrator      | 覆盖度、变题、Fallback | Post-MVP TBC | Post-MVP TBC |
| Researcher Live View        | 监控、接受 / 覆盖下一问 | Post-MVP TBC | Post-MVP TBC |
| Generic Adaptive Probe      | 无知识命中时追问 | Post-MVP TBC | Post-MVP TBC |
| Domain Intelligence         | 内部 / 外部源、Connector | 桩       | ≥1 真源   |
| Knowledge Cards + RAG       | 机制—信号—假设—追问        | Stretch | ✅       |
| Question Guardrail          | 中立、保密、可回答性         | 简版      | ✅       |
| Evidence / Insight Pipeline | Theme、Insight、审核   | 轻量      | ✅       |
| Report Generation           | Summary、导出         | 基础      | 增强      |
| Research Memory             | 跨项目复用              | —       | Phase 2 |
| Admin / Governance          | SSO、RBAC、审计        | —       | Phase 2 |


---



## 08 | 成功指标（立项层）


| 类别  | 指标（完整产品目标方向）                                       |
| --- | -------------------------------------------------- |
| 效率  | 访谈到可汇报材料周期缩短；报告制作时间下降                              |
| 质量  | Insight 证据关联率 ≥95%；研究员采纳率 ≥80%                     |
| 体验  | 访谈完成率；下一问延迟可接受；Session 可恢复                         |
| USP | 知识增强追问可追溯；Mechanism-aware 盲评优于 Generic；零高风险诱导 / 泄露 |
| 合规  | 数据分级、AI 通道、保留策略确认（Phase 1 前）                       |


POC 具体阈值见 **EXECUTION_PRD_CN.md** §验收。

---



## 09 | 风险与回应（摘要）


| 风险            | 回应                              |
| ------------- | ------------------------------- |
| 工程知识导致诱导提问    | 假设仅系统内部使用；Guardrail + 中性表述      |
| 资料过期 / 型号不匹配  | 元数据过滤、有效期、审核状态                  |
| AI 幻觉 / 不可信摘要 | Evidence-first；Quote 必须回到 Turn  |
| 知识过多发散        | Coverage Map、追问预算、top-k         |
| POC 范围膨胀      | 执行 PRD 明确 Must / Stretch / 不做   |
| 客户未定          | 通用 POC + Connector 桩；7/31 后绑定场景 |


---



## 10 | RASIC

**RASIC：** R 执行 · A 拍板 · S 支援 · I 知会 · C 咨询  

**角色：** UX · Data · PM（兼岗 TBC）· Res · **Eng**（前端+后端+AI，当前合一）· Biz · IT/Sec · Ops（正式产品）

### 10.1 客户定义 + POC


| 角色     | 试点客户定义 | 收集 data 信息 | POC 范围与验收 | 大纲体验与规则 | 实时采访 | 总结报告 | 内部数据接口 | Kennel | POC 演示 |
| ------ | ------ | ---------- | --------- | ------- | ---- | ---- | ------ | ------ | ------ |
| UX     | R      | C          | A/R       | A/R     | C    | A/C  | I      | R      | A      |
| Data   | R      | A/R        | C         | S       | I    | C    | A/C    | R      | S      |
| PM     | C      | C          | R         | C       | C    | C    | C      | A      | R      |
| Res    | C      | C          | C         | C       | C    | C    | I      | I      | S      |
| Eng    | I      | C          | C         | R       | A/R  | R    | R      | S      | R      |
| Biz    | A/C    | C          | I         | I       | I    | I    | I      | I      | C/I    |
| IT/Sec | I      | I          | I         | I       | C    | I    | C      | I      | I      |




### 10.2 Phase 1 — 正式产品


| 角色     | 产品路线 | 多项目 | 全链路 | 数据源选型 | 数据接入 | 博世语境 | 证据链 | 报告  | 合规  | 上线  | 推广  |
| ------ | ---- | --- | --- | ----- | ---- | ---- | --- | --- | --- | --- | --- |
| UX     | C    | A/R | A/R | C     | I    | A/R  | A/R | A/C | I   | I   | R   |
| Data   | C    | C   | S   | A/R   | A/C  | R    | C   | C   | C   | C   | S   |
| PM     | A/R  | R   | R   | C     | C    | C    | C   | R   | C   | A   | A/R |
| Res    | C    | C   | C   | C     | I    | C    | C   | C   | I   | I   | R   |
| Eng    | C    | R   | R   | R     | R    | R    | R   | R   | S   | S   | S   |
| Biz    | C    | C   | C   | C     | C    | C    | I   | C   | C   | C   | A/C |
| IT/Sec | I    | C   | I   | C     | C    | C    | I   | I   | A/R | C   | I   |
| Ops    | I    | I   | I   | I     | S    | I    | I   | I   | S   | R   | S   |




### 10.3 Phase 2


| 角色     | 知识库策略 | 知识库实现 | 多 BU | 内外部关联 | 模板/看板 | 多 BU 运营 |
| ------ | ----- | ----- | ---- | ----- | ----- | ------- |
| UX     | C     | C     | C    | C     | A/R   | S       |
| Data   | A/R   | A/C   | C    | A/R   | S     | S       |
| PM     | R     | C     | A/R  | R     | R     | A       |
| Res    | C     | C     | I    | C     | C     | C       |
| Eng    | R     | R     | R    | R     | R     | S       |
| Biz    | C     | C     | C    | C     | C     | R       |
| IT/Sec | C     | C     | A/C  | C     | I     | C       |
| Ops    | I     | S     | R    | I     | R     | A/R     |


---



## 11 | Open Items / TBC


| 项                      | Owner        | 截止           |
| ---------------------- | ------------ | ------------ |
| 试点客户与 Sponsor          | Data + UX    | 2026-07-31   |
| data 信息清单与结论           | Data + UX    | 2026-07-31   |
| 内部数据源选型                | 客户定义后        | Kennel 后     |
| 合规（分级、AI 通道、托管）        | IT/Sec + 项目组 | Phase 1 前    |
| PM / Ops 是否单列；客户定义最终 A | 项目组          | TBC          |
| Kennel 后排期微调           | 项目组          | 2026-07-31 后 |


---



## 12 | 一句话定位

> **Research Insight Synthesis Engine 是以可追溯 Evidence 和 Human Review 为核心，把已有研究材料转化为可审核 Finding、Recommendation 与结构化交付的企业级 Research Intelligence 能力。实时 AI 访谈为 Post-MVP TBC。**

---



## Appendix | Document Control


| 字段                   | 值                                             |
| -------------------- | --------------------------------------------- |
| **Document Version** | 2.1                                           |
| **Last Updated**     | 2026-08-11                                    |
| **Status**           | Draft                                         |
| **Languages**        | `PRD.md` · `PRD_CN.md` · `PRD_bilingual.html` |
| **Execution**        | `EXECUTION_PRD.md` · `EXECUTION_PRD_CN.md`    |

