#!/bin/bash
# 双击此文件即可启动网站（macOS Finder）
cd "$(dirname "$0")"
chmod +x start.sh 2>/dev/null || true
exec ./start.sh
