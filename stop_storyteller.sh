#!/usr/bin/env bash
#
# 停止 Cyber-Pingshu Workstation（storyteller）
# - 从 storyteller.pid 读取 PID
# - 递归结束该 PID 及其所有子进程（如 FFmpeg、Playwright 等）

set -eo pipefail

kill_tree() {
  local root_pid="$1"
  if [[ -z "$root_pid" ]]; then
    return 0
  fi

  # 先找出所有子进程并递归终止
  local children
  children="$(pgrep -P "$root_pid" || true)"
  if [[ -n "$children" ]]; then
    for child in $children; do
      kill_tree "$child"
    done
  fi

  if ps -p "$root_pid" >/dev/null 2>&1; then
    echo "[DEBUG] kill PID=$root_pid"
    kill "$root_pid" 2>/dev/null || true
  fi
}

cleanup_orphan_roots() {
  local ignore_pid="${1:-}"

  # 根据命令行模式查找可能残留的 storyteller 主进程
  # 这里假设入口为 app.py，且通过 python/uv 启动
  local patterns=(
    "uv run python app.py"
    "python app.py"
  )

  local found_any=0

  for pat in "${patterns[@]}"; do
    local pids
    pids="$(pgrep -f "$pat" || true)"
    if [[ -n "$pids" ]]; then
      found_any=1
      for pid in $pids; do
        # 跳过当前这次启动记录的 PID（如果有）
        if [[ -n "$ignore_pid" && "$pid" == "$ignore_pid" ]]; then
          continue
        fi
        echo "[INFO] 发现历史残留 storyteller 主进程（PID=$pid, pattern='$pat'），尝试清理..."
        kill_tree "$pid"
      done
    fi
  done

  if [[ "$found_any" -eq 0 ]]; then
    echo "[INFO] 未发现任何 storyteller 相关进程需要清理。"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$LOG_DIR/storyteller.pid"

mkdir -p "$LOG_DIR"

APP_PID=""
if [[ -f "$PID_FILE" ]]; then
  APP_PID="$(cat "$PID_FILE" || true)"
fi

if [[ -n "$APP_PID" ]] && ps -p "$APP_PID" >/dev/null 2>&1; then
  echo "[INFO] 正在停止 storyteller 及其关联进程（根 PID=$APP_PID）..."
  kill_tree "$APP_PID"

  # 简单等待一小会儿，检查是否都已退出
  sleep 2

  if ps -p "$APP_PID" >/dev/null 2>&1; then
    echo "[WARN] 根进程仍在运行，可考虑手动执行：kill -9 $APP_PID"
  else
    echo "[INFO] storyteller 及其子进程已停止。"
  fi
else
  if [[ -n "$APP_PID" ]]; then
    echo "[INFO] 未找到 PID=$APP_PID 对应的运行进程，可能已经退出。"
  else
    echo "[INFO] 未从 PID 文件中获取到有效 PID（可能文件为空或不存在），改为按进程名进行清理。"
  fi
fi

# 无论 PID 文件是否存在，都尝试清理可能残留的主进程
cleanup_orphan_roots "$APP_PID"

if [[ -f "$PID_FILE" ]]; then
  rm -f "$PID_FILE"
fi

