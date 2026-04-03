"""
Docker 跨架构构建平台 - 后端应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import tasks, health, storage
from app.core.config import settings
from app.core.security import setup_rate_limiting

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动 Docker 跨架构构建平台...")
    
    # 启动时初始化
    from app.services.cleaner import start_cleanup_scheduler
    from app.core.session import start_session_cleanup
    from app.services.qemu_setup import qemu_setup
    from app.services.storage import get_storage, get_storage_type
    import asyncio
    
    # 0. 初始化存储
    logger.info("初始化存储...")
    storage_instance = get_storage()
    logger.info(f"存储类型: {get_storage_type().value}")
    
    # 1. 设置 QEMU 跨架构支持
    logger.info("检查 QEMU 跨架构支持...")
    await qemu_setup.register_qemu()
    await qemu_setup.check_buildx_available()
    await qemu_setup.setup_buildx_builder()
    
    # 2. 启动清理调度器
    start_cleanup_scheduler()
    
    # 3. 启动会话清理任务
    asyncio.create_task(start_session_cleanup())
    
    yield
    
    # 关闭时清理
    logger.info("🛑 关闭应用...")


app = FastAPI(
    title="Docker Cross-Platform Build API",
    description="在线 Docker 镜像跨架构构建平台 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 安全中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# 限流中间件
setup_rate_limiting(app)

# 注册路由
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["构建任务"])
app.include_router(storage.router, prefix="/api/storage", tags=["文件存储"])


@app.get("/")
async def root():
    return {
        "name": "Docker Cross-Platform Build API",
        "version": "1.0.0",
        "docs": "/docs"
    }
