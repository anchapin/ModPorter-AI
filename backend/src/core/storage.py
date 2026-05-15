"""
Storage Configuration for portkit.

Provides:
- Local file storage (development)
- S3-compatible storage (production, Tigris on Fly.io)
- File organization by user/job
- Cleanup utilities
"""

import os
import shutil
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class StorageBackend(Enum):
    """Available storage backends"""

    LOCAL = "local"
    S3 = "s3"


class StorageManager:
    """
    Abstract storage manager supporting multiple backends.

    File organization:
    - uploads/{user_id}/{job_id}/original.jar
    - processing/{job_id}/
    - results/{job_id}/

    Supports:
    - Local filesystem (development)
    - S3-compatible storage (production, Tigris on Fly.io)
    """

    UPLOADS_DIR = "uploads"
    PROCESSING_DIR = "processing"
    RESULTS_DIR = "results"
    DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_TTL_DAYS = 7

    def __init__(
        self,
        backend: Optional[StorageBackend] = None,
        base_path: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_region: Optional[str] = None,
        s3_endpoint_url: Optional[str] = None,
        default_ttl_days: int = DEFAULT_TTL_DAYS,
    ):
        if backend is None:
            backend_str = os.getenv("STORAGE_BACKEND", "local").lower()
            backend = StorageBackend.LOCAL if backend_str == "local" else StorageBackend.S3

        self.backend = backend
        self.base_path = base_path or os.getenv("STORAGE_PATH", "/tmp/portkit-uploads")

        # S3 config - works with AWS, Tigris, MinIO, etc.
        self.s3_bucket = s3_bucket or os.getenv("S3_BUCKET", "")
        self.s3_region = s3_region or os.getenv(
            "AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        self.s3_endpoint_url = s3_endpoint_url or os.getenv("S3_ENDPOINT_URL", "")

        self.default_ttl_days = default_ttl_days
        self._upload_status: Dict[str, Dict[str, Any]] = {}

        # Lazy-loaded async S3 client
        self._s3_client = None

        if self.backend == StorageBackend.LOCAL:
            self._init_local_storage()

        logger.info(f"StorageManager initialized with {self.backend.value} backend")

    async def _get_s3_client(self):
        """Get or create an aiobotocore S3 client."""
        if self._s3_client is not None:
            return self._s3_client

        try:
            from aiobotocore.session import AioSession
        except ImportError:
            raise ImportError(
                "aiobotocore is required for S3 storage. Install it with: pip install aiobotocore"
            )

        session = AioSession()
        kwargs = {
            "service_name": "s3",
            "region_name": self.s3_region,
        }
        if self.s3_endpoint_url:
            kwargs["endpoint_url"] = self.s3_endpoint_url

        # Credentials from env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        self._s3_client = session.create_client(**kwargs)
        await self._s3_client.__aenter__()
        return self._s3_client

    async def close(self):
        """Clean up the S3 client session."""
        if self._s3_client is not None:
            await self._s3_client.__aexit__(None, None, None)
            self._s3_client = None

    def _s3_key(
        self, job_id: str, filename: str, user_id: str = "default", category: str = "original"
    ) -> str:
        """Generate an S3 object key following the same directory structure."""
        key_templates = {
            "original": f"{self.UPLOADS_DIR}/{user_id}/{job_id}/{filename}",
            "processing": f"{self.PROCESSING_DIR}/{job_id}/{filename}",
            "result": f"{self.RESULTS_DIR}/{job_id}/{filename}",
        }
        return key_templates.get(category, f"{category}/{job_id}/{filename}")

    def _init_local_storage(self):
        """Initialize local storage directory structure"""
        for dir_name in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            dir_path = os.path.join(self.base_path, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            logger.debug(f"Created storage directory: {dir_path}")

    async def save_file(
        self,
        content: bytes,
        job_id: str,
        filename: str,
        user_id: str = "default",
        category: str = "original",
    ) -> str:
        if self.backend == StorageBackend.LOCAL:
            return await self._save_local(content, job_id, filename, user_id, category)
        elif self.backend == StorageBackend.S3:
            return await self._save_s3(content, job_id, filename, user_id, category)
        else:
            raise ValueError(f"Unknown storage backend: {self.backend}")

    async def _save_local(
        self, content: bytes, job_id: str, filename: str, user_id: str, category: str
    ) -> str:
        if category == "original":
            dir_path = os.path.join(self.base_path, self.UPLOADS_DIR, user_id, job_id)
        elif category == "processing":
            dir_path = os.path.join(self.base_path, self.PROCESSING_DIR, job_id)
        elif category == "result":
            dir_path = os.path.join(self.base_path, self.RESULTS_DIR, job_id)
        else:
            dir_path = os.path.join(self.base_path, category, job_id)

        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        self._upload_status[job_id] = {
            "status": "completed",
            "progress": 100,
            "message": "File saved successfully",
            "path": file_path,
            "size": len(content),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"File saved locally: {file_path}")
        return file_path

    async def _save_s3(
        self, content: bytes, job_id: str, filename: str, user_id: str, category: str
    ) -> str:
        client = await self._get_s3_client()
        key = self._s3_key(job_id, filename, user_id, category)

        await client.put_object(
            Bucket=self.s3_bucket,
            Key=key,
            Body=content,
        )

        s3_uri = f"s3://{self.s3_bucket}/{key}"
        self._upload_status[job_id] = {
            "status": "completed",
            "progress": 100,
            "message": "File saved successfully",
            "path": s3_uri,
            "key": key,
            "size": len(content),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"File saved to S3: {s3_uri}")
        return s3_uri

    async def get_file(
        self, job_id: str, filename: str, user_id: str = "default"
    ) -> Optional[bytes]:
        if self.backend == StorageBackend.LOCAL:
            return await self._get_local(job_id, filename, user_id)
        elif self.backend == StorageBackend.S3:
            return await self._get_s3(job_id, filename, user_id)
        return None

    async def _get_local(self, job_id: str, filename: str, user_id: str) -> Optional[bytes]:
        search_paths = [
            os.path.join(self.base_path, self.UPLOADS_DIR, user_id, job_id, filename),
            os.path.join(self.base_path, self.PROCESSING_DIR, job_id, filename),
            os.path.join(self.base_path, self.RESULTS_DIR, job_id, filename),
        ]

        for path in search_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    return f.read()

        logger.warning(f"File not found: {job_id}/{filename}")
        return None

    async def _get_s3(self, job_id: str, filename: str, user_id: str) -> Optional[bytes]:
        client = await self._get_s3_client()

        for category in ["original", "processing", "result"]:
            key = self._s3_key(job_id, filename, user_id, category)
            try:
                resp = await client.get_object(Bucket=self.s3_bucket, Key=key)
                async with resp["Body"] as stream:
                    return await stream.read()
            except client.exceptions.NoSuchKey:
                continue
            except Exception as e:
                if (
                    hasattr(e, "response")
                    and e.response.get("Error", {}).get("Code") == "NoSuchKey"
                ):
                    continue
                logger.error(f"S3 get_object error for {key}: {e}")
                return None

        logger.warning(f"File not found in S3: {job_id}/{filename}")
        return None

    async def get_upload_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._upload_status.get(job_id)

    async def delete_job_files(self, job_id: str, user_id: str = "default") -> bool:
        if self.backend == StorageBackend.LOCAL:
            return await self._delete_local(job_id, user_id)
        elif self.backend == StorageBackend.S3:
            return await self._delete_s3(job_id, user_id)
        return False

    async def _delete_local(self, job_id: str, user_id: str) -> bool:
        deleted = False
        paths = [
            os.path.join(self.base_path, self.UPLOADS_DIR, user_id, job_id),
            os.path.join(self.base_path, self.PROCESSING_DIR, job_id),
            os.path.join(self.base_path, self.RESULTS_DIR, job_id),
        ]

        for path in paths:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    logger.info(f"Deleted: {path}")
                    deleted = True
                except Exception as e:
                    logger.error(f"Error deleting {path}: {e}")

        if job_id in self._upload_status:
            del self._upload_status[job_id]

        return deleted

    async def _delete_s3(self, job_id: str, user_id: str) -> bool:
        client = await self._get_s3_client()
        deleted = False

        for category in ["original", "processing", "result"]:
            if category == "original":
                prefix = f"{self.UPLOADS_DIR}/{user_id}/{job_id}/"
            elif category == "processing":
                prefix = f"{self.PROCESSING_DIR}/{job_id}/"
            else:
                prefix = f"{self.RESULTS_DIR}/{job_id}/"

            try:
                paginator = client.get_paginator("list_objects_v2")
                async for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                    objects = page.get("Contents", [])
                    if objects:
                        keys = [{"Key": obj["Key"]} for obj in objects]
                        await client.delete_objects(
                            Bucket=self.s3_bucket,
                            Delete={"Objects": keys},
                        )
                        deleted = True
                        logger.info(f"Deleted {len(keys)} objects from S3 prefix: {prefix}")
            except Exception as e:
                logger.error(f"S3 delete error for prefix {prefix}: {e}")

        if job_id in self._upload_status:
            del self._upload_status[job_id]

        return deleted

    async def cleanup_old_files(self, ttl_days: Optional[int] = None) -> int:
        ttl = ttl_days or self.default_ttl_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl)

        deleted_count = 0
        if self.backend == StorageBackend.LOCAL:
            deleted_count = await self._cleanup_local(cutoff)
        elif self.backend == StorageBackend.S3:
            deleted_count = await self._cleanup_s3(cutoff)

        logger.info(f"Cleaned up {deleted_count} old files")
        return deleted_count

    async def _cleanup_local(self, cutoff: datetime) -> int:
        deleted = 0
        for dir_name in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            dir_path = os.path.join(self.base_path, dir_name)
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                for name in dirs:
                    path = os.path.join(root, name)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
                        if mtime < cutoff:
                            shutil.rmtree(path)
                            deleted += 1
                    except Exception as e:
                        logger.error(f"Error cleaning {path}: {e}")
        return deleted

    async def _cleanup_s3(self, cutoff: datetime) -> int:
        client = await self._get_s3_client()
        deleted = 0

        # Normalize cutoff to UTC for consistent comparison
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)

        for prefix_base in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            try:
                paginator = client.get_paginator("list_objects_v2")
                async for page in paginator.paginate(
                    Bucket=self.s3_bucket, Prefix=f"{prefix_base}/"
                ):
                    for obj in page.get("Contents", []):
                        last_modified = obj["LastModified"]
                        if last_modified.tzinfo is None:
                            last_modified = last_modified.replace(tzinfo=timezone.utc)
                        if last_modified < cutoff:
                            await client.delete_object(
                                Bucket=self.s3_bucket,
                                Key=obj["Key"],
                            )
                            deleted += 1
            except Exception as e:
                logger.error(f"S3 cleanup error for prefix {prefix_base}/: {e}")

        return deleted

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for direct S3 download."""
        if self.backend != StorageBackend.S3:
            return None

        client = await self._get_s3_client()
        try:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None

    async def get_storage_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "backend": self.backend.value,
            "upload_count": len(self._upload_status),
        }

        if self.backend == StorageBackend.LOCAL:
            stats["base_path"] = self.base_path
            stats["total_size"] = self._get_local_size()
            stats["file_count"] = self._get_local_file_count()
        elif self.backend == StorageBackend.S3:
            stats["s3_bucket"] = self.s3_bucket
            stats["s3_region"] = self.s3_region
            if self.s3_endpoint_url:
                stats["s3_endpoint"] = self.s3_endpoint_url
            stats["total_size"], stats["file_count"] = await self._get_s3_stats()

        return stats

    async def _get_s3_stats(self) -> tuple:
        """Get total size and file count from S3 bucket."""
        client = await self._get_s3_client()
        total_size = 0
        file_count = 0

        try:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.s3_bucket):
                for obj in page.get("Contents", []):
                    total_size += obj.get("Size", 0)
                    file_count += 1
        except Exception as e:
            logger.error(f"Failed to get S3 stats: {e}")

        return total_size, file_count

    def _get_local_size(self) -> int:
        total = 0
        for dir_name in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            dir_path = os.path.join(self.base_path, dir_name)
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    for f in files:
                        try:
                            total += os.path.getsize(os.path.join(root, f))
                        except (OSError, FileNotFoundError, PermissionError):
                            pass
        return total

    def _get_local_file_count(self) -> int:
        count = 0
        for dir_name in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            dir_path = os.path.join(self.base_path, dir_name)
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    count += len(files)
        return count


# Singleton instance
storage_manager = StorageManager()

__all__ = ["StorageManager", "storage_manager", "StorageBackend"]
