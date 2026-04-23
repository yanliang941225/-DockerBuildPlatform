"""
任务管理器服务
"""
import json
import uuid
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict, field, fields
from app.core.config import settings
from app.api.schemas import TaskStatus, LogEntry
import asyncio

logger = logging.getLogger(__name__)


def task_to_dict(task: 'Task') -> dict:
    """将 Task 转换为字典"""
    result = {}
    for f in fields(task):
        value = getattr(task, f.name)
        if isinstance(value, datetime):
            result[f.name] = value.isoformat()
        elif isinstance(value, TaskStatus):
            result[f.name] = value.value if hasattr(value, 'value') else str(value)
        elif isinstance(value, list):
            result[f.name] = value
        elif isinstance(value, dict):
            result[f.name] = value
        elif value is None or isinstance(value, (str, int, float, bool)):
            result[f.name] = value
        else:
            result[f.name] = str(value) if value is not None else None
    return result


def dict_to_task(data: dict) -> 'Task':
    """从字典创建 Task"""
    # 转换日期字符串
    for date_field in ['created_at', 'expires_at']:
        if date_field in data and isinstance(data[date_field], str):
            data[date_field] = datetime.fromisoformat(data[date_field])
    
    # 转换状态
    if 'status' in data:
        if isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
    
    return Task(**data)


@dataclass
class Task:
    """任务数据模型"""
    task_id: str
    target_arch: str
    status: TaskStatus
    created_at: datetime
    expires_at: datetime
    user_id: Optional[str] = None        # 关联的用户会话 ID
    dockerfile_key: Optional[str] = None
    dockerfile_name: Optional[str] = None
    context_key: Optional[str] = None
    context_name: Optional[str] = None
    image_name: Optional[str] = None     # 用户指定的镜像名称
    image_tag: str = "latest"           # 用户指定的镜像版本
    result_key: Optional[str] = None
    error_message: Optional[str] = None
    logs: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class TaskManager:
    """任务管理器 - 支持文件持久化"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._user_tasks: Dict[str, List[str]] = {}  # user_id -> [task_ids]
        self._lock = asyncio.Lock()
        # 持久化文件路径
        self._persist_dir = os.path.join(settings.STORAGE_LOCAL_PATH, "tasks")
        self._persist_file = os.path.join(self._persist_dir, "tasks.json")
        # 启动时加载
        self._load_tasks()

    def _load_tasks(self):
        """从磁盘加载任务"""
        try:
            if os.path.exists(self._persist_file):
                os.makedirs(self._persist_dir, exist_ok=True)
                with open(self._persist_file, 'r') as f:
                    data = json.load(f)
                
                for task_data in data.get('tasks', []):
                    try:
                        task = dict_to_task(task_data)
                        self._tasks[task.task_id] = task
                        
                        # 恢复用户索引
                        if task.user_id:
                            if task.user_id not in self._user_tasks:
                                self._user_tasks[task.user_id] = []
                            if task.task_id not in self._user_tasks[task.user_id]:
                                self._user_tasks[task.user_id].append(task.task_id)
                    except Exception as e:
                        logger.warning(f"加载任务失败: {e}")
                
                logger.info(f"从磁盘加载了 {len(self._tasks)} 个任务")
        except Exception as e:
            logger.error(f"加载任务失败: {e}")

    def _save_tasks(self):
        """保存所有任务到磁盘"""
        try:
            os.makedirs(self._persist_dir, exist_ok=True)
            tasks_data = [task_to_dict(t) for t in self._tasks.values()]
            
            with open(self._persist_file, 'w') as f:
                json.dump({'tasks': tasks_data, 'saved_at': datetime.utcnow().isoformat()}, f, indent=2)
            
            logger.debug(f"已保存 {len(self._tasks)} 个任务到磁盘")
        except Exception as e:
            logger.error(f"保存任务失败: {e}")

    async def create_task(
        self,
        target_arch: str,
        user_id: Optional[str] = None,
        image_name: Optional[str] = None,
        image_tag: str = "latest"
    ) -> Task:
        """创建新任务"""
        async with self._lock:
            task_id = str(uuid.uuid4())
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=settings.FILE_EXPIRE_HOURS)

            task = Task(
                task_id=task_id,
                target_arch=target_arch,
                status=TaskStatus.PENDING,
                created_at=now,
                expires_at=expires_at,
                user_id=user_id,
                image_name=image_name,
                image_tag=image_tag
            )

            self._tasks[task_id] = task

            # 维护用户任务索引
            if user_id:
                if user_id not in self._user_tasks:
                    self._user_tasks[user_id] = []
                self._user_tasks[user_id].append(task_id)

            # 异步保存，不阻塞主流程
            asyncio.create_task(self._save_task_async(task))

            return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        async with self._lock:
            task = self._tasks.get(task_id)
            
            # 检查是否过期
            if task and datetime.utcnow() > task.expires_at:
                task.status = TaskStatus.EXPIRED
            
            return task
    
    async def update_status(self, task_id: str, status: TaskStatus, error_message: Optional[str] = None):
        """更新任务状态"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                if error_message:
                    task.error_message = error_message
                asyncio.create_task(self._save_task_async(task))
    
    async def update_dockerfile(
        self, 
        task_id: str, 
        key: str, 
        filename: str, 
        size: int
    ):
        """更新 Dockerfile 信息"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.dockerfile_key = key
                task.dockerfile_name = filename
                task.metadata['dockerfile_size'] = size
                # 在锁内直接添加日志（不需要再次加锁）
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "message": f"Dockerfile 已上传: {filename} ({size} bytes)"
                }
                task.logs.append(log_entry)
                log_entry2 = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "message": f"Dockerfile key 已设置: {key}"
                }
                task.logs.append(log_entry2)
                if len(task.logs) > 1000:
                    task.logs = task.logs[-1000:]
                asyncio.create_task(self._save_task_async(task))
    
    async def update_context(
        self,
        task_id: str,
        key: str,
        filename: str,
        size: int
    ):
        """更新上下文文件信息"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.context_key = key
                task.context_name = filename
                task.metadata['context_size'] = size
                # 在锁内直接添加日志（不需要再次加锁）
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "message": f"构建上下文已上传: {filename} ({size} bytes)"
                }
                task.logs.append(log_entry)
                if len(task.logs) > 1000:
                    task.logs = task.logs[-1000:]
                asyncio.create_task(self._save_task_async(task))
    
    async def set_result(self, task_id: str, result_key: str):
        """设置构建结果"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.result_key = result_key
                task.status = TaskStatus.SUCCESS
                # 延长过期时间：成功任务延长到24小时
                task.expires_at = datetime.utcnow() + timedelta(hours=24)
                asyncio.create_task(self._add_log_async(task_id, "success", "镜像构建成功！"))
                asyncio.create_task(self._save_task_async(task))
    
    async def set_error(self, task_id: str, error_message: str):
        """设置错误信息"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = error_message
                asyncio.create_task(self._add_log_async(task_id, "error", f"构建失败: {error_message}"))
                await self._save_task(task)
    
    async def add_log(self, task_id: str, level: str, message: str):
        """添加日志条目（线程安全版本）"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": level,
                    "message": message
                }
                task.logs.append(log_entry)
                if len(task.logs) > 1000:
                    task.logs = task.logs[-1000:]
    
    async def get_logs(
        self, 
        task_id: str, 
        since: Optional[int] = None
    ) -> List[LogEntry]:
        """获取日志"""
        task = await self.get_task(task_id)
        if not task:
            return []
        
        logs = task.logs
        if since is not None:
            logs = logs[since:]
        
        return [
            LogEntry(
                timestamp=datetime.fromisoformat(log["timestamp"]),
                level=log["level"],
                message=log["message"]
            )
            for log in logs
        ]
    
    async def delete_task(self, task_id: str):
        """删除任务"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                # 从用户索引中移除
                if task.user_id and task.user_id in self._user_tasks:
                    if task_id in self._user_tasks[task.user_id]:
                        self._user_tasks[task.user_id].remove(task_id)
                del self._tasks[task_id]
    
    async def list_tasks(
        self, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Task]:
        """获取任务列表"""
        async with self._lock:
            # 按创建时间倒序
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True
            )
            
            # 分页
            return sorted_tasks[offset:offset + limit]

    async def get_tasks_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Task]:
        """获取指定用户的所有任务（使用索引优化）"""
        async with self._lock:
            # 使用索引快速定位用户的任务
            task_ids = self._user_tasks.get(user_id, [])
            if not task_ids:
                return []

            # 从索引中获取任务并按时间排序
            user_tasks = []
            now = datetime.utcnow()
            for tid in task_ids:
                task = self._tasks.get(tid)
                if task:
                    # 检查是否过期
                    if now > task.expires_at:
                        task.status = TaskStatus.EXPIRED
                    user_tasks.append(task)

            # 按创建时间倒序
            sorted_tasks = sorted(
                user_tasks,
                key=lambda t: t.created_at,
                reverse=True
            )
            # 分页
            return sorted_tasks[offset:offset + limit]
    
    async def cleanup_expired(self) -> int:
        """清理过期任务，返回清理数量"""
        async with self._lock:
            now = datetime.utcnow()
            expired = [
                task_id for task_id, task in self._tasks.items()
                if now > task.expires_at
            ]
            
            for task_id in expired:
                del self._tasks[task_id]
            
            return len(expired)
    
    async def _save_task(self, task: Task):
        """保存任务到持久化存储"""
        await asyncio.to_thread(self._save_tasks)

    async def _save_task_async(self, task: Task):
        """异步保存任务到持久化存储"""
        await asyncio.to_thread(self._save_tasks)

    async def _add_log_async(self, task_id: str, level: str, message: str):
        """异步添加日志条目"""
        # 日志暂时保存在内存中
        pass


# 全局实例
task_manager = TaskManager()
