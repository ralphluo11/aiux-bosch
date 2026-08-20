@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
  set "PYTHON_CMD=python"
)

rem Key/model/endpoint now live in .env (see ensure_dotenv_loaded() in
rem src\ai_ux_core\config.py) so they persist across terminals instead of
rem needing $env: every session. Scaffold it once from the example, but
rem never touch an existing .env.
if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo 已从 .env.example 创建 .env——请先打开根目录的 .env 文件填入 AI_UX_LLM_API_KEY，
    echo 保存后重新双击本脚本。此前不会自动打开浏览器，避免看到离线预览误以为是真实结果。
    notepad ".env"
    pause
    exit /b 0
  )
)

start "AI UX Interview Server" cmd /k "%PYTHON_CMD% -m ai_ux_core.web"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/?debug=1"
endlocal
