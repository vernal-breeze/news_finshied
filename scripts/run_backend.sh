#!/bin/bash
# ============================================================
# 后端服务直接启动脚本 (Mac/Linux)
# ============================================================
# 假设依赖已安装，直接启动服务
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
BACKEND_PORT=8000

# 日志函数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  新闻内容采编系统 - 后端服务启动${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查 Python
log_info "检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 未安装"
    exit 1
fi

# 检查虚拟环境