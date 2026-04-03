"""
健康检查 API
"""
from fastapi import APIRouter
from datetime import datetime
import platform

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查接口
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Docker Cross-Platform Build API",
        "version": "1.0.0"
    }


@router.get("/status")
async def system_status():
    """
    系统状态接口
    """
    import psutil
    import subprocess

    # 获取 Docker 状态
    docker_available = False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5
        )
        docker_available = result.returncode == 0
    except:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version()
        },
        "services": {
            "docker": "available" if docker_available else "unavailable",
            "qiniu": "configured" if _check_qiniu_config() else "not_configured"
        },
        "resources": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent
        }
    }


def _check_qiniu_config() -> bool:
    """检查七牛云配置"""
    from app.core.config import settings
    return bool(settings.QINIU_ACCESS_KEY and settings.QINIU_SECRET_KEY)
