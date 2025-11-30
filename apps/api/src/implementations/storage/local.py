"""
Local filesystem storage backend implementation.
"""

from __future__ import annotations

import os
import shutil
import hashlib
import mimetypes
import aiofiles
import aiofiles.os
from typing import BinaryIO, AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path

from src.core.interfaces.storage import StorageFile, PresignedURL


class LocalStorageBackend:
    """
    Local filesystem storage backend.

    Stores files in a local directory. Useful for development and
    single-server deployments. For production, use S3 or similar.

    Usage:
        storage = LocalStorageBackend(base_path="./uploads")

        # Upload
        file_info = await storage.upload(
            key="users/123/avatar.jpg",
            data=image_bytes,
            content_type="image/jpeg",
        )

        # Download
        data = await storage.download("users/123/avatar.jpg")

        # Stream large files
        async for chunk in storage.stream("large-file.zip"):
            yield chunk

        # Check existence
        exists = await storage.exists("users/123/avatar.jpg")

        # Delete
        await storage.delete("users/123/avatar.jpg")
    """

    def __init__(
        self,
        base_path: str = "./uploads",
        base_url: str | None = None,
        chunk_size: int = 8192,
    ):
        """
        Initialize local storage backend.

        Args:
            base_path: Directory to store files
            base_url: Base URL for generating download URLs (e.g., "/files")
            chunk_size: Chunk size for streaming
        """
        self.base_path = Path(base_path)
        self.base_url = base_url or "/files"
        self.chunk_size = chunk_size

        # Create base directory if needed
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        """Get full filesystem path for key."""
        # Prevent path traversal attacks
        safe_key = key.lstrip("/").replace("..", "")
        return self.base_path / safe_key

    def _compute_etag(self, data: bytes) -> str:
        """Compute ETag (MD5 hash) for data."""
        return hashlib.md5(data).hexdigest()

    async def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """Upload a file."""
        full_path = self._full_path(key)

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Get bytes from BinaryIO if needed
        if hasattr(data, "read"):
            data = data.read()

        # Write file
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)

        # Store metadata in sidecar file (optional)
        if metadata:
            meta_path = full_path.with_suffix(full_path.suffix + ".meta")
            import json
            async with aiofiles.open(meta_path, "w") as f:
                await f.write(json.dumps(metadata))

        return StorageFile(
            key=key,
            size=len(data),
            content_type=content_type,
            etag=self._compute_etag(data),
            last_modified=datetime.utcnow(),
            metadata=metadata,
        )

    async def download(self, key: str) -> bytes:
        """Download file contents."""
        full_path = self._full_path(key)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def stream(self, key: str) -> AsyncIterator[bytes]:
        """Stream file contents in chunks."""
        full_path = self._full_path(key)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(self.chunk_size):
                yield chunk

    async def delete(self, key: str) -> bool:
        """Delete a file."""
        full_path = self._full_path(key)

        if not full_path.exists():
            return False

        await aiofiles.os.remove(full_path)

        # Also delete metadata file if exists
        meta_path = full_path.with_suffix(full_path.suffix + ".meta")
        if meta_path.exists():
            await aiofiles.os.remove(meta_path)

        return True

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        full_path = self._full_path(key)
        return full_path.exists()

    async def get_metadata(self, key: str) -> StorageFile | None:
        """Get file metadata without downloading."""
        full_path = self._full_path(key)

        if not full_path.exists():
            return None

        stat = full_path.stat()

        # Try to load custom metadata
        metadata = None
        meta_path = full_path.with_suffix(full_path.suffix + ".meta")
        if meta_path.exists():
            import json
            async with aiofiles.open(meta_path, "r") as f:
                content = await f.read()
                metadata = json.loads(content)

        # Guess content type
        content_type, _ = mimetypes.guess_type(str(full_path))
        content_type = content_type or "application/octet-stream"

        return StorageFile(
            key=key,
            size=stat.st_size,
            content_type=content_type,
            etag=None,  # Would need to read file to compute
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            metadata=metadata,
        )

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> tuple[list[StorageFile], str | None]:
        """List files with prefix."""
        prefix_path = self._full_path(prefix) if prefix else self.base_path
        files: list[StorageFile] = []

        # Walk directory
        for root, _, filenames in os.walk(prefix_path):
            for filename in filenames:
                # Skip metadata files
                if filename.endswith(".meta"):
                    continue

                full_path = Path(root) / filename
                key = str(full_path.relative_to(self.base_path))

                # Get basic info
                stat = full_path.stat()
                content_type, _ = mimetypes.guess_type(str(full_path))

                files.append(StorageFile(
                    key=key,
                    size=stat.st_size,
                    content_type=content_type or "application/octet-stream",
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                ))

                if len(files) >= limit:
                    # Return next token (last key)
                    return files, key

        return files, None

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> PresignedURL:
        """
        Get presigned URL for direct upload.

        Note: Local storage doesn't support true presigned URLs.
        Returns a URL that should be handled by your API endpoint.
        """
        return PresignedURL(
            url=f"{self.base_url}/upload/{key}",
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            headers={"Content-Type": content_type},
        )

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedURL:
        """
        Get presigned URL for direct download.

        Note: Local storage doesn't support true presigned URLs.
        Returns a URL that should be handled by your API endpoint.
        """
        url = f"{self.base_url}/{key}"
        if filename:
            url += f"?filename={filename}"

        return PresignedURL(
            url=url,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
        )

    async def copy(self, source_key: str, dest_key: str) -> StorageFile:
        """Copy file to new location."""
        source_path = self._full_path(source_key)
        dest_path = self._full_path(dest_key)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_key}")

        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(source_path, dest_path)

        # Copy metadata if exists
        source_meta = source_path.with_suffix(source_path.suffix + ".meta")
        if source_meta.exists():
            dest_meta = dest_path.with_suffix(dest_path.suffix + ".meta")
            shutil.copy2(source_meta, dest_meta)

        # Return new file info
        return await self.get_metadata(dest_key)
