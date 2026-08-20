#!/bin/bash
cd "$(dirname "$0")" || exit 1

echo "========================================"
echo "  UXGS Research Agent 一键启动"
echo "========================================"
echo

if [ -z "$AI_UX_LLM_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
  echo "请输入 Bosch LLM API Key（直接回车进入离线预览）："
  read -r -s AI_UX_LLM_API_KEY
  echo
  export AI_UX_LLM_API_KEY
fi

ACTIVE_API_KEY="${AI_UX_LLM_API_KEY:-${OPENAI_API_KEY:-}}"
if [ -n "$ACTIVE_API_KEY" ] && ! ACTIVE_API_KEY="$ACTIVE_API_KEY" python3 -c 'import os, sys; key = os.environ.get("ACTIVE_API_KEY", "").strip(); sys.exit(0 if key.isascii() and key.isprintable() else 1)'; then
  echo "API Key 格式错误：检测到中文、全角字符或不可见字符。"
  echo "请重新双击启动文件，并只粘贴实际 API Key，不要粘贴说明文字或引号。"
  read -r -p "按回车键关闭…" _
  exit 1
fi
unset ACTIVE_API_KEY

# 当前 POC 使用的 Bosch OpenAI-compatible endpoint。
# 如外部环境已提供不同配置，则尊重外部配置。
export AI_UX_LLM_BASE_URL="${AI_UX_LLM_BASE_URL:-https://llms.documind.bosch-app.com/v1}"
export AI_UX_LLM_MODEL="${AI_UX_LLM_MODEL:-gpt-5.4-mini}"
export AI_UX_LLM_API_STYLE="${AI_UX_LLM_API_STYLE:-chat_completions}"
export PYTHONPATH="src:.vendor"

# 在启动页面前验证代理隧道和模型网关。未带令牌访问 /models 时，
# 401/403 代表网络已经到达网关；000 或其它连接失败代表代理不可用。
if [ -n "$AI_UX_LLM_API_KEY" ] || [ -n "$OPENAI_API_KEY" ]; then
  PREFLIGHT_CODE="$(curl -sS --max-time 15 -o /tmp/uxgs-llm-preflight.txt -w '%{http_code}' "$AI_UX_LLM_BASE_URL/models" 2>/dev/null || true)"
  case "$PREFLIGHT_CODE" in
    200|401|403|404)
      echo "模型网关连接正常（HTTP $PREFLIGHT_CODE）。"
      ;;
    *)
      echo
      echo "模型网关连接失败（HTTP ${PREFLIGHT_CODE:-000}）。"
      echo "当前地址：$AI_UX_LLM_BASE_URL"
      echo "请先运行 codex-net 检查 Bosch 代理出口，再重新启动。"
      echo "本次将进入离线预览，避免在页面任务中途失败。"
      unset AI_UX_LLM_API_KEY
      unset OPENAI_API_KEY
      ;;
  esac
fi

# Python 不会热加载新增接口。若检测到旧实例，先关闭后再启动当前版本。
EXISTING_PID="$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$EXISTING_PID" ]; then
  echo "检测到旧的 Research Agent 服务，正在重新启动……"
  kill $EXISTING_PID 2>/dev/null || true
  sleep 1
fi

python3 -m ai_ux_core.web &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "正在启动，请稍候……"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
    open "http://127.0.0.1:8000/#/sources"
    echo
    echo "Research Agent 已打开。"
    echo "请保持此窗口运行；停止服务请按 Control + C。"
    wait "$SERVER_PID"
    exit $?
  fi
  sleep 1
done

echo
echo "启动失败：请检查上方错误信息，或确认 8000 端口没有被占用。"
wait "$SERVER_PID"
