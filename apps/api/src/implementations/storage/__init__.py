"""
Storage backend implementations.

Available backends:
- LocalStorageBackend: Local filesystem (development)
- S3StorageBackend: AWS S3 / MinIO (using aioboto3)
- CloudStorageBackend: Multi-cloud via Apache Libcloud (30+ providers)

Usage:
    # Use the FastAPI dependency for automatic configuration:
    from src.utils.storage import get_storage

    @router.post("/upload")
    async def upload(storage: StorageBackend = Depends(get_storage)):
        ...

    # Or instantiate directly:
    from src.implementations.storage import LocalStorageBackend, S3StorageBackend

    storage = LocalStorageBackend(base_path="./uploads")
    storage = S3StorageBackend(bucket="my-bucket", region="us-east-1", ...)
"""

from src.implementations.storage.local import LocalStorageBackend
from src.implementations.storage.s3 import S3StorageBackend
from src.implementations.storage.cloud import CloudStorageBackend

__all__ = ["LocalStorageBackend", "S3StorageBackend", "CloudStorageBackend"]
