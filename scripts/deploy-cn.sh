# Docker Build Platform - 完整部署脚本（国内镜像加速版）
# 使用方法: ./scripts/deploy-cn.sh

#!/bin/bash
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

# =============================================================================
# 配置国内镜像源
# =============================================================================

configure_docker_mirror() {
    log_info "配置 Docker 国内镜像加速..."
    
    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi
    
    # 检测操作系统类型
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - 检查 Docker Desktop 配置
        log_info "检测到 macOS 系统"
        
        # 尝试通过命令行配置 Docker Desktop
        if command -v docker &> /dev/null; then
            # Docker Desktop for Mac 可以通过 defaults 命令配置
            DOCKER_CONF="$HOME/Library/Containers/com.docker.docker/Data/docker-desktop.json"
            
            if [ -f "$DOCKER_CONF" ]; then
                log_info "找到 Docker Desktop 配置: $DOCKER_CONF"
            else
                log_warn "请手动配置 Docker Desktop: 打开 Docker Desktop -> Settings -> Docker Engine"
                log_warn "添加以下配置:"
                echo ""
                cat << 'EOF'
{
  "registry-mirrors": [
    "https://docker.npmmirror.com",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
                echo ""
            fi
        fi
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        log_info "检测到 Linux 系统"
        
        DOCKER_CONF="/etc/docker/daemon.json"
        
        if [ -w "$DOCKER_CONF" ] || [ -w "$(dirname "$DOCKER_CONF")" ]; then
            log_info "配置 Docker 镜像加速..."
            
            # 创建配置目录
            sudo mkdir -p /etc/docker 2>/dev/null || true
            
            # 备份现有配置
            if [ -f "$DOCKER_CONF" ]; then
                sudo cp "$DOCKER_CONF" "${DOCKER_CONF}.bak.$(date +%Y%m%d%H%M%S)"
            fi
            
            # 写入新配置
            sudo tee "$DOCKER_CONF" > /dev/null << 'EOF'
{
  "registry-mirrors": [
    "https://docker.npmmirror.com",
    "https://mirror.ccs.tencentyun.com",
    "https://dockerhub.azk8s.cn",
    "https://reg-mirror.qiniu.com"
  ]
}
EOF
            
            # 重启 Docker
            log_info "重启 Docker 服务..."
            sudo systemctl restart docker 2>/dev/null || \
            sudo service docker restart 2>/dev/null || \
            log_warn "请手动重启 Docker 服务"
            
            log_success "Docker 镜像加速配置完成"
        else
            log_warn "无法写入 $DOCKER_CONF，请手动配置"
        fi
    fi
    
    # 验证配置
    log_info "验证 Docker 镜像源..."
    docker info 2>/dev/null | grep -A 10 "Registry Mirrors" || log_info "使用默认镜像源"
}

# =============================================================================
# 配置 BuildX 和 QEMU
# =============================================================================

setup_buildx() {
    log_info "配置 Docker BuildX..."
    
    # 创建构建器
    docker buildx create --name cn-builder --driver docker-container --use 2>/dev/null || \
    docker buildx use default 2>/dev/null || true
    
    # 启动构建器
    docker buildx inspect --bootstrap 2>/dev/null || true
    
    log_success "BuildX 配置完成"
}

setup_qemu() {
    log_info "配置 QEMU 跨架构支持..."
    
    # 使用国内镜像
    docker pull multiarch/qemu-user-static:latest --disable-content-trust 2>/dev/null || \
    docker pull docker.io/multiarch/qemu-user-static:latest
    
    # 注册 QEMU
    docker run --rm --privileged \
        multiarch/qemu-user-static:latest \
        --reset -p yes --credential yes
    
    log_success "QEMU 配置完成"
}

# =============================================================================
# 构建镜像（使用国内源）
# =============================================================================

build_images() {
    log_info "构建 Docker 镜像（使用国内镜像源）..."
    
    cd "$PROJECT_ROOT"
    
    # 拉取基础镜像（带超时重试）
    log_info "拉取 Python 基础镜像..."
    docker pull python:3.11-slim 2>/dev/null || \
    docker pull registry.docker-cn.com/library/python:3.11-slim 2>/dev/null || true
    
    log_info "拉取 Node 基础镜像..."
    docker pull node:20-alpine 2>/dev/null || \
    docker pull registry.docker-cn.com/library/node:20-alpine 2>/dev/null || true
    
    log_info "拉取 Nginx 基础镜像..."
    docker pull nginx:alpine 2>/dev/null || \
    docker pull registry.docker-cn.com/library/nginx:alpine 2>/dev/null || true
    
    # 构建镜像
    log_info "构建后端镜像..."
    docker build -t docker-build-backend:latest -f backend/Dockerfile backend/
    
    log_info "构建前端镜像..."
    docker build -t docker-build-frontend:latest -f frontend/Dockerfile frontend/
    
    log_success "镜像构建完成"
}

# =============================================================================
# 启动服务
# =============================================================================

start_services() {
    log_info "启动服务..."
    
    cd "$PROJECT_ROOT"
    
    # 确保 .env 存在
    if [ ! -f ".env" ]; then
        cp .env.example .env
        log_warn "已创建 .env 文件，请根据需要修改"
    fi
    
    # 启动服务
    docker compose up -d
    
    log_success "服务启动成功！"
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:3000"
    echo "  后端: http://localhost:8000"
    echo "  API文档: http://localhost:8000/api/docs"
}

# =============================================================================
# 主流程
# =============================================================================

main() {
    echo ""
    echo "============================================"
    echo "  Docker Build Platform - 快速部署"
    echo "  使用国内镜像源加速"
    echo "============================================"
    echo ""
    
    case "${1:-all}" in
        mirror)
            configure_docker_mirror
            ;;
        qemu)
            setup_qemu
            ;;
        build)
            build_images
            ;;
        start)
            start_services
            ;;
        all)
            configure_docker_mirror
            setup_buildx
            setup_qemu
            build_images
            start_services
            ;;
        *)
            echo "用法: $0 {mirror|qemu|build|start|all}"
            echo ""
            echo "选项:"
            echo "  mirror  - 配置 Docker 国内镜像加速"
            echo "  qemu    - 配置 QEMU 跨架构支持"
            echo "  build   - 构建镜像"
            echo "  start   - 启动服务"
            echo "  all     - 执行全部步骤（默认）"
            exit 1
            ;;
    esac
}

main "$@"
