#!/usr/bin/env bash
# 新闻内容采编系统一键启动脚本
# 用法:
#   ./start.sh                 启动前后端
#   ./start.sh backend         仅启动后端
#   ./start.sh frontend        仅启动前端
#   ./start.sh stop            停止服务
#   ./start.sh restart         重启服务
#   ./start.sh status          查看状态
#   ./start.sh logs [backend|frontend]

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_HEALTH_PATH="${BACKEND_HEALTH_PATH:-/health}"
UVICORN_RELOAD="${UVICORN_RELOAD:-0}"

BACKEND_PID_FILE="/tmp/news_editor_backend.pid"
FRONTEND_PID_FILE="/tmp/news_editor_frontend.pid"
BACKEND_LOG_FILE="/tmp/news_editor_backend.log"
FRONTEND_LOG_FILE="/tmp/news_editor_frontend.log"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }

has_cmd() {
    command -v "$1" >/dev/null 2>&1
}

pid_alive() {
    local pid="$1"
    kill -0 "${pid}" >/dev/null 2>&1
}

port_pids() {
    local port="$1"
    lsof -t -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ' || true
}

wait_http_up() {
    local url="$1"
    local retries="${2:-20}"
    local i=0
    while [ "${i}" -lt "${retries}" ]; do
        if curl -fsS "${url}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        i=$((i + 1))
    done
    return 1
}

stop_by_pid_file() {
    local pid_file="$1"
    local name="$2"
    if [ -f "${pid_file}" ]; then
        local pid
        pid="$(cat "${pid_file}" 2>/dev/null || true)"
        if [ -n "${pid}" ] && pid_alive "${pid}"; then
            kill "${pid}" >/dev/null 2>&1 || true
            sleep 1
            if pid_alive "${pid}"; then
                kill -9 "${pid}" >/dev/null 2>&1 || true
            fi
            log_ok "${name} 已停止 (PID: ${pid})"
        fi
        rm -f "${pid_file}"
    fi
}

stop_by_port() {
    local port="$1"
    local name="$2"
    local pids
    pids="$(port_pids "${port}")"
    if [ -n "${pids}" ]; then
        log_warn "${name} 端口 ${port} 被占用，正在清理: ${pids}"
        kill ${pids} >/dev/null 2>&1 || true
        sleep 1
        pids="$(port_pids "${port}")"
        if [ -n "${pids}" ]; then
            kill -9 ${pids} >/dev/null 2>&1 || true
            sleep 1
        fi
        if [ -z "$(port_pids "${port}")" ]; then
            log_ok "${name} 端口 ${port} 已释放"
        else
            log_error "${name} 端口 ${port} 释放失败，请手动处理"
            exit 1
        fi
    fi
}

check_python() {
    if ! has_cmd python3; then
        log_error "未检测到 python3，请先安装 Python 3.10+"
        exit 1
    fi
    local py_ver
    py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    local major minor
    major="$(python3 -c 'import sys;print(sys.version_info.major)')"
    minor="$(python3 -c 'import sys;print(sys.version_info.minor)')"
    if [ "${major}" -lt 3 ] || { [ "${major}" -eq 3 ] && [ "${minor}" -lt 10 ]; }; then
        log_error "Python 版本过低: ${py_ver}，需要 3.10+"
        exit 1
    fi
    log_ok "Python ${py_ver}"
}

check_node() {
    if ! has_cmd node; then
        log_error "未检测到 Node.js，请先安装 Node.js"
        exit 1
    fi
    if ! has_cmd npm; then
        log_error "未检测到 npm，请先安装 npm"
        exit 1
    fi
    log_ok "Node $(node -v)"
}

check_env_file() {
    if [ -f "${BACKEND_DIR}/.env" ]; then
        log_ok "环境配置已就绪"
        return
    fi
    if [ ! -f "${BACKEND_DIR}/.env.example" ]; then
        log_warn "未找到 .env.example 模板"
        return
    fi
    echo ""
    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│  首次使用提示                                           │${NC}"
    echo -e "${YELLOW}│                                                         │${NC}"
    echo -e "${YELLOW}│  ${NC}检测到缺少环境变量文件，正在创建...                      ${YELLOW}│${NC}"
    echo -e "${YELLOW}│  ${NC}后端会使用默认配置启动，部分 AI 功能需 API Key              ${YELLOW}│${NC}"
    echo -e "${YELLOW}│                                                         │${NC}"
    echo -e "${YELLOW}│  ${NC}如需使用 AI 功能，请编辑 ${BLUE}backend/.env${NC} 填入:          ${YELLOW}│${NC}"
    echo -e "${YELLOW}│  ${NC}  SILICONFLOW_API_KEY=sk-xxx                            ${YELLOW}│${NC}"
    echo -e "${YELLOW}│  ${NC}免费注册 → https://cloud.siliconflow.cn/                  ${YELLOW}│${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${NC}"
    echo ""
    cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
    log_ok "已自动创建 backend/.env，可后续编辑填入 API Key"
}

ensure_backend_deps() {
    cd "${BACKEND_DIR}"

    # 尝试使用 venv；若 venv 不可用则回退到系统 Python
    if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "${BACKEND_DIR}/venv/bin/activate"
    else
        # venv 不存在或不完整，检查系统 Python 是否有依赖
        if python3 -c "import fastapi, uvicorn, sqlalchemy, requests, bs4" 2>/dev/null; then
            log_ok "使用系统 Python（依赖已就绪）"
            return
        fi
        # 系统 Python 缺少依赖，尝试安装
        log_warn "将使用系统 Python 安装依赖 (--break-system-packages)"
        export PIP_BREAK_SYSTEM_PACKAGES=1
    fi

    # 默认离线友好：依赖可用就跳过联网安装
    if [ "${FORCE_INSTALL:-0}" != "1" ] && python3 - <<'PY'
import importlib.util as u
mods = ["fastapi", "uvicorn", "sqlalchemy", "requests", "bs4", "pydantic", "pydantic_settings"]
missing = [m for m in mods if u.find_spec(m) is None]
raise SystemExit(1 if missing else 0)
PY
    then
        log_ok "后端依赖已就绪，跳过安装"
        return
    fi

    log_info "安装/更新后端依赖..."
    python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
    if ! python3 -m pip install -r requirements.txt; then
        log_error "后端依赖安装失败（网络不可用或镜像异常）。如已安装依赖可重试启动，或设置 FORCE_INSTALL=1 再执行。"
        exit 1
    fi
}

ensure_frontend_deps() {
    cd "${FRONTEND_DIR}"
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    fi
}

init_database() {
    cd "${BACKEND_DIR}"
    # shellcheck disable=SC1091
    if [ -f "${BACKEND_DIR}/venv/bin/activate" ]; then
        source "${BACKEND_DIR}/venv/bin/activate"
    else
        export PATH="$(echo "$PATH" | sed "s|${BACKEND_DIR}/venv/bin:||g")"
    fi
    export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH:-}"
    mkdir -p data
    python3 -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)" >/dev/null
    log_ok "数据库初始化完成"
}

start_backend() {
    cd "${BACKEND_DIR}"
    # shellcheck disable=SC1091
    if [ -f "${BACKEND_DIR}/venv/bin/activate" ]; then
        source "${BACKEND_DIR}/venv/bin/activate"
    else
        # venv 不完整，确保使用系统命令而非 venv 残留
        export PATH="$(echo "$PATH" | sed "s|${BACKEND_DIR}/venv/bin:||g")"
    fi
    stop_by_pid_file "${BACKEND_PID_FILE}" "后端服务"
    stop_by_port "${BACKEND_PORT}" "后端服务"
    export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH:-}"
    export DEBUG="${DEBUG:-true}"
    export ENVIRONMENT="${ENVIRONMENT:-development}"
    export SECRET_KEY="${SECRET_KEY:-dev-local-key}"
    log_info "启动后端服务..."

    local uvicorn_args=(app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}")
    if [ "${UVICORN_RELOAD}" = "1" ]; then
        uvicorn_args+=(--reload)
    fi

    nohup uvicorn "${uvicorn_args[@]}" >"${BACKEND_LOG_FILE}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${BACKEND_PID_FILE}"
    if wait_http_up "http://127.0.0.1:${BACKEND_PORT}${BACKEND_HEALTH_PATH}" 40; then
        log_ok "后端已启动: http://localhost:${BACKEND_PORT} (PID: ${pid})"
    else
        if [ -f "${BACKEND_LOG_FILE}" ]; then
            log_warn "后端日志摘要:"
            tail -n 30 "${BACKEND_LOG_FILE}" || true
        fi
        log_error "后端启动失败，日志见 ${BACKEND_LOG_FILE}"
        exit 1
    fi
}

start_frontend() {
    cd "${FRONTEND_DIR}"
    stop_by_pid_file "${FRONTEND_PID_FILE}" "前端服务"
    stop_by_port "${FRONTEND_PORT}" "前端服务"
    log_info "启动前端服务..."
    nohup npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" >"${FRONTEND_LOG_FILE}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${FRONTEND_PID_FILE}"
    if wait_http_up "http://127.0.0.1:${FRONTEND_PORT}" 30; then
        log_ok "前端已启动: http://localhost:${FRONTEND_PORT} (PID: ${pid})"
    else
        log_warn "前端正在启动中，日志见 ${FRONTEND_LOG_FILE}"
    fi
}

stop_services() {
    log_info "停止服务..."
    stop_by_pid_file "${BACKEND_PID_FILE}" "后端服务"
    stop_by_pid_file "${FRONTEND_PID_FILE}" "前端服务"
    stop_by_port "${BACKEND_PORT}" "后端服务"
    stop_by_port "${FRONTEND_PORT}" "前端服务"
    log_ok "停止完成"
}

show_status() {
    echo ""
    echo -e "${CYAN}========== 服务状态 ==========${NC}"
    if [ -f "${BACKEND_PID_FILE}" ] && pid_alive "$(cat "${BACKEND_PID_FILE}")"; then
        echo -e "${GREEN}后端: 运行中${NC} PID=$(cat "${BACKEND_PID_FILE}") URL=http://localhost:${BACKEND_PORT}"
    elif [ -n "$(port_pids "${BACKEND_PORT}")" ]; then
        echo -e "${YELLOW}后端: 端口占用${NC} PORT=${BACKEND_PORT} PID=$(port_pids "${BACKEND_PORT}")"
    else
        echo -e "${RED}后端: 未运行${NC}"
    fi

    if [ -f "${FRONTEND_PID_FILE}" ] && pid_alive "$(cat "${FRONTEND_PID_FILE}")"; then
        echo -e "${GREEN}前端: 运行中${NC} PID=$(cat "${FRONTEND_PID_FILE}") URL=http://localhost:${FRONTEND_PORT}"
    elif [ -n "$(port_pids "${FRONTEND_PORT}")" ]; then
        echo -e "${YELLOW}前端: 端口占用${NC} PORT=${FRONTEND_PORT} PID=$(port_pids "${FRONTEND_PORT}")"
    else
        echo -e "${RED}前端: 未运行${NC}"
    fi
    echo -e "${CYAN}日志:${NC}"
    echo "  后端: ${BACKEND_LOG_FILE}"
    echo "  前端: ${FRONTEND_LOG_FILE}"
    echo ""
}

show_logs() {
    local svc="${1:-all}"
    case "${svc}" in
        backend)
            tail -f "${BACKEND_LOG_FILE}"
            ;;
        frontend)
            tail -f "${FRONTEND_LOG_FILE}"
            ;;
        all|*)
            log_info "后端日志: ${BACKEND_LOG_FILE}"
            tail -n 80 "${BACKEND_LOG_FILE}" 2>/dev/null || true
            echo ""
            log_info "前端日志: ${FRONTEND_LOG_FILE}"
            tail -n 80 "${FRONTEND_LOG_FILE}" 2>/dev/null || true
            ;;
    esac
}

usage() {
    cat <<EOF
用法:
  ./start.sh [backend|frontend|stop|restart|status|logs|check|all]
示例:
  ./start.sh
  ./start.sh backend
  ./start.sh stop
  ./start.sh logs backend
EOF
}

main() {
    local cmd="${1:-all}"
    case "${cmd}" in
        backend)
            check_env_file
            check_python
            ensure_backend_deps
            init_database
            start_backend
            ;;
        frontend)
            check_node
            ensure_frontend_deps
            start_frontend
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            check_env_file
            check_python
            check_node
            ensure_backend_deps
            ensure_frontend_deps
            init_database
            start_backend
            start_frontend
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-all}"
            ;;
        check)
            if ! wait_http_up "http://127.0.0.1:${BACKEND_PORT}${BACKEND_HEALTH_PATH}" 2; then
                log_error "后端未运行，请先执行 ./start.sh backend 或 ./start.sh"
                exit 1
            fi
            python3 - <<PY
import requests
base = "http://127.0.0.1:${BACKEND_PORT}"
status = requests.get(base + "${BACKEND_HEALTH_PATH}", timeout=5).status_code
print("status_code=", status)
try:
    r = requests.post(base + "/api/clues/collect/multichannel", params={
        "keywords": "人工智能",
        "channels": "news",
        "max_results": 3,
    }, timeout=20)
    print("clue_collect_code=", r.status_code)
    data = r.json().get("data", {})
    print("clue_collect_created=", data.get("created"))
except Exception as e:
    print("clue_collect_error=", str(e))
PY
            ;;
        all)
            check_env_file
            check_python
            check_node
            ensure_backend_deps
            ensure_frontend_deps
            init_database
            start_backend
            start_frontend
            echo ""
            echo -e "${GREEN}启动完成${NC}"
            echo -e "前端: ${BLUE}http://localhost:${FRONTEND_PORT}${NC}"
            echo -e "后端: ${BLUE}http://localhost:${BACKEND_PORT}${NC}"
            echo -e "文档: ${BLUE}http://localhost:${BACKEND_PORT}/docs${NC}"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"
