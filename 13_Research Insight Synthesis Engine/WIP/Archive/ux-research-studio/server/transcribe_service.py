from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from .config import (
    OPENAI_API_KEY,
    TRANSCRIBE_API_KEY,
    TRANSCRIBE_BASE_URL,
    WHISPER_MODEL,
)

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def _api_key() -> str:
    key = (TRANSCRIBE_API_KEY or OPENAI_API_KEY or "").strip()
    if not key:
        raise RuntimeError(
            "未配置转写 API。请在 .env 设置 TRANSCRIBE_API_KEY（OpenAI）"
            "，或确保 OPENAI_API_KEY 可用于 api.openai.com 的 Whisper。"
        )
    return key


def _extract_audio(media_path: Path, work_dir: Path) -> Path:
    if media_path.suffix.lower() not in VIDEO_EXT:
        return media_path
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "视频转写需要 ffmpeg。请安装：brew install ffmpeg"
        )
    out = work_dir / f"{media_path.stem}_audio.mp3"
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "4",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(f"ffmpeg 提取音频失败：{proc.stderr[-800:]}")
    return out


def transcribe_with_whisper(audio_path: Path) -> str:
    base = TRANSCRIBE_BASE_URL.rstrip("/")
    url = f"{base}/audio/transcriptions"
    key = _api_key()

    with audio_path.open("rb") as f:
        files = {"file": (audio_path.name, f, "application/octet-stream")}
        data = {"model": WHISPER_MODEL, "response_format": "text"}
        with httpx.Client(timeout=600.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                files=files,
                data=data,
            )
    if resp.status_code >= 400:
        hint = ""
        if "deepseek" in base.lower():
            hint = " DeepSeek 接口不支持 Whisper，请单独配置 TRANSCRIBE_API_KEY 为 OpenAI Key。"
        raise RuntimeError(f"转写 API 错误 ({resp.status_code})：{resp.text[:400]}{hint}")
    return resp.text.strip()


def transcribe_media_file(
    media_path: Path,
    interviews_base: Path,
    original_name: str,
    username: str,
) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        audio = _extract_audio(media_path, work)
        text = transcribe_with_whisper(audio)

    stem = Path(original_name).stem
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)[:80]
    tpath = interviews_base / "transcripts" / f"{safe}.md"
    header = (
        f"---\n"
        f"source: {original_name}\n"
        f"uploaded_by: {username}\n"
        f"method: whisper\n"
        f"model: {WHISPER_MODEL}\n"
        f"---\n\n"
    )
    tpath.write_text(header + text + "\n", encoding="utf-8")
    return tpath
