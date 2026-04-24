"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "Docker Build Platform"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://39.99.225.96",
        "http://39.99.225.96:3000",
        "https://39.99.225.96",
        "https://39.99.225.96:3000",
        "*",  # 开发环境允许所有
    ]
    
    # 存储配置
    STORAGE_TYPE: str = "local"  # 存储类型: auto, local, qiniu, oss, s3
    
    # 七牛云配置
    QINIU_ACCESS_KEY: str = ""
    QINIU_SECRET_KEY: str = ""
    QINIU_BUCKET: str = "docker-build-files"
    QINIU_REGION: str = "z0"  # 华北区
    
    # 文件配置
    FILE_EXPIRE_HOURS: int = 24      # 上传文件过期时间（小时）
    RESULT_EXPIRE_HOURS: int = 24   # 构建结果文件过期时间（小时）
    MAX_FILE_SIZE_MB: int = 500
    MAX_CONTEXT_SIZE_MB: int = 500
    ALLOWED_DOCKERFILE_EXTENSIONS: List[str] = [".dockerfile", ".Dockerfile", "Dockerfile"]
    ALLOWED_CONTEXT_EXTENSIONS: List[str] = [".zip", ".tar", ".tar.gz", ".tgz"]
    
    # 安全配置
    RATE_LIMIT_PER_MINUTE: int = 30
    
    # 会话配置
    SESSION_TTL_HOURS: int = 24              # 会话有效期（小时）
    SESSION_COOKIE_NAME: str = "db_session"  # Session Cookie 名称
    MAX_TASKS_PER_USER: int = 10            # 单用户最大任务数
    MAX_CONCURRENT_BUILDS_PER_USER: int = 2  # 单用户最大并发构建数
    MAX_TASKS_PER_IP: int = 50             # 单 IP 最大任务数
    
    # 构建配置
    BUILD_TIMEOUT_MINUTES: int = 300
    BUILD_WORKERS: int = 4
    BUILD_WORKDIR: str = "/tmp/docker-builds"
    AUTO_REGISTER_QEMU: bool = True  # 启动时自动注册 QEMU
    
    # QEMU 支持的架构
    QEMU_ARCHITECTURES: List[str] = ["arm64", "arm/v7", "riscv64", "ppc64le"]
    
    # 存储路径
    UPLOAD_DIR: str = "/tmp/uploads"  # 临时上传目录
    RESULT_DIR: str = "/app/storage/results"  # 结果文件持久化存储
    STORAGE_LOCAL_PATH: str = "/app/storage"  # 本地存储根路径

    @property
    def result_dir(self) -> str:
        """动态计算结果目录路径"""
        env_path = os.environ.get("RESULT_DIR")
        if env_path:
            return env_path
        return self.RESULT_DIR
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def max_context_size_bytes(self) -> int:
        return self.MAX_CONTEXT_SIZE_MB * 1024 * 1024
    
    @property
    def storage_local_path(self) -> str:
        """动态计算本地存储路径"""
        # 优先使用环境变量
        env_path = os.environ.get("STORAGE_LOCAL_PATH")
        if env_path:
            return env_path
        return self.STORAGE_LOCAL_PATH
    
    @property
    def app_root(self) -> str:
        """获取应用根目录"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(os.path.dirname(current_dir))
    
    class Config:
        env_file = "/app/.env"
        case_sensitive = True


settings = Settings()

# 确保目录存在
os.makedirs(settings.storage_local_path, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.result_dir, exist_ok=True)
os.makedirs(settings.BUILD_WORKDIR, exist_ok=True)
