#!/bin/bash
# 双击此文件即可启动 UX Research Studio（macOS Finder）
STUDIO_DIR="$(dirname "$0")/ux-research-studio"
if [ ! -d "$STUDIO_DIR" ]; then
  osascript -e 'display alert "找不到 ux-research-studio 文件夹" as critical'
  read -r -p "按回车键关闭…" _
  exit 1
fi
cd "$STUDIO_DIR"
chmod +x start.sh "启动 UX Research Studio.command" 2>/dev/null || true
exec ./start.sh
