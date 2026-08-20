from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

_dotenv_loaded = False


def ensure_dotenv_loaded() -> None:
    """Load `.env` into os.environ once per process, without any pip dependency.

    Values already present in the real environment always win, matching the
    `${VAR:-default}` precedence START_MAC.command already uses, so a shell
    export or CI secret still overrides whatever is in the file.
    """
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    if not ENV_FILE_PATH.is_file():
        return
    for raw_line in ENV_FILE_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class LLMSettings:
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    api_style: str


def load_llm_settings(*, default_timeout_seconds: float) -> LLMSettings:
    """Single read point for the `AI_UX_LLM_*` group.

    Previously `llm.py`, `research_agent.py`, and `document_parser.py` each
    called `os.environ.get(...)` independently with their own defaults; this
    collects that into one place so the three callers can't silently drift.
    `default_timeout_seconds` stays a parameter rather than one shared
    constant because the live interview probe and the batch research agent
    have deliberately different timeout budgets (fast turnaround for a
    participant waiting on the next question vs. a background analysis job).
    """
    ensure_dotenv_loaded()
    api_key = os.environ.get("AI_UX_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    return LLMSettings(
        api_key=api_key.strip() if api_key else None,
        base_url=os.environ.get("AI_UX_LLM_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.environ.get("AI_UX_LLM_MODEL", "gpt-5.6-terra").strip(),
        timeout_seconds=float(
            os.environ.get("AI_UX_LLM_TIMEOUT_SECONDS", str(default_timeout_seconds))
        ),
        api_style=os.environ.get("AI_UX_LLM_API_STYLE", "auto").strip(),
    )
