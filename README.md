# 🐳 Docker Build Platform

**一个现代化的在线 Docker 镜像跨架构构建平台。无需注册登录，只需上传 Dockerfile，即可构建支持多种 CPU 架构的 Docker 镜像。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg?logo=react)](https://react.dev/)

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🌐 **零门槛使用** | 无需注册、登录，打开网页即可开始构建 |
| 🏗️ **多架构构建** | 同时构建 `amd64`、`arm64`、`armv7` 架构镜像 |
| ⚡ **实时日志** | 实时查看构建过程，随时掌握构建状态 |
| 🔒 **安全可靠** | Dockerfile 安全扫描、文件验证、请求限流 |
| 🛡️ **隐私保护** | 构建完成后 24 小时内自动清理所有数据 |
| 🚀 **高速构建** | 预配置多个 Docker Hub 镜像源，加速构建 |

## 🎯 适用场景

- 为 Apple Silicon Mac 构建兼容的 Docker 镜像
- 为树莓派、ARM 开发板构建轻量级容器镜像
- 一次构建，多架构部署到不同服务器
- 开发者快速验证 Dockerfile 的跨架构兼容性

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- （可选）七牛云账户（用于云端存储）

### 1. 克隆并配置

```bash
git clone https://github.com/yanliang941225/-DockerBuildPlatform.git
cd dockerbuild
cp .env.example .env
```

编辑 `.env` 文件，选择存储方式：

```bash
# 方式一：本地存储（推荐，无需注册任何服务）
STORAGE_TYPE=local

# 方式二：七牛云存储
STORAGE_TYPE=qiniu
QINIU_ACCESS_KEY=your_access_key
QINIU_SECRET_KEY=your_secret_key
QINIU_BUCKET=your_bucket_name
QINIU_REGION=z0

# 方式三：自动选择（默认）
STORAGE_TYPE=auto
```

### 2. 启动服务

```bash
docker-compose up -d
```

访问 **http://localhost:3000**

## 💡 使用流程

```
1️⃣ 选择架构     →  amd64 / arm64 / armv7
2️⃣ 填写镜像信息  →  名称和标签（可选）
3️⃣ 上传文件     →  拖拽 Dockerfile 和构建上下文
4️⃣ 开始构建     →  实时查看日志和进度
5️⃣ 下载镜像     →  获取构建完成的 tar 包
```

## 🛠️ 技术栈

| 分类 | 技术 |
|------|------|
| 前端 | React 18 · TypeScript · Vite · TailwindCSS · shadcn/ui |
| 后端 | Python 3.11 · FastAPI · Pydantic |
| 容器 | Docker · BuildKit · QEMU |
| 存储 | 本地存储 / 七牛云 OSS |

## 📁 项目结构

```
.
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由（任务、存储、健康检查）
│   │   ├── core/              # 核心配置（安全、限流、会话）
│   │   └── services/          # 业务服务（构建器、存储抽象、任务管理）
│   ├── main.py
│   └── requirements.txt
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/        # UI 组件
│   │   ├── pages/             # 页面
│   │   ├── hooks/             # 自定义 Hooks
│   │   └── lib/               # 工具函数
│   └── package.json
│
├── scripts/                    # 部署脚本
├── docker-compose.yml
└── .env.example
```

## 🔌 API 文档

启动服务后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要接口

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/tasks/` | 创建构建任务 |
| `GET` | `/api/tasks/{id}` | 获取任务详情 |
| `POST` | `/api/tasks/{id}/dockerfile` | 上传 Dockerfile |
| `POST` | `/api/tasks/{id}/context` | 上传构建上下文 |
| `POST` | `/api/tasks/{id}/build` | 开始构建 |
| `GET` | `/api/tasks/{id}/logs` | 获取构建日志 |
| `GET` | `/api/tasks/{id}/progress` | 构建进度 |

## 🏪 存储架构

采用存储抽象层设计，支持多种存储后端：

| 存储类型 | 配置 | 说明 |
|---------|------|------|
| 本地存储 | `local` | 无需配置，文件存储在容器内 |
| 七牛云 | `qiniu` | 云端存储，高可用 |
| 自动选择 | `auto` | 优先七牛云，不可用则本地 |

扩展新的存储后端只需继承 `BaseStorage` 基类即可。

## 🔐 安全特性

- **文件上传**：类型白名单、大小限制、文件名 sanitization
- **Dockerfile 扫描**：检测 `rm -rf /` 等危险指令
- **网络防护**：请求频率限制、CORS 配置、安全响应头
- **构建隔离**：超时控制、资源限制、沙箱执行

## 📦 本地开发

```bash
# 后端
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](LICENSE)
