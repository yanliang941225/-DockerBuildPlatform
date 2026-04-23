"""
任务管理 API 路由
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import logging
import os
import uuid
import time
from datetime import datetime, timedelta

from .schemas import (
    TaskResponse, TaskCreate, UploadResponse, ErrorResponse,
    TaskStatus, Architecture, BuildProgress, LogEntry
)
from app.core.config import settings
from app.core.security import (
    SecurityValidator, RequestValidator, 
    user_rate_limiter, session_manager, generate_fingerprint_hash
)
from app.core.session import session_manager, UserSession
from app.services.task_manager import task_manager
from app.services.storage import get_storage
from app.services.docker_builder import DockerBuilder

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局实例
docker_builder = DockerBuilder()


def get_storage_instance():
    """获取存储实例"""
    return get_storage()


async def get_session(request: Request) -> Optional[UserSession]:
    """获取当前会话"""
    return getattr(request.state, "session", None)


async def get_client_ip(request: Request) -> str:
    """获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/session/init", include_in_schema=False)
async def init_session(
    request: Request,
    response: Response,
    fingerprint: str = Query(..., description="浏览器指纹"),
    user_agent: str = Query(..., description="浏览器 User-Agent")
):
    """
    初始化会话（前端调用此接口创建会话）
    解析指纹参数并创建会话
    """
    ip = await get_client_ip(request)

    # 提取指纹参数（前端会传来更详细的参数）
    screen = request.query_params.get("screen", "")
    timezone = request.query_params.get("timezone", "")
    language = request.query_params.get("language", "")
    platform = request.query_params.get("platform", "")
    canvas = request.query_params.get("canvas", "")
    webgl = request.query_params.get("webgl", "")

    # 生成指纹 hash
    fp_hash = generate_fingerprint_hash(
        user_agent=user_agent,
        screen=screen,
        timezone=timezone,
        language=language,
        platform=platform,
        canvas_fingerprint=canvas,
        webgl_fingerprint=webgl
    )

    # 创建会话
    session = await session_manager.create_session(
        fingerprint=fp_hash,
        ip_address=ip,
        user_agent=user_agent
    )

    # 直接设置 Cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.session_id,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=True,
        samesite="lax"
    )

    logger.info(f"会话初始化: {session.session_id[:8]}...")

    return {
        "session_id": session.session_id,
        "message": "会话已创建"
    }


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(request: Request, task_data: TaskCreate):
    """
    创建新的构建任务
    """
    session = await get_session(request)
    ip = await get_client_ip(request)
    
    # 如果没有会话，创建一个（使用 IP 作为指纹）
    if not session:
        logger.warning(f"[调试] 创建任务时无会话，为 IP {ip} 创建临时会话")
        from app.core.session import generate_fingerprint_hash
        # 使用 IP + 时间戳生成临时指纹
        temp_fingerprint = generate_fingerprint_hash(
            user_agent=request.headers.get("user-agent", ""),
            screen="",
            timezone="",
            language="",
            platform="",
            canvas_fingerprint=ip,  # 使用 IP 作为临时指纹
            webgl_fingerprint=str(int(time.time()))
        )
        session = await session_manager.create_session(
            fingerprint=temp_fingerprint,
            ip_address=ip,
            user_agent=request.headers.get("user-agent", "")
        )
        logger.info(f"[调试] 已创建临时会话: {session.session_id[:8]}...")
    
    # 检查用户任务数限制
    is_allowed, error_msg = await user_rate_limiter.check_rate_limit(
        session, ip, "general"
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    # 检查最大任务数
    stats = await session_manager.get_user_stats(session.session_id)
    if stats and stats["task_count"] >= settings.MAX_TASKS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"已达到最大任务数限制 ({settings.MAX_TASKS_PER_USER})"
        )

    try:
        task = await task_manager.create_task(
            target_arch=task_data.target_arch.value,
            user_id=session.session_id if session else None,
            image_name=task_data.image_name,
            image_tag=task_data.image_tag or "latest"
        )

        # 更新用户任务计数
        if session:
            await session_manager.update_task_count(session.session_id)

        logger.info(f"创建任务: {task.task_id}, 用户: {session.session_id[:8] if session else 'anonymous'}, 目标架构: {task.target_arch}, 镜像: {task.image_name}:{task.image_tag}")

        response = TaskResponse(
            task_id=task.task_id,
            status=task.status,
            target_arch=task.target_arch,
            created_at=task.created_at,
            expires_at=task.expires_at,
            dockerfile_uploaded=False,
            context_uploaded=False,
            image_name=task.image_name,
            image_tag=task.image_tag
        )

        return response
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my")
async def get_my_tasks(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    获取当前用户的任务列表
    使用会话 ID 标识用户，返回该用户创建的所有任务
    """
    session = await get_session(request)
    
    # 调试信息
    session_id_from_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    logger.info(f"[调试] /my 请求 - Cookie: {session_id_from_cookie[:8] if session_id_from_cookie else 'None'}")
    logger.info(f"[调试] /my 请求 - session对象: {session.session_id[:8] if session else 'None'}")
    
    if not session:
        logger.warning("[调试] /my 请求 - 无有效会话，返回空列表")
        return {"tasks": [], "total": 0, "message": "无有效会话"}

    # 调试：检查任务管理器中的用户索引
    from app.services.task_manager import task_manager
    user_task_ids = task_manager._user_tasks.get(session.session_id, [])
    logger.info(f"[调试] /my 请求 - 用户索引中的任务数: {len(user_task_ids)}")
    logger.info(f"[调试] /my 请求 - 用户索引中的任务IDs: {[t[:8] for t in user_task_ids]}")

    tasks = await task_manager.get_tasks_by_user(session.session_id, limit, offset)
    storage = get_storage_instance()
    
    logger.info(f"[调试] /my 请求 - 返回任务数: {len(tasks)}")

    return {
        "tasks": [
            TaskResponse(
                task_id=t.task_id,
                status=t.status,
                target_arch=t.target_arch,
                created_at=t.created_at,
                expires_at=t.expires_at,
                dockerfile_uploaded=bool(t.dockerfile_key),
                context_uploaded=bool(t.context_key),
                image_name=t.image_name,
                image_tag=t.image_tag,
                error_message=t.error_message,
                # 成功且有结果文件的任务，提供下载链接
                download_url=storage.get_download_url(t.result_key) if t.status == TaskStatus.SUCCESS and t.result_key else None,
                download_expires_at=t.expires_at if t.status == TaskStatus.SUCCESS else None
            ) for t in tasks
        ],
        "total": len(tasks),
        "session_id": session.session_id[:8] + "..."
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """
    获取任务详情（公开接口，不需要会话）
    只要知道 task_id 就可以查看任务状态
    """
    task = await task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 生成下载链接（如果任务成功）
    download_url = None
    download_expires_at = None
    
    if task.status == TaskStatus.SUCCESS and task.result_key:
        try:
            storage = get_storage_instance()
            download_url = storage.get_download_url(task.result_key)
            download_expires_at = task.expires_at
        except Exception as e:
            logger.warning(f"生成下载链接失败: {e}")
    
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        target_arch=task.target_arch,
        created_at=task.created_at,
        expires_at=task.expires_at,
        dockerfile_uploaded=bool(task.dockerfile_key),
        context_uploaded=bool(task.context_key),
        image_name=task.image_name,
        image_tag=task.image_tag,
        error_message=task.error_message,
        download_url=download_url,
        download_expires_at=download_expires_at
    )


@router.post("/{task_id}/dockerfile", response_model=UploadResponse)
async def upload_dockerfile(
    task_id: str,
    file: UploadFile = File(...)
):
    """
    上传 Dockerfile
    """
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.dockerfile_key:
        raise HTTPException(status_code=400, detail="Dockerfile 已上传")
    
    # 验证文件扩展名
    if not RequestValidator.validate_file_extension(
        file.filename, 
        settings.ALLOWED_DOCKERFILE_EXTENSIONS
    ):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，支持: {', '.join(settings.ALLOWED_DOCKERFILE_EXTENSIONS)}"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 验证文件大小
    if not RequestValidator.validate_file_size(
        len(content), 
        settings.max_file_size_bytes
    ):
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制，最大 {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # 清理文件名
    safe_filename = SecurityValidator.sanitize_filename(file.filename)
    
    # 基本格式验证：确保是有效的文本
    try:
        content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Dockerfile 必须是有效的 UTF-8 文本文件")
    
    # 上传到存储
    try:
        file_key = f"uploads/{task_id}/Dockerfile"
        storage = get_storage_instance()

        # 验证上传是否成功（使用异步版本避免阻塞事件循环）
        upload_success = await storage.upload_file_async(
            key=file_key,
            content=content,
            content_type="text/plain"
        )

        # 检查上传结果
        if not upload_success:
            raise RuntimeError(f"文件上传失败，可能是存储服务不可用")

        # 验证文件确实存在
        if not await storage.file_exists_async(file_key):
            raise RuntimeError(f"文件上传后验证失败，存储中找不到该文件")
        
        # 更新任务
        await task_manager.update_dockerfile(task_id, file_key, safe_filename, len(content))
        
        logger.info(f"任务 {task_id}: Dockerfile 上传成功，已验证存在")
        
        return UploadResponse(
            success=True,
            filename=safe_filename,
            size=len(content),
            message="Dockerfile 上传成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传 Dockerfile 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/context", response_model=UploadResponse)
async def upload_context(
    task_id: str,
    file: UploadFile = File(...)
):
    """
    上传构建上下文（压缩文件）
    """
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证文件扩展名
    if not RequestValidator.validate_file_extension(
        file.filename,
        settings.ALLOWED_CONTEXT_EXTENSIONS
    ):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，支持: {', '.join(settings.ALLOWED_CONTEXT_EXTENSIONS)}"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 验证文件大小
    if not RequestValidator.validate_file_size(
        len(content),
        settings.max_context_size_bytes
    ):
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制，最大 {settings.MAX_CONTEXT_SIZE_MB}MB"
        )
    
    # 清理文件名
    safe_filename = SecurityValidator.sanitize_filename(file.filename)
    
    # 上传到存储
    try:
        file_key = f"uploads/{task_id}/context/{safe_filename}"
        content_type = "application/zip" if safe_filename.endswith('.zip') else "application/gzip"
        
        storage = get_storage_instance()
        
        # 验证上传是否成功（使用异步版本避免阻塞事件循环）
        upload_success = await storage.upload_file_async(
            key=file_key,
            content=content,
            content_type=content_type
        )
        
        # 检查上传结果
        if not upload_success:
            raise RuntimeError(f"文件上传失败，可能是存储服务不可用")
        
        # 验证文件确实存在
        if not await storage.file_exists_async(file_key):
            raise RuntimeError(f"文件上传后验证失败，存储中找不到该文件")
        
        # 更新任务
        await task_manager.update_context(task_id, file_key, safe_filename, len(content))
        
        logger.info(f"任务 {task_id}: 上下文文件上传成功，已验证存在")
        
        return UploadResponse(
            success=True,
            filename=safe_filename,
            size=len(content),
            message="构建上下文上传成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传上下文文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/build")
async def start_build(
    request: Request,
    task_id: str,
    background_tasks: BackgroundTasks
):
    """
    开始构建镜像
    """
    session = await get_session(request)
    ip = await get_client_ip(request)
    
    # 检查并发构建限制
    is_allowed, error_msg = await user_rate_limiter.check_build_limit(session, ip)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    logger.info(f"[调试] 开始构建请求 - task_id: {task_id}, status: {task.status}, dockerfile_key: {task.dockerfile_key}")
    
    if not task.dockerfile_key:
        logger.error(f"[调试] Dockerfile 未上传 - task_id: {task_id}")
        raise HTTPException(status_code=400, detail="请先上传 Dockerfile")
    
    if task.status in [TaskStatus.BUILDING, TaskStatus.SUCCESS]:
        raise HTTPException(status_code=400, detail="任务已在执行或已完成")
    
    # 验证 Dockerfile 文件是否真的存在于存储中
    try:
        storage = get_storage_instance()
        if not await storage.file_exists_async(task.dockerfile_key):
            logger.error(f"[调试] Dockerfile 文件不存在于存储中 - key: {task.dockerfile_key}")
            raise HTTPException(status_code=400, detail="Dockerfile 文件丢失，请重新上传")
        logger.info(f"[调试] Dockerfile 验证通过 - key: {task.dockerfile_key}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[调试] 验证 Dockerfile 时出错: {e}")
        raise HTTPException(status_code=500, detail=f"验证 Dockerfile 时出错: {str(e)}")
    
    # 更新状态为构建中
    await task_manager.update_status(task_id, TaskStatus.BUILDING)
    
    # 增加构建计数
    if session:
        await user_rate_limiter.increment_build(session.session_id)
    
    # 后台执行构建
    background_tasks.add_task(
        _build_with_cleanup,
        task_id=task_id,
        session_id=session.session_id if session else None
    )
    
    logger.info(f"任务 {task_id}: 构建已启动, 用户: {session.session_id[:8] if session else 'anonymous'}")
    
    return {"message": "构建已启动", "task_id": task_id}


async def _build_with_cleanup(task_id: str, session_id: Optional[str]):
    """构建任务（含清理）"""
    start_time = time.time()
    
    try:
        await docker_builder.build_image(task_id=task_id)
    finally:
        # 减少构建计数
        if session_id:
            await user_rate_limiter.decrement_build(session_id)
            # 记录构建时间
            build_duration = int(time.time() - start_time)
            await session_manager.record_build_time(session_id, build_duration)


@router.get("/{task_id}/logs")
async def get_build_logs(
    task_id: str,
    since: Optional[int] = Query(None, description="从第N条日志开始获取")
):
    """
    获取构建日志
    """
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    logs = await task_manager.get_logs(task_id, since)
    
    return {
        "task_id": task_id,
        "status": task.status,
        "logs": [log.model_dump() for log in logs],
        "total": len(logs)
    }


@router.get("/{task_id}/progress", response_model=BuildProgress)
async def get_build_progress(task_id: str):
    """
    获取构建进度
    """
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    logs = await task_manager.get_logs(task_id)
    
    # 计算进度
    progress = 0
    current_step = None
    
    if task.status == TaskStatus.PENDING:
        progress = 0
    elif task.status == TaskStatus.UPLOADING:
        progress = 10
        current_step = "上传文件中..."
    elif task.status == TaskStatus.BUILDING:
        # 根据日志计算进度
        if logs:
            for log in logs:
                if "Step" in log.message or "FROM" in log.message:
                    progress = 30
                    current_step = log.message[:50]
                elif "RUN" in log.message:
                    progress = max(progress, 50)
                    current_step = log.message[:50]
                elif "Successfully built" in log.message:
                    progress = 90
                elif "Pushing" in log.message:
                    progress = 95
    elif task.status == TaskStatus.SUCCESS:
        progress = 100
        current_step = "构建完成"
    elif task.status == TaskStatus.FAILED:
        progress = 0
        current_step = "构建失败"
    
    return BuildProgress(
        task_id=task_id,
        status=task.status,
        progress=progress,
        current_step=current_step,
        logs=logs
    )


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """
    取消/删除任务
    """
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == TaskStatus.BUILDING:
        raise HTTPException(status_code=400, detail="构建中的任务无法删除")
    
    # 删除相关文件
    try:
        storage = get_storage_instance()
        if task.dockerfile_key:
            await storage.delete_file_async(task.dockerfile_key)
        if task.context_key:
            await storage.delete_file_async(task.context_key)
        if task.result_key:
            await storage.delete_file_async(task.result_key)
    except Exception as e:
        logger.warning(f"清理文件失败: {e}")
    
    # 删除任务
    await task_manager.delete_task(task_id)
    
    logger.info(f"任务 {task_id}: 已删除")
    
    return {"message": "任务已删除"}


@router.get("/")
async def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    获取任务列表
    """
    tasks = await task_manager.list_tasks(limit, offset)

    return {
        "tasks": [
            TaskResponse(
                task_id=t.task_id,
                status=t.status,
                target_arch=t.target_arch,
                created_at=t.created_at,
                expires_at=t.expires_at,
                dockerfile_uploaded=bool(t.dockerfile_key),
                context_uploaded=bool(t.context_key),
                image_name=t.image_name,
                image_tag=t.image_tag,
                error_message=t.error_message
            ) for t in tasks
        ],
        "total": len(tasks)
    }