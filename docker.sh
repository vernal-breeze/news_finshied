#!/bin/bash
# ============================================================
# 新闻内容采编系统 - Docker 操作脚本
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 .env 文件
check_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}[提示] 未找到 .env 文件，正在从模板创建...${NC}"
        cp .env.example .env
        echo -e "${GREEN}[完成] 已创建 .env，请根据需要修改配置${NC}"
    fi
}

# 启动全部服务
start() {
    check_env
    echo -e "${GREEN}[启动] 正在启动所有服务...${NC}"
    docker compose up -d --build
    echo ""
    echo -e "${GREEN}[完成] 服务已启动:${NC}"
    echo "  前端: http://localhost:${FRONTEND_PORT:-3000}"
    echo "  后端: http://localhost:${BACKEND_PORT:-8000}"
    echo "  MySQL: localhost:${MYSQL_PORT:-3306}"
    echo ""
    echo "查看日志: $0 logs"
    echo "查看状态: $0 status"
}

# 停止全部服务
stop() {
    echo -e "${YELLOW}[停止] 正在停止所有服务...${NC}"
    docker compose down
    echo -e "${GREEN}[完成] 所有服务已停止${NC}"
}

# 查看日志
logs() {
    local service="${1:-backend}"
    docker compose logs -f "$service"
}

# 查看状态
status() {
    echo -e "${GREEN}[状态] 服务运行状态:${NC}"
    docker compose ps
    echo ""
    echo -e "${GREEN}[健康检查]${NC}"
    docker compose ps --format "table {{.Name}}\t{{.Status}}"
}

# 重建并重启
rebuild() {
    echo -e "${YELLOW}[重建] 正在重新构建并启动...${NC}"
    docker compose up -d --build --force-recreate
    echo -e "${GREEN}[完成] 重建完成${NC}"
}

# 清除所有数据（包括数据库）
clean() {
    echo -e "${RED}[警告] 此操作将删除所有容器和数据卷（包括数据库数据）${NC}"
    read -p "确认清除? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker compose down -v
        echo -e "${GREEN}[完成] 所有容器和数据已清除${NC}"
    else
        echo -e "${YELLOW}[取消] 操作已取消${NC}"
    fi
}

# 连接 MySQL 命令行
mysql_cli() {
    echo -e "${GREEN}[MySQL] 连接到数据库...${NC}"
    docker compose exec mysql mysql -u news_editor -p"${MYSQL_PASSWORD:-apppass123}" news_editor
}

# 数据库备份
backup() {
    local backup_dir="./backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$backup_dir"
    echo -e "${GREEN}[备份] 正在备份数据库...${NC}"
    docker compose exec mysql mysqldump -u root -p"${MYSQL_ROOT_PASSWORD:-rootpass123}" \
        --single-transaction news_editor | gzip > "$backup_dir/news_editor_${timestamp}.sql.gz"
    echo -e "${GREEN}[完成] 备份已保存: ${backup_dir}/news_editor_${timestamp}.sql.gz${NC}"
}

# 帮助信息
help() {
    echo "新闻内容采编系统 - Docker 操作脚本"
    echo ""
    echo "用法: $0 <命令>"
    echo ""
    echo "命令:"
    echo "  start     启动所有服务（自动创建 .env）"
    echo "  stop      停止所有服务"
    echo "  status    查看服务状态"
    echo "  logs      查看后端日志（默认）"
    echo "  logs <s>  查看指定服务日志（mysql/backend/frontend）"
    echo "  rebuild   重新构建并启动"
    echo "  clean     清除所有容器和数据（⚠️ 危险）"
    echo "  mysql     连接 MySQL 命令行"
    echo "  backup    备份数据库"
    echo "  help      显示此帮助"
}

# 主入口
case "${1:-help}" in
    start)    start ;;
    stop)     stop ;;
    status)   status ;;
    logs)     logs "${2:-backend}" ;;
    rebuild)  rebuild ;;
    clean)    clean ;;
    mysql)    mysql_cli ;;
    backup)   backup ;;
    help|*)   help ;;
esac
