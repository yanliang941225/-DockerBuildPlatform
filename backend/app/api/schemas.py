"""
任务相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 等待中
    UPLOADING = "uploading"       # 上传中
    BUILDING = "building"          # 构建中
    SUCCESS = "success"            # 构建成功
    FAILED = "failed"             # 构建失败
    CANCELLED = "cancelled"       # 已取消
    EXPIRED = "expired"           # 已过期


class Architecture(str, Enum):
    """支持的架构"""
    AMD64 = "linux/amd64"         # X86_64
    ARM64 = "linux/arm64"         # ARM64
    ARMV7 = "linux/arm/v7"        # ARMv7


class TaskCreate(BaseModel):
    """创建任务请求"""
    target_arch: Architecture = Field(..., description="目标架构")
    image_name: Optional[str] = Field(None, description="镜像名称")
    image_tag: Optional[str] = Field("latest", description="镜像版本标签")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: TaskStatus
    target_arch: str
    created_at: datetime
    expires_at: datetime
    dockerfile_uploaded: bool = False
    context_uploaded: bool = False
    image_name: Optional[str] = None
    image_tag: Optional[str] = "latest"
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    download_expires_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: datetime
    level: str  # info, warning, error, success
    message: str


class BuildProgress(BaseModel):
    """构建进度"""
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)  # 0-100%
    current_step: Optional[str] = None
    logs: List[LogEntry] = []


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    filename: str
    size: int
    message: str


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    code: int = 400
