# File Storage

Multi-cloud file storage powered by Apache Libcloud. Supports 30+ cloud providers with a unified API.

## Supported Providers

| Provider | Backend Value | Description |
|----------|---------------|-------------|
| **Local** | `local` | Local filesystem (development) |
| **AWS S3** | `s3` | Amazon S3 |
| **Google Cloud** | `gcs` | Google Cloud Storage |
| **Azure** | `azure` | Azure Blob Storage |
| **DigitalOcean** | `digitalocean` | DigitalOcean Spaces |
| **Backblaze** | `backblaze` | Backblaze B2 |
| **Linode** | `linode` | Linode Object Storage |
| **MinIO** | `minio` | Self-hosted S3-compatible |
| **+ 20 more** | See Libcloud docs | Rackspace, etc. |

## Quick Start

```python
from fastapi import UploadFile, Depends
from src.utils.storage import get_storage, validate_upload, generate_file_key
from src.core.interfaces.storage import StorageBackend

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    # Validate
    validate_upload(file, max_size_mb=5, allowed_types=["image/*"])

    # Generate key
    key = generate_file_key("avatars", file.filename, user_id=str(current_user.id))

    # Upload (works with any provider!)
    content = await file.read()
    result = await storage.upload(key, content, file.content_type)

    return {"key": result.key, "size": result.size}
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
STORAGE_CONTAINER=my-bucket
STORAGE_KEY=AKIA...
STORAGE_SECRET=...
STORAGE_REGION=us-east-1
```

### Google Cloud Storage

```env
STORAGE_BACKEND=gcs
STORAGE_CONTAINER=my-bucket
STORAGE_KEY=service-account@project.iam.gserviceaccount.com
STORAGE_SECRET=/path/to/credentials.json
STORAGE_PROJECT=my-project
```

### Azure Blob Storage

```env
STORAGE_BACKEND=azure
STORAGE_CONTAINER=my-container
STORAGE_KEY=account-name
STORAGE_SECRET=account-key
```

### DigitalOcean Spaces

```env
STORAGE_BACKEND=digitalocean
STORAGE_CONTAINER=my-space
STORAGE_KEY=...
STORAGE_SECRET=...
STORAGE_REGION=nyc3
```

### Backblaze B2

```env
STORAGE_BACKEND=backblaze
STORAGE_CONTAINER=my-bucket
STORAGE_KEY=application-key-id
STORAGE_SECRET=application-key
```

### MinIO (Self-Hosted S3)

```env
STORAGE_BACKEND=minio
STORAGE_CONTAINER=my-bucket
STORAGE_KEY=minioadmin
STORAGE_SECRET=minioadmin
STORAGE_ENDPOINT=http://localhost:9000
```

## File Validation

```python
from src.utils.storage import validate_upload, validate_image, validate_document

# Generic validation
validate_upload(file, max_size_mb=10, allowed_types=["image/*", "application/pdf"])

# Image-specific (jpeg, png, gif, webp)
validate_image(file, max_size_mb=5)

# Document-specific (pdf, docx, xlsx, etc.)
validate_document(file, max_size_mb=20)
```

## Key Generation

```python
from src.utils.storage import generate_file_key, generate_dated_key

# With user/tenant namespacing
key = generate_file_key("documents", "report.pdf", user_id="123", tenant_id="456")
# "tenant_456/user_123/documents/a1b2c3d4_report.pdf"

# Date-partitioned (for lifecycle policies)
key = generate_dated_key("uploads", "data.csv")
# "uploads/2024/01/15/a1b2c3d4_data.csv"
```

## Storage Operations

### Upload

```python
result = await storage.upload(
    key="data/export.json",
    data=json_bytes,
    content_type="application/json",
    metadata={"created_by": "user_123"},
)
```

### Download

```python
data = await storage.download("documents/report.pdf")

# Stream for large files
async for chunk in storage.stream("large-file.zip"):
    yield chunk
```

### Other Operations

```python
# Check existence
exists = await storage.exists("path/to/file.txt")

# Get metadata
meta = await storage.get_metadata("path/to/file.txt")

# Delete
await storage.delete("path/to/file.txt")

# Copy
await storage.copy("source.txt", "dest.txt")

# List files
files, next_token = await storage.list_files(prefix="users/123/", limit=100)
```

### Presigned URLs

```python
# Direct upload URL (client uploads directly to cloud)
presigned = await storage.get_presigned_upload_url(
    key="documents/file.pdf",
    content_type="application/pdf",
    expires_in=3600,
)
# Client PUTs to presigned.url

# Direct download URL
presigned = await storage.get_presigned_download_url(
    key="documents/file.pdf",
    expires_in=3600,
    filename="download.pdf",
)
```

## Architecture

```
src/core/interfaces/storage.py          # StorageBackend protocol
src/implementations/storage/
├── __init__.py
├── local.py                            # LocalStorageBackend
├── s3.py                               # S3StorageBackend (direct boto3)
└── cloud.py                            # CloudStorageBackend (Libcloud)
src/utils/storage.py                    # Utilities and dependencies
```

## Installing Libcloud

```bash
pip install apache-libcloud
```

Or add to pyproject.toml:
```toml
[project.dependencies]
apache-libcloud = "^3.8"
```

## MinIO Setup (Docker)

```yaml
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
```

## Security

### Filename Sanitization

All filenames are automatically sanitized:
- Path traversal prevented (`../` removed)
- Special characters replaced
- Dangerous extensions rejected (`.exe`, `.php`, etc.)

### Access Control

```python
@router.get("/files/{key:path}")
async def download_file(
    key: str,
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    # Verify user has access
    if not key.startswith(f"user_{current_user.id}/"):
        raise HTTPException(403, "Access denied")

    return await storage.download(key)
```

## Best Practices

1. **Use presigned URLs** for large files - bypass your server
2. **Validate on client AND server** - size and type checks
3. **Namespace by tenant/user** - data isolation
4. **Date-partition keys** - easier lifecycle management
5. **Set bucket policies** - lifecycle rules for auto-cleanup
6. **Don't store secrets in metadata** - it's not encrypted
