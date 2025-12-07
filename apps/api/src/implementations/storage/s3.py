"""
S3-compatible storage backend implementation.

Works with:
- AWS S3
- MinIO
- DigitalOcean Spaces
- Cloudflare R2
- Any S3-compatible storage
"""

from __future__ import annotations

import hashlib
from typing import BinaryIO, AsyncIterator, Optional
from datetime import datetime, timedelta
from io import BytesIO

from src.core.interfaces.storage import StorageFile, PresignedURL


class S3StorageBackend:
    """
    S3-compatible storage backend.

    Works with AWS S3, MinIO, and any S3-compatible service.

    Usage:
        # AWS S3
        storage = S3StorageBackend(
            bucket="my-bucket",
            region="us-east-1",
            access_key="AKIA...",
            secret_key="...",
        )

        # MinIO
        storage = S3StorageBackend(
            bucket="my-bucket",
            endpoint_url="http://localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
        )

        # Upload
        file_info = await storage.upload(
            key="users/123/avatar.jpg",
            data=image_bytes,
            content_type="image/jpeg",
        )

        # Get presigned URL for direct upload
        presigned = await storage.get_presigned_upload_url(
            key="users/123/document.pdf",
            content_type="application/pdf",
        )
        # Client uploads directly to presigned.url
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        use_ssl: bool = True,
        public_url: Optional[str] = None,
    ):
        """
        Initialize S3 storage backend.

        Args:
            bucket: S3 bucket name
            region: AWS region (default: us-east-1)
            access_key: AWS access key ID (or MinIO access key)
            secret_key: AWS secret access key (or MinIO secret key)
            endpoint_url: Custom endpoint for MinIO/compatible services
            use_ssl: Use HTTPS (default: True)
            public_url: Public URL prefix for generating public URLs
        """
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self.public_url = public_url

        # Import here to avoid requiring boto3 if not using S3
        try:
            import aioboto3
        except ImportError:
            raise ImportError(
                "aioboto3 is required for S3 storage. "
                "Install with: pip install aioboto3"
            )

        # Create session
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self._endpoint_url = endpoint_url
        self._use_ssl = use_ssl

    def _get_client_config(self) -> dict:
        """Get configuration for S3 client."""
        config = {}
        if self._endpoint_url:
            config["endpoint_url"] = self._endpoint_url
        if not self._use_ssl:
            config["use_ssl"] = False
        return config

    async def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """Upload a file to S3."""
        # Convert to bytes if needed
        if hasattr(data, "read"):
            data = data.read()

        # Compute ETag
        etag = hashlib.md5(data).hexdigest()

        # Prepare upload args
        extra_args = {
            "ContentType": content_type,
        }
        if metadata:
            extra_args["Metadata"] = metadata

        async with self._session.client("s3", **self._get_client_config()) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                **extra_args,
            )

        return StorageFile(
            key=key,
            size=len(data),
            content_type=content_type,
            etag=etag,
            last_modified=datetime.utcnow(),
            metadata=metadata,
        )

    async def upload_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """
        Upload a file from an async stream.

        Useful for large files to avoid loading into memory.
        """
        # For S3, we need to use multipart upload for streaming
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        async with self._session.client("s3", **self._get_client_config()) as s3:
            # Start multipart upload
            mpu = await s3.create_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                **extra_args,
            )
            upload_id = mpu["UploadId"]

            parts = []
            part_number = 1
            total_size = 0
            buffer = BytesIO()

            try:
                async for chunk in stream:
                    buffer.write(chunk)
                    total_size += len(chunk)

                    # Upload part when buffer is large enough (5MB minimum)
                    if buffer.tell() >= 5 * 1024 * 1024:
                        buffer.seek(0)
                        part = await s3.upload_part(
                            Bucket=self.bucket,
                            Key=key,
                            UploadId=upload_id,
                            PartNumber=part_number,
                            Body=buffer.read(),
                        )
                        parts.append({
                            "PartNumber": part_number,
                            "ETag": part["ETag"],
                        })
                        part_number += 1
                        buffer = BytesIO()

                # Upload remaining data
                if buffer.tell() > 0:
                    buffer.seek(0)
                    part = await s3.upload_part(
                        Bucket=self.bucket,
                        Key=key,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=buffer.read(),
                    )
                    parts.append({
                        "PartNumber": part_number,
                        "ETag": part["ETag"],
                    })

                # Complete multipart upload
                await s3.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )

            except Exception:
                # Abort on error
                await s3.abort_multipart_upload(
                    Bucket=self.bucket,
                    Key=key,
                    UploadId=upload_id,
                )
                raise

        return StorageFile(
            key=key,
            size=total_size,
            content_type=content_type,
            last_modified=datetime.utcnow(),
            metadata=metadata,
        )

    async def download(self, key: str) -> bytes:
        """Download file contents."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
            except s3.exceptions.NoSuchKey:
                raise FileNotFoundError(f"File not found: {key}")

    async def stream(self, key: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """Stream file contents in chunks."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                async with response["Body"] as stream:
                    while True:
                        chunk = await stream.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                if "NoSuchKey" in str(e):
                    raise FileNotFoundError(f"File not found: {key}")
                raise

    async def delete(self, key: str) -> bool:
        """Delete a file."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple files at once. Returns count of deleted files."""
        if not keys:
            return 0

        async with self._session.client("s3", **self._get_client_config()) as s3:
            # S3 allows max 1000 keys per request
            deleted = 0
            for i in range(0, len(keys), 1000):
                batch = keys[i:i + 1000]
                response = await s3.delete_objects(
                    Bucket=self.bucket,
                    Delete={
                        "Objects": [{"Key": k} for k in batch],
                        "Quiet": True,
                    },
                )
                deleted += len(batch) - len(response.get("Errors", []))

            return deleted

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def get_metadata(self, key: str) -> StorageFile | None:
        """Get file metadata without downloading."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            try:
                response = await s3.head_object(Bucket=self.bucket, Key=key)
                return StorageFile(
                    key=key,
                    size=response["ContentLength"],
                    content_type=response.get("ContentType", "application/octet-stream"),
                    etag=response.get("ETag", "").strip('"'),
                    last_modified=response.get("LastModified"),
                    metadata=response.get("Metadata"),
                )
            except Exception:
                return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> tuple[list[StorageFile], str | None]:
        """List files with prefix."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            kwargs = {
                "Bucket": self.bucket,
                "MaxKeys": limit,
            }
            if prefix:
                kwargs["Prefix"] = prefix
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = await s3.list_objects_v2(**kwargs)

            files = []
            for obj in response.get("Contents", []):
                files.append(StorageFile(
                    key=obj["Key"],
                    size=obj["Size"],
                    content_type="application/octet-stream",  # Not available in list
                    etag=obj.get("ETag", "").strip('"'),
                    last_modified=obj.get("LastModified"),
                ))

            next_token = response.get("NextContinuationToken")
            return files, next_token

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
        max_size: int | None = None,
    ) -> PresignedURL:
        """
        Get presigned URL for direct upload.

        Client can PUT directly to this URL without going through your API.
        """
        async with self._session.client("s3", **self._get_client_config()) as s3:
            # Generate presigned POST for more control, or simple PUT
            url = await s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

            return PresignedURL(
                url=url,
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                headers={
                    "Content-Type": content_type,
                },
            )

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedURL:
        """
        Get presigned URL for direct download.

        Client can download directly from this URL.
        """
        async with self._session.client("s3", **self._get_client_config()) as s3:
            params = {
                "Bucket": self.bucket,
                "Key": key,
            }

            # Set Content-Disposition to force download with filename
            if filename:
                params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

            url = await s3.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )

            return PresignedURL(
                url=url,
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            )

    async def copy(self, source_key: str, dest_key: str) -> StorageFile:
        """Copy file to new location."""
        async with self._session.client("s3", **self._get_client_config()) as s3:
            await s3.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": source_key},
                Key=dest_key,
            )

            return await self.get_metadata(dest_key)

    def get_public_url(self, key: str) -> str:
        """
        Get public URL for a file.

        Only works if bucket/object has public read access.
        """
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{key}"

        if self._endpoint_url:
            return f"{self._endpoint_url}/{self.bucket}/{key}"

        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
