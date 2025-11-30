"""
Storage backend protocol.
Implementations: LocalStorage, S3Storage, GCSStorage, AzureBlobStorage
"""
from __future__ import annotations

from typing import Protocol, BinaryIO, AsyncIterator
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StorageFile:
    """Represents a stored file."""
    key: str
    size: int
    content_type: str
    etag: str | None = None
    last_modified: datetime | None = None
    metadata: dict[str, str] | None = None


@dataclass
class PresignedURL:
    """Presigned URL for direct upload/download."""
    url: str
    expires_at: datetime
    headers: dict[str, str] | None = None


class StorageBackend(Protocol):
    """
    Protocol for file storage backends.

    Example implementations:
    - LocalStorageBackend: Store files on local filesystem
    - S3StorageBackend: AWS S3 or S3-compatible (MinIO)
    - GCSStorageBackend: Google Cloud Storage
    """

    async def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """Upload a file."""
        ...

    async def download(self, key: str) -> bytes:
        """Download file contents."""
        ...

    async def stream(self, key: str) -> AsyncIterator[bytes]:
        """Stream file contents in chunks."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete a file. Returns True if deleted, False if not found."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        ...

    async def get_metadata(self, key: str) -> StorageFile | None:
        """Get file metadata without downloading."""
        ...

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> tuple[list[StorageFile], str | None]:
        """List files with prefix. Returns (files, next_token)."""
        ...

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> PresignedURL:
        """Get presigned URL for direct upload."""
        ...

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedURL:
        """Get presigned URL for direct download."""
        ...

    async def copy(self, source_key: str, dest_key: str) -> StorageFile:
        """Copy file to new location."""
        ...
