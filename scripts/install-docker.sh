#!/bin/bash
# =============================================================================
# Docker Desktop 安装脚本（macOS）
# =============================================================================

set -e

echo "============================================"
echo "  Docker Desktop 安装脚本"
echo "============================================"
echo ""

# 检查操作系统
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "此脚本仅适用于 macOS 系统"
    exit 1
fi

# 检查是否已安装
if command -v docker &> /dev/null; then
    echo "Docker 已安装: $(docker --version)"
    exit 0
fi

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo "错误: 请先安装 Homebrew"
    echo "访问: https://brew.sh"
    exit 1
fi

echo "选项 1: 使用 Homebrew 安装（推荐）"
echo "  brew install --cask docker"
echo ""
echo "选项 2: 手动下载安装"
echo "  访问: https://www.docker.com/products/docker-desktop/"
echo ""
echo "============================================"
echo "请选择安装方式："
echo ""
echo "  1) 使用 Homebrew 安装"
echo "  2) 打开浏览器下载 Docker Desktop"
echo "  3) 退出"
echo ""
read -p "请输入选项 [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "正在安装 Docker Desktop..."
        brew install --cask docker
        echo ""
        echo "安装完成！"
        echo ""
        echo "请启动 Docker Desktop:"
        echo "  1. 打开 Launchpad"
        echo "  2. 找到并点击 Docker 图标"
        echo "  3. 等待 Docker Desktop 启动完成（约需 1-2 分钟）"
        echo "  4. 验证安装: docker --version"
        ;;
    2)
        echo "正在打开 Docker Desktop 下载页面..."
        open "https://www.docker.com/products/docker-desktop/"
        ;;
    3)
        echo "已退出"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
