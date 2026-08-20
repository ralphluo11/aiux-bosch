# 复用方案记录

记录 `AI_Research_Copilot_v0` 从外部方案里直接搬运、改造或参考的设计，以及对应实现在代码里的位置。目的是让后来者知道"这段逻辑为什么长这样"和"原始出处在哪"，而不用重新翻聊天记录。

新增能力都做成加法：不删除、不替换现有的确定性校验（`_validate_traceability` / `_filter_untraceable_candidates` / `_validate_evidence_synthesis`），只在其基础上补一层。

---

## 1. 来源：`ai-interview-/interview-core-v0/research_analysis/`

本机路径：`C:\Users\LOU8SGH\Desktop\ai-interview-\interview-core-v0\research_analysis\`

这是同一套 `ai_ux_core` 血缘下更早的一个分支，专门设计了访谈后分析的三层 assurance（确定性 Gate → LLM Judge → 异常触发人工审核），针对 `Transcript → Highlights → Themes → Insights → Report` 这条链路，附带 5 个 prompt、JSON Schema 和正反 fixture。

### 已经存在、不需要重复搬运的部分

对照后发现 `AI_Research_Copilot_v0/src/ai_ux_core/research_agent.py` 里已经有等价甚至更完整的确定性 Gate 实现，**这部分不搬运**，避免重复造轮子：

| research_analysis 的检查项 | 本项目里已经实现的等价物 |
|---|---|
| anchor 能否在原文唯一定位 | `_validate_traceability` 里的 `quote_not_found_in_transcript` 校验（[research_agent.py](../src/ai_ux_core/research_agent.py) 约第 830 行） |
| theme / insight 引用的 ID 是否存在 | `_validate_traceability` 的 `finding_references_unknown_evidence` / `insight_references_unknown_finding` |
| 未通过校验时的处理 | `_filter_untraceable_candidates`：本项目选择"过滤掉并在 limitations 里说明"，比 research_analysis 原设计（硬拒绝整批）更贴合 Alpha 阶段的可用性 |

### 本次直接搬运/改造的部分

**LLM Judge 层**——research_analysis 里完全没有对应实现，是本项目此前最大的空白（PRD 自己标注"Evidence → Finding → Insight AI Pipeline / 质量未验证"）。

- 来源 prompt：`research_analysis/prompts/04_insight_judge.md`
- 改造后落地位置：[research_agent.py](../src/ai_ux_core/research_agent.py) 的 `JUDGE_SCHEMA` / `JUDGE_INSTRUCTIONS` / `judge_synthesis()`
- 改动点：
  - 原设计只判断 `Insight`；本项目沿用同一套 verdict（`pass` / `revise` / `reject` / `human_review`）和 10 个 failure code（`RQ_IRRELEVANT`、`UNSUPPORTED_CLAIM`、`OVERGENERALIZED_POPULATION` 等），原样保留，因为这套分类已经足够通用。
  - 新增服务端强校验：judgements 必须覆盖输入里的每一条 insight_id，不多不少（`_validate_judgements`），这是本项目自己加的，原设计里没有——因为 strict JSON Schema 不能保证模型不遗漏。
  - `OfflineResearchPreviewAgent` 按项目一贯的"离线模式不伪装真实 AI"原则，返回全部 `human_review` 而不是跳过评审。

**Theme / Coding 聚类层**——research_analysis 设计里 `Highlight → Theme → Insight` 的中间那一步，本项目此前完全没有：Evidence 是直接一次性丢给模型让它跳到写 Finding，300 条 Evidence 在一次调用里既要发现模式又要写好 Finding 文字，规模一大容易漏模式、也容易把不相关证据硬凑到一起。

- 参考设计：`research_analysis/prompts/02_theme_clustering.md`（跨访谈聚类 + 隐藏在后台的 lightweight codebook 字段）
- 落地位置：[research_agent.py](../src/ai_ux_core/research_agent.py) 的 `THEME_SCHEMA` / `THEME_INSTRUCTIONS` / `cluster_themes()`，以及改造后的 `EVIDENCE_SYNTHESIS_FINDING_SCHEMA`（Finding 新增必填 `theme_ids`）
- 改动点：
  - 原设计 Theme 是 `Highlight` 的容器；本项目对象模型是 Evidence，做了改写，`evidence_ids` 直接对应本项目已有的逐字校验 Evidence，不用额外再造一层 Highlight 概念。
  - `participant_count` 不信任模型输出——`cluster_themes()` 里服务端自己按 `evidence_id → participant_id` 重新数一遍唯一参与者数量，写回每个 theme，这是照抄 research_analysis 强调的"participant count 是否按唯一参与者计算"这条 deterministic gate 原则，但没有对应字段可抄，是重新实现的。
  - 新增服务端强校验（`_validate_themes` / `_validate_evidence_synthesis` 里的 `finding_evidence_outside_referenced_themes`）：Finding 引用的 evidence_id 必须落在它引用的至少一个 theme 范围内，防止模型在 Theme 聚类之后又"串戏"引用不相关证据。
  - `EVIDENCE_SYNTHESIS_INSTRUCTIONS` 和 `EVIDENCE_SYNTHESIS_SCHEMA` 因此从"Evidence 直接到 Finding"改成"Evidence + Theme 到 Finding"，`synthesize_evidence()` 的函数签名多了一个必填的 `themes` 参数，这是本次唯一一处修改了既有公开方法签名的地方，调用方只有 `application.py` 一处，已同步更新。
  - `OfflineResearchPreviewAgent.cluster_themes()` 不聚类，把所有 evidence_id 原样放进 `unclustered_evidence_ids`，同样遵守"离线模式不伪装真实 AI"。

**单人证据群体化检查**——research_analysis 设计文档里提到"单人证据是否被写成群体性结论"，原实现在 `research_validation.py` 里针对 Highlight/Theme 模型；本项目的对象模型是 Evidence/Finding，做了改写而不是直接复制代码。

- 落地位置：[research_agent.py](../src/ai_ux_core/research_agent.py) 的 `flag_overgeneralized_findings()`
- 设计取舍：故意做成**建议性标记**而非硬拒绝——Alpha 阶段单参与者的 Finding 很常见且合理，误判成本比漏判更高，所以只在文本命中"用户普遍/大多数用户"等群体性措辞时才标记，交给人工审核判断。
- 接入点：[application.py](../src/ai_ux_core/application.py) 的 `analyze_project()`，作为新的 `quality_assurance` 阶段，结果写入分析结果的 `quality_assurance.overgeneralization_flags`。

---

## 2. 来源：Mizzen AI（觅深科技）公开方法论

仓库：[github.com/MizzenAI/mizzen-cli](https://github.com/MizzenAI/mizzen-cli)（MIT License）
本机克隆路径（临时）：scratchpad 下的 `mizzen-cli/`
具体文件：`skills/mizzen-cli/rules/follow-up.md`

Mizzen Insight（觅深科技产品）是做实时 AI 主持深访的独立产品，2026 年拿了红杉中国种子基金领投的近千万美元融资。他们的追问深度方法论是公开文档，和本项目"设计一份能问出好问题的问卷"这个目标是同一个问题的两种应用场景（一个用在实时访谈，一个用在预生成问卷）。

### 搬运内容

**追问深度四档模型**：`none`（不追问）/ `light`（最多追问 2 次，让回答说完整）/ `heavy`（主动追问 2-3 次，围绕为什么/怎么做/当时感觉/能否举例）/ `timed`（限定时间预算内动态追问，必须同时给时长）。

- 落地位置：[research_agent.py](../src/ai_ux_core/research_agent.py)
  - `QUESTIONNAIRE_SCHEMA` 里每道题新增 `follow_up_depth`（枚举）和 `time_budget_minutes`（0-60 的整数，仅 `timed` 时允许非 0）两个必填字段，与原有的 `max_followups`（数量护栏）并存，不替换。
  - `QUESTIONNAIRE_INSTRUCTIONS` 新增第 16 条规则，把 Mizzen 的深度选择建议和四条追问铁律（只用开放式问法、引用受访者原话、一次只问一个方向、只问 why/how/what 不问 yes/no）写成生成约束。
  - `generate_questionnaire()` 里新增服务端校验：`timed` 必须带 1-60 的 `time_budget_minutes`，非 `timed` 必须是 0——这条硬校验是照抄 Mizzen CLI 自己的约束（"`timed` 必须同时设置 `--time-budget`，其他级别不得设置该参数"）。

### 没有搬运的部分

- 题型taxonomy（open_ended / multiple_choice / scale / submission / cascading / matrix / ranking / proportion / statement 九种）——本项目当前只做开放式追问式问卷，不是结构化调查问卷，题型体系不适用，先不引入。
- 甄别（Screening）设计（意图伪装、陷阱选项）——这是招募阶段的能力，当前 Alpha 假设材料和参与者已经确定，不涉及招募筛选，属于 Post-MVP 范畴。
- Insight 报告的具体呈现格式——Mizzen 没有公开这部分（`InsightResponse.sections` 在其开源 CLI 里就是 `unknown[]`，服务端不透传结构），无法参考。

---

## 3. 本次未做、后续用 LLM Prompt 而非开源模型实现的部分

以下是此前策略讨论中识别的缺口，按约定先不接开源模型（FunASR / PaddleOCR / BGE-M3 / Presidio），因为会打破项目"零 pip 依赖"的设计前提；等环境/GPU/PyPI 访问问题明确后再决定是否升级：

| 缺口 | 现状 | 计划 |
|---|---|---|
| Knowledge Card 语义检索 | `retrieval.py` 仍是纯关键词匹配 | 未来改成让 LLM 直接做相关性排序（prompt-based ranking），不接向量库 |
| PII 二次校验 | `tools/pii_redactor.py` 仍是纯正则/词典，且未接入上传流程 | 未来在正则之外加一层 LLM prompt 复核，且需要先决定要不要把它接进 `add_project_document` 摄入路径（目前是独立 CLI，不在本次改动范围内） |
| OCR / 音视频转写 | 已经是 Live AI Endpoint（prompt-based），本身就符合"LLM Prompt"路线，不用动 | 无需改动 |

Judge 层本身就是这次唯一落地的"LLM Prompt 方案"——它是新的第二次 LLM 调用，不是本地模型，符合"剩下的方案先用 LLM Prompt 实现"的决定。

---

## 4. 本次改动清单

- [research_agent.py](../src/ai_ux_core/research_agent.py)：
  - 新增 `JUDGE_SCHEMA` / `JUDGE_INSTRUCTIONS` / `judge_synthesis()`（`OpenAIResponsesResearchAgent` 与 `OfflineResearchPreviewAgent` 均实现）、`flag_overgeneralized_findings()`；
  - 新增 `THEME_SCHEMA` / `THEME_INSTRUCTIONS` / `cluster_themes()`（同样两个 Agent 都实现）、`EVIDENCE_SYNTHESIS_FINDING_SCHEMA`；`synthesize_evidence()` 签名新增必填 `themes` 参数；`_validate_evidence_synthesis()` 新增 `theme_ids` 校验；
  - `QUESTIONNAIRE_SCHEMA` / `QUESTIONNAIRE_INSTRUCTIONS` / `generate_questionnaire()` 新增 `follow_up_depth` / `time_budget_minutes` 校验。
- [application.py](../src/ai_ux_core/application.py)：`analyze_project()` 管线从三段变五段（`evidence_extraction → theme_clustering → cross_source_synthesis → quality_assurance → human_review`），新增 `theme_clustering` 阶段调用 `cluster_themes()`，结果写入 `themes` 字段；`quality_assurance` 阶段调用 `flag_overgeneralized_findings` 和 `judge_synthesis`，并新增 Judge revise 闭环：对 `verdict=="revise"` 的 Insight 调用 `revise_insights()`，把改写结果原地写回（只改 `statement`/`confidence`，`finding_ids` 由服务端固定不给模型改），追加 `revision_history` 留痕，再对被改写的 Insight 单独重新 `judge_synthesis()` 一次并回填最终判定；封顶重试 1 次，不会无限循环。`quality_assurance` 新增 `revised_insight_count` 字段。
- [tests/test_research_agent.py](../tests/test_research_agent.py)：新增 21 个用例（Judge 覆盖率校验、offline 兜底、follow_up_depth 校验、单人泛化检测、Theme 聚类的引用校验与参与者计数、Finding 越界引用 Theme 的拒绝、`revise_insights` 的覆盖率校验和 offline 兜底）。
- [tests/test_web.py](../tests/test_web.py)：新增 `FakeQualityAssuranceResearchAgent` 测试替身和 `QualityAssuranceRevisionTests`，端到端验证"生成 Insight → Judge 判 revise → 自动改写 → 重新判 pass"整条闭环通过真实 HTTP API 跑通。
- 全量测试从 44 个增至 66 个，新增用例全部通过；3-4 个 Windows 临时文件锁报错（`tearDownClass` 阶段 SQLite 文件句柄未释放，每多一个用临时 SQLite 库的测试类就多一次同类报错）和 1 个 `pii_redactor` CLI 失败是改动前就存在的环境问题，与本次改动无关。
- 已经用真实的"冰箱"项目数据（5 个来源，之前跑过完整流程的那个项目）跑过端到端验证：`POST /api/projects/{id}/analyze` 返回 200，五段管线全部执行完，不覆盖项目原有的 `human_edited` 产出（`save_analysis` 每次写入新的 `run_id`，不是覆盖）。

## 5. 配置集中化：.env 支持

不是外部方案复用，是应用户要求做的内部重构，记在这里方便和上面的改动串起来看。

**问题**：`llm.py`、`research_agent.py`、`document_parser.py` 三处各自独立 `os.environ.get("AI_UX_LLM_API_KEY")`，默认值还不一致（比如超时时间 `llm.py` 默认 20 秒、`research_agent.py` 默认 60 秒），改一处不会同步到另外两处。而且 Windows 端（`START_WINDOWS.bat`）没有 Mac 端（`START_MAC.command`）那种"没 Key 就交互提示"的机制，每次开新终端都要手动重新 `$env:` 一遍，不会保留。

**方案**：新增 [config.py](../src/ai_ux_core/config.py)：
- `ensure_dotenv_loaded()`：纯标准库实现的 `.env` 加载，从项目根目录读 `KEY=VALUE`（支持 `#` 注释、引号包裹的值），只在**真实环境变量还没设置**时才写入 `os.environ`，保证 `export` / `$env:` / CI secret 永远优先于 `.env` 文件，跟 `START_MAC.command` 现有的 `${VAR:-default}` 精神一致。每进程只读一次。
- `load_llm_settings(*, default_timeout_seconds)`：`AI_UX_LLM_*` 这组变量的唯一读取点。`default_timeout_seconds` 保留成参数而不是写死一个常量，是因为 Interview Probe（20 秒，受访者在等下一题）和材料分析 Agent（60 秒，后台批处理）的超时差异是故意的，不能被"统一"抹掉。
- `InterviewApplication.__init__`（[application.py](../src/ai_ux_core/application.py)）是所有构造路径的唯一入口，在这里调用一次 `ensure_dotenv_loaded()`，保证不管从 `build_demo_application()`、直接构造还是别的入口进来，`.env` 都已经加载完，包括 `AI_UX_DATABASE_PATH` 这类不属于 LLM 组、但同样是 `os.environ.get` 读取的变量。
- `llm.py` / `research_agent.py` / `document_parser.py` 的三处 `build_*_from_env()` / `_ai_settings()` 全部改成调用 `load_llm_settings()`，不再各自读环境变量。
- `.env.example` 重写：真正被代码读取的变量放前面并加注释说明谁在用；`.env.example` 原来列的 ASR/Diarize/Embedding/Batch/Eval 五组凭证代码里一个都没接，改成注释掉并标注"尚未接入"，不然容易让人以为填了就生效。
- `START_WINDOWS.bat` 补上"没有 `.env` 就从 `.env.example` 复制一份、打开记事本、暂停等填完"的逻辑，跟 Mac 端补齐 Key 配置体验。

**测试**：[tests/test_config.py](../tests/test_config.py) 新增 5 个用例（解析、真实环境变量优先、缺文件时不报错、单进程只读一次、`OPENAI_API_KEY` 兜底），全部通过；改用了独立的 setUp/tearDown 隔离 `config` 模块的全局状态和 `os.environ`，避免污染同进程里跑的其他测试（比如让某个原本该是 `offline_preview` 的测试意外读到残留的假 Key）。另外用真实起服务 + 设一个假 Key 环境变量的方式做了端到端验证：`/api/health` 返回 `research_agent_mode: "live_ai"`，确认 Key 确实通过这条新路径传到了两条链路（Interview Probe 和材料分析 Agent）上；验证完已经把服务恢复回无 Key 的离线状态。

**没做的**：`.env.example` 里标了"尚未接入"的那五组凭证还是没有对应代码——如果以后真的要接本地 ASR/Embedding 等独立 Endpoint，应该扩展 `config.py` 加新的 `load_*_settings()`，而不是让调用方各自再读一次环境变量，重蹈这次要修的覆辙。

## 6. 尚未做的后续工作

- 前端（`static/`）还没有展示 `themes`、`quality_assurance` 里的 judgements、overgeneralization_flags 和 `revision_history`，人工审核页面目前看不到这几层新信息，需要单独排期。
- Recommendation 层完全没做：`ANALYSIS_SCHEMA` / `EVIDENCE_SYNTHESIS_SCHEMA` 里没有 `recommendations` 字段，但 `EXECUTION_PRD_CN.md` 的 Artifact Contract 明确要求 Finding 和 Recommendation 分离——这是 PRD 承诺了但代码没实现的部分。
- Coverage/Gap 检查（对照 Research Question 和 Finding，检查关键遗漏）还没做，对应 PRD 验收指标"关键遗漏率 ≤5%"。
- 未提交上次讨论中确认的 12 天 WIP 改动到 git（用户明确选择不做检查点，直接改）；本次新增内容和原有 WIP 混在同一个未提交的 working tree 里，正式提交前建议review 一遍 diff。
