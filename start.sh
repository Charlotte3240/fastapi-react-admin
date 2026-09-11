#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${PROJECT_DIR}/.run"
API_PID_FILE="${RUN_DIR}/api.pid"
WORKER_PID_FILE="${RUN_DIR}/worker.pid"
WEB_PID_FILE="${RUN_DIR}/web.pid"
API_LOG="${RUN_DIR}/api.log"
WORKER_LOG="${RUN_DIR}/worker.log"
WEB_LOG="${RUN_DIR}/web.log"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-8001}"

cd "${PROJECT_DIR}"

usage() {
  cat <<'EOF'
用法：./start.sh [命令]

  start     执行数据库迁移并启动 API、Worker、Web（默认）
  stop      停止本脚本启动的全部进程
  restart   重启全部进程
  status    查看运行状态
  logs      持续查看全部日志（Ctrl+C 退出）
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令：$1" >&2
    exit 1
  fi
}

is_running() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] && kill -0 "$(<"${pid_file}")" 2>/dev/null
}

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_port() {
  local name="$1" port="$2" pid_file="$3"
  for _ in {1..40}; do
    if port_in_use "${port}"; then
      return 0
    fi
    if ! is_running "${pid_file}"; then
      echo "${name} 启动失败，请查看 ${RUN_DIR}/${name}.log" >&2
      return 1
    fi
    sleep 0.25
  done
  echo "等待 ${name} 监听 ${port} 端口超时" >&2
  return 1
}

start_process() {
  local name="$1" pid_file="$2" log_file="$3"
  shift 3
  if is_running "${pid_file}"; then
    echo "${name} 已运行，PID $(<"${pid_file}")"
    return 0
  fi
  rm -f "${pid_file}"
  nohup "$@" >>"${log_file}" 2>&1 &
  echo "$!" >"${pid_file}"
  echo "已启动 ${name}，PID $!"
}

stop_process() {
  local name="$1" pid_file="$2"
  if ! is_running "${pid_file}"; then
    rm -f "${pid_file}"
    echo "${name} 未运行"
    return 0
  fi
  local pid
  pid="$(<"${pid_file}")"
  pkill -TERM -P "${pid}" 2>/dev/null || true
  kill -TERM "${pid}" 2>/dev/null || true
  for _ in {1..20}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      break
    fi
    sleep 0.25
  done
  if kill -0 "${pid}" 2>/dev/null; then
    kill -KILL "${pid}" 2>/dev/null || true
  fi
  rm -f "${pid_file}"
  echo "已停止 ${name}"
}

run_migrations() {
  echo "正在执行数据库迁移……"
  (
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_DIR}/.env"
    set +a
    cd "${PROJECT_DIR}/apps/api"
    uv run alembic upgrade head
  )
}

start_all() {
  require_command uv
  require_command pnpm
  require_command lsof
  if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
    echo "缺少 .env，请先从 .env.example 复制并填写配置" >&2
    exit 1
  fi
  if port_in_use "${API_PORT}" && ! is_running "${API_PID_FILE}"; then
    echo "${API_PORT} 端口已被其他进程占用，可通过 API_PORT 指定其他端口" >&2
    exit 1
  fi
  if port_in_use "${WEB_PORT}" && ! is_running "${WEB_PID_FILE}"; then
    echo "${WEB_PORT} 端口已被其他进程占用，可通过 WEB_PORT 指定其他端口" >&2
    exit 1
  fi

  mkdir -p "${RUN_DIR}"
  run_migrations
  start_process api "${API_PID_FILE}" "${API_LOG}" \
    uv run uvicorn unibiz.main:app --host 127.0.0.1 --port "${API_PORT}" --reload
  if ! wait_for_port api "${API_PORT}" "${API_PID_FILE}"; then
    stop_all
    exit 1
  fi
  start_process worker "${WORKER_PID_FILE}" "${WORKER_LOG}" uv run python -m unibiz.worker
  start_process web "${WEB_PID_FILE}" "${WEB_LOG}" env \
    UNIBIZ_API_TARGET="http://localhost:${API_PORT}" PORT="${WEB_PORT}" pnpm --dir apps/web dev
  if ! wait_for_port web "${WEB_PORT}" "${WEB_PID_FILE}"; then
    stop_all
    exit 1
  fi

  echo
  echo "UniBiz 已启动："
  echo "  Web:     http://localhost:${WEB_PORT}"
  echo "  API:     http://localhost:${API_PORT}"
  echo "  Swagger: http://localhost:${API_PORT}/docs"
  echo "  日志:    ./start.sh logs"
  echo "  停止:    ./start.sh stop"
}

stop_all() {
  stop_process web "${WEB_PID_FILE}"
  stop_process worker "${WORKER_PID_FILE}"
  stop_process api "${API_PID_FILE}"
}

show_status() {
  local name pid_file
  for entry in "API:${API_PID_FILE}" "Worker:${WORKER_PID_FILE}" "Web:${WEB_PID_FILE}"; do
    name="${entry%%:*}"
    pid_file="${entry#*:}"
    if is_running "${pid_file}"; then
      echo "${name}: 运行中（PID $(<"${pid_file}")）"
    else
      echo "${name}: 未运行"
    fi
  done
}

show_logs() {
  mkdir -p "${RUN_DIR}"
  touch "${API_LOG}" "${WORKER_LOG}" "${WEB_LOG}"
  tail -n 100 -F "${API_LOG}" "${WORKER_LOG}" "${WEB_LOG}"
}

case "${1:-start}" in
  start) start_all ;;
  stop) stop_all ;;
  restart) stop_all; start_all ;;
  status) show_status ;;
  logs) show_logs ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac
