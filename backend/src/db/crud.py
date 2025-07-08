from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.db import models
import uuid

async def create_job(
    session: AsyncSession,
    *,
    file_id: str,
    original_filename: str,
    target_version: str,
    options: Optional[dict] = None
) -> models.ConversionJob:
    job = models.ConversionJob(
        status="queued",
        input_data={
            "file_id": file_id,
            "original_filename": original_filename,
            "target_version": target_version,
            "options": options or {},
        }
    )
    # By using the relationship, SQLAlchemy will handle creating both
    # records and linking them in a single transaction.
    job.progress = models.JobProgress(progress=0)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job

async def get_job(session: AsyncSession, job_id: str) -> Optional[models.ConversionJob]:
    # Convert string job_id to UUID for database query
    job_uuid = uuid.UUID(job_id)
    stmt = select(models.ConversionJob).where(models.ConversionJob.id == job_uuid).options(selectinload(models.ConversionJob.progress))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    return job

async def list_jobs(session: AsyncSession) -> List[models.ConversionJob]:
    stmt = select(models.ConversionJob).options(selectinload(models.ConversionJob.progress)).order_by(models.ConversionJob.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()

async def update_job_status(session: AsyncSession, job_id: str, status: str) -> Optional[models.ConversionJob]:
    # Update status on ConversionJob
    # Convert string job_id to UUID for database query
    job_uuid = uuid.UUID(job_id)
    stmt = update(models.ConversionJob).where(models.ConversionJob.id == job_uuid).values(status=status)
    await session.execute(stmt)
    await session.commit()
    job = await get_job(session, job_id)
    return job

async def upsert_progress(session: AsyncSession, job_id: str, progress: int) -> models.JobProgress:
    # Use PostgreSQL's ON CONFLICT DO UPDATE for an atomic upsert operation
    from sqlalchemy import func
    # Convert string job_id to UUID for database query
    job_uuid = uuid.UUID(job_id)
    stmt = pg_insert(models.JobProgress).values(
        job_id=job_uuid,
        progress=progress
    ).on_conflict_do_update(
        index_elements=['job_id'],
        set_={'progress': progress, 'last_update': func.now()}
    ).returning(models.JobProgress)

    result = await session.execute(stmt)
    prog = result.scalar_one()
    await session.commit()
    return prog