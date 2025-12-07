"""
File Storage Utilities.

Provides:
- FastAPI dependencies for storage backend
- File upload validation (size, type)
- Key generation helpers
- Common upload patterns

Usage:
    from src.utils.storage import get_storage, upload_file, validate_upload

    @router.post("/upload")
    async def upload(
        file: UploadFile,
        storage: StorageBackend = Depends(get_storage),
    ):
        # Validate
        validate_upload(file, max_size_mb=10, allowed_types=["image/*"])

        # Generate key
        key = generate_file_key("avatars", file.filename, user_id=user.id)

        # Upload
        result = await upload_file(storage, key, file)
        return {"url": result.key}
"""

from __future__ import annotations

import re
import uuid
import mimetypes
from datetime import datetime
from typing import Optional, Sequence
from pathlib import Path

from fastapi import Depends, UploadFile, HTTPException

from src.core.config import settings
from src.core.interfaces.storage import StorageBackend, StorageFile


# ============================================================
# CONFIGURATION
# ============================================================

# Default allowed file types
DEFAULT_ALLOWED_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
]

# Dangerous file extensions to always reject
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".php", ".jsp", ".asp",
    ".dll", ".so", ".dylib", ".bin", ".com", ".msi",
}


# ============================================================
# FASTAPI DEPENDENCY
# ============================================================

async def get_storage() -> StorageBackend:
    """
    FastAPI dependency to get the configured storage backend.

    Configuration via environment:
        STORAGE_BACKEND=local|s3|gcs|azure|digitalocean|...
        STORAGE_LOCAL_PATH=./uploads
        STORAGE_CONTAINER=my-bucket
        STORAGE_KEY=access-key
        STORAGE_SECRET=secret-key
        STORAGE_REGION=us-east-1
        STORAGE_ENDPOINT=http://localhost:9000  (for MinIO)

    Supported backends (via Apache Libcloud):
        - local: Local filesystem
        - s3: AWS S3 or S3-compatible (MinIO)
        - gcs: Google Cloud Storage
        - azure: Azure Blob Storage
        - digitalocean: DigitalOcean Spaces
        - backblaze: Backblaze B2
        - linode: Linode Object Storage
        - And 20+ more providers

    Usage:
        @router.post("/upload")
        async def upload(
            file: UploadFile,
            storage: StorageBackend = Depends(get_storage),
        ):
            ...
    """
    storage_config = settings.storage
    backend = storage_config.backend.lower()

    if backend == "local":
        from src.implementations.storage.local import LocalStorageBackend

        return LocalStorageBackend(
            base_path=storage_config.local_path,
            base_url="/files",
        )

    # All cloud providers use Libcloud
    from src.implementations.storage.cloud import CloudStorageBackend

    # Map common names to Libcloud provider names
    provider_map = {
        "s3": "s3",
        "aws": "s3",
        "minio": "s3",
        "gcs": "google_storage",
        "google": "google_storage",
        "azure": "azure_blobs",
        "digitalocean": "digitalocean_spaces",
        "spaces": "digitalocean_spaces",
        "backblaze": "backblaze_b2",
        "b2": "backblaze_b2",
        "linode": "linode_object_storage",
    }

    provider = provider_map.get(backend, backend)

    # Build kwargs
    kwargs = {
        "provider": provider,
        "container": storage_config.container,
        "key": storage_config.key,
        "secret": storage_config.secret,
    }

    if storage_config.region:
        kwargs["region"] = storage_config.region

    if storage_config.project:
        kwargs["project"] = storage_config.project

    # For MinIO / custom endpoints
    if storage_config.endpoint:
        # Parse endpoint URL
        from urllib.parse import urlparse
        parsed = urlparse(storage_config.endpoint)
        kwargs["host"] = parsed.hostname
        if parsed.port:
            kwargs["port"] = parsed.port
        if parsed.scheme == "http":
            kwargs["secure"] = False

    return CloudStorageBackend(**kwargs)


# ============================================================
# FILE VALIDATION
# ============================================================

def validate_upload(
    file: UploadFile,
    max_size_mb: float = 10,
    allowed_types: Optional[Sequence[str]] = None,
    allowed_extensions: Optional[Sequence[str]] = None,
) -> None:
    """
    Validate an uploaded file.

    Args:
        file: FastAPI UploadFile
        max_size_mb: Maximum file size in megabytes
        allowed_types: Allowed MIME types (supports wildcards like "image/*")
        allowed_extensions: Allowed file extensions (e.g., [".jpg", ".png"])

    Raises:
        HTTPException: If validation fails

    Usage:
        validate_upload(
            file,
            max_size_mb=5,
            allowed_types=["image/*", "application/pdf"],
        )
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check extension for dangerous files
    ext = Path(file.filename).suffix.lower()
    if ext in DANGEROUS_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed: {ext}",
        )

    # Check allowed extensions if specified
    if allowed_extensions:
        allowed_extensions = [e.lower() for e in allowed_extensions]
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File extension not allowed. Allowed: {', '.join(allowed_extensions)}",
            )

    # Check content type
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
    if allowed_types:
        if not _matches_mime_type(content_type, allowed_types):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed: {content_type}",
            )

    # Check file size (if available)
    if file.size and file.size > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB",
        )


def _matches_mime_type(content_type: Optional[str], patterns: Sequence[str]) -> bool:
    """Check if content type matches any pattern (supports wildcards)."""
    if not content_type:
        return False

    for pattern in patterns:
        if pattern == content_type:
            return True
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if content_type.startswith(prefix + "/"):
                return True

    return False


async def validate_upload_size(
    file: UploadFile,
    max_size_mb: float = 10,
) -> int:
    """
    Validate file size by reading content.

    Use this when file.size is not available (chunked uploads).
    Returns the actual file size.

    Usage:
        size = await validate_upload_size(file, max_size_mb=10)
    """
    max_bytes = int(max_size_mb * 1024 * 1024)
    content = await file.read()
    size = len(content)

    if size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB",
        )

    # Reset file position for subsequent reads
    await file.seek(0)
    return size


# ============================================================
# KEY GENERATION
# ============================================================

def generate_file_key(
    prefix: str,
    filename: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    unique: bool = True,
) -> str:
    """
    Generate a storage key for a file.

    Args:
        prefix: Path prefix (e.g., "avatars", "documents")
        filename: Original filename
        user_id: Optional user ID for namespacing
        tenant_id: Optional tenant ID for namespacing
        unique: Add UUID to ensure uniqueness

    Returns:
        Storage key like "tenant_123/user_456/avatars/abc123_document.pdf"

    Usage:
        key = generate_file_key(
            "documents",
            "report.pdf",
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
        )
    """
    # Sanitize filename
    safe_filename = sanitize_filename(filename)

    # Add unique prefix if requested
    if unique:
        unique_id = uuid.uuid4().hex[:8]
        name, ext = Path(safe_filename).stem, Path(safe_filename).suffix
        safe_filename = f"{unique_id}_{name}{ext}"

    # Build path parts
    parts = []
    if tenant_id:
        parts.append(f"tenant_{tenant_id}")
    if user_id:
        parts.append(f"user_{user_id}")
    parts.append(prefix)
    parts.append(safe_filename)

    return "/".join(parts)


def generate_dated_key(
    prefix: str,
    filename: str,
    date: Optional[datetime] = None,
) -> str:
    """
    Generate a date-partitioned storage key.

    Useful for organizing files by date for easier lifecycle management.

    Returns:
        Key like "uploads/2024/01/15/abc123_document.pdf"
    """
    date = date or datetime.utcnow()
    safe_filename = sanitize_filename(filename)

    # Add unique prefix
    unique_id = uuid.uuid4().hex[:8]
    name, ext = Path(safe_filename).stem, Path(safe_filename).suffix
    safe_filename = f"{unique_id}_{name}{ext}"

    return f"{prefix}/{date.year}/{date.month:02d}/{date.day:02d}/{safe_filename}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage.

    - Removes path components
    - Replaces spaces with underscores
    - Removes special characters
    - Lowercases extension
    """
    # Get just the filename, no path
    filename = Path(filename).name

    # Split name and extension
    name, ext = Path(filename).stem, Path(filename).suffix

    # Sanitize name: keep alphanumeric, underscore, hyphen
    name = re.sub(r"[^\w\-]", "_", name)
    name = re.sub(r"_+", "_", name)  # Collapse multiple underscores
    name = name.strip("_")

    # Limit length
    if len(name) > 100:
        name = name[:100]

    # Lowercase extension
    ext = ext.lower()

    return f"{name}{ext}" if name else f"file{ext}"


# ============================================================
# UPLOAD HELPERS
# ============================================================

async def upload_file(
    storage: StorageBackend,
    key: str,
    file: UploadFile,
    metadata: Optional[dict[str, str]] = None,
) -> StorageFile:
    """
    Upload a FastAPI UploadFile to storage.

    Usage:
        result = await upload_file(storage, "avatars/user123.jpg", file)
    """
    content = await file.read()
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0]

    return await storage.upload(
        key=key,
        data=content,
        content_type=content_type or "application/octet-stream",
        metadata=metadata,
    )


async def upload_bytes(
    storage: StorageBackend,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    metadata: Optional[dict[str, str]] = None,
) -> StorageFile:
    """
    Upload raw bytes to storage.

    Usage:
        result = await upload_bytes(storage, "data/export.json", json_bytes)
    """
    return await storage.upload(
        key=key,
        data=data,
        content_type=content_type,
        metadata=metadata,
    )


# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_image(
    file: UploadFile,
    max_size_mb: float = 5,
    allowed_formats: Optional[Sequence[str]] = None,
) -> None:
    """
    Validate an image upload.

    Args:
        file: FastAPI UploadFile
        max_size_mb: Maximum file size
        allowed_formats: Allowed formats (default: jpeg, png, gif, webp)

    Usage:
        validate_image(file, max_size_mb=2)
    """
    allowed_formats = allowed_formats or ["jpeg", "png", "gif", "webp"]
    allowed_types = [f"image/{fmt}" for fmt in allowed_formats]

    validate_upload(
        file,
        max_size_mb=max_size_mb,
        allowed_types=allowed_types,
    )


def validate_document(
    file: UploadFile,
    max_size_mb: float = 20,
) -> None:
    """
    Validate a document upload (PDF, Office docs, etc.).

    Usage:
        validate_document(file, max_size_mb=10)
    """
    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
    ]

    validate_upload(
        file,
        max_size_mb=max_size_mb,
        allowed_types=allowed_types,
    )
