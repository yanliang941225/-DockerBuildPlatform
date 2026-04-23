#!/bin/bash
# =============================================================================
# Docker Build CLI - 部署脚本
# 用于一键部署 Docker Build 服务
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
ENV_FILE="${PROJECT_ROOT}/.env"

# 使用说明
usage() {
    echo -e "${BLUE}${BOLD}Docker Build CLI - 部署脚本${NC}"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  ${GREEN}start${NC}       启动所有服务"
    echo "  ${GREEN}stop${NC}        停止所有服务"
    echo "  ${GREEN}restart${NC}     重启所有服务"
    echo "  ${GREEN}logs${NC}         查看服务日志"
    echo "  ${GREEN}status${NC}       查看服务状态"
    echo "  ${GREEN}clean${NC}         清理资源（停止并删除容器、卷）"
    echo "  ${GREEN}init${NC}          初始化环境（首次部署）"
    echo "  ${GREEN}update${NC}        更新并重启服务"
    echo "  ${GREEN}ssh${NC}           进入后端容器"
    echo "  ${GREEN}health${NC}        检查服务健康状态"
    echo ""
    echo "选项:"
    echo "  --help, -h    显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 init                   # 首次部署，初始化环境"
    echo "  $0 start                  # 启动服务"
    echo "  $0 logs -f backend        # 查看后端日志"
    echo "  $0 update                 # 更新并重启"
    exit 0
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# 打印分隔线
print_line() {
    echo "============================================"
}

# 检查 Docker Compose 命令
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        log_error "Docker Compose 未安装"
        exit 1
    fi
}

# 检查环境配置
check_env() {
    log_info "检查环境配置..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warn ".env 文件不存在，正在创建..."
        cp "${ENV_FILE}.example" "$ENV_FILE" 2>/dev/null || \
        cat > "$ENV_FILE" << 'EOF'
# Docker Build 环境配置
# 复制此文件为 .env 并根据需要修改

# ============================================
# 存储配置
# ============================================
# 存储类型: auto（自动选择）, local（本地存储）, qiniu（七牛云）
STORAGE_TYPE=local

# 七牛云配置（STORAGE_TYPE=auto 或 qiniu 时需要）
QINIU_ACCESS_KEY=your_access_key_here
QINIU_SECRET_KEY=your_secret_key_here
QINIU_BUCKET=docker-build-files
QINIU_REGION=z0

# ============================================
# 服务配置
# ============================================
HOST=0.0.0.0
PORT=8000

# ============================================
# 文件配置
# ============================================
FILE_EXPIRE_HOURS=5
MAX_FILE_SIZE_MB=500
MAX_CONTEXT_SIZE_MB=500

# ============================================
# 安全配置
# ============================================
RATE_LIMIT_PER_MINUTE=30
SESSION_TTL_HOURS=5
MAX_TASKS_PER_USER=10
MAX_CONCURRENT_BUILDS_PER_USER=2
EOF
        log_warn "请编辑 $ENV_FILE 配置文件"
    fi
    
    # 检查 Docker
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请先启动 Docker"
        exit 1
    fi
    
    log_success "环境检查通过"
}

# 初始化环境
init_env() {
    log_step "初始化 Docker Build 环境..."
    print_line
    
    # 检查环境
    check_env
    
    # 检查 Docker BuildX
    log_info "检查 Docker BuildX..."
    if docker buildx version &> /dev/null; then
        log_success "Docker BuildX 已安装"
    else
        log_error "Docker BuildX 未安装，请升级 Docker"
        exit 1
    fi
    
    # 创建 BuildX 构建器
    log_info "配置 Docker BuildX..."
    docker buildx create --use default 2>/dev/null || true
    docker buildx inspect --bootstrap &> /dev/null || \
        docker buildx create --name default --driver docker-container --use 2>/dev/null || true
    
    log_success "BuildX 配置完成"
    
    # 拉取 QEMU 镜像
    log_info "拉取 QEMU 跨架构支持镜像..."
    docker pull multiarch/qemu-user-static:latest --quiet
    log_success "QEMU 镜像就绪"
    
    # 创建必要目录
    log_info "创建数据目录..."
    mkdir -p "${PROJECT_ROOT}/data/storage"
    mkdir -p "${PROJECT_ROOT}/data/builds"
    mkdir -p "${PROJECT_ROOT}/data/results"
    
    log_success "数据目录创建完成"
    print_line
    log_success "初始化完成！"
    echo ""
    echo -e "${GREEN}下一步:${NC}"
    echo "  1. 编辑 .env 文件配置存储选项"
    echo "  2. 运行 '$0 start' 启动服务"
}

# 启动服务
start_services() {
    log_step "启动 Docker Build 服务..."
    print_line
    
    local COMPOSE_CMD=$(get_compose_cmd)
    
    # 启动服务
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    
    log_success "服务启动中..."
    echo ""
    
    # 等待服务启动
    sleep 3
    
    # 显示状态
    status_services
}

# 停止服务
stop_services() {
    log_step "停止 Docker Build 服务..."
    print_line
    
    local COMPOSE_CMD=$(get_compose_cmd)
    
    $COMPOSE_CMD -f "$COMPOSE_FILE" stop
    
    log_success "服务已停止"
}

# 重启服务
restart_services() {
    log_step "重启 Docker Build 服务..."
    print_line
    
    local COMPOSE_CMD=$(get_compose_cmd)
    
    $COMPOSE_CMD -f "$COMPOSE_FILE" restart
    
    log_success "服务已重启"
    echo ""
    status_services
}

# 查看日志
show_logs() {
    local SERVICE=${1:-""}
    local COMPOSE_CMD=$(get_compose_cmd)
    
    if [[ -n "$SERVICE" ]]; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f "$SERVICE"
    else
        $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f
    fi
}

# 查看状态
status_services() {
    log_step "服务状态"
    print_line
    
    local COMPOSE_CMD=$(get_compose_cmd)
    
    echo -e "${BOLD}容器状态:${NC}"
    $COMPOSE_CMD -f "$COMPOSE_FILE" ps
    
    echo ""
    echo -e "${BOLD}镜像状态:${NC}"
    docker images | grep docker-build || echo "  (无自定义镜像)"
    
    echo ""
    echo -e "${BOLD}访问地址:${NC}"
    echo "  前端: http://localhost:3000"
    echo "  后端 API: http://localhost:8000"
    echo "  API 文档: http://localhost:8000/api/docs"
}

# 健康检查
health_check() {
    log_step "健康检查"
    print_line
    
    local BACKEND_URL="http://localhost:8000/api/health"
    local FRONTEND_URL="http://localhost:3000"
    
    # 检查后端
    echo -n "后端 API: "
    if curl -sf "$BACKEND_URL" &> /dev/null; then
        log_success "正常"
    else
        log_error "不可用"
    fi
    
    # 检查前端
    echo -n "前端服务: "
    if curl -sf "$FRONTEND_URL" &> /dev/null; then
        log_success "正常"
    else
        log_error "不可用"
    fi
}

# 清理资源
clean_resources() {
    log_warn "即将清理所有 Docker Build 资源..."
    echo "这将:"
    echo "  1. 停止所有服务"
    echo "  2. 删除所有容器"
    echo "  3. 删除所有数据卷"
    echo ""
    read -p "确认清理? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        local COMPOSE_CMD=$(get_compose_cmd)
        
        $COMPOSE_CMD -f "$COMPOSE_FILE" down -v --remove-orphans
        
        log_success "资源已清理"
    else
        log_info "已取消"
    fi
}

# 进入后端容器
ssh_backend() {
    docker exec -it docker-build-backend /bin/bash
}

# 更新服务
update_services() {
    log_step "更新 Docker Build 服务..."
    print_line
    
    local COMPOSE_CMD=$(get_compose_cmd)
    
    # 拉取最新代码
    log_info "拉取最新代码..."
    cd "$PROJECT_ROOT"
    if git rev-parse &> /dev/null; then
        git pull origin main 2>/dev/null || log_warn "无法拉取代码，请手动更新"
    fi
    
    # 重启服务
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d --remove-orphans
    
    log_success "更新完成！"
    echo ""
    status_services
}

# 主命令处理
COMMAND=${1:-}

case $COMMAND in
    init)
        init_env
        ;;
    start)
        check_env
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    status)
        status_services
        ;;
    clean)
        clean_resources
        ;;
    update)
        check_env
        update_services
        ;;
    ssh)
        ssh_backend
        ;;
    health)
        health_check
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        if [[ -n "$COMMAND" ]]; then
            log_error "未知命令: $COMMAND"
        fi
        usage
        ;;
esac
