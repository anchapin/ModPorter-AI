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
    options: Optional[dict] = None,
) -> models.ConversionJob:
    job = models.ConversionJob(
        status="queued",
        input_data={
            "file_id": file_id,
            "original_filename": original_filename,
            "target_version": target_version,
            "options": options or {},
        },
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
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return None
    stmt = (
        select(models.ConversionJob)
        .where(models.ConversionJob.id == job_uuid)
        .options(selectinload(models.ConversionJob.progress))
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    return job


async def list_jobs(session: AsyncSession) -> List[models.ConversionJob]:
    stmt = (
        select(models.ConversionJob)
        .options(selectinload(models.ConversionJob.progress))
        .order_by(models.ConversionJob.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_job_status(
    session: AsyncSession, job_id: str, status: str
) -> Optional[models.ConversionJob]:
    # Update status on ConversionJob
    # Convert string job_id to UUID for database query
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return None
    stmt = (
        update(models.ConversionJob)
        .where(models.ConversionJob.id == job_uuid)
        .values(status=status)
    )
    await session.execute(stmt)
    await session.commit()
    job = await get_job(session, job_id)
    return job


async def upsert_progress(
    session: AsyncSession, job_id: str, progress: int
) -> models.JobProgress:
    # Use PostgreSQL's ON CONFLICT DO UPDATE for an atomic upsert operation
    from sqlalchemy import func

    # Convert string job_id to UUID for database query
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise ValueError(f"Invalid job_id format: {job_id}")
    stmt = (
        pg_insert(models.JobProgress)
        .values(job_id=job_uuid, progress=progress)
        .on_conflict_do_update(
            index_elements=["job_id"],
            set_={"progress": progress, "last_update": func.now()},
        )
        .returning(models.JobProgress)
    )

    result = await session.execute(stmt)
    prog = result.scalar_one()
    await session.commit()
    return prog


# CRUD operations for DocumentEmbedding
from src.db.models import DocumentEmbedding
from sqlalchemy import delete # Added delete
from uuid import UUID as PyUUID # For type hinting UUID objects

async def create_document_embedding(
    db: AsyncSession,
    embedding: list[float],
    document_source: str,
    content_hash: str,
) -> DocumentEmbedding:
    """
    Creates a new document embedding record.
    """
    db_embedding = DocumentEmbedding(
        embedding=embedding,
        document_source=document_source,
        content_hash=content_hash,
    )
    db.add(db_embedding)
    await db.commit()
    await db.refresh(db_embedding)
    return db_embedding


async def get_document_embedding_by_hash(
    db: AsyncSession, content_hash: str
) -> Optional[DocumentEmbedding]:
    """
    Retrieves a document embedding by its content hash.
    """
    stmt = select(DocumentEmbedding).where(
        DocumentEmbedding.content_hash == content_hash
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_document_embedding_by_id(
    db: AsyncSession, embedding_id: PyUUID
) -> Optional[DocumentEmbedding]:
    """
    Retrieves a document embedding by its ID.
    """
    stmt = select(DocumentEmbedding).where(DocumentEmbedding.id == embedding_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_document_embedding(
    db: AsyncSession,
    embedding_id: PyUUID,
    embedding: Optional[list[float]] = None,
    document_source: Optional[str] = None,
) -> Optional[DocumentEmbedding]:
    """
    Updates a document embedding. Only provided fields are updated.
    """
    db_embedding = await get_document_embedding_by_id(db, embedding_id)
    if db_embedding is None:
        return None

    update_data = {}
    if embedding is not None:
        update_data["embedding"] = embedding
    if document_source is not None:
        update_data["document_source"] = document_source

    if not update_data: # Nothing to update
        return db_embedding

    stmt = (
        update(DocumentEmbedding)
        .where(DocumentEmbedding.id == embedding_id)
        .values(**update_data)
    )
    await db.execute(stmt)
    await db.commit()
    await db.refresh(db_embedding)
    return db_embedding


async def delete_document_embedding(db: AsyncSession, embedding_id: PyUUID) -> bool:
    """
    Deletes a document embedding by its ID.
    Returns True if deleted, False otherwise.
    """
    db_embedding = await get_document_embedding_by_id(db, embedding_id)
    if db_embedding is None:
        return False

    stmt = delete(DocumentEmbedding).where(DocumentEmbedding.id == embedding_id)
    await db.execute(stmt)
    await db.commit()
    return True


async def find_similar_embeddings(
    db: AsyncSession, query_embedding: list[float], limit: int = 5
) -> List[DocumentEmbedding]:
    """
    Finds document embeddings similar to the query_embedding using L2 distance.
    """
    stmt = (
        select(DocumentEmbedding)
        .order_by(DocumentEmbedding.embedding.l2_distance(query_embedding))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
