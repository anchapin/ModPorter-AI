"""
Storage Configuration for ModPorter-AI.

Provides:
- Local file storage (development)
- S3-compatible storage (production)
- File organization by user/job
- Cleanup utilities
"""

import os
import shutil
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
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
    - /uploads/{user_id}/{job_id}/original.jar
    - /processing/{job_id}/
    - /results/{job_id}/

    Supports:
    - Local filesystem (development)
    - S3-compatible storage (production)
    """

    # Directory structure
    UPLOADS_DIR = "uploads"
    PROCESSING_DIR = "processing"
    RESULTS_DIR = "results"

    # Default settings
    DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_TTL_DAYS = 7  # Default file retention

    def __init__(
        self,
        backend: Optional[StorageBackend] = None,
        base_path: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_region: Optional[str] = None,
        default_ttl_days: int = DEFAULT_TTL_DAYS,
    ):
        """
        Initialize storage manager.

        Args:
            backend: Storage backend to use (defaults to local)
            base_path: Base directory for local storage
            s3_bucket: S3 bucket name (for S3 backend)
            s3_region: S3 region (for S3 backend)
            default_ttl_days: Default TTL for file cleanup
        """
        # Determine backend
        if backend is None:
            backend_str = os.getenv("STORAGE_BACKEND", "local").lower()
            backend = StorageBackend.LOCAL if backend_str == "local" else StorageBackend.S3

        self.backend = backend

        # Local storage config
        self.base_path = base_path or os.getenv("STORAGE_PATH", "/tmp/modporter-uploads")

        # S3 config
        self.s3_bucket = s3_bucket or os.getenv("S3_BUCKET", "")
        self.s3_region = s3_region or os.getenv("AWS_REGION", "us-east-1")

        # TTL config
        self.default_ttl_days = default_ttl_days

        # In-memory status storage (would be Redis in production)
        self._upload_status: Dict[str, Dict[str, Any]] = {}

        # Initialize storage directories
        if self.backend == StorageBackend.LOCAL:
            self._init_local_storage()

        logger.info(f"StorageManager initialized with {self.backend.value} backend")

    def _init_local_storage(self):
        """Initialize local storage directory structure"""
        dirs = [
            self.UPLOADS_DIR,
            self.PROCESSING_DIR,
            self.RESULTS_DIR,
        ]

        for dir_name in dirs:
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
        """
        Save a file to storage.

        Args:
            content: File content as bytes
            job_id: Unique job identifier
            filename: Original or desired filename
            user_id: User identifier (for multi-tenant storage)
            category: Category (original, processed, result)

        Returns:
            Path to saved file
        """
        if self.backend == StorageBackend.LOCAL:
            return await self._save_local(content, job_id, filename, user_id, category)
        elif self.backend == StorageBackend.S3:
            return await self._save_s3(content, job_id, filename, user_id, category)
        else:
            raise ValueError(f"Unknown storage backend: {self.backend}")

    async def _save_local(
        self, content: bytes, job_id: str, filename: str, user_id: str, category: str
    ) -> str:
        """Save file to local filesystem"""
        # Determine directory based on category
        if category == "original":
            dir_path = os.path.join(self.base_path, self.UPLOADS_DIR, user_id, job_id)
        elif category == "processing":
            dir_path = os.path.join(self.base_path, self.PROCESSING_DIR, job_id)
        elif category == "result":
            dir_path = os.path.join(self.base_path, self.RESULTS_DIR, job_id)
        else:
            dir_path = os.path.join(self.base_path, category, job_id)

        os.makedirs(dir_path, exist_ok=True)

        # Save file
        file_path = os.path.join(dir_path, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        # Update status
        self._upload_status[job_id] = {
            "status": "completed",
            "progress": 100,
            "message": "File saved successfully",
            "path": file_path,
            "size": len(content),
            "saved_at": datetime.now().isoformat(),
        }

        logger.info(f"File saved locally: {file_path}")
        return file_path

    async def _save_s3(
        self, content: bytes, job_id: str, filename: str, user_id: str, category: str
    ) -> str:
        """Save file to S3 (placeholder - needs boto3)"""
        # TODO: Implement S3 storage
        # For now, fall back to local
        logger.warning("S3 storage not implemented, using local storage")
        return await self._save_local(content, job_id, filename, user_id, category)

    async def get_file(
        self, job_id: str, filename: str, user_id: str = "default"
    ) -> Optional[bytes]:
        """
        Retrieve a file from storage.

        Args:
            job_id: Job identifier
            filename: File name to retrieve
            user_id: User identifier

        Returns:
            File content as bytes, or None if not found
        """
        if self.backend == StorageBackend.LOCAL:
            return await self._get_local(job_id, filename, user_id)
        elif self.backend == StorageBackend.S3:
            return await self._get_s3(job_id, filename, user_id)
        return None

    async def _get_local(self, job_id: str, filename: str, user_id: str) -> Optional[bytes]:
        """Get file from local storage"""
        # Try multiple locations
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
        """Get file from S3 (placeholder)"""
        logger.warning("S3 storage not implemented")
        return None

    async def get_upload_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an upload job.

        Args:
            job_id: Job identifier

        Returns:
            Status dict with status, progress, message
        """
        return self._upload_status.get(job_id)

    async def delete_job_files(self, job_id: str, user_id: str = "default") -> bool:
        """
        Delete all files associated with a job.

        Args:
            job_id: Job identifier
            user_id: User identifier

        Returns:
            True if successful
        """
        if self.backend == StorageBackend.LOCAL:
            return await self._delete_local(job_id, user_id)
        elif self.backend == StorageBackend.S3:
            return await self._delete_s3(job_id, user_id)
        return False

    async def _delete_local(self, job_id: str, user_id: str) -> bool:
        """Delete files from local storage"""
        deleted = False

        # Paths to check
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

        # Clear status
        if job_id in self._upload_status:
            del self._upload_status[job_id]

        return deleted

    async def _delete_s3(self, job_id: str, user_id: str) -> bool:
        """Delete files from S3 (placeholder)"""
        logger.warning("S3 storage not implemented")
        return False

    async def cleanup_old_files(self, ttl_days: Optional[int] = None) -> int:
        """
        Clean up files older than TTL.

        Args:
            ttl_days: Time to live in days (uses default if not specified)

        Returns:
            Number of files deleted
        """
        ttl = ttl_days or self.default_ttl_days
        cutoff = datetime.now() - timedelta(days=ttl)

        deleted_count = 0

        if self.backend == StorageBackend.LOCAL:
            deleted_count = await self._cleanup_local(cutoff)
        elif self.backend == StorageBackend.S3:
            deleted_count = await self._cleanup_s3(cutoff)

        logger.info(f"Cleaned up {deleted_count} old files")
        return deleted_count

    async def _cleanup_local(self, cutoff: datetime) -> int:
        """Clean up old local files"""
        deleted = 0

        for dir_name in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            dir_path = os.path.join(self.base_path, dir_name)
            if not os.path.exists(dir_path):
                continue

            # Walk directory
            for root, dirs, files in os.walk(dir_path):
                for name in dirs:
                    path = os.path.join(root, name)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(path))
                        if mtime < cutoff:
                            shutil.rmtree(path)
                            deleted += 1
                    except Exception as e:
                        logger.error(f"Error cleaning {path}: {e}")

        return deleted

    async def _cleanup_s3(self, cutoff: datetime) -> int:
        """Clean up old S3 files (placeholder)"""
        logger.warning("S3 cleanup not implemented")
        return 0

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dict with storage stats
        """
        stats = {
            "backend": self.backend.value,
            "base_path": self.base_path if self.backend == StorageBackend.LOCAL else None,
            "s3_bucket": self.s3_bucket if self.backend == StorageBackend.S3 else None,
            "upload_count": len(self._upload_status),
        }

        if self.backend == StorageBackend.LOCAL:
            stats["total_size"] = self._get_local_size()
            stats["file_count"] = self._get_local_file_count()

        return stats

    def _get_local_size(self) -> int:
        """Get total size of local storage"""
        total = 0
        for dir_name in [self.UPLOADS_DIR, self.PROCESSING_DIR, self.RESULTS_DIR]:
            dir_path = os.path.join(self.base_path, dir_name)
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    for f in files:
                        try:
                            total += os.path.getsize(os.path.join(root, f))
                        except:
                            pass
        return total

    def _get_local_file_count(self) -> int:
        """Get total file count in local storage"""
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
