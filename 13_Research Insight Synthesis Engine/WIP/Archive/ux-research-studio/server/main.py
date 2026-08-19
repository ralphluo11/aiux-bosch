from __future__ import annotations

import json
from typing import Any, Optional

import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import activity_log
from . import auth
from . import cursor_bridge
from . import interviews as interview_assets
from .config import (
    AI_PROVIDER,
    HOST,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    PORT,
    STUDIO_ACCESS_TOKEN,
    STUDIO_DIR,
    STUDIO_REQUIRE_AUTH,
    lan_urls,
)
from .modules_meta import MODULES, module_by_id
from .prompts import build_system_prompt, build_user_prompt
from . import chat_refine
from . import ppt_export
from . import workspace

app = FastAPI(title="UX Research Studio", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = STUDIO_DIR / "static"

# 无需登录即可访问的 API（其余 /api/* 均需有效 session）
AUTH_PUBLIC_API = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/logout",
}


@app.middleware("http")
async def enforce_login_middleware(request: Request, call_next):
    path = request.url.path
    if auth.auth_enabled() and path.startswith("/api/") and path not in AUTH_PUBLIC_API:
        session_token = request.headers.get("x-session-token")
        if not auth.parse_session(session_token):
            return JSONResponse(
                status_code=401,
                content={"detail": "请先注册并登录"},
            )
    return await call_next(request)


def _authorize(
    request: Request,
    x_studio_token: Optional[str] = None,
    token: Optional[str] = None,
) -> str:
    """共享令牌 + 注册用户会话（可同时启用）。"""
    session_token = request.headers.get("x-session-token")
    username = "anonymous"
    if auth.auth_enabled():
        username = auth.require_user(session_token)
    elif session_token:
        username = auth.parse_session(session_token) or "anonymous"
    if STUDIO_ACCESS_TOKEN:
        provided = x_studio_token or token or request.query_params.get("token")
        if provided != STUDIO_ACCESS_TOKEN:
            raise HTTPException(status_code=401, detail="需要有效的访问令牌")
    return username


def _log_activity(
    username: str,
    project_path: str,
    action: str,
    *,
    detail: str = "",
    module_id: Optional[int] = None,
    file_path: str = "",
) -> None:
    if not project_path or username == "anonymous":
        return
    meta = module_by_id(module_id) if module_id else None
    activity_log.append(
        project_path,
        username,
        action,
        detail=detail,
        module_id=module_id,
        module_title=meta.title if meta else "",
        file_path=file_path,
    )


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class ProjectContext(BaseModel):
    topic: str = ""
    audience: str = ""
    stage: str = ""
    core_question: str = ""
    notes: str = ""
    project_path: str = ""


class GenerateRequest(BaseModel):
    module_id: int = Field(ge=1, le=9)
    context: ProjectContext
    prior_modules: dict[str, str] = Field(default_factory=dict)
    stream: bool = True
    provider: Optional[str] = None  # openai | cursor


class SaveRequest(BaseModel):
    module_id: int = Field(ge=1, le=9)
    project_path: str
    content: str
    extra_filename: Optional[str] = None


@app.get("/api/health")
def health(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    return {
        "ok": True,
        "ai_provider": AI_PROVIDER,
        "openai_configured": bool(OPENAI_API_KEY),
        "cursor_configured": cursor_bridge.cursor_available(),
        "cursor_chat_mode": True,
        "model": OPENAI_MODEL,
        "workspace": str(workspace.WORKSPACE_ROOT),
        "lan_urls": lan_urls(),
        "auth": auth.auth_status(x_session_token),
        "access_token_required": bool(STUDIO_ACCESS_TOKEN),
    }


@app.get("/api/auth/status")
def auth_status(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> dict:
    return auth.auth_status(x_session_token)


@app.post("/api/auth/register")
def register(body: RegisterRequest) -> dict:
    if not auth.auth_enabled():
        raise HTTPException(400, "未启用账户系统")
    profile = auth.register(body.username, body.password, body.display_name)
    token = auth.create_session(profile["username"])
    return {
        "session_token": token,
        "username": profile["username"],
        "display_name": profile["display_name"],
    }


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict:
    if not auth.auth_enabled():
        raise HTTPException(400, "未启用账户系统（STUDIO_REQUIRE_AUTH=false 可本地免登录）")
    from . import user_store

    profile = user_store.authenticate(body.username, body.password)
    if not profile:
        raise HTTPException(401, detail="用户名或密码错误")
    token = auth.create_session(profile["username"])
    return {
        "session_token": token,
        "username": profile["username"],
        "display_name": profile["display_name"],
    }


@app.post("/api/auth/logout")
def logout() -> dict:
    return {"ok": True}


class ActivityNote(BaseModel):
    action: str = "note"
    detail: str = ""
    module_id: Optional[int] = None


@app.get("/api/projects/{project_path:path}/activity")
def get_activity(
    project_path: str,
    request: Request,
    limit: int = Query(default=40, ge=1, le=200),
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        entries = activity_log.list_entries(project_path, limit=limit)
        log_md = f"WIP/Research/{activity_log.LOG_DIR_NAME}/{activity_log.MD_NAME}"
        return {"entries": entries, "log_markdown": log_md}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/projects/{project_path:path}/activity")
def note_activity(
    project_path: str,
    body: ActivityNote,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    _log_activity(
        username,
        project_path,
        body.action,
        detail=body.detail,
        module_id=body.module_id,
    )
    return {"ok": True}


@app.get("/api/modules")
def list_modules(
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> list[dict]:
    _authorize(request, x_studio_token, token=token)
    return [
        {
            "id": m.id,
            "title": m.title,
            "title_en": m.title_en,
            "output_file": m.output_file,
            "output_is_dir": m.output_is_dir,
            "sub_skill": m.sub_skill,
        }
        for m in MODULES
    ]


@app.get("/api/projects")
def projects(
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> list[dict]:
    _authorize(request, x_studio_token, token=token)
    items = workspace.list_projects()
    for p in items:
        if p.get("has_research") and p.get("path"):
            try:
                p["progress"] = workspace.progress_summary(p["path"])
            except ValueError:
                p["progress"] = None
    return items


@app.get("/api/projects/{project_path:path}/progress")
def get_progress(
    project_path: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        return workspace.read_progress(project_path)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class ProgressUpdate(BaseModel):
    completed: list[int] = Field(default_factory=list)
    current_module: int = Field(default=1, ge=1, le=9)
    mark_complete: Optional[int] = None
    mark_incomplete: Optional[int] = None


@app.post("/api/projects/{project_path:path}/progress")
def update_progress(
    project_path: str,
    body: ProgressUpdate,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    try:
        prog = workspace.read_progress(project_path)
        completed = set(prog.get("completed") or [])
        if body.mark_complete:
            completed.add(body.mark_complete)
            _log_activity(
                username,
                project_path,
                "mark_complete",
                module_id=body.mark_complete,
                detail="标记模块已完成",
            )
        if body.mark_incomplete and body.mark_incomplete in completed:
            completed.discard(body.mark_incomplete)
            _log_activity(
                username,
                project_path,
                "mark_incomplete",
                module_id=body.mark_incomplete,
                detail="取消已完成标记",
            )
        if body.completed:
            completed = set(body.completed)
        prog["completed"] = sorted(completed)
        prog["current_module"] = body.current_module
        saved = workspace.write_progress(project_path, prog)
        if not body.mark_complete and not body.mark_incomplete:
            _log_activity(
                username,
                project_path,
                "progress_update",
                detail=f"当前模块 {body.current_module}",
                module_id=body.current_module,
            )
        return {"progress": saved, "summary": workspace.progress_summary(project_path)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/projects/{project_path:path}/interviews")
def list_interviews(
    project_path: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        return interview_assets.list_assets(project_path)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/projects/{project_path:path}/interviews/combined")
def interviews_combined(
    project_path: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        content = interview_assets.combined_transcripts(project_path)
        return {"content": content, "length": len(content)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/projects/{project_path:path}/interviews/upload")
async def upload_interviews(
    project_path: str,
    request: Request,
    files: list[UploadFile] = File(...),
    auto_transcribe: str = Form(default="true"),
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    try:
        auto = str(auto_transcribe).lower() in ("1", "true", "yes", "on")
        result = await interview_assets.upload_files(
            project_path, files, username, auto_transcribe=auto
        )
        _log_activity(
            username,
            project_path,
            "interview_upload",
            detail=f"上传 {len(files)} 个访谈文件",
            module_id=6,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/projects/{project_path:path}/interviews/{file_id}/transcribe")
def transcribe_interview(
    project_path: str,
    file_id: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    try:
        result = interview_assets.transcribe_asset(project_path, file_id, username)
        _log_activity(
            username,
            project_path,
            "interview_transcribe",
            detail=f"转写 {file_id}",
            module_id=6,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/api/projects/{project_path:path}/interviews/{file_id}")
def delete_interview(
    project_path: str,
    file_id: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    try:
        assets = interview_assets.delete_asset(project_path, file_id)
        _log_activity(
            username,
            project_path,
            "interview_delete",
            detail=file_id,
            module_id=6,
        )
        return assets
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/projects/{project_path:path}/context")
def project_context(
    project_path: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        docs = workspace.read_project_context(project_path)
        files = workspace.list_research_files(project_path)
        return {"project_docs": docs, "research_files": files}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/projects/{project_path:path}/files/{filename:path}")
def get_file(
    project_path: str,
    filename: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        content = workspace.read_research_file(project_path, filename)
        return {"filename": filename, "content": content}
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/build-prompt")
def build_prompt(
    body: GenerateRequest,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    """无需 API：返回完整 Prompt，供粘贴到 Cursor 对话。"""
    _authorize(request, x_studio_token, token=token)
    meta = module_by_id(body.module_id)
    if not meta:
        raise HTTPException(400, "无效模块 ID")
    ctx = body.context.model_dump()
    if body.context.project_path:
        ctx["project_docs"] = workspace.read_project_context(body.context.project_path)
    prior: dict[int, str] = {}
    for k, v in body.prior_modules.items():
        try:
            prior[int(k)] = v
        except ValueError:
            continue
    system = build_system_prompt(meta)
    user = build_user_prompt(meta, ctx, prior)
    project = body.context.project_path or "[项目路径]"
    cursor_instruction = (
        f"请按 ux-research-planning 模块 {meta.id}（{meta.title}）生成画布内容。\n"
        f"落盘到：{project}/WIP/Research/{meta.output_file}\n"
        "只输出 Markdown 正文，不要解释过程。"
    )
    full_prompt = f"{cursor_instruction}\n\n---\n\n{user}"
    return {
        "module_id": meta.id,
        "module_title": meta.title,
        "output_file": meta.output_file,
        "system": system,
        "user": user,
        "cursor_instruction": cursor_instruction,
        "full_prompt": full_prompt,
        "save_path": f"{project}/WIP/Research/{meta.output_file}",
    }


@app.post("/api/generate")
async def generate(
    body: GenerateRequest,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
):
    username = _authorize(request, x_studio_token, token=token)
    if body.context.project_path:
        _log_activity(
            username,
            body.context.project_path,
            "generate",
            module_id=body.module_id,
            detail="DeepSeek 生成模块内容",
        )

    provider = (body.provider or AI_PROVIDER or "openai").lower()
    meta = module_by_id(body.module_id)
    if not meta:
        raise HTTPException(400, "无效模块 ID")

    ctx = body.context.model_dump()
    if body.context.project_path:
        ctx["project_docs"] = workspace.read_project_context(body.context.project_path)

    prior: dict[int, str] = {}
    for k, v in body.prior_modules.items():
        try:
            prior[int(k)] = v
        except ValueError:
            continue

    system = build_system_prompt(meta)
    user = build_user_prompt(meta, ctx, prior)

    if provider == "cursor":
        if not cursor_bridge.cursor_available():
            raise HTTPException(
                503,
                "Cursor SDK 未就绪：设置 CURSOR_API_KEY 并在 ux-research-studio 执行 npm install",
            )
        try:
            content = await cursor_bridge.generate_via_cursor(
                system,
                user,
                body.context.project_path or "",
            )
        except RuntimeError as e:
            raise HTTPException(503, str(e)) from e
        return {"content": content, "module_id": body.module_id, "provider": "cursor"}

    if not OPENAI_API_KEY:
        raise HTTPException(503, "未配置 OPENAI_API_KEY，请在 .env 中设置")

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "max_tokens": 8192,
        "stream": body.stream,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    if body.stream:

        async def event_stream():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{OPENAI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status_code >= 400:
                        text = await resp.aread()
                        yield f"data: {json.dumps({'error': text.decode()})}\n\n"
                        return
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        chunk = line[6:].strip()
                        if chunk == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(chunk)
                            delta = (
                                data.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                yield f"data: {json.dumps({'content': delta})}\n\n"
                        except json.JSONDecodeError:
                            continue

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json={**payload, "stream": False},
        )
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return {"content": content, "module_id": body.module_id}


@app.post("/api/save")
def save_output(
    body: SaveRequest,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    meta = module_by_id(body.module_id)
    if not meta:
        raise HTTPException(400, "无效模块 ID")
    try:
        saved = workspace.write_module_output(
            body.project_path,
            meta,
            body.content,
            body.extra_filename,
        )
        _log_activity(
            username,
            body.project_path,
            "save",
            module_id=body.module_id,
            file_path=saved,
            detail="保存模块到 WIP/Research",
        )
        return {"saved_path": saved, "module_id": body.module_id}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class FieldCatalogItem(BaseModel):
    id: str
    label: str = ""
    section: str = ""
    type: str = "text"


class ChatRequest(BaseModel):
    module_id: int = Field(ge=1, le=9)
    project_path: str
    context: ProjectContext
    current_fields: dict[str, Any] = Field(default_factory=dict)
    field_catalog: list[FieldCatalogItem] = Field(default_factory=list)
    prior_modules: dict[str, str] = Field(default_factory=dict)
    history: list[ChatMessage] = Field(default_factory=list)
    message: str = ""
    force_confirm: bool = False


@app.post("/api/chat")
async def module_chat(
    body: ChatRequest,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    if not body.message.strip() and not body.force_confirm:
        raise HTTPException(400, "请输入消息")
    ctx = body.context.model_dump()
    ctx["project_path"] = body.project_path or ctx.get("project_path") or ""
    try:
        result = chat_refine.chat_turn(
            body.module_id,
            ctx,
            body.current_fields,
            body.prior_modules,
            [m.model_dump() for m in body.history],
            body.message.strip() or "确认应用修改",
            force_confirm=body.force_confirm,
            field_catalog=[f.model_dump() for f in body.field_catalog],
        )
        if body.project_path and result.get("status") == "confirmed":
            _log_activity(
                username,
                body.project_path,
                "chat_apply",
                module_id=body.module_id,
                detail=body.message[:80] or "对话确认应用",
            )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/api/projects/{project_path:path}/export-ppt")
def export_ppt_endpoint(
    project_path: str,
    body: ProjectContext,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    username = _authorize(request, x_studio_token, token=token)
    ctx = body.model_dump()
    ctx["project_path"] = project_path
    try:
        out = ppt_export.export_ppt(project_path, ctx)
        rel = out.relative_to(workspace.WORKSPACE_ROOT).as_posix()
        _log_activity(
            username,
            project_path,
            "export_ppt",
            detail=out.name,
        )
        return {
            "ok": True,
            "path": rel,
            "filename": out.name,
            "download_url": f"/api/projects/{project_path}/exports/{out.name}",
        }
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/projects/{project_path:path}/exports/{filename:path}")
def download_export(
    project_path: str,
    filename: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
):
    _authorize(request, x_studio_token, token=token)
    try:
        base = workspace.research_dir(project_path) / "exports"
        target = (base / filename).resolve()
        if not str(target).startswith(str(base.resolve())):
            raise HTTPException(400, "无效路径")
        if not target.is_file():
            raise HTTPException(404, "文件不存在")
        return FileResponse(
            target,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=target.name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/validate")
def validate(
    project_path: str,
    request: Request,
    x_studio_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    _authorize(request, x_studio_token, token=token)
    try:
        return workspace.run_validation(project_path)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def run() -> None:
    import uvicorn

    urls = lan_urls()
    print("\n=== UX Research Studio ===")
    print(f"工作区: {workspace.WORKSPACE_ROOT}")
    ai_name = "DeepSeek" if "deepseek" in (OPENAI_BASE_URL or "").lower() else AI_PROVIDER
    print(f"AI: {ai_name} {'已配置' if OPENAI_API_KEY else '未配置'}")
    if STUDIO_REQUIRE_AUTH:
        print("账户: 已强制注册/登录（data/users.json）")
    else:
        print("⚠  账户: 免登录模式（STUDIO_REQUIRE_AUTH=false，不建议用于团队共享）")
    print("局域网访问地址:")
    for u in urls:
        print(f"  {u}")
    print()
    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    run()
