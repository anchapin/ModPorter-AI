from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from . import models

async def create_job(
    session: AsyncSession,
    *,
    file_id: str,
    original_filename: str,
    target_version: str,
    options: Optional[dict] = None
) -> models.ConversionJob:
    job = models.ConversionJob(
        status="preprocessing",
        input_data={
            "file_id": file_id,
            "original_filename": original_filename,
            "target_version": target_version,
            "options": options or {},
        }
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    # Also create initial JobProgress row at 0
    progress = models.JobProgress(
        job_id=job.id,
        progress=0
    )
    session.add(progress)
    await session.commit()
    await session.refresh(job)
    return job

async def get_job(session: AsyncSession, job_id: str) -> Optional[models.ConversionJob]:
    stmt = select(models.ConversionJob).where(models.ConversionJob.id == job_id).options(selectinload(models.ConversionJob.progress))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    return job

async def list_jobs(session: AsyncSession) -> List[models.ConversionJob]:
    stmt = select(models.ConversionJob).options(selectinload(models.ConversionJob.progress)).order_by(models.ConversionJob.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()

async def update_job_status(session: AsyncSession, job_id: str, status: str) -> Optional[models.ConversionJob]:
    # Update status on ConversionJob
    stmt = update(models.ConversionJob).where(models.ConversionJob.id == job_id).values(status=status)
    await session.execute(stmt)
    await session.commit()
    job = await get_job(session, job_id)
    return job

async def upsert_progress(session: AsyncSession, job_id: str, progress: int) -> models.JobProgress:
    # Try to update, else insert
    stmt = select(models.JobProgress).where(models.JobProgress.job_id == job_id)
    result = await session.execute(stmt)
    prog = result.scalar_one_or_none()
    if prog:
        prog.progress = progress
        session.add(prog)
        await session.commit()
        await session.refresh(prog)
        return prog
    else:
        prog = models.JobProgress(job_id=job_id, progress=progress)
        session.add(prog)
        await session.commit()
        await session.refresh(prog)
        return prog