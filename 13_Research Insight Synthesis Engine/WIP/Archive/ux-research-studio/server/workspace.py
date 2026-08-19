from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import VALIDATE_SCRIPT, WORKSPACE_ROOT
from .modules_meta import ModuleMeta


def safe_project_path(relative: str) -> Path:
    rel = relative.strip().strip("/")
    if not rel or ".." in rel.split("/"):
        raise ValueError("无效的项目路径")
    root = (WORKSPACE_ROOT / rel).resolve()
    if not str(root).startswith(str(WORKSPACE_ROOT)):
        raise ValueError("路径超出工作区")
    return root


def research_dir(project_relative: str) -> Path:
    project = safe_project_path(project_relative)
    research = project / "WIP" / "Research"
    research.mkdir(parents=True, exist_ok=True)
    return research


def project_docs_dir(project_relative: str) -> Path | None:
    """PRD/背景目录：优先项目根 00_Project_Docs，兼容 WIP/00_Project_Docs。"""
    project = safe_project_path(project_relative)
    root_docs = project / "00_Project_Docs"
    if root_docs.is_dir():
        return root_docs
    legacy = project / "WIP" / "00_Project_Docs"
    if legacy.is_dir():
        return legacy
    return None


def list_projects(max_depth: int = 2) -> list[dict]:
    """扫描工作区内含 WIP 的项目文件夹。"""
    found: list[dict] = []

    def add(rel: str, has_research: bool, has_docs: bool) -> None:
        found.append(
            {
                "path": rel,
                "has_research": has_research,
                "has_docs": has_docs,
            }
        )

    for child in sorted(WORKSPACE_ROOT.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        wip = child / "WIP"
        if wip.is_dir():
            rel = child.relative_to(WORKSPACE_ROOT).as_posix()
            project = child
            has_docs = (project / "00_Project_Docs").is_dir() or (
                wip / "00_Project_Docs"
            ).is_dir()
            add(rel, (wip / "Research").is_dir(), has_docs)
            continue
        for sub in sorted(child.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            wip2 = sub / "WIP"
            if wip2.is_dir():
                rel = sub.relative_to(WORKSPACE_ROOT).as_posix()
                has_docs = (sub / "00_Project_Docs").is_dir() or (
                    wip2 / "00_Project_Docs"
                ).is_dir()
                add(rel, (wip2 / "Research").is_dir(), has_docs)

    return found


def read_project_context(project_relative: str, max_chars: int = 12000) -> str:
    docs = project_docs_dir(project_relative)
    if docs is None:
        return ""
    parts: list[str] = []
    md_paths: list[Path] = []
    prd_dir = docs / "01_PRD"
    if prd_dir.is_dir():
        md_paths.extend(sorted(prd_dir.glob("*.md")))
    md_paths.extend(sorted(docs.glob("*.md")))
    for path in md_paths[:5]:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(docs).as_posix()
        parts.append(f"### {rel}\n{text[:3000]}")
    body = "\n\n".join(parts)
    return body[:max_chars]


def list_research_files(project_relative: str) -> list[dict]:
    research = research_dir(project_relative)
    items: list[dict] = []
    for path in sorted(research.rglob("*.md")):
        rel = path.relative_to(research).as_posix()
        items.append({"name": rel, "size": path.stat().st_size})
    return items


def read_research_file(project_relative: str, filename: str) -> str:
    research = research_dir(project_relative)
    target = (research / filename).resolve()
    if not str(target).startswith(str(research.resolve())):
        raise ValueError("无效文件路径")
    if not target.is_file():
        raise FileNotFoundError(filename)
    return target.read_text(encoding="utf-8")


def write_module_output(
    project_relative: str,
    meta: ModuleMeta,
    content: str,
    extra_filename=None,
) -> str:
    research = research_dir(project_relative)
    if meta.output_is_dir:
        folder = research / meta.output_file
        folder.mkdir(parents=True, exist_ok=True)
        name = extra_filename or "segment_01.md"
        if not name.endswith(".md"):
            name += ".md"
        path = folder / name
    else:
        path = research / meta.output_file
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path.relative_to(WORKSPACE_ROOT).as_posix()


PROGRESS_FILE = ".uxrs-progress.json"


def default_progress() -> dict:
    return {
        "completed": [],
        "current_module": 1,
        "modules": {},
        "updated_at": None,
    }


def read_progress(project_relative: str) -> dict:
    research = research_dir(project_relative)
    path = research / PROGRESS_FILE
    if not path.is_file():
        return default_progress()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        base = default_progress()
        base.update(data)
        return base
    except (json.JSONDecodeError, OSError):
        return default_progress()


def write_progress(project_relative: str, data: dict) -> dict:
    research = research_dir(project_relative)
    payload = {**default_progress(), **data}
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = research / PROGRESS_FILE
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def progress_summary(project_relative: str) -> dict:
    prog = read_progress(project_relative)
    completed = sorted(prog.get("completed") or [])
    current = prog.get("current_module") or (completed[-1] + 1 if completed else 1)
    if current > 9:
        current = 9
    return {
        "completed": completed,
        "current_module": current,
        "completed_count": len(completed),
        "total": 9,
        "updated_at": prog.get("updated_at"),
        "percent": round(len(completed) / 9 * 100),
    }


def run_validation(project_relative: str) -> dict:
    research = research_dir(project_relative)
    if not VALIDATE_SCRIPT.is_file():
        return {"ok": False, "stdout": "", "stderr": "校验脚本不存在"}
    proc = subprocess.run(
        ["python3", str(VALIDATE_SCRIPT), str(research)],
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }
