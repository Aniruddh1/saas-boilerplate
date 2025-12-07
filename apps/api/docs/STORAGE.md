# File Storage

Enterprise file storage with multiple backends: Local, S3, and MinIO.

## Overview

| Backend | Use Case | Configuration |
|---------|----------|---------------|
| **Local** | Development, single server | `STORAGE_BACKEND=local` |
| **S3** | Production, AWS | `STORAGE_BACKEND=s3` |
| **MinIO** | Self-hosted S3-compatible | `STORAGE_BACKEND=s3` + endpoint |

## Quick Start

### Upload File

```python
from fastapi import UploadFile, Depends
from src.utils.storage import (
    get_storage,
    validate_upload,
    generate_file_key,
    upload_file,
)
from src.core.interfaces.storage import StorageBackend

@router.post("/upload")
async def upload_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    # Validate
    validate_upload(file, max_size_mb=5, allowed_types=["image/*"])

    # Generate key
    key = generate_file_key(
        "avatars",
        file.filename,
        user_id=str(current_user.id),
    )

    # Upload
    result = await upload_file(storage, key, file)

    return {"key": result.key, "size": result.size}
```

### Presigned URLs (Direct Upload/Download)

```python
@router.post("/upload-url")
async def get_upload_url(
    filename: str,
    content_type: str,
    storage: StorageBackend = Depends(get_storage),
):
    """Get presigned URL for direct upload to S3."""
    key = generate_file_key("documents", filename)

    presigned = await storage.get_presigned_upload_url(
        key=key,
        content_type=content_type,
        expires_in=3600,  # 1 hour
    )

    return {
        "upload_url": presigned.url,
        "key": key,
        "expires_at": presigned.expires_at,
    }

@router.get("/download-url/{key:path}")
async def get_download_url(
    key: str,
    storage: StorageBackend = Depends(get_storage),
):
    """Get presigned URL for direct download."""
    presigned = await storage.get_presigned_download_url(
        key=key,
        expires_in=3600,
        filename="download.pdf",  # Forces download with this name
    )

    return {"url": presigned.url}
```

## Configuration

### Local Storage (Development)

```env
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./uploads
```

### AWS S3

```env
STORAGE_BACKEND=s3
STORAGE_S3_BUCKET=my-app-files
STORAGE_S3_REGION=us-east-1
STORAGE_S3_ACCESS_KEY=AKIA...
STORAGE_S3_SECRET_KEY=...
```

### MinIO (Self-Hosted)

```env
STORAGE_BACKEND=s3
STORAGE_S3_BUCKET=my-bucket
STORAGE_S3_ENDPOINT=http://localhost:9000
STORAGE_S3_ACCESS_KEY=minioadmin
STORAGE_S3_SECRET_KEY=minioadmin
```

### DigitalOcean Spaces / Cloudflare R2

```env
STORAGE_BACKEND=s3
STORAGE_S3_BUCKET=my-space
STORAGE_S3_REGION=nyc3
STORAGE_S3_ENDPOINT=https://nyc3.digitaloceanspaces.com
STORAGE_S3_ACCESS_KEY=...
STORAGE_S3_SECRET_KEY=...
```

## File Validation

### Basic Validation

```python
from src.utils.storage import validate_upload

# Validate with size and type restrictions
validate_upload(
    file,
    max_size_mb=10,
    allowed_types=["image/*", "application/pdf"],
)
```

### Image Validation

```python
from src.utils.storage import validate_image

validate_image(file, max_size_mb=5)
# Allows: jpeg, png, gif, webp
```

### Document Validation

```python
from src.utils.storage import validate_document

validate_document(file, max_size_mb=20)
# Allows: pdf, docx, xlsx, pptx, txt, csv
```

### Validate Size by Reading

```python
from src.utils.storage import validate_upload_size

# For chunked uploads where file.size is unavailable
size = await validate_upload_size(file, max_size_mb=10)
```

## Key Generation

### Basic Key

```python
from src.utils.storage import generate_file_key

key = generate_file_key(
    "documents",
    "report.pdf",
    user_id="123",
    tenant_id="456",
)
# "tenant_456/user_123/documents/a1b2c3d4_report.pdf"
```

### Date-Partitioned Key

```python
from src.utils.storage import generate_dated_key

key = generate_dated_key("uploads", "data.csv")
# "uploads/2024/01/15/a1b2c3d4_data.csv"
```

### Sanitize Filename

```python
from src.utils.storage import sanitize_filename

safe = sanitize_filename("My Document (1).PDF")
# "my_document_1.pdf"
```

## Storage Operations

### Upload

```python
# Upload bytes
result = await storage.upload(
    key="data/export.json",
    data=json_bytes,
    content_type="application/json",
    metadata={"created_by": "user_123"},
)

# Upload from UploadFile
result = await upload_file(storage, key, file)
```

### Download

```python
# Download to bytes
data = await storage.download("documents/report.pdf")

# Stream for large files
async for chunk in storage.stream("large-file.zip"):
    yield chunk
```

### Check Existence

```python
exists = await storage.exists("avatars/user123.jpg")
```

### Get Metadata

```python
meta = await storage.get_metadata("documents/report.pdf")
# StorageFile(key=..., size=1024, content_type="application/pdf", ...)
```

### Delete

```python
# Single file
deleted = await storage.delete("temp/file.txt")

# Multiple files (S3 only)
count = await storage.delete_many(["file1.txt", "file2.txt"])
```

### Copy

```python
new_file = await storage.copy(
    "drafts/document.pdf",
    "published/document.pdf",
)
```

### List Files

```python
files, next_token = await storage.list_files(
    prefix="users/123/",
    limit=100,
)

# Paginate
while next_token:
    more_files, next_token = await storage.list_files(
        prefix="users/123/",
        continuation_token=next_token,
    )
    files.extend(more_files)
```

## Streaming Upload (Large Files)

```python
# S3 backend supports streaming upload
async def upload_large_file(stream: AsyncIterator[bytes]):
    result = await storage.upload_stream(
        key="large/file.zip",
        stream=stream,
        content_type="application/zip",
    )
    return result
```

## Architecture

```
src/core/interfaces/storage.py          # StorageBackend protocol
src/implementations/storage/
├── __init__.py
├── local.py                            # LocalStorageBackend
└── s3.py                               # S3StorageBackend (S3/MinIO)
src/utils/storage.py                    # Utilities and dependencies
```

## Security Considerations

### Filename Sanitization

All filenames are automatically sanitized:
- Path traversal prevented (`../` removed)
- Special characters replaced
- Dangerous extensions rejected (`.exe`, `.php`, etc.)

### Presigned URLs

- Use short expiration times (1 hour for uploads, less for downloads)
- Validate content type on upload
- Don't expose internal keys in URLs

### Access Control

```python
@router.get("/files/{key:path}")
async def download_file(
    key: str,
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    # Check user has access to this file
    if not key.startswith(f"user_{current_user.id}/"):
        raise HTTPException(403, "Access denied")

    return await storage.download(key)
```

## MinIO Setup (Docker)

```yaml
# docker-compose.yml
services:
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  minio_data:
```

Create bucket:
```bash
# Using mc (MinIO client)
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/my-bucket
```

## Best Practices

1. **Use presigned URLs** for direct upload/download to reduce server load
2. **Validate before upload** - check size and type client-side too
3. **Use meaningful keys** - include tenant/user IDs for isolation
4. **Set lifecycle policies** - auto-delete old files in S3
5. **Don't store sensitive data** in metadata - it's not encrypted
6. **Use date-partitioned keys** for files that accumulate
7. **Handle large files** with streaming, not loading into memory
