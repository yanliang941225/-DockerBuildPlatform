# Docker Build CLI 脚本

这个目录包含用于构建和部署 Docker Build 服务的脚本。

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `build.sh` | 构建 Docker 镜像 |
| `deploy.sh` | 部署和管理服务 |

## 快速开始

### 1. 首次部署

```bash
# 初始化环境
./scripts/deploy.sh init

# 启动服务
./scripts/deploy.sh start
```

### 2. 日常使用

```bash
# 启动服务
./scripts/deploy.sh start

# 查看状态
./scripts/deploy.sh status

# 查看日志
./scripts/deploy.sh logs

# 停止服务
./scripts/deploy.sh stop

# 重启服务
./scripts/deploy.sh restart
```

## build.sh - 构建脚本

用于构建前后端 Docker 镜像。

```bash
# 构建所有服务
./scripts/build.sh

# 只构建后端
./scripts/build.sh backend

# 只构建前端
./scripts/build.sh frontend

# 不使用缓存重新构建
./scripts/build.sh --no-cache

# 强制重新构建
./scripts/build.sh --force
```

## deploy.sh - 部署脚本

用于部署和管理 Docker Build 服务。

```bash
# 初始化环境（首次使用）
./scripts/deploy.sh init

# 启动所有服务
./scripts/deploy.sh start

# 停止所有服务
./scripts/deploy.sh stop

# 重启所有服务
./scripts/deploy.sh restart

# 查看服务状态
./scripts/deploy.sh status

# 查看日志
./scripts/deploy.sh logs
./scripts/deploy.sh logs backend  # 只看后端日志

# 健康检查
./scripts/deploy.sh health

# 进入后端容器
./scripts/deploy.sh ssh

# 更新服务
./scripts/deploy.sh update

# 清理所有资源（容器、数据卷）
./scripts/deploy.sh clean

# 查看帮助
./scripts/deploy.sh --help
```

## 服务访问

部署成功后，可以通过以下地址访问：

- 前端界面: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/api/docs

## 配置

编辑 `.env` 文件来配置服务：

```bash
# 存储类型: auto, local, qiniu
STORAGE_TYPE=local

# 七牛云配置（可选）
QINIU_ACCESS_KEY=your_key
QINIU_SECRET_KEY=your_secret
QINIU_BUCKET=docker-build-files
```

## 故障排除

### QEMU 相关问题

如果遇到跨架构构建问题：

```bash
# 手动注册 QEMU
docker run --rm --privileged \
    multiarch/qemu-user-static:latest \
    --reset -p yes
```

### BuildX 相关问题

```bash
# 查看 BuildX 状态
docker buildx ls

# 重置 BuildX
docker buildx prune --all
```

### 查看容器日志

```bash
# 查看所有日志
./scripts/deploy.sh logs

# 只看后端日志
docker logs docker-build-backend

# 只看前端日志
docker logs docker-build-frontend
```
