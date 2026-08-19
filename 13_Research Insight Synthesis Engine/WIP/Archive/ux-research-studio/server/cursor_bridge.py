from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from .config import STUDIO_DIR, WORKSPACE_ROOT

CURSOR_API_KEY = os.getenv("CURSOR_API_KEY", "").strip()
CURSOR_MODEL = os.getenv("CURSOR_MODEL", "composer-2")
SCRIPT = STUDIO_DIR / "scripts" / "cursor_generate.mjs"


def cursor_available() -> bool:
    return bool(CURSOR_API_KEY) and SCRIPT.is_file()


async def generate_via_cursor(
    system: str,
    user: str,
    project_path: str,
) -> str:
    if not CURSOR_API_KEY:
        raise RuntimeError("未配置 CURSOR_API_KEY")
    if not SCRIPT.is_file():
        raise RuntimeError("缺少 scripts/cursor_generate.mjs，请运行 npm install")

    project_abs = (WORKSPACE_ROOT / project_path).resolve()
    payload = {
        "system": system,
        "user": user,
        "cwd": str(project_abs if project_abs.is_dir() else WORKSPACE_ROOT),
        "model": CURSOR_MODEL,
    }

    proc = await asyncio.create_subprocess_exec(
        "node",
        str(SCRIPT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "CURSOR_API_KEY": CURSOR_API_KEY},
        cwd=str(STUDIO_DIR),
    )
    stdout, stderr = await proc.communicate(json.dumps(payload).encode("utf-8"))
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace") or stdout.decode("utf-8", errors="replace")
        raise RuntimeError(err.strip() or "Cursor SDK 调用失败")

    data = json.loads(stdout.decode("utf-8"))
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("content", "")
