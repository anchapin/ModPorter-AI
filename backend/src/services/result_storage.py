"""
Result Storage Service

Stores conversion results in database and file system.
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

logger = logging.getLogger(__name__)


# Storage paths
TEMP_UPLOADS_DIR = Path("/app/temp_uploads")
CONVERSION_OUTPUTS_DIR = Path("/app/conversion_outputs")

# Expiration policy
RESULT_EXPIRY_DAYS = 30


class ResultStorage:
    """Storage service for conversion results."""

    def __init__(self):
        self.temp_dir = TEMP_UPLOADS_DIR
        self.output_dir = CONVERSION_OUTPUTS_DIR

        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Result storage initialized. Output dir: {self.output_dir}")

    async def store_result(
        self,
        job_id: str,
        user_id: Optional[str],
        bedrock_code: str,
        result_metadata: Dict[str, Any],
        db: AsyncSession,
    ) -> str:
        """
        Store conversion result.

        Args:
            job_id: Job ID
            user_id: User ID (optional)
            bedrock_code: Generated Bedrock code
            result_metadata: Result metadata
            db: Database session

        Returns:
            Result ID
        """
        result_id = str(uuid.uuid4())

        # Store bedrock code as file
        output_file = self.output_dir / f"{result_id}.mcaddon"
        with open(output_file, "w") as f:
            f.write(bedrock_code)

        logger.info(f"Stored bedrock code to {output_file}")

        # Store result metadata in database
        db_result = ConversionResult(
            id=result_id,
            job_id=job_id,
            output_data={
                "metadata": result_metadata,
                "output_file": str(output_file),
                "code_length": len(bedrock_code),
            },
        )

        db.add(db_result)

        # Update job status
        job = await db.get(ConversionJob, job_id)
        if job:
            job.status = "completed"

        await db.commit()

        logger.info(f"Result {result_id} stored for job {job_id}")
        return result_id

    async def get_result(self, result_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Get stored result.

        Args:
            result_id: Result ID
            db: Database session

        Returns:
            Result data or None
        """
        result = await db.get(ConversionResult, result_id)
        if not result:
            return None

        # Read bedrock code from file
        output_file = result.output_data.get("output_file")
        bedrock_code = ""

        if output_file and os.path.exists(output_file):
            with open(output_file, "r") as f:
                bedrock_code = f.read()

        return {
            "result_id": result_id,
            "job_id": result.job_id,
            "bedrock_code": bedrock_code,
            "metadata": result.output_data.get("metadata", {}),
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }

    async def download_result(self, result_id: str) -> Optional[str]:
        """
        Get file path for download.

        Args:
            result_id: Result ID

        Returns:
            File path or None
        """
        output_file = self.output_dir / f"{result_id}.mcaddon"
        if output_file.exists():
            return str(output_file)
        return None

    async def cleanup_expired_results(self, db: AsyncSession) -> int:
        """
        Clean up results older than expiry period.

        Args:
            db: Database session

        Returns:
            Number of results cleaned up
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=RESULT_EXPIRY_DAYS)

        # Find expired results
        stmt = select(ConversionResult).where(ConversionResult.created_at < cutoff)
        result = await db.execute(stmt)
        expired_results = result.scalars().all()

        cleaned = 0
        for db_result in expired_results:
            # Delete file
            output_file = db_result.output_data.get("output_file")
            if output_file and os.path.exists(output_file):
                os.remove(output_file)
                logger.debug(f"Deleted expired file: {output_file}")

            # Delete database record
            await db.delete(db_result)
            cleaned += 1

        await db.commit()
        logger.info(f"Cleaned up {cleaned} expired results")

        return cleaned

    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        # Count files and total size
        total_files = 0
        total_size = 0

        for file in self.output_dir.glob("*.mcaddon"):
            total_files += 1
            total_size += file.stat().st_size

        return {
            "total_results": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "output_directory": str(self.output_dir),
            "expiry_days": RESULT_EXPIRY_DAYS,
        }


# Singleton instance
_result_storage = None


def get_result_storage() -> ResultStorage:
    """Get or create result storage singleton."""
    global _result_storage
    if _result_storage is None:
        _result_storage = ResultStorage()
    return _result_storage
