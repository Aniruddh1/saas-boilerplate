"""
Multi-cloud storage backend using Apache Libcloud.

Supports 30+ cloud providers with a unified interface:
- AWS S3
- Google Cloud Storage
- Azure Blob Storage
- DigitalOcean Spaces
- MinIO (S3-compatible)
- Rackspace, Linode, and many more

Install: pip install apache-libcloud
"""

from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from typing import AsyncIterator, Optional
from datetime import datetime, timedelta
from functools import partial

from src.core.interfaces.storage import StorageFile, PresignedURL


class CloudStorageBackend:
    """
    Multi-cloud storage backend using Apache Libcloud.

    Supports all major cloud providers with a unified API.

    Usage:
        # AWS S3
        storage = CloudStorageBackend(
            provider="s3",
            container="my-bucket",
            key="AKIA...",
            secret="...",
            region="us-east-1",
        )

        # Google Cloud Storage
        storage = CloudStorageBackend(
            provider="google_storage",
            container="my-bucket",
            key="service-account@project.iam.gserviceaccount.com",
            secret="/path/to/credentials.json",
            project="my-project",
        )

        # Azure Blob Storage
        storage = CloudStorageBackend(
            provider="azure_blobs",
            container="my-container",
            key="account-name",
            secret="account-key",
        )

        # DigitalOcean Spaces
        storage = CloudStorageBackend(
            provider="digitalocean_spaces",
            container="my-space",
            key="access-key",
            secret="secret-key",
            region="nyc3",
        )

        # MinIO (S3-compatible)
        storage = CloudStorageBackend(
            provider="s3",
            container="my-bucket",
            key="minioadmin",
            secret="minioadmin",
            host="localhost",
            port=9000,
            secure=False,
        )
    """

    # Provider name mappings
    PROVIDERS = {
        "s3": "S3",
        "aws": "S3",
        "gcs": "GOOGLE_STORAGE",
        "google": "GOOGLE_STORAGE",
        "google_storage": "GOOGLE_STORAGE",
        "azure": "AZURE_BLOBS",
        "azure_blobs": "AZURE_BLOBS",
        "digitalocean": "DIGITALOCEAN_SPACES",
        "digitalocean_spaces": "DIGITALOCEAN_SPACES",
        "spaces": "DIGITALOCEAN_SPACES",
        "linode": "LINODE_OBJECT_STORAGE",
        "backblaze": "BACKBLAZE_B2",
        "b2": "BACKBLAZE_B2",
        "rackspace": "CLOUDFILES",
        "minio": "S3",  # MinIO uses S3 protocol
    }

    def __init__(
        self,
        provider: str,
        container: str,
        key: str,
        secret: str,
        region: Optional[str] = None,
        project: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        secure: bool = True,
    ):
        """
        Initialize cloud storage backend.

        Args:
            provider: Cloud provider name (s3, gcs, azure, etc.)
            container: Bucket/container name
            key: Access key / account name / service account email
            secret: Secret key / account key / credentials path
            region: Region (for S3, DigitalOcean, etc.)
            project: Project ID (for GCS)
            host: Custom host (for MinIO or self-hosted S3)
            port: Custom port (for MinIO)
            secure: Use HTTPS (default: True)
        """
        try:
            from libcloud.storage.types import Provider
            from libcloud.storage.providers import get_driver
        except ImportError:
            raise ImportError(
                "apache-libcloud is required for cloud storage. "
                "Install with: pip install apache-libcloud"
            )

        # Resolve provider name
        provider_key = provider.lower()
        if provider_key not in self.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Supported: {list(self.PROVIDERS.keys())}"
            )

        provider_enum = getattr(Provider, self.PROVIDERS[provider_key])
        driver_cls = get_driver(provider_enum)

        # Build driver kwargs based on provider
        driver_kwargs = {}

        if region:
            driver_kwargs["region"] = region

        if project:  # For GCS
            driver_kwargs["project"] = project

        # For MinIO / custom S3 endpoint
        if host:
            driver_kwargs["host"] = host
        if port:
            driver_kwargs["port"] = port
        if not secure:
            driver_kwargs["secure"] = False

        # Create driver
        self._driver = driver_cls(key, secret, **driver_kwargs)
        self._container_name = container
        self._container = None

    def _get_container(self):
        """Get or create container (lazy load)."""
        if self._container is None:
            try:
                self._container = self._driver.get_container(self._container_name)
            except Exception:
                # Container doesn't exist, create it
                self._container = self._driver.create_container(self._container_name)
        return self._container

    def _sync_upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: Optional[dict[str, str]],
    ) -> StorageFile:
        """Synchronous upload."""
        container = self._get_container()

        extra = {"content_type": content_type}
        if metadata:
            extra["meta_data"] = metadata

        obj = self._driver.upload_object_via_stream(
            iterator=iter([data]),
            container=container,
            object_name=key,
            extra=extra,
        )

        return StorageFile(
            key=obj.name,
            size=obj.size,
            content_type=content_type,
            etag=obj.hash if hasattr(obj, "hash") else hashlib.md5(data).hexdigest(),
            last_modified=datetime.utcnow(),
            metadata=metadata,
        )

    async def upload(
        self,
        key: str,
        data: bytes | BytesIO,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> StorageFile:
        """Upload a file."""
        if hasattr(data, "read"):
            data = data.read()

        return await asyncio.to_thread(
            self._sync_upload, key, data, content_type, metadata
        )

    def _sync_download(self, key: str) -> bytes:
        """Synchronous download."""
        container = self._get_container()
        obj = self._driver.get_object(container.name, key)

        chunks = []
        for chunk in self._driver.download_object_as_stream(obj):
            chunks.append(chunk)

        return b"".join(chunks)

    async def download(self, key: str) -> bytes:
        """Download file contents."""
        try:
            return await asyncio.to_thread(self._sync_download, key)
        except Exception as e:
            if "not found" in str(e).lower():
                raise FileNotFoundError(f"File not found: {key}")
            raise

    async def stream(self, key: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """Stream file contents in chunks."""
        # Download and yield in chunks (Libcloud doesn't support true async streaming)
        data = await self.download(key)
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    def _sync_delete(self, key: str) -> bool:
        """Synchronous delete."""
        try:
            container = self._get_container()
            obj = self._driver.get_object(container.name, key)
            return self._driver.delete_object(obj)
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a file."""
        return await asyncio.to_thread(self._sync_delete, key)

    def _sync_exists(self, key: str) -> bool:
        """Synchronous exists check."""
        try:
            container = self._get_container()
            self._driver.get_object(container.name, key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        return await asyncio.to_thread(self._sync_exists, key)

    def _sync_get_metadata(self, key: str) -> Optional[StorageFile]:
        """Synchronous metadata fetch."""
        try:
            container = self._get_container()
            obj = self._driver.get_object(container.name, key)

            return StorageFile(
                key=obj.name,
                size=obj.size,
                content_type=obj.extra.get("content_type", "application/octet-stream"),
                etag=obj.hash if hasattr(obj, "hash") else None,
                last_modified=obj.extra.get("last_modified"),
                metadata=obj.meta_data if hasattr(obj, "meta_data") else None,
            )
        except Exception:
            return None

    async def get_metadata(self, key: str) -> Optional[StorageFile]:
        """Get file metadata without downloading."""
        return await asyncio.to_thread(self._sync_get_metadata, key)

    def _sync_list_files(
        self,
        prefix: str,
        limit: int,
    ) -> list[StorageFile]:
        """Synchronous list files."""
        container = self._get_container()
        files = []

        for obj in self._driver.iterate_container_objects(container, prefix=prefix):
            files.append(StorageFile(
                key=obj.name,
                size=obj.size,
                content_type=obj.extra.get("content_type", "application/octet-stream"),
                etag=obj.hash if hasattr(obj, "hash") else None,
                last_modified=obj.extra.get("last_modified"),
            ))

            if len(files) >= limit:
                break

        return files

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> tuple[list[StorageFile], Optional[str]]:
        """List files with prefix."""
        # Note: Libcloud doesn't support continuation tokens natively
        # We'll return None for next_token
        files = await asyncio.to_thread(self._sync_list_files, prefix, limit)
        return files, None

    def _sync_get_presigned_url(
        self,
        key: str,
        expires_in: int,
        method: str = "GET",
    ) -> str:
        """Get presigned URL (sync)."""
        container = self._get_container()

        try:
            obj = self._driver.get_object(container.name, key)
        except Exception:
            # Object doesn't exist yet (for upload URLs)
            # Create a temporary reference
            from libcloud.storage.base import Object
            obj = Object(
                name=key,
                size=0,
                hash=None,
                extra={},
                container=container,
                meta_data={},
                driver=self._driver,
            )

        return self._driver.get_object_cdn_url(obj)

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> PresignedURL:
        """
        Get presigned URL for direct upload.

        Note: Not all Libcloud providers support presigned URLs.
        Falls back to CDN URL where available.
        """
        try:
            url = await asyncio.to_thread(
                self._sync_get_presigned_url, key, expires_in, "PUT"
            )
        except Exception:
            # Fallback: return a placeholder
            url = f"/upload/{key}"

        return PresignedURL(
            url=url,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            headers={"Content-Type": content_type},
        )

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: Optional[str] = None,
    ) -> PresignedURL:
        """Get presigned URL for direct download."""
        try:
            url = await asyncio.to_thread(
                self._sync_get_presigned_url, key, expires_in, "GET"
            )
        except Exception:
            url = f"/download/{key}"

        return PresignedURL(
            url=url,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
        )

    def _sync_copy(self, source_key: str, dest_key: str) -> StorageFile:
        """Synchronous copy."""
        container = self._get_container()
        source_obj = self._driver.get_object(container.name, source_key)

        # Download and re-upload (Libcloud doesn't have native copy)
        data = b"".join(self._driver.download_object_as_stream(source_obj))
        content_type = source_obj.extra.get("content_type", "application/octet-stream")

        new_obj = self._driver.upload_object_via_stream(
            iterator=iter([data]),
            container=container,
            object_name=dest_key,
            extra={"content_type": content_type},
        )

        return StorageFile(
            key=new_obj.name,
            size=new_obj.size,
            content_type=content_type,
            last_modified=datetime.utcnow(),
        )

    async def copy(self, source_key: str, dest_key: str) -> StorageFile:
        """Copy file to new location."""
        return await asyncio.to_thread(self._sync_copy, source_key, dest_key)
