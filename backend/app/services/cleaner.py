"""
定时清理服务
"""
import asyncio
import logging
from datetime import datetime, timedelta
from app.core.config import settings
from app.services.task_manager import task_manager
from app.services.storage import get_storage, get_storage_type

logger = logging.getLogger(__name__)


async def cleanup_expired_tasks():
    """清理过期任务"""
    try:
        deleted = await task_manager.cleanup_expired()
        if deleted > 0:
            logger.info(f"清理了 {deleted} 个过期任务")
    except Exception as e:
        logger.error(f"清理过期任务失败: {e}")


async def cleanup_expired_files():
    """清理过期文件"""
    try:
        storage = get_storage()

        # 检查存储是否支持列表和删除操作
        if not storage.is_configured():
            logger.info("存储未配置或不支持清理操作，跳过文件清理")
            return

        storage_type = get_storage_type()
        logger.info(f"使用 {storage_type.value} 存储进行清理")

        deleted = 0
        cutoff = datetime.utcnow() - timedelta(hours=settings.FILE_EXPIRE_HOURS)
        result_cutoff = datetime.utcnow() - timedelta(hours=settings.RESULT_EXPIRE_HOURS)

        # 清理上传目录（使用较短过期时间）
        try:
            upload_files = storage.list_files(prefix="uploads/")
            logger.info(f"检查 {len(upload_files)} 个上传文件...")

            for file_key in upload_files:
                # 获取文件修改时间
                file_mtime = storage.get_file_mtime(file_key)
                if file_mtime and file_mtime < cutoff:
                    if storage.delete_file(file_key):
                        deleted += 1
                        logger.info(f"删除过期文件: {file_key}")

            logger.info(f"上传目录清理完成，删除了 {deleted} 个文件")
        except Exception as e:
            logger.warning(f"清理上传目录失败: {e}")

        # 清理结果目录（使用较长过期时间：RESULT_EXPIRE_HOURS）
        try:
            result_files = storage.list_files(prefix="results/")
            result_deleted = 0

            for file_key in result_files:
                file_mtime = storage.get_file_mtime(file_key)
                if file_mtime and file_mtime < result_cutoff:
                    if storage.delete_file(file_key):
                        result_deleted += 1
                        logger.info(f"删除过期结果文件: {file_key}")

                        # 同时清理对应的任务记录
                        # 从 file_key 中提取 task_id，格式: results/{task_id}/{filename}
                        try:
                            parts = file_key.split('/')
                            if len(parts) >= 2:
                                result_task_id = parts[1]
                                await task_manager.delete_task(result_task_id)
                                logger.info(f"已清理过期结果对应的任务: {result_task_id}")
                        except Exception as e:
                            logger.warning(f"清理过期任务失败: {e}")

            if result_deleted > 0:
                logger.info(f"结果目录清理完成，删除了 {result_deleted} 个文件")
        except Exception as e:
            logger.warning(f"清理结果目录失败: {e}")

        if deleted > 0:
            logger.info(f"共清理了 {deleted} 个过期文件")

    except Exception as e:
        logger.error(f"清理过期文件失败: {e}")


async def cleanup_loop():
    """定时清理循环"""
    while True:
        try:
            await cleanup_expired_tasks()
            await cleanup_expired_files()
        except Exception as e:
            logger.error(f"清理循环异常: {e}")
        
        # 每小时执行一次
        await asyncio.sleep(3600)


def start_cleanup_scheduler():
    """启动清理调度器"""
    asyncio.create_task(cleanup_loop())
    logger.info("清理调度器已启动")


# 如果需要更精确的清理，可以使用 APScheduler
# 但对于简单的场景，上面的定时循环已经足够
