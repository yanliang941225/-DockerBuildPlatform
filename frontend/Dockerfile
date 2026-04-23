# 前端 Dockerfile
# 使用阿里云 npm 镜像加速

# 构建阶段
FROM node:20-alpine AS build

# 配置 Alpine 国内镜像（阿里云）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# 安装依赖（git 用于某些 npm 包，以及构建工具）
RUN apk add --no-cache git python3 make g++

# 配置 npm 镜像（阿里云 npmmirror）
RUN npm config set registry https://registry.npmmirror.com

WORKDIR /app

# 先复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install --legacy-peer-deps

# 复制源代码
COPY . .

# 验证关键文件存在
RUN ls -la src/main.tsx index.html

# 构建（跳过 tsc 检查以加快构建速度）
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
