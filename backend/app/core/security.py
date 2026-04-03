"""
安全防护模块
包含限流、请求验证等安全功能
"""
from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import re
import time
import logging
from typing import Optional, Set, List, Dict
from dataclasses import dataclass

from app.core.config import settings
from app.core.session import session_manager, generate_fingerprint_hash, UserSession

logger = logging.getLogger(__name__)

# 限流器（保留原有的 IP 限流作为兜底）
limiter = Limiter(key_func=get_remote_address)


def setup_rate_limiting(app):
    """配置限流"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # 添加会话中间件
    app.add_middleware(SessionMiddleware)


class SecurityValidator:
    """安全验证器"""
    
    # 允许的安全命令模式（避免误报）
    # 例如: rm -rf /var/lib/apt/lists/* 是 apt-get 安装后的标准清理操作
    SAFE_PATTERNS: List[re.Pattern] = [
        re.compile(r'\brm\s+-rf\s+/var/lib/apt/lists/', re.IGNORECASE),
        re.compile(r'\brm\s+-rf\s+/var/cache/apt/', re.IGNORECASE),
        re.compile(r'\brm\s+-rf\s+/tmp/', re.IGNORECASE),
    ]

    # 危险命令模式
    DANGEROUS_PATTERNS: List[re.Pattern] = [
        re.compile(r'\brm\s+-rf\s+/', re.IGNORECASE),
        re.compile(r'\brm\s+-rf\s+\*', re.IGNORECASE),
        re.compile(r':\(\)\{\s*:\|\:&\s*\}', re.IGNORECASE),
        re.compile(r'\.bashrc|\.bash_profile', re.IGNORECASE),
        re.compile(r'--privileged', re.IGNORECASE),
        re.compile(r'--security-opt', re.IGNORECASE),
        re.compile(r'mount\s+--bind', re.IGNORECASE),
        re.compile(r'chmod\s+777\s+/', re.IGNORECASE),
        re.compile(r'curl\s+.*\|.*sh', re.IGNORECASE),
        re.compile(r'wget\s+.*\|.*sh', re.IGNORECASE),
        re.compile(r'nc\s+-[el]', re.IGNORECASE),
        re.compile(r'/etc/passwd', re.IGNORECASE),
        re.compile(r'/etc/shadow', re.IGNORECASE),
        re.compile(r'sudo\s+', re.IGNORECASE),
        re.compile(r'adduser|useradd', re.IGNORECASE),
    ]
    
    # 允许的基础指令
    ALLOWED_COMMANDS: Set[str] = {
        'apt-get', 'apt', 'yum', 'dnf', 'apk',  # 包管理器
        'pip', 'pip3', 'npm', 'yarn', 'pnpm',  # 包管理器
        'RUN', 'CMD', 'ENTRYPOINT', 'COPY', 'ADD',  # Docker 指令
        'FROM', 'WORKDIR', 'ENV', 'EXPOSE', 'VOLUME',  # Docker 指令
        'USER', 'LABEL', 'ARG', 'ONBUILD', 'HEALTHCHECK',  # Docker 指令
    }
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """
        验证文件名安全性
        防止路径遍历攻击
        """
        if not filename:
            return False
        
        # 检查路径遍历
        dangerous_patterns = ['..', '~', '$', '|', '&', ';', '`', '$(', '${']
        for pattern in dangerous_patterns:
            if pattern in filename:
                return False
        
        # 检查绝对路径
        if filename.startswith('/') or filename.startswith('\\'):
            return False
        
        return True
    
    @classmethod
    def validate_dockerfile_content(cls, content: str, skip_security_check: bool = False) -> tuple[bool, str]:
        """
        验证 Dockerfile 内容安全性
        返回: (是否通过, 错误信息)

        Args:
            content: Dockerfile 内容
            skip_security_check: 是否跳过安全检查（用于用户上传自己的 Dockerfile 时）
        """
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # 移除注释
            code_part = line.split('#')[0].strip()

            if not code_part:
                continue

            # 检查是否是已知的安全命令，如果是则跳过
            if cls._is_safe_command(code_part):
                continue

            # 如果启用了安全检查，检查危险模式
            if not skip_security_check:
                for pattern in cls.DANGEROUS_PATTERNS:
                    if pattern.search(code_part):
                        return False, f"第 {line_num} 行包含危险指令: {code_part[:50]}..."

            # 检查未授权的系统修改
            if 'chpasswd' in code_part.lower():
                return False, f"第 {line_num} 行包含密码修改指令"

            if '/etc/sudoers' in code_part:
                return False, f"第 {line_num} 行尝试修改 sudoers"

            # 检查网络访问危险操作
            if 'eval ' in code_part and ('$' in code_part):
                return False, f"第 {line_num} 行包含危险的 eval 指令"

        return True, ""

    @classmethod
    def _is_safe_command(cls, code_part: str) -> bool:
        """检查是否是已知的安全命令"""
        for pattern in cls.SAFE_PATTERNS:
            if pattern.search(code_part):
                return True
        return False
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """清理文件名，移除危险字符"""
        # 移除危险字符
        filename = re.sub(r'[^\w\s\-\.]', '_', filename)
        # 限制长度
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + '.' + ext if ext else name[:255]
        return filename


class RequestValidator:
    """请求验证器"""
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """验证文件扩展名"""
        if not filename:
            return False
        
        # 标准化允许的扩展名列表（确保都有点）
        normalized_allowed = set()
        for ext in allowed_extensions:
            if ext.startswith('.'):
                normalized_allowed.add(ext.lower())
            else:
                normalized_allowed.add('.' + ext.lower())
        
        # 检查文件名是否完全匹配允许的列表（针对无扩展名的文件如 Dockerfile）
        if filename in allowed_extensions:
            return True
        
        # 如果文件名包含扩展名
        if '.' in filename:
            ext = '.' + filename.rsplit('.', 1)[1].lower()
            return ext in normalized_allowed
        
        return False
    
    @staticmethod
    def validate_file_size(size: int, max_size: int) -> bool:
        """验证文件大小"""
        return 0 < size <= max_size


def create_security_headers() -> dict:
    """创建安全响应头"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
    }


class RateLimitTracker:
    """请求频率追踪"""
    
    def __init__(self):
        self.requests: dict = {}
        self.window = 60  # 60秒窗口
    
    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        
        # 清理过期记录
        if client_id in self.requests:
            self.requests[client_id] = [
                t for t in self.requests[client_id] 
                if now - t < self.window
            ]
        else:
            self.requests[client_id] = []
        
        # 检查限制
        if len(self.requests[client_id]) >= settings.RATE_LIMIT_PER_MINUTE:
            return False
        
        # 记录请求
        self.requests[client_id].append(now)
        return True


rate_limit_tracker = RateLimitTracker()


class SessionMiddleware(BaseHTTPMiddleware):
    """会话中间件 - 处理用户识别和会话管理"""
    
    EXCLUDED_PATHS = {
        "/", "/docs", "/openapi.json", "/redoc",
        "/api/health", "/favicon.ico"
    }
    
    async def dispatch(self, request: Request, call_next):
        # 排除不需要会话的路径
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # 获取或创建会话
        session: Optional[UserSession] = None
        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        
        logger.info(f"[SessionMiddleware] 路径: {request.url.path}, Cookie中的session_id: {session_id[:8] if session_id else 'None'}")
        
        if session_id:
            is_valid, session = await session_manager.validate_session(session_id)
            logger.info(f"[SessionMiddleware] session验证结果: is_valid={is_valid}, session_id={session.session_id[:8] if session else 'None'}")
            if not is_valid:
                session_id = None
        else:
            logger.info("[SessionMiddleware] 没有Cookie中的session_id")
        
        # 将会话信息附加到请求状态
        request.state.session = session
        request.state.session_id = session_id
        
        # 处理请求
        response = await call_next(request)

        # 如果没有有效会话但有指纹，则创建新会话
        if not session and getattr(request.state, 'fingerprint', None):
            ip = self._get_client_ip(request)
            ua = request.headers.get("user-agent", "")

            session = await session_manager.create_session(
                fingerprint=getattr(request.state, 'fingerprint', ''),
                ip_address=ip,
                user_agent=ua
            )

            # 设置 Cookie
            response.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=session.session_id,
                max_age=settings.SESSION_TTL_HOURS * 3600,
                httponly=True,
                samesite="lax"
            )

            # 附加到响应状态
            response.state.new_session = session

        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class UserRateLimiter:
    """基于用户会话的限流器"""
    
    def __init__(self):
        self._request_counts: Dict[str, List[float]] = {}
        self._build_counts: Dict[str, int] = {}
        self._lock = time
    
    async def check_rate_limit(
        self,
        session: Optional[UserSession],
        ip_address: str,
        action: str = "general"
    ) -> tuple[bool, str]:
        """
        检查限流
        
        Args:
            session: 用户会话
            ip_address: IP 地址
            action: 操作类型 (general, upload, build)
        
        Returns:
            (是否允许, 错误消息)
        """
        now = time.time()
        window = 60  # 1分钟窗口
        
        # 根据操作类型设置不同的限制
        limits = {
            "general": settings.RATE_LIMIT_PER_MINUTE,
            "upload": settings.RATE_LIMIT_PER_MINUTE // 2,
            "build": 5  # 构建操作更严格的限制
        }
        limit = limits.get(action, limits["general"])
        
        # 如果有会话，按会话 ID 限流
        if session:
            client_id = session.session_id
        else:
            client_id = f"ip:{ip_address}"
        
        # 清理过期记录
        if client_id in self._request_counts:
            self._request_counts[client_id] = [
                t for t in self._request_counts[client_id]
                if now - t < window
            ]
        else:
            self._request_counts[client_id] = []
        
        # 检查限制
        if len(self._request_counts[client_id]) >= limit:
            return False, f"请求过于频繁，请 {60 - int(now - self._request_counts[client_id][0])} 秒后重试"
        
        # 记录请求
        self._request_counts[client_id].append(now)
        return True, ""
    
    async def check_build_limit(
        self,
        session: Optional[UserSession],
        ip_address: str
    ) -> tuple[bool, str]:
        """检查并发构建限制"""
        max_concurrent = settings.MAX_CONCURRENT_BUILDS_PER_USER
        
        if session:
            client_id = session.session_id
        else:
            client_id = f"ip:{ip_address}"
        
        current_builds = self._build_counts.get(client_id, 0)
        
        if current_builds >= max_concurrent:
            return False, f"同时最多 {max_concurrent} 个构建任务"
        
        return True, ""
    
    async def increment_build(self, session_id: str):
        """增加构建计数"""
        self._build_counts[session_id] = self._build_counts.get(session_id, 0) + 1
    
    async def decrement_build(self, session_id: str):
        """减少构建计数"""
        if session_id in self._build_counts:
            self._build_counts[session_id] = max(0, self._build_counts[session_id] - 1)


user_rate_limiter = UserRateLimiter()


async def get_or_create_session(request: Request) -> Optional[UserSession]:
    """
    获取或创建会话的辅助函数
    
    从请求中提取指纹并获取/创建会话
    """
    session = getattr(request.state, "session", None)
    
    if not session:
        # 尝试从 Cookie 获取
        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_id:
            session = await session_manager.get_session(session_id)
    
    return session
