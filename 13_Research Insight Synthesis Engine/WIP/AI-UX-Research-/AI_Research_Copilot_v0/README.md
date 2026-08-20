# AI Research Copilot — v0.5 Multi-Interview Agent / v0.6 Experience Demo

运行环境支持 Python 3.9 及以上（包括 macOS Command Line Tools 自带的 Python 3.9）。

## v0.6 新增：多格式研究材料导入

Agent 工作台支持批量导入：

- 文本：`.txt`、`.md`、`.csv`、`.json`；
- Word：`.docx`，按段落提取文字；
- PowerPoint：`.pptx`，按 Slide 提取文字；
- Excel：`.xlsx`，按工作表和行提取单元格内容。
- PDF：`.pdf`，按页提取并保留 `[PDF page N]`；扫描页在 Live AI 可用时执行 OCR；
- 图片：`.png`、`.jpg/.jpeg`、`.webp`、`.gif`，通过配置的视觉 Endpoint 提取可见文字；
- 音频/视频：`.mp3`、`.mp4`、`.mpeg`、`.mpga`、`.m4a`、`.wav`、`.webm`，通过转写 Endpoint 生成 speaker + 时间码分段。

Office 文件在本机服务端解析，提取结果保留 `[DOCX paragraph]`、`[PPTX slide]`、
`[XLSX sheet ... row ...]`、`[PDF page]`、`[IMAGE region]` 和 `[MEDIA start-end speaker]`
来源标记，再进入 Evidence → Finding → Insight 链路。图片、扫描 PDF、音频和视频需要配置
Live AI Key 与兼容的视觉/转写 Endpoint；缺失时明确失败，不保存不可追溯的空结果。旧格式
`.doc`、`.ppt`、`.xls` 不在本次范围。单文件上限 25 MB，提取文字上限 200,000 字符。超过 45,000 字符的
单个 Source 会在分析时自动拆分为带 `__part_01` 标记的片段，不会静默截断；当前单次分析
分析采用分层流程：逐片段提取并逐字验证 Evidence，再基于已验证 Evidence 进行跨来源
Finding / Insight 综合。项目不再受 200,000 字符总量限制；当前同步 POC 单次最多处理
40 个内部片段和 300 条 Evidence Candidate，后续应迁移为可恢复的异步任务队列。

## v0.5 新增：项目制、多访谈与持久化

`/agent.html` 现在支持：

- 创建 Research Project；
- 保存 Research Goal、Research Questions 与 Target Users；
- 批量导入 `.txt`、`.md`、`.csv`、`.json`；
- 每个文件形成一个 Participant Transcript；
- 将多个 Transcript 一次交给 Research Agent；
- 保存每次 Agent 分析结果；
- 关闭浏览器和服务后重新打开项目；
- 查看最近一次 Evidence、Findings、Insights、Gaps 与 Limitations。

数据默认存储于 `data/research_agent.db`，该数据库已加入 `.gitignore`。由于本项目位于 OneDrive，同步客户端仍可能同步数据库，因此只能放脱敏材料。需要本机独立路径时，可设置 `AI_UX_DATABASE_PATH`。数据不会自动进入正式 Knowledge 或跨项目 Memory。

当前 v0.5 为低投入验证版：多个 Transcript 在一次结构化 Agent 调用中完成综合。正式 v0.6 应拆成“单份 Evidence 提取 → 跨访谈 Finding / Insight 综合”两阶段工作流，避免长材料遗漏并降低回归评测成本。

## v0.4 新增：真实 Research Synthesis Agent

打开 `http://127.0.0.1:8000/agent.html` 可进入最小 Agent 工作台。它接收脱敏访谈文本，并通过 Responses-compatible Endpoint 生成结构化：

- Evidence（逐字引用 + Participant ID）；
- Findings（必须引用 Evidence）；
- Insights（必须引用 Findings）；
- Gaps 与 Limitations；
- `ai_draft` 状态，明确要求研究员审核。

服务端会再次验证 quote 是否逐字存在于对应 transcript，防止模型生成伪造引语。请求设置 `store: false`；但真实 Bosch 数据仍只能发送到经过批准的企业 Endpoint。

如果未配置 API Key，Agent 工作台进入 `offline_preview`：只提取原文验证证据链，不生成 Findings 或 Insights，也不会伪装成真实 AI 分析。

API 兼容模式默认是 `AI_UX_LLM_API_STYLE=auto`：先尝试 `/responses`，明确返回 404 时自动切换到 `/chat/completions`。也可以显式设置 `responses` 或 `chat_completions`。

当前仓库包含两层：

- **v0.3 可运行核心**：动态追问、Knowledge Card、Guardrail、Human Review、
  Evaluation 与 Offline Rules，后端 Session API 仍在但当前 Research Studio 前端未接入；
- **Research Studio**（`static/wizard.js`，`/` 主入口）：项目制真实工作台，从
  Project Brief 到问卷生成、材料上传、Evidence→Theme→Synthesis→Judge 结构化分析、
  人工审核与交付，全部走真实项目数据和真实 API，未配置 Key 时自动降级为
  Offline Preview，不使用 mock 数据。

这不是语音壳，而是第一版可验证的 **Interview Intelligence**：

```text
Research Brief + Guide
          +
Approved Knowledge Cards
          +
Participant Answer
          ↓
Hybrid Retrieval → LLM Probe Planner → Guardrail
          ↓
Researcher Accept / Edit / Reject
          ↓
Evaluation Record + Bad Case
```

## 这一版能验证什么

- 同一个主问题下，模型会根据不同回答生成不同追问；
- 只有检索命中的 `approved` Knowledge Card 可以作为工程/产品依据；
- LLM 必须结构化返回：追问、信号、信息缺口、候选假设、Card ID 和简短理由；
- 未检索到的 Card 引用、诱导问题、双重问题和内部信息会被 Guardrail 拦截；
- 模型不可用或输出被拦截时自动回退到确定性追问，访谈不会中断；
- Researcher Live View 可以接受、修改或拒绝下一问；
- 每轮可按 Relevance / Depth / Neutrality / Grounding / Non-redundancy 评分；
- 访谈结束可下载 Evaluation JSON，直接形成 Golden Set / Bad Case 的原始输入。

## Mac 最快运行

### 真实 LLM 模式

推荐：把 `.env.example` 复制成 `.env` 填好 Key，改一次以后每次直接运行即可，不用重新 `export`
（见下方"配置"一节）。也可以继续用环境变量的老方式，在 VS Code 打开 `ai-research-copilot`，
终端运行：

```bash
export OPENAI_API_KEY="你的 API key"
export AI_UX_LLM_MODEL="gpt-5.6-terra"
PYTHONPATH=src python3 -m ai_ux_core.web
```

然后打开：

```text
http://127.0.0.1:8000/
```

页面右上角显示 `LLM Live`，且 Agent 工作台显示 `Live AI`，才代表真实模型已接入；否则显示
`Demo mode · API pending`。ChatGPT 订阅与 API key 是两套独立凭证；不要把
key 写进代码或上传 GitHub。

也可以双击 `START_MAC.command`：它会在本机临时询问 key，然后启动调试页面。

### 无 Key 的离线回退

```bash
PYTHONPATH=src python3 -m ai_ux_core.web
```

该模式可以体验所有 Demo 页面、状态推进和本地数据，也可以验证原有状态机与
安全回退，但不代表真实 AI、ASR 或企业数据能力。

## Demo walkthrough

建议按以下顺序演示：

1. `Overview` 查看研究项目与待办；
2. 打开 `Studies` → `Research setup`，编辑 Brief；
3. 生成并发布 `Interview guide`；
4. 复制 Participant Link，完成 consent、device check 与三轮访谈；
5. 回到 `Live interview`，接受、编辑或拒绝 AI Candidate Probe；
6. 在 `Evidence & insights` 审核 Evidence，并查看完整 Traceability；
7. 打开 `Research report`，直接编辑并检查引用；
8. 查看 `Knowledge` 与 `Evaluations` 的 API / Golden Set 占位。

Demo 状态保存在浏览器 `localStorage`，刷新不会丢失；清除站点数据可恢复初始场景。

## 推荐测试

主问题出现后，分别开始新会话输入：

```text
后面的菜经常冻住，但是门边饮料不够冷，而且塞满东西时更明显。
```

```text
每次做完饭会频繁开门，关上以后很久才重新变冷，门边还会有水珠。
```

```text
就是不太方便，但我暂时说不清具体哪里。
```

在 Researcher Live View 中检查：

1. 三次追问是否不同；
2. 是否只引用匹配的 Card；
3. 问题是否中性且只补一个信息缺口；
4. 修改追问后 Participant 当前问题是否同步变化；
5. 最终 Evaluation JSON 是否保留原始问题、修改版和评分。

## 测试

不需要 `pip install`，仍然只用 Python 标准库：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 配置

把 `.env.example` 复制成项目根目录下的 `.env`（已在 `.gitignore` 里，不会被提交），填好后
Mac/Windows、每次新开终端都会自动生效，不用每次手动 `export`。真实环境变量（`export` /
`$env:` / CI secret）优先级永远高于 `.env` 里的值。加载逻辑集中在
[`src/ai_ux_core/config.py`](src/ai_ux_core/config.py) 的 `load_llm_settings()`，
`llm.py`、`research_agent.py`、`document_parser.py` 三处都从这一个函数取值，不再各自
读一遍环境变量。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `OPENAI_API_KEY` / `AI_UX_LLM_API_KEY` | 无 | 模型凭证 |
| `AI_UX_LLM_MODEL` | `gpt-5.6-terra` | 模型 |
| `AI_UX_LLM_BASE_URL` | `https://api.openai.com/v1` | Responses API 地址 |
| `AI_UX_LLM_TIMEOUT_SECONDS` | Interview Probe 20 秒 / 材料分析 Agent 60 秒 | 单次生成超时；两条链路默认值不同，是故意的（前者是受访者在等下一题，后者是后台批处理），设置该变量会同时覆盖两处 |
| `AI_UX_LLM_API_STYLE` | `auto` | `responses` / `chat_completions` / 自动 404 回退 |
| `AI_UX_VISION_MODEL` | 回退到 `AI_UX_LLM_MODEL` | 图片 OCR 用的模型 |
| `AI_UX_TRANSCRIBE_MODEL` | `gpt-4o-transcribe-diarize` | 音视频转写模型 |
| `AI_UX_AUDIO_BASE_URL` | 回退到 `AI_UX_LLM_BASE_URL` | 音视频转写 Endpoint |

`ProbeGenerator` 是独立接口。接 Bosch approved LLM 时，替换 adapter 或配置
兼容的 Responses endpoint 即可；Interview Orchestrator、Knowledge Cards、
Human Review 和 Evaluation schema 不需要改。

## API

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/api/health` | LLM / Offline 运行状态 |
| `POST` | `/api/agent/analyze` | 真实 Research Synthesis Agent：Transcript → Evidence → Finding → Insight |
| `POST` | `/api/projects/{id}/documents` | 上传并解析文档、PDF、图片及带时间码的音视频研究材料 |
| `POST` | `/api/projects/{id}/questionnaire` | 根据当前 Project Brief 调用 AI 生成并保存结构化问卷 |
| `GET` | `/api/study` | Research Brief 与 Guide |
| `POST` | `/api/sessions` | 创建访谈 |
| `GET` | `/api/sessions/{id}` | 当前问题与逐轮记录 |
| `POST` | `/api/sessions/{id}/answers` | 提交 final transcript，生成下一问 |
| `POST` | `/api/sessions/{id}/reviews` | 接受、修改或拒绝追问并评分 |
| `GET` | `/api/sessions/{id}/evaluation` | 导出可评估记录 |

## API integration points

`static/wizard.js` 直接调用上面的 Project 系列 API，没有 mock adapter 这一层——
未配置 Key 时后端自动返回 `offline_preview` 结果，前端原样展示，不在前端伪造数据。

Questionnaire Builder 已使用真实项目 API：在配置经批准的 AI Endpoint 时显示
`Live AI`、模型名与 `ai_draft`；没有 Key 时只生成明确标记的 `Offline preview`，
不会把静态问题表述为 AI 结果。每次生成保存到 SQLite，并随项目重新加载。

## 仍未做（真实能力）

- Streaming ASR 和浏览器麦克风；
- 真正分离的 Participant / Researcher 双端实时同步；
- 数据库持久化；
- 企业知识 Connector 和权限。
- 真实 Guide / Evidence / Insight / Report 模型调用；
- 生产级身份、审计、保留与删除；
- PPT / Word 文件生成。

推荐接入顺序：Main LLM → Live ASR → Persistence → Evidence / Insight →
Embedding / Connector。每个能力保持独立 adapter。
