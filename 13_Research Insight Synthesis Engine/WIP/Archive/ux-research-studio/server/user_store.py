from __future__ import annotations

import json
import os
import re
import secrets
import time
from hashlib import pbkdf2_hmac
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

from .config import STUDIO_DIR

USERS_FILE = STUDIO_DIR / "data" / "users.json"
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\-\u4e00-\u9fff]{2,32}$")
PBKDF2_ITERATIONS = 120_000


def _ensure_data_dir() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({"users": {}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load() -> dict:
    _ensure_data_dir()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"users": {}}


def _save(data: dict) -> None:
    _ensure_data_dir()
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return salt, digest.hex()


def verify_password_record(password: str, record: dict) -> bool:
    salt = record.get("salt", "")
    expected = record.get("password_hash", "")
    if not salt or not expected:
        return False
    _, got = _hash_password(password, salt)
    return secrets.compare_digest(got, expected)


def register_user(username: str, password: str, display_name: str = "") -> dict:
    username = username.strip()
    display_name = (display_name or username).strip()
    if not USERNAME_RE.match(username):
        raise HTTPException(400, "用户名 2–32 位，可用字母/数字/下划线/中文")
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")

    data = _load()
    users = data.setdefault("users", {})
    if username in users:
        raise HTTPException(409, "用户名已存在，请直接登录或换一个")

    salt, pwd_hash = _hash_password(password)
    users[username] = {
        "password_hash": pwd_hash,
        "salt": salt,
        "display_name": display_name,
        "created_at": _iso_now(),
    }
    _save(data)
    return {"username": username, "display_name": display_name}


def authenticate(username: str, password: str) -> Optional[dict]:
    username = username.strip()
    data = _load()
    record = data.get("users", {}).get(username)
    if not record or not verify_password_record(password, record):
        return None
    return {
        "username": username,
        "display_name": record.get("display_name") or username,
    }


def user_count() -> int:
    return len(_load().get("users", {}))


def get_profile(username: str) -> Optional[dict]:
    record = _load().get("users", {}).get(username)
    if not record:
        return None
    return {
        "username": username,
        "display_name": record.get("display_name") or username,
    }


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
