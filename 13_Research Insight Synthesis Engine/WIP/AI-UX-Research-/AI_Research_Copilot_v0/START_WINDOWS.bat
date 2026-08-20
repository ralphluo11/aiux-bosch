@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
set "PORT=8000"

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

rem Restart only a previous server for this project.  This prevents a browser
rem tab from silently continuing to use an older process that loaded no API key.
powershell -NoProfile -Command "$listener=Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue; if($listener){$processInfo=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $listener[0].OwningProcess); if($processInfo.Name -eq 'python.exe' -and $processInfo.CommandLine -match 'ai_ux_core\.web'){Stop-Process -Id $listener[0].OwningProcess -Force; Start-Sleep -Seconds 1}else{Write-Host 'Port %PORT% is used by another application.'; exit 11}}"
if errorlevel 11 (
  echo Port %PORT% is occupied by another application. Close that application and run this file again.
  pause
  exit /b 1
)

start "AI UX Interview Server" cmd /k "%PYTHON_CMD% -m ai_ux_core.web --port %PORT%"
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try{$health=Invoke-RestMethod -Uri 'http://127.0.0.1:%PORT%/api/health' -TimeoutSec 8; if($health.research_agent_mode -eq 'live_ai'){Write-Host ('Live AI connected: ' + $health.research_agent_model)}else{Write-Host 'Service started in Offline Preview. Check .env.'; exit 2}}catch{Write-Host ('Service did not start: ' + $_.Exception.Message); exit 1}"
if errorlevel 1 (
  echo The server did not enter Live AI mode. Check the message above before continuing.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:%PORT%/?debug=1"
endlocal
