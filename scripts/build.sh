#!/bin/bash
# =============================================================================
# Docker Build CLI - 构建脚本
# 用于本地构建前后端 Docker 镜像
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

# 默认值
SKIP_TESTS=false
NO_CACHE=false
FORCE_REBUILD=false
SERVICES=""

# 使用说明
usage() {
    echo -e "${BLUE}Docker Build CLI - 构建脚本${NC}"
    echo ""
    echo "用法: $0 [选项] [服务...]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示帮助信息"
    echo "  -s, --skip-tests        跳过测试"
    echo "  -n, --no-cache          不使用缓存构建"
    echo "  -f, --force             强制重新构建（即使镜像已存在）"
    echo "  -a, --all               构建所有服务"
    echo ""
    echo "服务 (默认为全部):"
    echo "  backend                构建后端服务"
    echo "  frontend               构建前端服务"
    echo "  qemu-setup             构建 QEMU 注册服务"
    echo ""
    echo "示例:"
    echo "  $0                     # 构建所有服务"
    echo "  $0 backend             # 只构建后端"
    echo "  $0 -n backend frontend # 不使用缓存构建后端和前端"
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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        # 尝试使用 docker compose (v2)
        if docker compose version &> /dev/null; then
            COMPOSE_CMD="docker compose"
        else
            log_error "Docker Compose 未安装"
            exit 1
        fi
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # 检查 Docker 服务
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请先启动 Docker"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -n|--no-cache)
            NO_CACHE=true
            shift
            ;;
        -f|--force)
            FORCE_REBUILD=true
            shift
            ;;
        -a|--all)
            SERVICES=""
            shift
            ;;
        backend|frontend|qemu-setup)
            if [[ -n "$SERVICES" ]]; then
                SERVICES="$SERVICES $1"
            else
                SERVICES="$1"
            fi
            shift
            ;;
        *)
            log_error "未知参数: $1"
            usage
            ;;
    esac
done

# 构建参数
BUILD_ARGS=""
if [[ "$NO_CACHE" == true ]]; then
    BUILD_ARGS="$BUILD_ARGS --no-cache"
fi

# 进入项目目录
cd "$PROJECT_ROOT"

# 检查依赖
check_dependencies

# 确定要构建的服务
if [[ -z "$SERVICES" ]]; then
    BUILD_SERVICES="qemu-setup backend frontend"
else
    BUILD_SERVICES="$SERVICES"
fi

log_info "开始构建服务: $BUILD_SERVICES"

# 构建镜像
for SERVICE in $BUILD_SERVICES; do
    case $SERVICE in
        qemu-setup)
            log_info "构建 QEMU 注册镜像..."
            docker pull multiarch/qemu-user-static:latest
            log_success "QEMU 镜像就绪"
            ;;
        backend)
            log_info "构建后端服务..."
            if [[ "$FORCE_REBUILD" == true || "$NO_CACHE" == true ]]; then
                docker build $BUILD_ARGS -t docker-build-backend:latest -f backend/Dockerfile backend/
            else
                docker build $BUILD_ARGS -t docker-build-backend:latest -f backend/Dockerfile backend/
            fi
            log_success "后端镜像构建完成: docker-build-backend:latest"
            ;;
        frontend)
            log_info "构建前端服务..."
            if [[ "$FORCE_REBUILD" == true || "$NO_CACHE" == true ]]; then
                docker build $BUILD_ARGS -t docker-build-frontend:latest -f frontend/Dockerfile frontend/
            else
                docker build $BUILD_ARGS -t docker-build-frontend:latest -f frontend/Dockerfile frontend/
            fi
            log_success "前端镜像构建完成: docker-build-frontend:latest"
            ;;
        *)
            log_error "未知服务: $SERVICE"
            ;;
    esac
done

log_success "所有镜像构建完成！"
echo ""
echo "构建的镜像:"
docker images | grep docker-build || true
echo ""
log_info "使用 'scripts/deploy.sh start' 启动服务"
