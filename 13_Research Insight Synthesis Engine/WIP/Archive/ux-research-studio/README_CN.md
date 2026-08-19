# UX Research Studio

将 `.cursor/skills/ux-research-*` 九模块研究规划流程搬到**局域网 Web 界面**：逐步生成、预览 Markdown、保存到各项目的 `WIP/Research/`。

## 功能

- 对齐 Cursor 编排 Skill：`ux-research-planning` 模块 1–9
- 启动四问 + 项目背景（自动读取 `00_Project_Docs/` 摘要；兼容旧路径 `WIP/00_Project_Docs/`）
- OpenAI 兼容 API 流式生成
- 一键保存到标准文件名（与 `validate_research_outputs.py` 一致）
- **局域网访问**：服务绑定 `0.0.0.0`，同事用你机器的 IP 打开

## 如何申请 API（网页一键 AI 生成）

### 方案 A：OpenAI 兼容 API（推荐，配置最简单）

适用于：OpenAI 官方、Azure OpenAI、国内合规中转（DeepSeek、通义、Moonshot 等 **OpenAI 格式**接口）。

1. **注册并充值**（任选其一）  
   - 国际：[platform.openai.com](https://platform.openai.com) → API keys → Create key  
   - 国内常见：各厂商控制台创建「API Key」，并记下 **Base URL**（与 OpenAI 不同）

2. **写入** `ux-research-studio/.env`：
   ```env
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-xxxxxxxx
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL=gpt-4o
   ```
   若用国内中转，把 `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 改成厂商文档里的值。

3. **重启服务**：`./start.sh`  
4. 网页引擎选 **「OpenAI 兼容 API」** → **AI 生成**

> 公司环境：优先问 IT 是否已有 **Azure OpenAI** 或统一网关，用企业 Key，勿用个人账号处理客户数据。

---

### 方案 B：Cursor Agent SDK API

适用于：已有 Cursor 订阅、希望生成逻辑与 Cursor Agent 一致。

1. 登录 [cursor.com/dashboard](https://cursor.com/dashboard)  
2. 进入 **Integrations**（或团队 **Settings → Service Accounts**）  
3. **Create API Key**，复制（只显示一次）  
4. 在项目目录执行：
   ```bash
   cd ux-research-studio
   npm install
   ```
5. **`.env`**：
   ```env
   AI_PROVIDER=cursor
   CURSOR_API_KEY=你的Key
   CURSOR_MODEL=composer-2
   ```
6. 重启 `./start.sh`，网页选 **「Cursor Agent SDK」**

文档：[Cursor SDK TypeScript](https://cursor.com/docs/sdk/typescript)

---

### 配置完成后怎么确认成功？

- 打开 http://127.0.0.1:8765 ，顶栏应显示 **OpenAI✓** 或 **Cursor✓**  
- 选项目 + 模块 → **AI 生成**，右侧应有流式文字（OpenAI）或一次性结果（Cursor）

---

## 快速启动

```bash
cd ux-research-studio
chmod +x start.sh
./start.sh
```

首次运行会创建 `.venv` 和 `.env`。编辑 `.env`：

```env
OPENAI_API_KEY=sk-...
# 可选：Azure / 国内中转
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 可选：简单访问控制（同事 URL 加 ?token=xxx）
STUDIO_ACCESS_TOKEN=your-team-secret
```

终端会打印局域网地址，例如：

```
http://192.168.x.x:8765
```

## 使用流程

1. 选择或输入**项目文件夹相对路径**（相对 `003_Project Files` 根目录）
2. 填写启动四问
3. 左侧按顺序点模块 1→9 → **AI 生成** → 审阅 → **保存到 WIP/Research**
4. 完成后点 **校验 Research 产物**

## 架构说明

| 组件 | 说明 |
|------|------|
| `server/` | FastAPI：读 `.cursor` 模块规则作 Prompt，调 LLM，写文件 |
| `static/` | 前端向导（无构建步骤） |
| `.cursor/skills/` | **单一事实来源**；改模块格式仍在这里维护 |

本 Studio **不替代** Cursor Agent 的 Hooks / 子 Agent 委派；适合团队内「无 Cursor 也能走流程填画布」的场景。复杂桌面扫描、长逐字稿分析仍建议在 Cursor 中委派子 Agent。

## 安全提示

- 仅在**受信任的内网**使用；默认需注册/登录
- 设置 `STUDIO_ACCESS_TOKEN` 可降低误连风险
- API Key 只保存在**运行服务的那台电脑**的 `.env`，勿提交到 Git
- 遵守 `global.md`：勿将未脱敏真实访谈提交到外部 API

## 故障排除

| 现象 | 处理 |
|------|------|
| 同事打不开 | 检查 macOS 防火墙；确认 `HOST=0.0.0.0` |
| AI 生成 503 | 配置 `OPENAI_API_KEY` 并重启 |
| 项目列表为空 | 确认项目下有 `WIP/` 目录 |
| 校验 MISSING | 逐步模式未完成全部模块属正常 |

## 怎么看？（登录 / 预览文件 / Cursor SDK）

### 1. 打开页面（一键启动）

在 **macOS** 上双击以下任一文件即可（会自动打开浏览器并显示局域网分享地址）：

- `003_Project Files/启动 UX Research Studio.command`（项目根目录，推荐）
- `ux-research-studio/启动 UX Research Studio.command`

首次双击若提示「无法打开」，请在 **系统设置 → 隐私与安全性** 中允许，或右键该文件 → **打开**。

也可用终端：

```bash
cd ux-research-studio
./start.sh
```

终端会打印地址，例如：

- 本机：`http://127.0.0.1:8765`
- 局域网：`http://192.168.x.x:8765`（把这条发给同事）

浏览器打开上述地址即可。

### 2. 注册与登录（默认开启）

首次打开页面会弹出 **注册 / 登录**：

1. **第一个同事**：在「注册」页创建用户名与密码（账户保存在 `ux-research-studio/data/users.json`，已加入 `.gitignore`）
2. **之后同事**：在「登录」页输入账号密码
3. 右上角显示当前用户，可 **退出** 后切换账号

可选 `.env`：

```env
SESSION_SECRET=随机一串字符
STUDIO_REQUIRE_AUTH=false   # 仅本地调试时可关闭登录
```

若同时设置了 `STUDIO_ACCESS_TOKEN`，访问链接需带令牌，例如：

`http://192.168.x.x:8765?token=team-secret`

### 3. 真实访谈素材上传

侧栏 **「访谈素材上传」**（需先选项目）：

| 类型 | 处理方式 |
|------|----------|
| `.txt` / `.md` 等文字稿 | 存入 `WIP/Research/06_interviews/uploads/text/`，并生成 `transcripts/*.md` |
| `.mp3` / `.mp4` 等音视频 | 存入 `uploads/media/`，可自动或手动 **转写** 为 `transcripts/*.md` |

- **模块 6 画布**：仅保存 **参考模拟**（SYNTHETIC）到 `06_interviews/reference/`，用于设计访纲，**不是**真实访谈。
- **模块 7+ AI 生成**：优先读取 `06_interviews/transcripts/` 下全部逐字稿（也兼容旧目录 `06_mock-transcripts/`）。

音视频转写需 **OpenAI Whisper**（与 DeepSeek 对话 Key 分开）：

```env
TRANSCRIBE_API_KEY=sk-...   # OpenAI Key
TRANSCRIBE_BASE_URL=https://api.openai.com/v1
```

视频转写需本机安装 **ffmpeg**：`brew install ffmpeg`

### 4. 项目修改记录（每人留痕）

每次 **保存、AI 生成、标记完成、更新进度、手动载入磁盘** 等操作，会自动写入当前项目的：

- `[项目]/WIP/Research/_uxrs_logs/activity.jsonl`（机器可读）
- `[项目]/WIP/Research/_uxrs_logs/ACTIVITY.md`（人类可读）

侧栏 **「本项目修改记录」** 可查看最近操作；完整历史请打开上述文件。

### 5. 研究对话（审慎改稿）

右下角 **圆形对话按钮**（可拖动位置）点开 **「研究对话」** 弹窗：

1. 描述你想改什么  
2. 助手会指出与前序模块的冲突、遗漏，并追问  
3. 给出「待确认修改」摘要后，点 **「确认应用到画布」**  
4. 满意后点 **「保存」** 写入 `WIP/Research/`

### 6. 导出汇报 PPT

侧栏 **「导出汇报 PPT」**：读取已保存的各模块 Markdown，填入假模版（`templates/UX_Research_Report_TEMPLATE.pptx`），输出到：

`[项目]/WIP/Research/exports/UX_Research_Report_*.pptx`

首次部署若缺模版，在 `ux-research-studio` 执行：

```bash
.venv/bin/pip install python-pptx
.venv/bin/python3 scripts/build_ppt_template.py
```

### 7. 预览已生成的 Research 文件

1. 左侧 **项目** 下拉框选一个项目（或手动输入项目路径）
2. 看 **「已生成文件」** 列表（`WIP/Research/` 下所有 `.md`）
3. **点击文件名** → 中间编辑区 + 右侧 **预览** 会显示该文件内容
4. 改完后可再点 **保存到 WIP/Research**（需先选中对应模块）

也可在 Finder 中直接打开磁盘路径查看，例如：

`[项目文件夹]/WIP/Research/01_research-objectives.md`

### 4. Cursor Agent SDK（可选，替代 OpenAI Key）

```bash
cd ux-research-studio
npm install
```

在 `.env` 中：

```env
AI_PROVIDER=cursor
CURSOR_API_KEY=你的_Cursor_API_Key
```

重启服务后，工具栏 **引擎** 选 **Cursor Agent SDK**，再点 **AI 生成**。  
（Cursor 模式为一次性返回，无流式；会在本机项目目录上跑 Agent。）

API Key 获取：Cursor 设置 → API，或见 [Cursor SDK 文档](https://cursor.com/docs/api/sdk/typescript)。

---

## 手动启动

```bash
cd ux-research-studio
source .venv/bin/activate
export PYTHONPATH="$(pwd)"
python3 -m server.main
```
