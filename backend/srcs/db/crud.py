from typing import Optional, List
from uuid import UUID as PyUUID # For type hinting UUID objects
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from . import models
from .models import DocumentEmbedding
from datetime import datetime

BASE_ASSET_PATH = "backend/addon_assets"

async def create_job(
    session: AsyncSession,
    *,
    file_id: str,
    original_filename: str,
    target_version: str,
    options: Optional[dict] = None,
    commit: bool = True,
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
    if commit:
        await session.commit()
        await session.refresh(job)
    else:
        await session.flush()  # Flush to get the ID without committing
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
        .options(
            selectinload(models.ConversionJob.results),
            selectinload(models.ConversionJob.progress),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_job_status(
    session: AsyncSession, job_id: str, status: str, commit: bool = True
) -> Optional[models.ConversionJob]:
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
    if commit:
        await session.commit()

    # Refresh the job object
    stmt = select(models.ConversionJob).where(models.ConversionJob.id == job_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_job_progress(
    session: AsyncSession, job_id: str, progress: int, commit: bool = True
) -> Optional[models.JobProgress]:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise ValueError(f"Invalid job_id format: {job_id}")

    # Use PostgreSQL's ON CONFLICT DO UPDATE for an atomic upsert operation

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
    if commit:
        await session.commit()
    return prog


async def get_job_progress(
    session: AsyncSession, job_id: str
) -> Optional[models.JobProgress]:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return None

    stmt = select(models.JobProgress).where(models.JobProgress.job_id == job_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_result(
    session: AsyncSession,
    *,
    job_id: str,
    output_data: dict,
    commit: bool = True,
) -> models.ConversionResult:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise ValueError("Invalid job_id format")

    result = models.ConversionResult(
        job_id=job_uuid,
        output_data=output_data,
    )
    session.add(result)
    if commit:
        await session.commit()
        await session.refresh(result)
    else:
        await session.flush()
    return result


# Feedback CRUD operations (enhanced for RL training)

async def create_enhanced_feedback(
    session: AsyncSession,
    *,
    job_id: PyUUID,
    feedback_type: str,
    user_id: Optional[str] = None,
    comment: Optional[str] = None,
    quality_rating: Optional[int] = None,
    specific_issues: Optional[List[str]] = None,
    suggested_improvements: Optional[str] = None,
    conversion_accuracy: Optional[int] = None,
    visual_quality: Optional[int] = None,
    performance_rating: Optional[int] = None,
    ease_of_use: Optional[int] = None,
    agent_specific_feedback: Optional[dict] = None,
    commit: bool = True,
) -> models.ConversionFeedback:
    feedback = models.ConversionFeedback(
        job_id=job_id,
        feedback_type=feedback_type,
        user_id=user_id,
        comment=comment,
    )
    session.add(feedback)
    if commit:
        await session.commit()
        await session.refresh(feedback)
    else:
        await session.flush()
    return feedback


async def get_feedback(session: AsyncSession, feedback_id: PyUUID) -> Optional[models.ConversionFeedback]:
    stmt = select(models.ConversionFeedback).where(models.ConversionFeedback.id == feedback_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_feedback_by_job_id(session: AsyncSession, job_id: PyUUID) -> List[models.ConversionFeedback]:
    stmt = select(models.ConversionFeedback).where(models.ConversionFeedback.job_id == job_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def list_all_feedback(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.ConversionFeedback]:
    stmt = select(models.ConversionFeedback).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


# Document Embedding CRUD operations

async def create_document_embedding(
    db: AsyncSession,
    *,
    embedding: list[float],
    document_source: str,
    content_hash: str,
    commit: bool = True,
) -> DocumentEmbedding:
    db_embedding = DocumentEmbedding(
        embedding=embedding,
        document_source=document_source,
        content_hash=content_hash,
    )
    db.add(db_embedding)
    if commit:
        await db.commit()
        await db.refresh(db_embedding)
    else:
        await db.flush()
    return db_embedding


async def get_document_embedding_by_id(
    db: AsyncSession, embedding_id: PyUUID
) -> Optional[DocumentEmbedding]:
    stmt = select(DocumentEmbedding).where(DocumentEmbedding.id == embedding_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_document_embedding_by_hash(
    db: AsyncSession, content_hash: str
) -> Optional[DocumentEmbedding]:
    stmt = select(DocumentEmbedding).where(DocumentEmbedding.content_hash == content_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_document_embedding(
    db: AsyncSession,
    embedding_id: PyUUID,
    *,
    embedding: Optional[list[float]] = None,
    document_source: Optional[str] = None,
) -> Optional[DocumentEmbedding]:
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


# A/B Testing CRUD operations

async def create_experiment(
    session: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: str = "draft",
    traffic_allocation: int = 100,
    commit: bool = True,
) -> models.Experiment:
    experiment = models.Experiment(
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        status=status,
        traffic_allocation=traffic_allocation,
    )
    session.add(experiment)
    if commit:
        await session.commit()
        await session.refresh(experiment)
    else:
        await session.flush()
    return experiment


async def get_experiment(
    session: AsyncSession, experiment_id: PyUUID
) -> Optional[models.Experiment]:
    stmt = select(models.Experiment).where(models.Experiment.id == experiment_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_experiments(
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Experiment]:
    stmt = select(models.Experiment)
    if status:
        stmt = stmt.where(models.Experiment.status == status)
    stmt = stmt.offset(skip).limit(limit).order_by(models.Experiment.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_experiment(
    session: AsyncSession,
    experiment_id: PyUUID,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    traffic_allocation: Optional[int] = None,
    commit: bool = True,
) -> Optional[models.Experiment]:
    experiment = await get_experiment(session, experiment_id)
    if not experiment:
        return None

    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if start_date is not None:
        update_data["start_date"] = start_date
    if end_date is not None:
        update_data["end_date"] = end_date
    if status is not None:
        update_data["status"] = status
    if traffic_allocation is not None:
        update_data["traffic_allocation"] = traffic_allocation

    if not update_data:  # Nothing to update
        return experiment

    stmt = (
        update(models.Experiment)
        .where(models.Experiment.id == experiment_id)
        .values(**update_data)
    )
    await session.execute(stmt)
    if commit:
        await session.commit()

    # Refresh the experiment object
    stmt = select(models.Experiment).where(models.Experiment.id == experiment_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_experiment(session: AsyncSession, experiment_id: PyUUID) -> bool:
    experiment = await get_experiment(session, experiment_id)
    if not experiment:
        return False

    stmt = delete(models.Experiment).where(models.Experiment.id == experiment_id)
    await session.execute(stmt)
    await session.commit()
    return True


async def create_experiment_variant(
    session: AsyncSession,
    *,
    experiment_id: PyUUID,
    name: str,
    description: Optional[str] = None,
    is_control: bool = False,
    strategy_config: Optional[dict] = None,
    commit: bool = True,
) -> models.ExperimentVariant:
    # If this is a control variant, make sure no other control variant exists for this experiment
    if is_control:
        # Use SELECT ... FOR UPDATE to prevent race conditions
        stmt = select(models.ExperimentVariant).where(
            models.ExperimentVariant.experiment_id == experiment_id,
            models.ExperimentVariant.is_control,
        ).with_for_update()
        result = await session.execute(stmt)
        existing_control = result.scalar_one_or_none()
        if existing_control:
            # Update the existing control variant to not be control
            update_stmt = (
                update(models.ExperimentVariant)
                .where(models.ExperimentVariant.id == existing_control.id)
                .values(is_control=False)
            )
            await session.execute(update_stmt)

    variant = models.ExperimentVariant(
        experiment_id=experiment_id,
        name=name,
        description=description,
        is_control=is_control,
        strategy_config=strategy_config,
    )
    session.add(variant)
    if commit:
        await session.commit()
        await session.refresh(variant)
    else:
        await session.flush()
    return variant


async def get_experiment_variant(
    session: AsyncSession, variant_id: PyUUID
) -> Optional[models.ExperimentVariant]:
    stmt = select(models.ExperimentVariant).where(models.ExperimentVariant.id == variant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_experiment_variants(
    session: AsyncSession, experiment_id: PyUUID
) -> List[models.ExperimentVariant]:
    stmt = (
        select(models.ExperimentVariant)
        .where(models.ExperimentVariant.experiment_id == experiment_id)
        .order_by(models.ExperimentVariant.created_at)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_experiment_variant(
    session: AsyncSession,
    variant_id: PyUUID,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_control: Optional[bool] = None,
    strategy_config: Optional[dict] = None,
    commit: bool = True,
) -> Optional[models.ExperimentVariant]:
    variant = await get_experiment_variant(session, variant_id)
    if not variant:
        return None

    # If this is being set as a control variant, make sure no other control variant exists for this experiment
    if is_control and is_control != variant.is_control:
        # Use SELECT ... FOR UPDATE to prevent race conditions
        stmt = select(models.ExperimentVariant).where(
            models.ExperimentVariant.experiment_id == variant.experiment_id,
            models.ExperimentVariant.is_control,
            models.ExperimentVariant.id != variant_id,
        ).with_for_update()
        result = await session.execute(stmt)
        existing_control = result.scalar_one_or_none()
        if existing_control:
            # Update the existing control variant to not be control
            update_stmt = (
                update(models.ExperimentVariant)
                .where(models.ExperimentVariant.id == existing_control.id)
                .values(is_control=False)
            )
            await session.execute(update_stmt)

    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if is_control is not None:
        update_data["is_control"] = is_control
    if strategy_config is not None:
        update_data["strategy_config"] = strategy_config

    if not update_data:  # Nothing to update
        return variant

    stmt = (
        update(models.ExperimentVariant)
        .where(models.ExperimentVariant.id == variant_id)
        .values(**update_data)
    )
    await session.execute(stmt)
    if commit:
        await session.commit()

    # Refresh the variant object
    stmt = select(models.ExperimentVariant).where(models.ExperimentVariant.id == variant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_experiment_variant(session: AsyncSession, variant_id: PyUUID) -> bool:
    variant = await get_experiment_variant(session, variant_id)
    if not variant:
        return False

    stmt = delete(models.ExperimentVariant).where(models.ExperimentVariant.id == variant_id)
    await session.execute(stmt)
    await session.commit()
    return True


async def create_experiment_result(
    session: AsyncSession,
    *,
    variant_id: PyUUID,
    session_id: PyUUID,
    kpi_quality: Optional[float] = None,
    kpi_speed: Optional[int] = None,
    kpi_cost: Optional[float] = None,
    user_feedback_score: Optional[float] = None,
    user_feedback_text: Optional[str] = None,
    result_metadata: Optional[dict] = None,
    commit: bool = True,
) -> models.ExperimentResult:
    result = models.ExperimentResult(
        variant_id=variant_id,
        session_id=session_id,
        kpi_quality=kpi_quality,
        kpi_speed=kpi_speed,
        kpi_cost=kpi_cost,
        user_feedback_score=user_feedback_score,
        user_feedback_text=user_feedback_text,
        result_asset_metadata=result_metadata,
    )
    session.add(result)
    if commit:
        await session.commit()
        await session.refresh(result)
    else:
        await session.flush()
    return result


async def get_experiment_result(
    session: AsyncSession, result_id: PyUUID
) -> Optional[models.ExperimentResult]:
    stmt = select(models.ExperimentResult).where(models.ExperimentResult.id == result_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_experiment_results(
    session: AsyncSession,
    *,
    variant_id: Optional[PyUUID] = None,
    session_id: Optional[PyUUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.ExperimentResult]:
    stmt = select(models.ExperimentResult)
    if variant_id:
        stmt = stmt.where(models.ExperimentResult.variant_id == variant_id)
    if session_id:
        stmt = stmt.where(models.ExperimentResult.session_id == session_id)
    stmt = stmt.offset(skip).limit(limit).order_by(models.ExperimentResult.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()

# Behavior File CRUD operations for post-conversion editor

async def create_behavior_file(
    session: AsyncSession,
    *,
    conversion_id: str,
    file_path: str,
    file_type: str,
    content: str,
    commit: bool = True,
) -> models.BehaviorFile:
    """Create a new behavior file entry."""
    try:
        conversion_uuid = uuid.UUID(conversion_id)
    except ValueError:
        raise ValueError("Invalid conversion_id format")

    behavior_file = models.BehaviorFile(
        conversion_id=conversion_uuid,
        file_path=file_path,
        file_type=file_type,
        content=content,
    )
    session.add(behavior_file)
    if commit:
        await session.commit()
        await session.refresh(behavior_file)
    else:
        await session.flush()
    return behavior_file


async def get_behavior_file(
    session: AsyncSession, file_id: str
) -> Optional[models.BehaviorFile]:
    """Get a specific behavior file by ID."""
    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        return None

    stmt = select(models.BehaviorFile).where(models.BehaviorFile.id == file_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_behavior_files_by_conversion(
    session: AsyncSession, conversion_id: str
) -> List[models.BehaviorFile]:
    """Get all behavior files for a specific conversion."""
    try:
        conversion_uuid = uuid.UUID(conversion_id)
    except ValueError:
        return []

    stmt = (
        select(models.BehaviorFile)
        .where(models.BehaviorFile.conversion_id == conversion_uuid)
        .order_by(models.BehaviorFile.file_path)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_behavior_file_content(
    session: AsyncSession,
    file_id: str,
    content: str,
    commit: bool = True,
) -> Optional[models.BehaviorFile]:
    """Update the content of a behavior file."""
    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        return None

    stmt = (
        update(models.BehaviorFile)
        .where(models.BehaviorFile.id == file_uuid)
        .values(content=content)
        .returning(models.BehaviorFile)
    )
    result = await session.execute(stmt)
    updated_file = result.scalar_one_or_none()

    if commit and updated_file:
        await session.commit()

    return updated_file


async def delete_behavior_file(session: AsyncSession, file_id: str) -> bool:
    """Delete a behavior file by ID."""
    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        return False

    stmt = delete(models.BehaviorFile).where(models.BehaviorFile.id == file_uuid)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def get_behavior_files_by_type(
    session: AsyncSession, conversion_id: str, file_type: str
) -> List[models.BehaviorFile]:
    """Get behavior files of a specific type for a conversion."""
    try:
        conversion_uuid = uuid.UUID(conversion_id)
    except ValueError:
        return []

    stmt = (
        select(models.BehaviorFile)
        .where(
            models.BehaviorFile.conversion_id == conversion_uuid,
            models.BehaviorFile.file_type == file_type,
        )
        .order_by(models.BehaviorFile.file_path)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# Alias for update_job_progress to maintain compatibility
async def upsert_progress(
    session: AsyncSession, job_id: str, progress: int, commit: bool = True
) -> Optional[models.JobProgress]:
    """Alias for update_job_progress to maintain backward compatibility."""
    return await update_job_progress(session, job_id, progress, commit)


async def list_jobs(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.ConversionJob]:
    """List all conversion jobs with pagination."""
    stmt = (
        select(models.ConversionJob)
        .options(
            selectinload(models.ConversionJob.results),
            selectinload(models.ConversionJob.progress),
        )
        .offset(skip)
        .limit(limit)
        .order_by(models.ConversionJob.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# Addon Asset CRUD operations
async def get_addon_asset(session: AsyncSession, asset_id: str) -> Optional[models.AddonAsset]:
    """Get an addon asset by ID."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    stmt = select(models.AddonAsset).where(models.AddonAsset.id == asset_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_addon_asset(
    session: AsyncSession,
    *,
    addon_id: str,
    asset_type: str,
    file_path: str,
    original_filename: str,
    commit: bool = True,
) -> models.AddonAsset:
    """Create a new addon asset."""
    try:
        addon_uuid = uuid.UUID(addon_id)
    except ValueError:
        raise ValueError(f"Invalid addon ID format: {addon_id}")

    # Prevent path traversal attacks
    if ".." in file_path or file_path.startswith("/"):
        raise ValueError("Invalid file path: path traversal detected")

    asset = models.AddonAsset(
        addon_id=addon_uuid,
        type=asset_type,
        path=file_path,
        original_filename=original_filename,
    )
    session.add(asset)
    if commit:
        await session.commit()
        await session.refresh(asset)
    else:
        await session.flush()
    return asset


async def update_addon_asset(
    session: AsyncSession,
    asset_id: str,
    *,
    asset_type: Optional[str] = None,
    file_path: Optional[str] = None,
    original_filename: Optional[str] = None,
    commit: bool = True,
) -> Optional[models.AddonAsset]:
    """Update an addon asset."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    # Check if asset exists
    asset = await get_addon_asset(session, asset_id)
    if not asset:
        return None

    # Update fields if provided
    update_data = {}
    if asset_type is not None:
        update_data["type"] = asset_type
    if file_path is not None:
        # Prevent path traversal attacks
        if ".." in file_path or file_path.startswith("/"):
            raise ValueError("Invalid file path: path traversal detected")
        update_data["path"] = file_path
    if original_filename is not None:
        update_data["original_filename"] = original_filename

    if update_data:
        stmt = (
            update(models.AddonAsset)
            .where(models.AddonAsset.id == asset_uuid)
            .values(**update_data)
            .returning(models.AddonAsset)
        )
        result = await session.execute(stmt)
        if commit:
            await session.commit()
        asset = result.scalar_one_or_none()

    return asset


async def delete_addon_asset(session: AsyncSession, asset_id: str) -> bool:
    """Delete an addon asset."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    # Check if asset exists
    asset = await get_addon_asset(session, asset_id)
    if not asset:
        return False

    stmt = delete(models.AddonAsset).where(models.AddonAsset.id == asset_uuid)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def list_addon_assets(
    session: AsyncSession,
    addon_id: str,
    *,
    asset_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.AddonAsset]:
    """List addon assets for a given addon."""
    try:
        addon_uuid = uuid.UUID(addon_id)
    except ValueError:
        raise ValueError(f"Invalid addon ID format: {addon_id}")

    stmt = (
        select(models.AddonAsset)
        .where(models.AddonAsset.addon_id == addon_uuid)
        .offset(skip)
        .limit(limit)
        .order_by(models.AddonAsset.created_at.desc())
    )

    if asset_type:
        stmt = stmt.where(models.AddonAsset.type == asset_type)

    result = await session.execute(stmt)
    return result.scalars().all()


# Asset CRUD operations
async def get_asset(session: AsyncSession, asset_id: str) -> Optional[models.Asset]:
    """Get an asset by ID."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    stmt = select(models.Asset).where(models.Asset.id == asset_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_asset(
    session: AsyncSession,
    *,
    conversion_id: str,
    asset_type: str,
    original_path: str,
    original_filename: str,
    file_size: Optional[int] = None,
    mime_type: Optional[str] = None,
    asset_metadata: Optional[dict] = None,
    commit: bool = True,
) -> models.Asset:
    """Create a new asset."""
    try:
        conversion_uuid = uuid.UUID(conversion_id)
    except ValueError:
        raise ValueError(f"Invalid conversion ID format: {conversion_id}")

    asset = models.Asset(
        conversion_id=conversion_uuid,
        asset_type=asset_type,
        original_path=original_path,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=mime_type,
        asset_metadata=asset_metadata or {},
        status="pending",
    )
    session.add(asset)
    if commit:
        await session.commit()
        await session.refresh(asset)
    else:
        await session.flush()
    return asset


async def update_asset_status(
    session: AsyncSession,
    asset_id: str,
    status: str,
    commit: bool = True,
) -> Optional[models.Asset]:
    """Update asset status."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    # Check if asset exists
    asset = await get_asset(session, asset_id)
    if not asset:
        return None

    stmt = (
        update(models.Asset)
        .where(models.Asset.id == asset_uuid)
        .values(status=status)
        .returning(models.Asset)
    )
    result = await session.execute(stmt)
    if commit:
        await session.commit()
    return result.scalar_one_or_none()


async def update_asset_metadata(
    session: AsyncSession,
    asset_id: str,
    asset_metadata: dict,
    commit: bool = True,
) -> Optional[models.Asset]:
    """Update asset metadata."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    # Check if asset exists
    asset = await get_asset(session, asset_id)
    if not asset:
        return None

    stmt = (
        update(models.Asset)
        .where(models.Asset.id == asset_uuid)
        .values(asset_metadata=asset_metadata)
        .returning(models.Asset)
    )
    result = await session.execute(stmt)
    if commit:
        await session.commit()
    return result.scalar_one_or_none()


async def delete_asset(session: AsyncSession, asset_id: str) -> bool:
    """Delete an asset."""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise ValueError(f"Invalid asset ID format: {asset_id}")

    # Check if asset exists
    asset = await get_asset(session, asset_id)
    if not asset:
        return False

    stmt = delete(models.Asset).where(models.Asset.id == asset_uuid)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def list_assets_for_conversion(
    session: AsyncSession,
    conversion_id: str,
    *,
    asset_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Asset]:
    """List assets for a given conversion."""
    try:
        conversion_uuid = uuid.UUID(conversion_id)
    except ValueError:
        raise ValueError(f"Invalid conversion ID format: {conversion_id}")

    stmt = (
        select(models.Asset)
        .where(models.Asset.conversion_id == conversion_uuid)
        .offset(skip)
        .limit(limit)
        .order_by(models.Asset.created_at.desc())
    )

    if asset_type:
        stmt = stmt.where(models.Asset.type == asset_type)

    result = await session.execute(stmt)
    return result.scalars().all()
