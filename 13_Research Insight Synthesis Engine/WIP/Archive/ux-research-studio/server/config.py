from __future__ import annotations

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STUDIO_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(
    os.getenv("WORKSPACE_ROOT") or STUDIO_DIR.parent
).resolve()

CURSOR_ROOT = WORKSPACE_ROOT / ".cursor"
SKILLS_ROOT = CURSOR_ROOT / "skills" / "ux-research-planning"
MODULES_DIR = SKILLS_ROOT / "modules"
GLOBAL_MD = CURSOR_ROOT / "config" / "global.md"
VALIDATE_SCRIPT = SKILLS_ROOT / "scripts" / "validate_research_outputs.py"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8765"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# 音视频转写（Whisper，需 OpenAI 或兼容端点；DeepSeek Key 不能用于转写）
TRANSCRIBE_API_KEY = os.getenv("TRANSCRIBE_API_KEY", "").strip()
TRANSCRIBE_BASE_URL = os.getenv(
    "TRANSCRIBE_BASE_URL", "https://api.openai.com/v1"
).rstrip("/")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
STUDIO_ACCESS_TOKEN = os.getenv("STUDIO_ACCESS_TOKEN", "").strip()
STUDIO_REQUIRE_AUTH = os.getenv("STUDIO_REQUIRE_AUTH", "true").strip().lower() not in (
    "0",
    "false",
    "no",
)

# openai | cursor（cursor 需 CURSOR_API_KEY + npm install）
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").strip().lower()
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY", "").strip()
CURSOR_MODEL = os.getenv("CURSOR_MODEL", "composer-2")


def lan_urls(port=None) -> list:
    p = port or PORT
    urls = [f"http://127.0.0.1:{p}"]
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                urls.append(f"http://{ip}:{p}")
    except OSError:
        pass
    return urls
