"""
Result Storage Service

Stores conversion results in database and object storage.
Supports both local filesystem (dev) and S3/Tigris (prod).
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import ConversionJob, ConversionResult
from core.storage import storage_manager, StorageBackend

logger = logging.getLogger(__name__)

RESULT_EXPIRY_DAYS = 30

TEMP_UPLOADS_DIR = Path(os.getenv("TEMP_UPLOADS_DIR", "/app/temp_uploads"))
CONVERSION_OUTPUTS_DIR = Path(os.getenv("CONVERSION_OUTPUTS_DIR", "/app/conversion_outputs"))


class ResultStorage:
    """Storage service for conversion results using StorageManager."""

    def __init__(self):
        self._storage = storage_manager
        self.temp_dir = TEMP_UPLOADS_DIR
        self.output_dir = CONVERSION_OUTPUTS_DIR
        if self._storage.backend == StorageBackend.LOCAL:
            try:
                self.temp_dir.mkdir(parents=True, exist_ok=True)
                self.output_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                logger.warning(f"Cannot create storage dirs (permission denied)")
        logger.info(f"Result storage initialized with {self._storage.backend.value} backend")

    async def store_result(
        self,
        job_id: str,
        user_id: Optional[str],
        bedrock_code: str,
        result_metadata: Dict[str, Any],
        db: AsyncSession,
    ) -> str:
        result_id = str(uuid.uuid4())
        filename = f"{result_id}.mcaddon"

        if self._storage.backend == StorageBackend.S3:
            path = await self._storage.save_file(
                content=bedrock_code.encode("utf-8"),
                job_id=job_id,
                filename=filename,
                user_id=user_id or "default",
                category="result",
            )
        else:
            output_file = self.output_dir / filename
            with open(output_file, "w") as fh:
                fh.write(bedrock_code)
            path = str(output_file)

        logger.info(f"Stored result {result_id} for job {job_id}")

        db_result = ConversionResult(
            id=result_id,
            job_id=job_id,
            output_data={
                "metadata": result_metadata,
                "output_file": path,
                "code_length": len(bedrock_code),
            },
        )
        db.add(db_result)

        job = await db.get(ConversionJob, job_id)
        if job:
            job.status = "completed"

        await db.commit()
        return result_id

    async def get_result(self, result_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        result = await db.get(ConversionResult, result_id)
        if not result:
            return None

        output_file = result.output_data.get("output_file", "")
        bedrock_code = ""

        if self._storage.backend == StorageBackend.S3 and output_file.startswith("s3://"):
            key = output_file.split("/", 3)[-1] if "/" in output_file else ""
            if key:
                job_id = result.job_id
                data = await self._storage.get_file(
                    job_id,
                    f"{result_id}.mcaddon",
                    result.output_data.get("user_id", "default"),
                )
                if data:
                    bedrock_code = data.decode("utf-8")
        elif output_file and os.path.exists(output_file):
            with open(output_file, "r") as fh:
                bedrock_code = fh.read()

        return {
            "result_id": result_id,
            "job_id": result.job_id,
            "bedrock_code": bedrock_code,
            "metadata": result.output_data.get("metadata", {}),
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }

    async def download_result(self, result_id: str) -> Optional[str]:
        if self._storage.backend == StorageBackend.S3:
            return None  # Use get_download_url for S3 downloads
        output_file = self.output_dir / f"{result_id}.mcaddon"
        if output_file.exists():
            return str(output_file)
        return None

    async def get_download_url(self, result_id: str, db: AsyncSession) -> Optional[str]:
        """Get a presigned download URL for S3-backed results."""
        result = await db.get(ConversionResult, result_id)
        if not result:
            return None
        key = f"{self._storage.RESULTS_DIR}/{result.job_id}/{result_id}.mcaddon"
        return await self._storage.get_presigned_url(key)

    async def cleanup_expired_results(self, db: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=RESULT_EXPIRY_DAYS)

        stmt = select(ConversionResult).where(ConversionResult.created_at < cutoff)
        result = await db.execute(stmt)
        expired_results = result.scalars().all()

        cleaned = 0
        for db_result in expired_results:
            if self._storage.backend == StorageBackend.S3:
                await self._storage.delete_job_files(db_result.job_id)
            else:
                output_file = db_result.output_data.get("output_file")
                if output_file and os.path.exists(output_file):
                    os.remove(output_file)
                    logger.debug(f"Deleted expired file: {output_file}")

            await db.delete(db_result)
            cleaned += 1

        await db.commit()
        logger.info(f"Cleaned up {cleaned} expired results")
        return cleaned

    def get_storage_stats(self) -> dict:
        stats = {
            "backend": self._storage.backend.value,
            "expiry_days": RESULT_EXPIRY_DAYS,
        }
        if self._storage.backend == StorageBackend.LOCAL:
            total_files = 0
            total_size = 0
            for file in self.output_dir.glob("*.mcaddon"):
                total_files += 1
                total_size += file.stat().st_size
            stats.update(
                {
                    "total_results": total_files,
                    "total_size_bytes": total_size,
                    "total_size_mb": total_size / (1024 * 1024),
                    "output_directory": str(self.output_dir),
                }
            )
        return stats


_result_storage = None


def get_result_storage() -> ResultStorage:
    global _result_storage
    if _result_storage is None:
        _result_storage = ResultStorage()
    return _result_storage
