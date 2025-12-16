#!/usr/bin/env bash
#
# 启动 Cyber-Pingshu Workstation（storyteller）
# - 使用 uv 运行桌面应用：uv run python app.py
# - 在后台运行，并将 PID 写入 logs/storyteller.pid

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$LOG_DIR/storyteller.pid"
LOG_FILE="$LOG_DIR/storyteller.log"

mkdir -p "$LOG_DIR"

if command -v uv >/dev/null 2>&1; then
  :
else
  echo "[ERROR] 未找到 uv 命令，请先安装 uv 并在本项目目录执行 uv sync。" >&2
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  EXISTING_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${EXISTING_PID}" ]] && ps -p "$EXISTING_PID" >/dev/null 2>&1; then
    echo "[INFO] 应用似乎已经在运行（PID=$EXISTING_PID），如需重启请先运行 ./stop_storyteller.sh。"
    exit 0
  else
    echo "[WARN] 检测到过期的 PID 文件，已清理。"
    rm -f "$PID_FILE"
  fi
fi

echo "[INFO] 使用 uv 启动 storyteller..."
nohup uv run python app.py >> "$LOG_FILE" 2>&1 &
APP_PID=$!

echo "$APP_PID" > "$PID_FILE"

echo "[INFO] storyteller 已在后台启动，PID=$APP_PID"
echo "[INFO] 日志输出：$LOG_FILE"
echo "[INFO] 停止应用：./stop_storyteller.sh"


