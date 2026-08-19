from __future__ import annotations

from pathlib import Path

from .canvas_templates import CANVAS_TEMPLATES
from .config import GLOBAL_MD, MODULES_DIR, SKILLS_ROOT
from . import interviews as interviews_assets
from .modules_meta import ModuleMeta, module_by_id


def _read(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def build_system_prompt(meta: ModuleMeta) -> str:
    global_rules = _read(GLOBAL_MD)
    module_rules = _read(MODULES_DIR / meta.module_file)
    sub = ""
    if meta.sub_skill:
        skill_path = SKILLS_ROOT.parent / meta.sub_skill / "SKILL.md"
        excerpt = _read(skill_path)
        if excerpt:
            sub = f"\n\n## 子 Skill 参考（{meta.sub_skill}）\n{excerpt[:4000]}"

    return f"""你是企业内部 UX / UXR 研究规划助手，严格遵循团队规范生成「研究规划画布」内容。

## 全局规范（global.md）
{global_rules}

## 当前模块规则（模块 {meta.id}）
{module_rules}
{sub}

## 输出要求
- 使用简体中文，专业简洁。
- 不预设结论；未验证内容写成假设。
- 严格按模块规则中的「输出格式」Markdown 结构输出。
- 模拟素材须标注 SYNTHETIC 或 模拟。
- 只输出模块正文 Markdown，不要解释你如何生成。
- 不要用 ```markdown 代码围栏包裹全文。
- 必须严格使用模块规则中的标题层级与板块结构（便于填入 Web 画布各格子）。
- 列表项使用「1. 」编号格式；标签行使用「**标签**：」中文冒号。
- 每个画布格子都必须填写实质内容，禁止留空或只写占位符。
- 模块 8：市场/组织/技术/用户痛点四项必须全部有字；关键旅程必须写满五个阶段（阶段一～阶段五）；洞察至少两条（洞察一、洞察二）。
- 落盘文件名：{meta.output_file}{"/[人群].md" if meta.output_is_dir else ""}
"""


def build_user_prompt(
    meta: ModuleMeta,
    context: dict,
    prior_modules=None,
) -> str:
    prior = prior_modules or {}
    prior_text = ""
    project_path = context.get("project_path") or ""
    combined = ""

    if meta.id >= 7 and project_path:
        combined = interviews_assets.combined_transcripts(project_path)
        if combined.strip():
            prior_text += f"\n\n### 访谈逐字稿（上传/转写，优先用于模块 7+）\n{combined[:20000]}"

    for mid in sorted(prior.keys()):
        if mid < meta.id and prior.get(mid):
            m = module_by_id(mid)
            title = m.title if m else f"模块{mid}"
            cap = 8000 if mid == 6 else 2500
            body = prior[mid][:cap]
            if mid == 6 and combined.strip() and meta.id >= 7:
                continue
            prior_text += f"\n\n### 已完成：{title}\n{body}"

    return f"""## 启动四问
1. 产品方向或课题：{context.get("topic", "")}
2. 目标用户：{context.get("audience", "")}
3. 项目阶段：{context.get("stage", "")}
4. 本次最需要解决的问题：{context.get("core_question", "")}

## 项目文件夹（相对工作区）
{context.get("project_path", "")}

## 补充说明
{context.get("notes", "无")}

## 项目背景文档摘录（若有）
{context.get("project_docs", "（无）")}

## 前序模块摘要（供连贯性参考）
{prior_text or "（尚无）"}

请生成模块 {meta.id}「{meta.title}」的完整画布内容。{_canvas_template_block(meta.id)}"""


def _canvas_template_block(module_id: int) -> str:
    tpl = CANVAS_TEMPLATES.get(module_id)
    if not tpl:
        return ""
    return f"""

## 必须严格遵循的 Markdown 模板（标题、**标签**：、编号格式勿改；填满每一项，禁止留空）
{tpl.strip()}
"""
