"""
存储相关 API 路由
提供文件下载等接口
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, Response
import logging

from app.services.storage import get_storage, get_storage_type, StorageType

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/download/{path:path}")
async def download_file(request: Request, path: str):
    """
    下载存储中的文件（主要用于本地存储）
    公开接口，不需要会话验证
    
    Args:
        path: 文件路径，如 "results/task-id/arm64.tar"
    """
    storage = get_storage()
    
    # 只有本地存储需要通过 API 下载
    if storage.storage_type != StorageType.LOCAL:
        raise HTTPException(
            status_code=400,
            detail="当前存储不支持直接下载，请使用云存储提供的下载链接"
        )
    
    # 验证文件存在
    full_path = storage._get_full_path(path)
    import os
    if not os.path.exists(full_path):
        logger.warning(f"文件不存在: {path}")
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
    
    try:
        # 获取文件大小
        file_size = os.path.getsize(full_path)
        logger.info(f"准备下载文件: {path}, 大小: {file_size} bytes")
        
        # 根据文件类型设置 media type
        content_type = "application/octet-stream"
        if path.endswith(".tar"):
            content_type = "application/x-tar"
        elif path.endswith(".gz") or path.endswith(".tgz"):
            content_type = "application/gzip"
        elif path.endswith(".zip"):
            content_type = "application/zip"
        elif path.endswith(".dockerfile") or path.endswith(".Dockerfile"):
            content_type = "text/plain"
        
        # 流式读取文件并返回
        def iterfile():
            with open(full_path, 'rb') as f:
                while chunk := f.read(8192 * 1024):  # 8MB chunks
                    yield chunk
        
        filename = path.split("/")[-1]
        
        return Response(
            content=iterfile(),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_storage_info():
    """获取存储信息"""
    storage = get_storage()
    
    return {
        "storage_type": storage.storage_type.value,
        "is_configured": storage.is_configured(),
        "message": f"当前使用 {storage.storage_type.value.upper()} 存储"
    }
