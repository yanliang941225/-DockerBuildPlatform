# Docker 构建平台 - 部署手册

本文档提供 Docker 构建平台的完整部署指南，支持单机和集群部署场景。

## 目录

- [系统要求](#系统要求)
- [环境准备](#环境准备)
- [配置说明](#配置说明)
- [快速部署](#快速部署)
- [生产环境部署](#生产环境部署)
- [文件大小限制配置](#文件大小限制配置)
- [安全配置](#安全配置)
- [运维管理](#运维管理)
- [故障排查](#故障排查)

---

## 系统要求

### 硬件要求

| 配置项 | 最低配置 | 推荐配置 |
|--------|----------|----------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 50 GB | 100 GB+ SSD |
| 网络 | 100 Mbps | 1 Gbps |

### 软件要求

- **操作系统**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.0+

### 构建资源限制

| 类型 | 限制大小 | 说明 |
|------|----------|------|
| 构建文件 (上传) | **1 GB** | Dockerfile + 构建上下文 |
| 生成的镜像 | **5 GB** | 最终构建产物的压缩包 |

---

## 环境准备

### 1. 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 验证安装
docker --version
docker-compose --version
```

### 2. 启用 Docker BuildKit

BuildKit 是跨架构构建的关键组件：

```bash
# 临时启用
export DOCKER_BUILDKIT=1

# 永久启用
sudo mkdir -p /etc/docker
cat << EOF | sudo tee /etc/docker/daemon.json
{
  "features": {
    "buildkit": true
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

### 3. 配置跨架构构建支持

```bash
# 安装 QEMU 用于 ARM 架构模拟
docker run --rm --privileged multiarch/qemu-user-static:register --reset

# 验证支持的架构
docker buildx ls
```

---

## 配置说明

### 环境变量配置

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑配置：

```bash
# ==================== 七牛云配置 ====================
QINIU_ACCESS_KEY=your_access_key_here
QINIU_SECRET_KEY=your_secret_key_here
QINIU_BUCKET=docker-build-files
QINIU_REGION=z0

# ==================== 文件限制配置 ====================
# 构建文件大小限制 (默认 1024MB = 1GB)
MAX_BUILD_SIZE_MB=1024

# 镜像文件大小限制 (默认 5120MB = 5GB)
MAX_IMAGE_SIZE_MB=5120

# ==================== 安全配置 ====================
# 文件过期时间 (小时)
FILE_EXPIRE_HOURS=5

# 每分钟请求限制
RATE_LIMIT_PER_MINUTE=30

# 构建超时 (分钟)
BUILD_TIMEOUT_MINUTES=60

# ==================== 服务配置 ====================
# 后端端口
BACKEND_PORT=8000

# 前端端口
FRONTEND_PORT=3000
```

### 七牛云存储配置

1. 登录 [七牛云控制台](https://portal.qiniu.com)
2. 创建存储空间 (建议使用华北区域 z0)
3. 获取 Access Key 和 Secret Key
4. 配置存储空间访问策略

---

## 快速部署

### 方式一：Docker Compose (推荐)

```bash
# 克隆项目
git clone <repository-url>
cd dockerbuild

# 配置环境变量
cp .env.example .env
vim .env  # 填写七牛云配置

# 启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

访问 `http://localhost:3000`

### 方式二：手动构建部署

```bash
# 1. 构建前端
cd frontend
npm install
npm run build

# 2. 构建后端
cd ../backend
pip install -r requirements.txt

# 3. 配置 Nginx
sudo cp nginx.conf /etc/nginx/sites-available/docker-build
sudo ln -s /etc/nginx/sites-available/docker-build /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl reload nginx

# 4. 使用 systemd 管理服务
sudo cp docker-build.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable docker-build
sudo systemctl start docker-build
```

---

## 生产环境部署

### 1. 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 增加 Docker 守护进程资源限制
cat << EOF | sudo tee /etc/docker/daemon.json
{
  "features": {
    "buildkit": true
  },
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "10"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  },
  "default-cgroupns-mode": "host",
  "max-concurrent-builds": 3
}
EOF

sudo systemctl restart docker
```

### 2. 反向代理配置 (Nginx)

```nginx
# /etc/nginx/sites-available/docker-build
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/docker-build/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket 支持 (实时日志)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # Gzip 压缩
    gzip on;
    gzip_types text/plain application/javascript application/json text/css application/xml;
    gzip_min_length 1000;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 配置
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 其余配置同上...
}
```

### 3. SSL 证书配置 (Let's Encrypt)

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

### 4. systemd 服务配置

创建 `/etc/systemd/system/docker-build.service`:

```ini
[Unit]
Description=Docker Build Platform
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/docker-build
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
Restart=on-failure
RestartSec=10s
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable docker-build
sudo systemctl start docker-build
```

---

## 文件大小限制配置

### 构建文件限制 (1GB)

编辑后端配置文件 `backend/app/core/config.py`:

```python
# 构建文件大小限制: 1GB = 1024MB
MAX_BUILD_SIZE_MB: int = 1024
MAX_BUILD_SIZE_BYTES: int = MAX_BUILD_SIZE_MB * 1024 * 1024

# 文件上传配置
UPLOAD_CONFIG = {
    "max_file_size": MAX_BUILD_SIZE_BYTES,
    "allowed_extensions": [".dockerfile", ".tar", ".gz", ".zip", ".tgz"],
    "temp_dir": "/tmp/uploads",
    "cleanup_hours": 5,
}
```

### 镜像文件限制 (5GB)

编辑 `backend/app/services/docker_builder.py`:

```python
# 镜像压缩包大小限制: 5GB = 5120MB
MAX_IMAGE_SIZE_MB: int = 5120
MAX_IMAGE_SIZE_BYTES: int = MAX_IMAGE_SIZE_MB * 1024 * 1024

# 构建资源配置
BUILD_CONFIG = {
    "max_image_size": MAX_IMAGE_SIZE_BYTES,
    "build_timeout": 3600,  # 60分钟
    "memory_limit": "4g",
    "cpus": 4,
}
```

### 前端文件验证

编辑 `frontend/src/components/FileUploader.tsx`:

```typescript
// 1GB = 1024 * 1024 * 1024 bytes
const MAX_BUILD_FILE_SIZE = 1024 * 1024 * 1024;

// 5GB = 5 * 1024 * 1024 * 1024 bytes
const MAX_IMAGE_SIZE = 5 * 1024 * 1024 * 1024;

// 文件大小格式化
const formatFileSize = (bytes: number): string => {
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  }
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }
  return (bytes / 1024).toFixed(2) + ' KB';
};
```

### Docker Build 资源限制

在 `docker-compose.yml` 中配置:

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    shm_size: '2gb'  # 共享内存限制
```

---

## 安全配置

### 1. Dockerfile 安全扫描

平台内置 Dockerfile 安全扫描，检测以下危险指令：

| 危险级别 | 指令示例 | 处理方式 |
|----------|----------|----------|
| 🔴 严重 | `FROM scratch` + `ADD` | 拒绝构建 |
| 🔴 严重 | `USER root` (无后续切换) | 警告 |
| 🟠 高危 | `curl \| sh` | 警告 |
| 🟠 高危 | `--privileged` | 警告 |
| 🟡 中危 | 下载外部脚本 | 警告 |

### 2. 网络安全

```python
# backend/app/core/security.py

# IP 白名单 (可选)
ALLOWED_IPS: list = [
    "127.0.0.1",
    "10.0.0.0/8",
]

# 请求速率限制
RATE_LIMITS = {
    "default": "30/minute",
    "upload": "10/minute",
    "build": "5/minute",
}

# CORS 配置
CORS_ORIGINS = [
    "https://your-domain.com",
]
```

### 3. 文件上传安全

```python
# 后端验证
ALLOWED_MIME_TYPES = {
    "application/x-tar",
    "application/gzip",
    "application/zip",
    "text/plain",
}

# 文件名 sanitization
def sanitize_filename(filename: str) -> str:
    import re
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    filename = filename[:255]  # 限制长度
    return filename
```

### 4. Docker 隔离

```yaml
# docker-compose.yml
services:
  backend:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp:size=1G,noexec,nosuid,nodev
```

---

## 运维管理

### 日常维护

```bash
# 查看服务状态
docker-compose ps

# 查看资源使用
docker stats

# 查看日志
docker-compose logs -f --tail=100

# 清理未使用的资源
docker system prune -f
docker volume prune -f

# 备份数据
docker run --rm -v $(pwd)/data:/data -v $(pwd)/backup:/backup alpine \
  tar czf /backup/backup-$(date +%Y%m%d).tar.gz /data
```

### 日志管理

```bash
# 配置日志轮转 /etc/logrotate.d/docker-build
/path/to/docker-build/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        docker-compose -f /path/to/docker-compose.yml restart > /dev/null 2>&1 || true
    endscript
}
```

### 监控配置

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=your_password
```

### 自动清理

平台自动清理配置 (`docker-compose.yml`):

```yaml
environment:
  - FILE_EXPIRE_HOURS=24  # 24小时后自动删除文件
  - CLEANUP_INTERVAL=3600  # 每小时检查一次
```

手动触发清理:

```bash
# 进入后端容器
docker exec -it docker-build-backend bash

# 手动清理过期文件
python -c "from app.services.cleanup import cleanup_expired_files; cleanup_expired_files()"
```

---

## 故障排查

### 常见问题

#### 1. 构建失败

```bash
# 查看详细日志
docker-compose logs backend | grep -A 50 "build failed"

# 检查 Docker 状态
docker info

# 检查 BuildKit 状态
docker buildx inspect --bootstrap
```

#### 2. 文件上传失败

```
可能原因:
1. 文件大小超过 1GB 限制
2. 文件类型不支持
3. 存储空间不足
4. 网络超时

解决方案:
1. 检查文件大小: ls -lh your-file.tar.gz
2. 压缩文件: tar -czvf smaller.tar.gz source/
3. 清理磁盘空间: docker system prune -a
4. 检查网络连接
```

#### 3. 镜像导出失败

```
可能原因:
1. 镜像大小超过 5GB 限制
2. 磁盘空间不足
3. 导出超时

解决方案:
1. 检查镜像大小: docker images
2. 优化 Dockerfile: 多阶段构建、清理缓存
3. 清理空间: docker system prune -a --volumes
4. 增加超时时间
```

#### 4. 跨架构构建失败

```bash
# 检查 QEMU 状态
docker run --rm --rm -v $(pwd):/build docker:latest --help

# 重新注册 QEMU
docker run --rm --privileged multiarch/qemu-user-static:register --reset

# 测试 ARM 构建
docker buildx build --platform linux/arm64 -t test:arm64 .
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/api/health

# 预期响应
{
  "status": "healthy",
  "docker": "connected",
  "qiniu": "connected",
  "version": "1.0.0"
}
```

### 日志级别

修改 `backend/app/core/config.py` 启用调试模式:

```python
LOG_LEVEL: str = "DEBUG"  # 开发环境
LOG_LEVEL: str = "INFO"   # 生产环境
```

---

## 升级指南

### 版本升级

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取最新代码
git pull origin main

# 3. 更新依赖
docker-compose pull

# 4. 重新构建
docker-compose up -d --build

# 5. 检查服务
docker-compose ps
docker-compose logs -f
```

### 数据迁移

```bash
# 导出数据
docker run --rm -v $(pwd)/data:/data -v $(pwd)/export:/export \
  alpine tar czf /export/data-$(date +%Y%m%d).tar.gz /data

# 导入数据
docker run --rm -v $(pwd)/data:/data -v $(pwd)/import:/import \
  alpine tar xzf /import/data-backup.tar.gz -C /
```

---

## 联系支持

- 文档版本: v1.0.0
- 最后更新: 2024-01
- 技术支持: support@example.com
