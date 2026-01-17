#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
DEBUG="${DEBUG:-0}"

function stop() {
  pids=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true
  [[ -f .run.pid ]] && kill -9 "$(cat .run.pid 2>/dev/null)" 2>/dev/null || true
  rm -f .run.pid
  echo "stopped"
}

function start() {
  stop
  
  # 只在首次创建 venv 时安装依赖
  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    ./.venv/bin/pip install -q -r requirements.txt
  fi
  
  # 启动服务
  echo "starting... http://${HOST}:${PORT}"
  cd "$ROOT_DIR"
  PYTHONPATH="${ROOT_DIR}/backend:${PYTHONPATH:-}" \
  HOST="${HOST}" PORT="${PORT}" DEBUG="${DEBUG}" \
  nohup ./.venv/bin/python backend/app.py >server.log 2>&1 </dev/null &
  local new_pid=$!
  echo $new_pid > .run.pid
  
  # 等待一下，确认进程还在运行
  sleep 2
  if ps -p "$new_pid" >/dev/null 2>&1; then
    # 再等一秒确认端口监听
    sleep 1
    if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
      echo "✓ running: pid=$new_pid http://${HOST}:${PORT}"
      echo "log: server.log"
    else
      echo "⚠ process started but port not listening yet (check server.log)"
      echo "pid=$new_pid"
    fi
  else
    echo "✗ failed to start (check server.log)"
    tail -n 20 server.log 2>/dev/null || true
    exit 1
  fi
}

function status() {
  if [[ -f .run.pid ]] && ps -p "$(cat .run.pid 2>/dev/null)" >/dev/null 2>&1; then
    echo "running: pid=$(cat .run.pid) http://${HOST}:${PORT}"
  else
    echo "not running"
  fi
}

cmd="${1:-}"
case "$cmd" in
  start) start ;;
  stop) stop ;;
  restart) start ;;
  status) status ;;
  "")
    echo "Usage: $0 {start|stop|restart|status}"
    echo ""
    echo "Commands:"
    echo "  ./run.sh start    - 启动服务"
    echo "  ./run.sh stop     - 停止服务"
    echo "  ./run.sh restart  - 重启服务"
    echo "  ./run.sh status   - 查看状态"
    exit 0
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
