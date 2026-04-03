"""
存储服务模块
支持多种存储后端：本地存储、七牛云、阿里云 OSS、AWS S3 等

使用方式:
    from app.services.storage import get_storage
    
    storage = get_storage()
    storage.upload_file("key", content)
    url = storage.get_download_url("key")
"""
from app.services.storage.base import (
    BaseStorage,
    StorageType,
    LocalStorage,
    QiniuStorageAdapter,
    StorageFactory,
    get_storage,
    get_storage_type,
)

__all__ = [
    "BaseStorage",
    "StorageType", 
    "LocalStorage",
    "QiniuStorageAdapter",
    "StorageFactory",
    "get_storage",
    "get_storage_type",
]
