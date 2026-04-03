"""
用户会话管理模块
基于 Cookie + 浏览器指纹 的无登录用户识别
支持文件持久化
"""
import uuid
import hashlib
import time
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, field, fields, asdict
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """用户会话"""
    session_id: str              # 会话 ID (UUID)
    fingerprint: str            # 浏览器指纹 hash
    ip_address: str             # IP 地址
    user_agent: str            # 用户代理
    created_at: float          # 创建时间戳
    last_active: float         # 最后活跃时间
    task_count: int = 0        # 该用户创建的任务数
    total_build_time: int = 0  # 累计构建时间（秒）
    blocked: bool = False       # 是否被封禁


def session_to_dict(session: UserSession) -> dict:
    """将会话转换为字典"""
    return {f.name: getattr(session, f.name) for f in fields(session)}


def dict_to_session(data: dict) -> UserSession:
    """从字典创建会话"""
    return UserSession(**data)


class SessionManager:
    """会话管理器 - 支持文件持久化"""
    
    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}
        self._fingerprint_index: Dict[str, str] = {}  # fingerprint -> session_id
        self._ip_index: Dict[str, List[str]] = {}     # ip -> [session_ids]
        self._lock = asyncio.Lock()
        self._session_ttl = settings.SESSION_TTL_HOURS * 3600  # 转换为秒
        self._cleanup_interval = 300  # 5分钟清理一次过期会话
        # 持久化
        self._persist_dir = os.path.join(settings.STORAGE_LOCAL_PATH, "sessions")
        self._persist_file = os.path.join(self._persist_dir, "sessions.json")
        # 加载持久化数据
        self._load_sessions()
    
    def _session_to_dict(self, session: UserSession) -> dict:
        """将会话转换为可序列化的字典"""
        return {
            'session_id': session.session_id,
            'fingerprint': session.fingerprint,
            'ip_address': session.ip_address,
            'user_agent': session.user_agent,
            'created_at': session.created_at,
            'last_active': session.last_active,
            'task_count': session.task_count,
            'total_build_time': session.total_build_time,
            'blocked': session.blocked
        }
    
    def _load_sessions(self):
        """从磁盘加载会话"""
        try:
            if os.path.exists(self._persist_file):
                os.makedirs(self._persist_dir, exist_ok=True)
                with open(self._persist_file, 'r') as f:
                    data = json.load(f)
                
                for session_data in data.get('sessions', []):
                    try:
                        session = dict_to_session(session_data)
                        # 检查是否过期
                        if not self._is_expired(session):
                            self._sessions[session.session_id] = session
                            self._fingerprint_index[session.fingerprint] = session.session_id
                            if session.ip_address not in self._ip_index:
                                self._ip_index[session.ip_address] = []
                            self._ip_index[session.ip_address].append(session.session_id)
                    except Exception as e:
                        logger.warning(f"加载会话失败: {e}")
                
                logger.info(f"从磁盘加载了 {len(self._sessions)} 个有效会话")
        except Exception as e:
            logger.error(f"加载会话失败: {e}")
    
    def _save_sessions(self):
        """保存所有会话到磁盘"""
        try:
            os.makedirs(self._persist_dir, exist_ok=True)
            sessions_data = [self._session_to_dict(s) for s in self._sessions.values()]
            
            with open(self._persist_file, 'w') as f:
                json.dump({'sessions': sessions_data, 'saved_at': datetime.now().isoformat()}, f)
            
            logger.debug(f"已保存 {len(self._sessions)} 个会话到磁盘")
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
    
    async def create_session(
        self,
        fingerprint: str,
        ip_address: str,
        user_agent: str
    ) -> UserSession:
        """创建新会话"""
        async with self._lock:
            # 检查该指纹是否已有活跃会话
            if fingerprint in self._fingerprint_index:
                existing_session_id = self._fingerprint_index[fingerprint]
                existing = self._sessions.get(existing_session_id)
                
                if existing and not self._is_expired(existing):
                    # 更新活跃时间，返回现有会话
                    existing.last_active = time.time()
                    self._save_sessions()  # 持久化
                    return existing
            
            # 创建新会话
            session_id = str(uuid.uuid4())
            now = time.time()
            
            session = UserSession(
                session_id=session_id,
                fingerprint=fingerprint,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=now,
                last_active=now
            )
            
            # 索引
            self._sessions[session_id] = session
            self._fingerprint_index[fingerprint] = session_id
            
            if ip_address not in self._ip_index:
                self._ip_index[ip_address] = []
            self._ip_index[ip_address].append(session_id)
            
            # 持久化
            self._save_sessions()
            
            logger.info(f"创建新会话: {session_id[:8]}..., IP: {ip_address}")
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话（使用乐观锁优化性能）"""
        # 先快速检查，不加锁
        session = self._sessions.get(session_id)
        if session is None:
            return None
        
        # 检查过期时更新 last_active
        now = time.time()
        if now - session.last_active > self._session_ttl:
            return None
        
        # 延迟更新活跃时间，避免频繁写锁
        if now - session.last_active > 60:  # 超过60秒才更新
            async with self._lock:
                if session in self._sessions.values():
                    session.last_active = now
        
        return session
    
    async def get_session_by_fingerprint(self, fingerprint: str) -> Optional[UserSession]:
        """通过指纹获取会话"""
        async with self._lock:
            session_id = self._fingerprint_index.get(fingerprint)
            if session_id:
                return await self.get_session(session_id)
            return None
    
    async def validate_session(self, session_id: str) -> tuple[bool, Optional[UserSession]]:
        """
        验证会话是否有效
        Returns: (is_valid, session)
        """
        session = await self.get_session(session_id)
        
        if not session:
            return False, None
        
        if session.blocked:
            logger.warning(f"会话 {session_id[:8]}... 被封禁")
            return False, session
        
        return True, session
    
    async def update_task_count(self, session_id: str, increment: int = 1):
        """更新用户的任务计数"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.task_count += increment
                session.last_active = time.time()
    
    async def record_build_time(self, session_id: str, seconds: int):
        """记录构建时间"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.total_build_time += seconds
                session.last_active = time.time()
    
    async def block_session(self, session_id: str):
        """封禁会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.blocked = True
                logger.warning(f"封禁会话: {session_id[:8]}...")
    
    async def get_user_stats(self, session_id: str) -> Optional[Dict]:
        """获取用户统计信息"""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "created_at": datetime.fromtimestamp(session.created_at).isoformat(),
            "task_count": session.task_count,
            "total_build_time": session.total_build_time,
            "is_blocked": session.blocked
        }
    
    async def get_ip_sessions(self, ip_address: str) -> List[UserSession]:
        """获取某 IP 的所有会话"""
        async with self._lock:
            session_ids = self._ip_index.get(ip_address, [])
            sessions = []
            
            for sid in session_ids:
                session = self._sessions.get(sid)
                if session and not self._is_expired(session):
                    sessions.append(session)
            
            return sessions
    
    async def cleanup_expired(self):
        """清理过期会话"""
        try:
            async with self._lock:
                expired_ids = []

                for session_id, session in list(self._sessions.items()):
                    if self._is_expired(session):
                        expired_ids.append(session_id)

                for session_id in expired_ids:
                    session = self._sessions.pop(session_id, None)
                    if session:
                        self._fingerprint_index.pop(session.fingerprint, None)
                        ip_sessions = self._ip_index.get(session.ip_address, [])
                        if session_id in ip_sessions:
                            ip_sessions.remove(session_id)
                        if not ip_sessions:
                            self._ip_index.pop(session.ip_address, None)

                if expired_ids:
                    logger.info(f"清理了 {len(expired_ids)} 个过期会话")
        except Exception as e:
            logger.error(f"清理会话时发生异常: {e}")
    
    def _is_expired(self, session: UserSession) -> bool:
        """检查会话是否过期"""
        return time.time() - session.last_active > self._session_ttl


# 全局会话管理器实例
session_manager = SessionManager()


def generate_fingerprint_hash(
    user_agent: str,
    screen: str,
    timezone: str,
    language: str,
    platform: str,
    canvas_fingerprint: Optional[str] = None,
    webgl_fingerprint: Optional[str] = None
) -> str:
    """
    生成浏览器指纹 hash
    
    Args:
        user_agent: 浏览器 User-Agent
        screen: 屏幕分辨率
        timezone: 时区
        language: 语言
        platform: 平台
        canvas_fingerprint: Canvas 指纹
        webgl_fingerprint: WebGL 指纹
    
    Returns:
        指纹 hash
    """
    components = [
        user_agent,
        screen,
        timezone,
        language,
        platform,
        canvas_fingerprint or "",
        webgl_fingerprint or ""
    ]
    
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def start_session_cleanup():
    """启动会话清理任务"""
    while True:
        await asyncio.sleep(300)  # 5分钟
        await session_manager.cleanup_expired()
