from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .workspace import research_dir

LOG_DIR_NAME = "_uxrs_logs"
JSONL_NAME = "activity.jsonl"
MD_NAME = "ACTIVITY.md"
MAX_MD_LINES = 300


def _log_dir(project_relative: str) -> Path:
    return research_dir(project_relative) / LOG_DIR_NAME


def _iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def append(
    project_relative: str,
    username: str,
    action: str,
    detail: str = "",
    module_id: Optional[int] = None,
    module_title: str = "",
    file_path: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """写入项目 WIP/Research/_uxrs_logs/，返回相对 Research 的日志路径。"""
    folder = _log_dir(project_relative)
    folder.mkdir(parents=True, exist_ok=True)

    entry = {
        "time": _iso_now(),
        "user": username,
        "action": action,
        "detail": detail,
        "module_id": module_id,
        "module_title": module_title,
        "file": file_path,
    }
    if extra:
        entry.update(extra)

    jsonl_path = folder / JSONL_NAME
    line = json.dumps(entry, ensure_ascii=False)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    _append_md(folder / MD_NAME, entry)
    return f"WIP/Research/{LOG_DIR_NAME}/{JSONL_NAME}"


def _append_md(md_path: Path, entry: dict) -> None:
    mod = ""
    if entry.get("module_id"):
        mod = f" · 模块{entry['module_id']} {entry.get('module_title') or ''}"
    file_part = f" · `{entry['file']}`" if entry.get("file") else ""
    line = (
        f"- **{entry['time']}** · **{entry['user']}** · "
        f"`{entry['action']}`{mod}{file_part}"
    )
    if entry.get("detail"):
        line += f" — {entry['detail']}"
    line += "\n"

    header = (
        "# UX Research Studio · 修改记录\n\n"
        "> 本文件由系统自动维护，记录谁在何时修改了哪些模块。\n\n"
    )
    if md_path.is_file():
        content = md_path.read_text(encoding="utf-8")
        if not content.startswith("# UX Research Studio"):
            content = header + content
        content = content.rstrip() + "\n" + line
        lines = content.splitlines()
        if len(lines) > MAX_MD_LINES:
            head = lines[:12]
            tail = lines[-(MAX_MD_LINES - 12) :]
            content = "\n".join(head + ["", "…（较早记录已省略）", ""] + tail) + "\n"
        md_path.write_text(content, encoding="utf-8")
    else:
        md_path.write_text(header + line, encoding="utf-8")


def list_entries(project_relative: str, limit: int = 50) -> list[dict]:
    jsonl_path = _log_dir(project_relative) / JSONL_NAME
    if not jsonl_path.is_file():
        return []
    lines = jsonl_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    items: list[dict] = []
    for line in lines[-limit:]:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(items))
