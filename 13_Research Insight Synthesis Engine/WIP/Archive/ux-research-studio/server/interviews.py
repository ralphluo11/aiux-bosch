from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile

from .workspace import research_dir, safe_project_path

INTERVIEWS_ROOT = "06_interviews"
TEXT_EXT = {".txt", ".md", ".markdown", ".vtt", ".srt"}
MEDIA_EXT = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".mov", ".aac", ".ogg", ".flac", ".mkv"}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200MB per file


def interviews_base(project_relative: str) -> Path:
    base = research_dir(project_relative) / INTERVIEWS_ROOT
    for sub in ("reference", "uploads/text", "uploads/media", "transcripts"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    readme = base / "README.md"
    if not readme.is_file():
        readme.write_text(
            """# 访谈素材目录

- `reference/` — 模拟逐字稿（SYNTHETIC），仅作访纲与问题设计参考
- `uploads/text/` — 上传的文字稿原文件
- `uploads/media/` — 上传的音频/视频原文件
- `transcripts/` — 可供模块 7+ 读取的 Markdown 逐字稿（文字上传或转写生成）

旧目录 `06_mock-transcripts/` 仍会被读取，建议逐步迁移到此目录。
""",
            encoding="utf-8",
        )
    return base


def manifest_path(project_relative: str) -> Path:
    return interviews_base(project_relative) / "manifest.json"


def _load_manifest(project_relative: str) -> dict:
    path = manifest_path(project_relative)
    if not path.is_file():
        return {"files": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"files": []}


def _save_manifest(project_relative: str, data: dict) -> None:
    path = manifest_path(project_relative)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _safe_name(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w\u4e00-\u9fff.\-]+", "_", base)
    return base or "upload"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def list_assets(project_relative: str) -> dict:
    base = interviews_base(project_relative)
    manifest = _load_manifest(project_relative)
    transcripts = []
    tdir = base / "transcripts"
    for p in sorted(tdir.glob("*.md")):
        transcripts.append(
            {
                "name": p.name,
                "path": f"WIP/Research/{INTERVIEWS_ROOT}/transcripts/{p.name}",
                "size": p.stat().st_size,
                "updated": _now(),
            }
        )
    return {
        "root": f"WIP/Research/{INTERVIEWS_ROOT}",
        "manifest": manifest.get("files", []),
        "transcripts": transcripts,
        "reference_count": len(list((base / "reference").glob("*.md"))),
    }


async def upload_files(
    project_relative: str,
    files: list[UploadFile],
    username: str,
    auto_transcribe: bool = True,
) -> dict:
    if not files:
        raise HTTPException(400, "请选择文件")
    base = interviews_base(project_relative)
    manifest = _load_manifest(project_relative)
    results: list[dict] = []

    for uf in files:
        raw_name = _safe_name(uf.filename or "upload")
        ext = Path(raw_name).suffix.lower()
        data = await uf.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, f"{raw_name} 超过 200MB 限制")
        if ext not in TEXT_EXT | MEDIA_EXT:
            raise HTTPException(
                400,
                f"不支持的类型 {ext}，文字支持 {', '.join(sorted(TEXT_EXT))}；媒体支持常见音视频",
            )

        file_id = uuid.uuid4().hex[:12]
        if ext in TEXT_EXT:
            dest = base / "uploads/text" / raw_name
            dest.write_bytes(data)
            text = _decode_text(data)
            tname = f"{Path(raw_name).stem}.md"
            tpath = base / "transcripts" / tname
            tpath.write_text(
                _transcript_header(raw_name, username, "text_upload")
                + text.strip()
                + "\n",
                encoding="utf-8",
            )
            entry = {
                "id": file_id,
                "original_name": raw_name,
                "kind": "text",
                "status": "ready",
                "upload_path": str(dest.relative_to(base)),
                "transcript_path": str(tpath.relative_to(base)),
                "uploaded_by": username,
                "uploaded_at": _now(),
            }
        else:
            dest = base / "uploads/media" / raw_name
            dest.write_bytes(data)
            entry = {
                "id": file_id,
                "original_name": raw_name,
                "kind": "media",
                "status": "pending",
                "upload_path": str(dest.relative_to(base)),
                "transcript_path": None,
                "uploaded_by": username,
                "uploaded_at": _now(),
            }
            if auto_transcribe:
                try:
                    from . import transcribe_service

                    tpath = transcribe_service.transcribe_media_file(dest, base, raw_name, username)
                    entry["status"] = "ready"
                    entry["transcript_path"] = str(tpath.relative_to(base))
                except Exception as e:
                    entry["status"] = "error"
                    entry["error"] = str(e)[:500]

        manifest.setdefault("files", []).append(entry)
        results.append(entry)

    _save_manifest(project_relative, manifest)
    return {"uploaded": results, "assets": list_assets(project_relative)}


def transcribe_asset(project_relative: str, file_id: str, username: str) -> dict:
    base = interviews_base(project_relative)
    manifest = _load_manifest(project_relative)
    entry = next((f for f in manifest.get("files", []) if f.get("id") == file_id), None)
    if not entry:
        raise HTTPException(404, "找不到该文件记录")
    if entry.get("kind") != "media":
        raise HTTPException(400, "仅音视频文件需要转写")
    src = base / entry["upload_path"]
    if not src.is_file():
        raise HTTPException(404, "原文件已丢失，请重新上传")

    from . import transcribe_service

    try:
        tpath = transcribe_service.transcribe_media_file(
            src, base, entry.get("original_name", src.name), username
        )
        entry["status"] = "ready"
        entry["transcript_path"] = str(tpath.relative_to(base))
        entry.pop("error", None)
        entry["transcribed_at"] = _now()
        entry["transcribed_by"] = username
    except Exception as e:
        entry["status"] = "error"
        entry["error"] = str(e)[:500]
        _save_manifest(project_relative, manifest)
        raise HTTPException(503, str(e)) from e

    _save_manifest(project_relative, manifest)
    return {"file": entry, "assets": list_assets(project_relative)}


def delete_asset(project_relative: str, file_id: str) -> dict:
    base = interviews_base(project_relative)
    manifest = _load_manifest(project_relative)
    files = manifest.get("files", [])
    entry = next((f for f in files if f.get("id") == file_id), None)
    if not entry:
        raise HTTPException(404, "找不到该文件记录")

    for key in ("upload_path", "transcript_path"):
        rel = entry.get(key)
        if rel:
            p = base / rel
            if p.is_file():
                p.unlink()
    manifest["files"] = [f for f in files if f.get("id") != file_id]
    _save_manifest(project_relative, manifest)
    return list_assets(project_relative)


def _decode_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _transcript_header(source: str, user: str, method: str) -> str:
    return (
        f"---\n"
        f"source: {source}\n"
        f"uploaded_by: {user}\n"
        f"method: {method}\n"
        f"---\n\n"
    )


def _read_md_chunk(path: Path, max_chars: int) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n…（已截断）"
    return text


def combined_transcripts(project_relative: str, max_total: int = 48000) -> str:
    """合并真实逐字稿 + 参考模拟稿，供模块 7+ 生成使用。"""
    research = research_dir(project_relative)
    parts: list[str] = []
    used = 0

    base = research / INTERVIEWS_ROOT
    tdir = base / "transcripts"
    if tdir.is_dir():
        for p in sorted(tdir.glob("*.md")):
            chunk = _read_md_chunk(p, 12000)
            if not chunk.strip():
                continue
            block = f"### 真实访谈逐字稿：{p.name}\n{chunk}"
            if used + len(block) > max_total:
                break
            parts.append(block)
            used += len(block)

    legacy = research / "06_mock-transcripts"
    if legacy.is_dir():
        for p in sorted(legacy.glob("*.md")):
            chunk = _read_md_chunk(p, 8000)
            if chunk.strip():
                block = f"### 逐字稿（旧目录）：{p.name}\n{chunk}"
                if used + len(block) > max_total:
                    break
                parts.append(block)
                used += len(block)

    ref = base / "reference"
    if ref.is_dir():
        for p in sorted(ref.glob("*.md")):
            chunk = _read_md_chunk(p, 6000)
            if chunk.strip():
                block = f"### 参考模拟（SYNTHETIC）：{p.name}\n{chunk}"
                if used + len(block) > max_total:
                    break
                parts.append(block)
                used += len(block)

    if not parts:
        return ""
    return "## 访谈素材汇总（真实逐字稿优先）\n\n" + "\n\n".join(parts)
