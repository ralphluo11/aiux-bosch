from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import HTTPException

from . import user_store
from .config import STUDIO_REQUIRE_AUTH

SESSION_SECRET = os.getenv("SESSION_SECRET", os.getenv("STUDIO_ACCESS_TOKEN", "uxrs-dev-secret-change-me"))
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
# 生产环境应保持 true；仅本地调试可设 STUDIO_REQUIRE_AUTH=false
REQUIRE_AUTH = STUDIO_REQUIRE_AUTH


def auth_enabled() -> bool:
    return REQUIRE_AUTH


def register(username: str, password: str, display_name: str = "") -> dict:
    return user_store.register_user(username, password, display_name)


def verify_password(username: str, password: str) -> bool:
    return user_store.authenticate(username, password) is not None


def create_session(username: str) -> str:
    payload = {
        "u": username,
        "exp": int(time.time()) + SESSION_DAYS * 86400,
    }
    msg = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(SESSION_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    raw = f"{msg}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def parse_session(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        msg, sig = raw.rsplit("|", 1)
        expected = hmac.new(SESSION_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        payload = json.loads(msg)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload.get("u")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def require_user(session_token: Optional[str]) -> str:
    if not auth_enabled():
        return "anonymous"
    username = parse_session(session_token)
    if not username:
        raise HTTPException(status_code=401, detail="请先注册并登录")
    return username


def auth_status(session_token: Optional[str]) -> dict:
    if not auth_enabled():
        return {
            "required": False,
            "logged_in": False,
            "username": None,
            "display_name": None,
            "auth_disabled": True,
            "message": "服务器未开启强制登录，请在 .env 设置 STUDIO_REQUIRE_AUTH=true 后重启",
        }
    username = parse_session(session_token)
    display_name = username
    if username:
        prof = user_store.get_profile(username)
        display_name = (prof or {}).get("display_name") or username
    return {
        "required": True,
        "logged_in": bool(username),
        "username": username,
        "display_name": display_name,
        "user_count": user_store.user_count(),
        "register_required": user_store.user_count() == 0,
    }
