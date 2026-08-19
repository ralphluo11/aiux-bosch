from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .modules_meta import module_by_id
from . import interviews as interview_assets


def _call_llm(system: str, user: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("未配置 OPENAI_API_KEY")
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.25,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code >= 400:
        raise RuntimeError(resp.text[:500])
    return resp.json()["choices"][0]["message"]["content"]


def _preview_value(val: Any, limit: int = 480) -> str:
    if isinstance(val, list):
        text = "；".join(str(x).strip() for x in val if str(x).strip())
    else:
        text = str(val or "").strip()
    if len(text) > limit:
        return text[:limit] + "…"
    return text or "（空）"


def _format_canvas_catalog(catalog: list[dict], current_fields: dict) -> str:
    if not catalog:
        return json.dumps(current_fields, ensure_ascii=False, indent=2)
    lines = []
    for item in catalog:
        fid = item.get("id") or ""
        label = item.get("label") or fid
        section = item.get("section") or ""
        ftype = item.get("type") or "text"
        preview = _preview_value(current_fields.get(fid))
        lines.append(
            f"- 画布名：【{label}】｜内部键（仅 JSON 用这个）：`{fid}`｜板块：{section}｜类型：{ftype}\n"
            f"  当前内容：{preview}"
        )
    return "\n".join(lines)


def _mentioned_field_ids(message: str, catalog: list[dict]) -> list[str]:
    if not message or not catalog:
        return []
    hits: list[str] = []
    msg = message.strip()
    for item in catalog:
        fid = item.get("id") or ""
        label = (item.get("label") or "").strip()
        section = (item.get("section") or "").strip()
        for needle in (label, section):
            if len(needle) >= 2 and needle in msg:
                hits.append(fid)
                break
    return list(dict.fromkeys(hits))


def _normalize_proposed_keys(
    proposed: Optional[dict],
    catalog: list[dict],
    valid_ids: set[str],
) -> dict[str, Any]:
    if not proposed:
        return {}
    if not catalog:
        return {k: v for k, v in proposed.items() if k in valid_ids}

    id_set = set(valid_ids)
    label_to_id = {(item.get("label") or "").strip(): item["id"] for item in catalog if item.get("label")}
    section_to_ids: dict[str, list[str]] = {}
    for item in catalog:
        sec = (item.get("section") or "").strip()
        if sec:
            section_to_ids.setdefault(sec, []).append(item["id"])

    def resolve_key(key: str) -> Optional[str]:
        k = (key or "").strip()
        if not k:
            return None
        if k in id_set:
            return k
        if k in label_to_id:
            return label_to_id[k]
        for label, fid in label_to_id.items():
            if label and (label in k or k in label):
                return fid
        for sec, fids in section_to_ids.items():
            if sec in k or k in sec:
                return fids[0] if len(fids) == 1 else None
        return None

    out: dict[str, Any] = {}
    for raw_key, val in proposed.items():
        fid = resolve_key(str(raw_key))
        if fid and fid in id_set:
            out[fid] = val
    return out


def _build_system(module_id: int) -> str:
    meta = module_by_id(module_id)
    title = meta.title if meta else f"模块{module_id}"
    return f"""你是 UX 研究规划教练，帮用户改「左侧画布」上的文字内容（模块 {module_id}：{title}）。

## 硬性规则
1. **默认必须直接出修改稿**：status 一律用 `awaiting_confirm`（禁止 `discussing`、禁止追问、禁止让用户再确认意图）。
2. `proposed_changes` 的 **key 只能是字段目录里的「内部键」**（如 `signal_market`），**禁止**用中文画布名当 key。
3. 用户说的「市场 / Q1 / 用户痛点 / 洞察二」等，对照「字段目录」里的【画布名】匹配内部键；只改用户点名的字段，未点名且未要求「全模块重写」的字段不要动。
4. `reply` 用用户能看懂的中文（写画布名），**不要**在 reply 里出现内部键、JSON、代码。
5. 在已有内容上按用户要求改写；列表字段输出字符串数组。
6. 若用户要求改某块但目录中找不到对应项，在 reply 末尾用一句话说明「未找到对应板块」，仍尽量改最接近的一块。

## 输出 JSON
{{
  "status": "awaiting_confirm",
  "reply": "2–3 句：说明改了哪些【画布名】+「确认后将写入左侧画布」",
  "questions": [],
  "conflicts": [],
  "gaps": [],
  "proposed_summary": "一句话",
  "proposed_changes": {{ "内部键": "新内容或数组" }}
}}
"""


def chat_turn(
    module_id: int,
    context: dict,
    current_fields: dict,
    prior_modules: dict,
    history: list[dict],
    user_message: str,
    force_confirm: bool = False,
    field_catalog: Optional[list[dict]] = None,
) -> dict[str, Any]:
    meta = module_by_id(module_id)
    if not meta:
        raise ValueError("无效模块 ID")

    catalog = field_catalog or []
    valid_ids = {item.get("id") for item in catalog if item.get("id")}
    if not valid_ids:
        valid_ids = set(current_fields.keys())

    project_path = context.get("project_path") or ""
    combined = ""
    if project_path and module_id >= 7:
        combined = interview_assets.combined_transcripts(project_path)[:8000]

    prior_text = ""
    for mid, body in sorted(prior_modules.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0):
        if int(mid) < module_id and body:
            prior_text += f"\n### 模块{mid}\n{str(body)[:2000]}\n"

    hist_lines = []
    for h in (history or [])[-6:]:
        role = h.get("role", "user")
        content = (h.get("content") or "")[:1000]
        hist_lines.append(f"{role}: {content}")

    mentioned = _mentioned_field_ids(user_message, catalog)
    mentioned_hint = ""
    if mentioned:
        labels = []
        for fid in mentioned:
            for item in catalog:
                if item.get("id") == fid:
                    labels.append(f"【{item.get('label')}】→ `{fid}`")
                    break
        mentioned_hint = "优先只修改以下字段（用户消息已点名）：\n" + "\n".join(f"- {x}" for x in labels)

    canvas_block = _format_canvas_catalog(catalog, current_fields)

    user_block = f"""## 启动四问
课题：{context.get("topic")}
用户：{context.get("audience")}
阶段：{context.get("stage")}
核心问题：{context.get("core_question")}

## 当前模块字段目录（左侧画布，按【画布名】理解；写 JSON 时用内部键）
{canvas_block}

{mentioned_hint}

## 前序模块摘要
{prior_text or "（无）"}

## 访谈素材摘要（若适用）
{combined or "（无）"}

## 对话历史
{chr(10).join(hist_lines) or "（无）"}

## 用户本条消息
{user_message}

## 指令
{"用户已确认应用上一版修改稿。" if force_confirm else "直接输出 awaiting_confirm + proposed_changes，禁止追问。"}
"""

    raw = _call_llm(_build_system(module_id), user_block)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise RuntimeError("模型未返回合法 JSON") from None
        data = json.loads(m.group(0))

    proposed_raw = data.get("proposed_changes")
    if isinstance(proposed_raw, dict):
        proposed = _normalize_proposed_keys(proposed_raw, catalog, valid_ids)
    else:
        proposed = {}

    if mentioned and proposed:
        filtered = {k: v for k, v in proposed.items() if k in mentioned}
        if filtered:
            proposed = filtered

    status = "awaiting_confirm" if proposed else "discussing"
    reply = (data.get("reply") or "").strip()
    if proposed and "确认" not in reply:
        reply = (reply + " 以下是修改后的版本，点「确认修改」将写入左侧画布。").strip()

    if not proposed and mentioned:
        names = []
        for fid in mentioned:
            for item in catalog:
                if item.get("id") == fid:
                    names.append(item.get("label") or fid)
                    break
        reply = (
            reply
            or f"未能生成「{'、'.join(names)}」的修改稿，请补充希望改成什么样（仍无需多轮确认）。"
        )

    return {
        "status": status,
        "reply": reply,
        "questions": [],
        "conflicts": data.get("conflicts") or [],
        "gaps": data.get("gaps") or [],
        "proposed_summary": data.get("proposed_summary") or "",
        "proposed_changes": proposed or None,
        "target_fields": mentioned,
    }
