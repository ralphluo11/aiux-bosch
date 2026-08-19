#!/usr/bin/env bash
# UX Research Studio — 启动局域网共享服务
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8765}"

echo ""
echo "=========================================="
echo "  UX Research Studio · 正在启动"
echo "=========================================="
echo ""

# 若端口已被占用，释放后重启（避免上次未关干净）
if lsof -ti ":${PORT}" >/dev/null 2>&1; then
  echo "⚠  端口 ${PORT} 已被占用，正在释放…"
  lsof -ti ":${PORT}" | xargs kill -9 2>/dev/null || true
  sleep 1
fi

if [ ! -d ".venv" ]; then
  echo "→ 首次运行：创建 Python 虚拟环境…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "→ 检查依赖…"
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "⚠  已创建 .env，请填入 OPENAI_API_KEY（DeepSeek）后重新双击启动。"
  echo ""
  read -r -p "按回车键关闭此窗口…" _
  exit 1
fi

# 本机 IP，供同事访问
LAN_IP=""
if command -v ipconfig >/dev/null 2>&1; then
  LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
fi
if [ -z "$LAN_IP" ]; then
  LAN_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "")
fi

echo ""
echo "  本机访问:    http://127.0.0.1:${PORT}"
if [ -n "$LAN_IP" ]; then
  echo "  局域网分享:  http://${LAN_IP}:${PORT}"
  echo ""
  echo "  把「局域网分享」地址发给同事即可（需同一 WiFi/内网）"
else
  echo "  局域网分享:  启动后见终端打印的地址"
fi
echo ""
echo "  关闭服务: 直接关掉此终端窗口，或按 Ctrl+C"
echo "=========================================="
echo ""

# 稍后在浏览器打开本机地址
(sleep 2 && open "http://127.0.0.1:${PORT}" 2>/dev/null) &

export PYTHONPATH="${PWD}"
exec python3 -m server.main
