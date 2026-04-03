# 后端 Dockerfile
# 使用清华 pip 镜像加速

FROM python:3.11-slim

WORKDIR /app

# 配置清华 pip 镜像（主要）+ 阿里云镜像（备用）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip config set global.extra-index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.timeout 120

# 安装系统依赖（使用国内镜像加速）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release && \
    rm -rf /var/lib/apt/lists/*

# 安装 Docker CLI 和 BuildX（使用 Docker 官方 apt 源）
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://mirror.sjtu.edu.cn/docker-ce/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /tmp/uploads /tmp/results /tmp/docker-builds /etc/docker ~/.docker

# 配置 Docker daemon registry 镜像（影响 docker pull）
RUN tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
    "registry-mirrors": [
        "https://docker-0.unsee.tech",
        "https://docker-cf.registry.cyou",
        "https://docker.1panel.live",
        "https://docker.m.daocloud.io"
    ]
}
EOF

# 配置 BuildKit registry 镜像（影响 docker buildx build）
# 注意：BuildKit 不读 daemon.json，需要单独的 buildkitd.toml
RUN tee /etc/buildkitd.toml > /dev/null <<'EOF'
# BuildKit registry mirrors 配置
[registry."docker.io"]
 mirrors = [
      "docker-0.unsee.tech",
      "docker-cf.registry.cyou",
      "docker.1panel.live",
      "docker.m.daocloud.io"
 ]
EOF

# 同时复制到用户目录（备用）
RUN tee ~/.docker/buildkitd.toml > /dev/null <<'EOF'
[registry."docker.io"]
 mirrors = [
      "docker-0.unsee.tech",
      "docker-cf.registry.cyou",
      "docker.1panel.live",
      "docker.m.daocloud.io"
 ]
EOF

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
