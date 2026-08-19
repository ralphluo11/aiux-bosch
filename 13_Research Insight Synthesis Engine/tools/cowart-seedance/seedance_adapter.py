#!/usr/bin/env python3
"""Minimal Cowart -> Seedance -> MP4 adapter using only the Python stdlib."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedance-1-5-pro-251215"
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


class SeedanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    poll_seconds: float = 5.0
    timeout_seconds: float = 900.0

    @classmethod
    def from_env(cls) -> "Config":
        key = os.getenv("ARK_API_KEY", "").strip()
        if not key:
            raise SeedanceError("缺少 ARK_API_KEY；请仅在本机环境变量中配置，不要写入画布或 HTML。")
        return cls(
            api_key=key,
            model=os.getenv("SEEDANCE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            base_url=os.getenv("SEEDANCE_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            poll_seconds=float(os.getenv("SEEDANCE_POLL_SECONDS", "5")),
            timeout_seconds=float(os.getenv("SEEDANCE_TIMEOUT_SECONDS", "900")),
        )


def _request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SeedanceError(f"Seedance HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SeedanceError(f"Seedance 请求失败: {exc}") from exc


def image_data_url(image_path: Path) -> str:
    if not image_path.is_file():
        raise SeedanceError(f"找不到首帧图片: {image_path}")
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_content(prompt: str, image_path: Path, ratio: str, duration: int) -> list[dict[str, Any]]:
    motion_prompt = f"{prompt.strip()} --ratio {ratio} --dur {duration}"
    return [
        {"type": "text", "text": motion_prompt},
        {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
    ]


def create_task(config: Config, content: list[dict[str, Any]]) -> dict[str, Any]:
    return _request_json(
        "POST",
        f"{config.base_url}/contents/generations/tasks",
        config.api_key,
        {"model": config.model, "content": content},
    )


def get_task(config: Config, task_id: str) -> dict[str, Any]:
    return _request_json(
        "GET",
        f"{config.base_url}/contents/generations/tasks/{task_id}",
        config.api_key,
    )


def wait_for_task(
    config: Config,
    task_id: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = now()
    while True:
        task = get_task(config, task_id)
        status = str(task.get("status", "unknown"))
        print(json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False), flush=True)
        if status in TERMINAL_STATES:
            if status != "succeeded":
                raise SeedanceError(f"视频任务未成功: {json.dumps(task.get('error', task), ensure_ascii=False)}")
            return task
        if now() - started >= config.timeout_seconds:
            raise SeedanceError(f"等待视频任务超时: {task_id}")
        sleep(config.poll_seconds)


def find_video_url(task: dict[str, Any]) -> str:
    content = task.get("content") or {}
    candidates = [
        content.get("video_url") if isinstance(content, dict) else None,
        content.get("url") if isinstance(content, dict) else None,
        task.get("video_url"),
        task.get("url"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    raise SeedanceError("任务成功，但响应中没有找到视频 URL。请保存响应并核对当前模型返回结构。")


def download_video(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "cowart-seedance-poc/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise SeedanceError(f"视频下载失败: {exc}") from exc
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(data)
    temporary.replace(destination)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 Cowart 页面首帧提交到 Seedance，并把 MP4 保存回页面资源目录。")
    parser.add_argument("--image", required=True, type=Path, help="由 Cowart 页面渲染得到的 PNG/JPEG")
    parser.add_argument("--prompt", required=True, help="镜头、动效与保真要求")
    parser.add_argument("--output", required=True, type=Path, help="输出 MP4；建议放在 canvas/pages/<page>/assets/")
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--submit-only", action="store_true", help="只提交任务并打印 task_id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        config = Config.from_env()
        content = build_content(args.prompt, args.image.resolve(), args.ratio, args.duration)
        created = create_task(config, content)
        task_id = str(created.get("id", ""))
        if not task_id:
            raise SeedanceError(f"创建任务响应缺少 id: {json.dumps(created, ensure_ascii=False)}")
        print(json.dumps({"task_id": task_id, "status": created.get("status", "queued")}, ensure_ascii=False))
        if args.submit_only:
            return 0
        completed = wait_for_task(config, task_id)
        video_url = find_video_url(completed)
        download_video(video_url, args.output.resolve())
        print(json.dumps({"status": "saved", "output": str(args.output.resolve())}, ensure_ascii=False))
        return 0
    except SeedanceError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
