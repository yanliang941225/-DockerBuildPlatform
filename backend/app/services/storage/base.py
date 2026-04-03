"""
存储服务抽象层
支持多种存储后端：本地存储、七牛云、阿里云 OSS、AWS S3 等
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from enum import Enum
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """存储类型枚举"""
    LOCAL = "local"
    QINIU = "qiniu"
    OSS = "oss"
    S3 = "s3"


class BaseStorage(ABC):
    """存储服务抽象基类"""
    
    @abstractmethod
    def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> bool:
        """上传文件"""
        pass
    
    @abstractmethod
    def download_file(self, key: str) -> Optional[bytes]:
        """下载文件"""
        pass
    
    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """检查文件是否存在"""
        pass
    
    @abstractmethod
    def get_download_url(self, key: str, expires: int = 3600) -> str:
        """获取下载链接"""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """列出文件"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """检查存储是否已配置"""
        pass

    @abstractmethod
    def get_file_mtime(self, key: str) -> Optional[datetime]:
        """获取文件修改时间"""
        pass

    @property
    @abstractmethod
    def storage_type(self) -> StorageType:
        """返回存储类型"""
        pass


class LocalStorage(BaseStorage):
    """本地文件系统存储"""
    
    def __init__(self, base_dir: str = "/tmp/docker-storage"):
        self.base_dir = base_dir
        import os
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"本地存储初始化完成，路径: {self.base_dir}")
    
    def _get_full_path(self, key: str) -> str:
        """获取完整路径"""
        import os
        # 安全处理：规范化路径，防止路径遍历攻击
        # 移除开头的斜杠，防止绝对路径注入
        safe_key = key.lstrip('/')
        # 确保只包含安全的字符
        safe_key = safe_key.replace('..', '')
        full_path = os.path.join(self.base_dir, safe_key)
        # 确保最终路径在 base_dir 内
        real_base = os.path.realpath(self.base_dir)
        real_full = os.path.realpath(os.path.dirname(full_path))
        if not real_full.startswith(real_base):
            raise ValueError(f"非法路径访问: {key}")
        return full_path
    
    def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> bool:
        try:
            import os
            full_path = self._get_full_path(key)
            
            logger.info(f"准备上传文件: key={key}, size={len(content)} bytes, path={full_path}")
            
            # 创建目录
            dir_path = os.path.dirname(full_path)
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"目录已创建/确认: {dir_path}")
            
            # 检查磁盘空间
            stat = os.statvfs(dir_path)
            free_space = stat.f_bavail * stat.f_frsize
            logger.info(f"磁盘空间: 可用 {free_space / (1024**3):.2f} GB, 需要 {len(content) / (1024**3):.2f} GB")
            
            if free_space < len(content):
                logger.error(f"磁盘空间不足: 需要 {len(content)} bytes, 可用 {free_space} bytes")
                return False
            
            with open(full_path, 'wb') as f:
                f.write(content)
            
            # 验证文件写入成功
            actual_size = os.path.getsize(full_path)
            if actual_size != len(content):
                logger.error(f"文件大小不匹配: 期望 {len(content)}, 实际 {actual_size}")
                os.remove(full_path)
                return False
            
            logger.info(f"文件上传成功: {key}, 大小: {actual_size} bytes")
            return True
        except PermissionError as e:
            logger.error(f"权限不足，无法写入文件 {key}: {e}")
            return False
        except OSError as e:
            logger.error(f"操作系统错误，上传文件 {key} 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"本地文件上传失败: {type(e).__name__}: {e}")
            return False
    
    def download_file(self, key: str) -> Optional[bytes]:
        try:
            full_path = self._get_full_path(key)
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"本地文件下载失败: {e}")
            return None
    
    def delete_file(self, key: str) -> bool:
        try:
            import os
            full_path = self._get_full_path(key)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"文件删除成功: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"本地文件删除失败: {e}")
            return False
    
    def file_exists(self, key: str) -> bool:
        import os
        return os.path.exists(self._get_full_path(key))
    
    def get_download_url(self, key: str, expires: int = 3600) -> str:
        """本地存储返回相对路径，前端通过 API 下载"""
        return f"/api/storage/download/{key}"
    
    def list_files(self, prefix: str = "") -> List[str]:
        import os
        results = []
        prefix_path = os.path.join(self.base_dir, prefix)
        
        if os.path.exists(prefix_path):
            if os.path.isfile(prefix_path):
                return [prefix]
            for root, _, files in os.walk(prefix_path):
                for file in files:
                    rel_path = os.path.relpath(
                        os.path.join(root, file),
                        self.base_dir
                    )
                    results.append(rel_path)
        
        return results
    
    def is_configured(self) -> bool:
        return True

    def get_file_mtime(self, key: str) -> Optional[datetime]:
        """获取文件修改时间"""
        import os
        from datetime import datetime
        try:
            full_path = self._get_full_path(key)
            if os.path.exists(full_path):
                mtime = os.path.getmtime(full_path)
                return datetime.fromtimestamp(mtime)
        except Exception as e:
            logger.warning(f"获取文件修改时间失败: {e}")
        return None

    @property
    def storage_type(self) -> StorageType:
        return StorageType.LOCAL


class QiniuStorageAdapter(BaseStorage):
    """七牛云存储适配器"""
    
    def __init__(self):
        self._auth = None
        self._bucket_domain = None
        self._bucket = None
        self._initialize()
    
    def _initialize(self):
        """初始化七牛云"""
        if settings.QINIU_ACCESS_KEY and settings.QINIU_SECRET_KEY:
            try:
                from qiniu import Auth
                self._auth = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
                self._bucket = settings.QINIU_BUCKET
                self._bucket_domain = f"{settings.QINIU_BUCKET}.s3.{settings.QINIU_REGION}.qiniucs.com"
                logger.info(f"七牛云存储初始化成功，Bucket: {settings.QINIU_BUCKET}")
            except ImportError:
                logger.warning("七牛云 SDK 未安装")
            except Exception as e:
                logger.error(f"七牛云初始化失败: {e}")
    
    def is_configured(self) -> bool:
        return self._auth is not None

    def get_file_mtime(self, key: str) -> Optional[datetime]:
        """获取文件修改时间（七牛云）"""
        if not self.is_configured():
            return None
        try:
            from qiniu import stat
            ret, info = stat(settings.QINIU_BUCKET, key)
            if info.status_code == 200 and ret:
                # 七牛云返回的是 Unix 时间戳
                return datetime.fromtimestamp(ret.get('fsize', 0))
        except Exception as e:
            logger.warning(f"获取文件修改时间失败: {e}")
        return None

    def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> bool:
        if not self.is_configured():
            logger.warning("七牛云未配置，跳过上传")
            return False
        
        try:
            from qiniu import put_data
            
            policy = {
                'expires': 3600,
                'scope': f"{settings.QINIU_BUCKET}:{key}",
            }
            
            token = self._auth.upload_token(
                settings.QINIU_BUCKET,
                key=key,
                expires=3600,
                policy=policy
            )
            
            ret, info = put_data(
                None, key, content,
                mime_type=content_type,
                upload_token=token
            )
            
            if info.status_code == 200:
                logger.info(f"七牛云上传成功: {key}")
                return True
            else:
                logger.error(f"七牛云上传失败: {info.text_body}")
                return False
                
        except Exception as e:
            logger.error(f"七牛云上传异常: {e}")
            return False
    
    def download_file(self, key: str) -> Optional[bytes]:
        """下载文件（需要公网访问或配置私有空间）"""
        if not self.is_configured():
            return None
        
        try:
            import requests
            url = self.get_download_url(key)
            response = requests.get(url)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"下载失败: {e}")
        return None
    
    def delete_file(self, key: str) -> bool:
        if not self.is_configured():
            return False
        
        try:
            from qiniu import delete
            ret, info = delete(settings.QINIU_BUCKET, key)
            if info.status_code == 200:
                logger.info(f"七牛云删除成功: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"七牛云删除失败: {e}")
            return False
    
    def file_exists(self, key: str) -> bool:
        if not self.is_configured():
            return False
        
        try:
            from qiniu import stat
            ret, info = stat(settings.QINIU_BUCKET, key)
            return info.status_code == 200
        except:
            return False
    
    def get_download_url(self, key: str, expires: int = 3600) -> str:
        if not self.is_configured():
            return ""
        
        base_url = f'http://{self._bucket_domain}/{key}'
        return self._auth.private_download_url(base_url, expires=expires)
    
    def list_files(self, prefix: str = "") -> List[str]:
        if not self.is_configured():
            return []
        
        try:
            from qiniu import preq
            
            items = []
            marker = None
            
            while True:
                ret, info = preq.list_prefix(
                    settings.QINIU_BUCKET,
                    prefix=prefix,
                    marker=marker,
                    limit=100
                )
                
                if ret and 'items' in ret:
                    items.extend([item['key'] for item in ret['items']])
                
                if not ret or not ret.get('marker'):
                    break
                
                marker = ret['marker']
            
            return items
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    @property
    def storage_type(self) -> StorageType:
        return StorageType.QINIU


class StorageFactory:
    """存储工厂类 - 根据配置创建合适的存储实例"""
    
    _instance: Optional[BaseStorage] = None
    
    @classmethod
    def get_storage(cls) -> BaseStorage:
        """
        获取存储实例
        
        存储选择逻辑:
        - STORAGE_TYPE=local: 强制使用本地存储
        - STORAGE_TYPE=qiniu: 强制使用七牛云
        - STORAGE_TYPE=auto (默认): 优先七牛云，不可用则本地
        """
        if cls._instance is not None:
            return cls._instance
        
        storage_type = settings.STORAGE_TYPE.lower()
        
        # 强制本地存储
        if storage_type == "local":
            cls._instance = LocalStorage(base_dir=settings.STORAGE_LOCAL_PATH)
            logger.info("使用本地存储")
            return cls._instance
        
        # 强制七牛云
        if storage_type == "qiniu":
            qiniu = QiniuStorageAdapter()
            if qiniu.is_configured():
                cls._instance = qiniu
                logger.info("使用七牛云存储")
                return cls._instance
            else:
                logger.error("配置了七牛云但凭证无效，将使用本地存储")
                cls._instance = LocalStorage(base_dir=settings.STORAGE_LOCAL_PATH)
                return cls._instance
        
        # 自动选择
        if settings.QINIU_ACCESS_KEY and settings.QINIU_SECRET_KEY:
            qiniu = QiniuStorageAdapter()
            if qiniu.is_configured():
                cls._instance = qiniu
                logger.info("使用七牛云存储（自动选择）")
                return cls._instance
        
        # 默认使用本地存储
        cls._instance = LocalStorage(base_dir=settings.STORAGE_LOCAL_PATH)
        logger.info("使用本地存储")
        return cls._instance
    
    @classmethod
    def get_local_storage(cls) -> LocalStorage:
        """获取本地存储实例"""
        return LocalStorage(base_dir=settings.STORAGE_LOCAL_PATH)
    
    @classmethod
    def reset(cls):
        """重置存储实例（用于测试或配置变更）"""
        cls._instance = None


# 便捷函数
def get_storage() -> BaseStorage:
    """获取当前配置的存储"""
    return StorageFactory.get_storage()


def get_storage_type() -> StorageType:
    """获取当前存储类型"""
    return get_storage().storage_type
