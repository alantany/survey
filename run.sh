#!/usr/bin/env bash
set -euo pipefail

# 通用启动脚本（本地/远程通用）
# - 不使用绝对路径
# - 默认仅本机访问：HOST=127.0.0.1
# - 远程需要外网访问：HOST=0.0.0.0

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

APP_CMD="backend/app.py"
PID_FILE=".run.pid"
LOG_FILE="server.log"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
DEBUG="${DEBUG:-0}"

function _is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

function status() {
  if _is_running; then
    echo "running: pid=$(cat "$PID_FILE")  http://${HOST}:${PORT}"
  else
    echo "not running"
  fi
}

function stop() {
  if _is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    echo "stopping pid=$pid ..."
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      echo "force kill pid=$pid ..."
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    echo "stopped"
  else
    echo "not running"
  fi
}

function start() {
  if _is_running; then
    status
    echo "already running, skip start."
    return 0
  fi

  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
  fi

  # 确保依赖存在（最小保证：flask/python-docx）
  ./.venv/bin/pip install -q -r requirements.txt

  echo "starting... HOST=${HOST} PORT=${PORT} DEBUG=${DEBUG}"
  nohup env HOST="$HOST" PORT="$PORT" DEBUG="$DEBUG" ./.venv/bin/python "$APP_CMD" >"$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1
  status
  echo "log: $LOG_FILE"
}

cmd="${1:-start}"
case "$cmd" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    echo "Examples:"
    echo "  $0 start"
    echo "  HOST=0.0.0.0 PORT=8000 DEBUG=0 $0 restart"
    exit 2
    ;;
esac


