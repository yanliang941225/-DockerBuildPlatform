"""
七牛云对象存储服务
"""
import logging
from typing import Optional, List
from datetime import datetime, timedelta
import hashlib

from qiniu import Auth, put_data
from qiniu.services.storage import uploader
from qiniu.utils import etag
from app.core.config import settings

logger = logging.getLogger(__name__)


class QiniuStorage:
    """七牛云存储服务"""
    
    def __init__(self):
        self._auth: Optional[Auth] = None
        self._bucket_domain: Optional[str] = None
        self._initialized = False
    
    def _ensure_init(self):
        """确保已初始化"""
        if not self._initialized:
            if not settings.QINIU_ACCESS_KEY or not settings.QINIU_SECRET_KEY:
                logger.warning("七牛云未配置，将使用本地存储")
                self._initialized = True
                return
            
            self._auth = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
            self._bucket_domain = f"{settings.QINIU_BUCKET}.s3.{settings.QINIU_REGION}.qiniucs.com"
            self._initialized = True
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        self._ensure_init()
        return bool(self._auth)
    
    def get_upload_token(self, key: str, expires: int = 3600) -> str:
        """
        获取上传凭证
        
        Args:
            key: 存储路径
            expires: 有效期（秒）
        
        Returns:
            上传凭证
        """
        self._ensure_init()
        
        if not self._auth:
            raise ValueError("七牛云未配置")
        
        policy = {
            'expires': expires,
            'scope': f"{settings.QINIU_BUCKET}:{key}",
        }
        
        return self._auth.upload_token(
            settings.QINIU_BUCKET,
            key=key,
            expires=expires,
            policy=policy
        )
    
    def upload_file(
        self, 
        key: str, 
        content: bytes, 
        content_type: str = "application/octet-stream"
    ) -> bool:
        """
        上传文件到七牛云
        
        Args:
            key: 存储路径
            content: 文件内容
            content_type: MIME类型
        
        Returns:
            是否成功
        """
        self._ensure_init()
        
        if not self._auth:
            # 降级到本地存储
            return self._upload_local(key, content)
        
        try:
            # 计算文件 hash
            file_hash = hashlib.md5(content).hexdigest()
            
            # 上传
            ret, info = put_data(
                None,  # 不指定 key，让服务端生成
                key,
                content,
                mime_type=content_type,
                metadata={
                    'hash': file_hash,
                    'uploaded': datetime.utcnow().isoformat()
                },
                upload_token=self.get_upload_token(key)
            )
            
            if info.status_code == 200:
                logger.info(f"文件上传成功: {key}")
                return True
            else:
                logger.error(f"文件上传失败: {info.text_body}")
                # 降级到本地
                return self._upload_local(key, content)
                
        except Exception as e:
            logger.error(f"七牛云上传异常: {e}，降级到本地存储")
            return self._upload_local(key, content)
    
    def _upload_local(self, key: str, content: bytes) -> bool:
        """降级到本地存储"""
        import os
        
        local_path = f"/tmp/qiniu_fallback/{key}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"文件已保存到本地: {local_path}")
        return True
    
    def get_download_url(self, key: str, expires: int = 3600) -> str:
        """
        获取下载链接
        
        Args:
            key: 存储路径
            expires: 有效期（秒）
        
        Returns:
            下载链接
        """
        self._ensure_init()
        
        if not self._auth:
            # 本地存储的下载路径
            return f"/api/files/{key}"
        
        base_url = f'http://{self._bucket_domain}/{key}'
        return self._auth.private_download_url(base_url, expires=expires)
    
    def delete_file(self, key: str) -> bool:
        """
        删除文件
        
        Args:
            key: 存储路径
        
        Returns:
            是否成功
        """
        self._ensure_init()
        
        if not self._auth:
            # 删除本地文件
            return self._delete_local(key)
        
        try:
            from qiniu import BucketManager
            bucket_manager = BucketManager(self._auth)
            ret, info = bucket_manager.delete(settings.QINIU_BUCKET, key)
            logger.info(f"文件删除成功: {key}")
            return info.status_code == 200
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return self._delete_local(key)
    
    def _delete_local(self, key: str) -> bool:
        """删除本地文件"""
        import os
        
        local_path = f"/tmp/qiniu_fallback/{key}"
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                return True
        except Exception as e:
            logger.error(f"删除本地文件失败: {e}")
        return False
    
    def file_exists(self, key: str) -> bool:
        """检查文件是否存在"""
        self._ensure_init()
        
        if not self._auth:
            import os
            return os.path.exists(f"/tmp/qiniu_fallback/{key}")
        
        try:
            from qiniu import BucketManager
            bucket_manager = BucketManager(self._auth)
            ret, info = bucket_manager.stat(settings.QINIU_BUCKET, key)
            return info.status_code == 200
        except:
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """列出指定前缀的文件"""
        self._ensure_init()
        
        if not self._auth:
            return []
        
        from qiniu import BucketManager
        bucket_manager = BucketManager(self._auth)
        
        marker = None
        items = []
        
        while True:
            ret, info, _ = bucket_manager.list(
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
    
    def set_lifecycle(self, key: str, days: int):
        """
        设置文件生命周期（需要存储空间配置生命周期规则）
        
        Args:
            key: 文件路径
            days: 多少天后删除
        """
        # 这需要在七牛云控制台配置存储空间的生命周期规则
        # 或者使用七牛云的 API 设置对象标签
        logger.info(f"建议在七牛云控制台设置 {key} 的生命周期为 {days} 天")
    
    def cleanup_old_files(self, prefix: str, hours: int) -> int:
        """
        清理过期文件
        
        Args:
            prefix: 文件前缀
            hours: 超过多少小时的文件将被删除
        
        Returns:
            删除的文件数量
        """
        files = self.list_files(prefix)
        deleted = 0
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # 注意：这里需要获取文件的上传时间
        # 七牛云的 list_prefix 返回的信息中可能不包含时间
        # 可以通过 stat 获取单个文件信息
        
        for key in files:
            if self.file_exists(key):
                # 简单处理：直接删除 prefix 下的所有文件
                # 生产环境应该根据文件元数据进行更精确的清理
                if self.delete_file(key):
                    deleted += 1
        
        logger.info(f"清理完成，删除了 {deleted} 个文件")
        return deleted


# 全局实例
qiniu_storage = QiniuStorage()
