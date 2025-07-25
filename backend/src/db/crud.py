from typing import Optional, List
from uuid import UUID as PyUUID # For type hinting UUID objects
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete # Added delete
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from db import models
from db.models import DocumentEmbedding


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
    session: AsyncSession, job_id: str, status: str, commit: bool = True
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
    if commit:
        await session.commit()
    job = await get_job(session, job_id)
    return job


async def upsert_progress(
    session: AsyncSession, job_id: str, progress: int, commit: bool = True
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
    if commit:
        await session.commit()
    return prog

# Addon Management CRUD functions

from uuid import UUID as PyUUID
from src.models import addon_models as pydantic_addon_models
from sqlalchemy import delete
import os
import shutil
import uuid as uuid_pkg # Renamed to avoid conflict with PyUUID
from fastapi import UploadFile

BASE_ASSET_PATH = "backend/addon_assets"

async def get_addon_details(session: AsyncSession, addon_id: PyUUID) -> Optional[models.Addon]:
    """
    Retrieves an addon and its associated blocks, assets, behaviors, and recipes.
    """
    stmt = (
        select(models.Addon)
        .where(models.Addon.id == addon_id)
        .options(
            selectinload(models.Addon.blocks).selectinload(models.AddonBlock.behavior),
            selectinload(models.Addon.assets),
            selectinload(models.Addon.recipes),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def update_addon_details(
    session: AsyncSession,
    addon_id: PyUUID,
    addon_data: pydantic_addon_models.AddonDataUpload,
    # user_id: str # user_id is part of addon_data
) -> models.Addon:
    """
    Updates an existing addon or creates a new one if it doesn't exist (upsert).
    Manages the full state of the addon's components (blocks, assets, recipes).
    """
    # Try to fetch existing addon
    existing_addon = await session.get(models.Addon, addon_id)

    if existing_addon:
        # Update existing addon
        existing_addon.name = addon_data.name
        existing_addon.description = addon_data.description
        existing_addon.user_id = addon_data.user_id # Allow user_id update

        # Clear existing child collections for a full replacement strategy
        # For blocks (and their behaviors)
        await session.execute(delete(models.AddonBehavior).where(models.AddonBehavior.block_id.in_(
            select(models.AddonBlock.id).where(models.AddonBlock.addon_id == addon_id)
        )))
        await session.execute(delete(models.AddonBlock).where(models.AddonBlock.addon_id == addon_id))
        # For assets
        await session.execute(delete(models.AddonAsset).where(models.AddonAsset.addon_id == addon_id))
        # For recipes
        await session.execute(delete(models.AddonRecipe).where(models.AddonRecipe.addon_id == addon_id))

        # Flush deletions to make sure they are processed before additions,
        # though SQLAlchemy usually handles order well.
        await session.flush()

        db_addon = existing_addon
    else:
        # Create new addon
        db_addon = models.Addon(
            id=addon_id, # Use provided addon_id for creation
            name=addon_data.name,
            description=addon_data.description,
            user_id=addon_data.user_id,
        )
        session.add(db_addon)
        # For a new addon, no need to delete children.

    # (Re-)create child objects from addon_data
    # Blocks and their Behaviors
    for block_data in addon_data.blocks:
        db_block = models.AddonBlock(
            addon_id=db_addon.id,
            identifier=block_data.identifier,
            properties=block_data.properties if block_data.properties is not None else {},
        )
        session.add(db_block) # Add block first to get an ID if it's autogen (not in this case as we provide it)
                               # Actually, block_id is UUID, so it's fine.
                               # More importantly, need to associate with db_addon if not done via relationship directly.
        db_addon.blocks.append(db_block) # Associate with parent

        if block_data.behavior:
            db_behavior = models.AddonBehavior(
                # block_id will be set by relationship if back_populates is correct and block is added to session.
                # However, explicit assignment is safer before commit.
                data=block_data.behavior.data,
            )
            db_block.behavior = db_behavior # Associate with block
            # session.add(db_behavior) # Not strictly necessary if cascade is set on AddonBlock.behavior relationship

    # Assets
    for asset_data in addon_data.assets:
        db_asset = models.AddonAsset(
            # addon_id=db_addon.id, # Will be set by relationship
            type=asset_data.type,
            path=asset_data.path,
            original_filename=asset_data.original_filename,
        )
        db_addon.assets.append(db_asset) # Associate with parent

    # Recipes
    for recipe_data in addon_data.recipes:
        db_recipe = models.AddonRecipe(
            # addon_id=db_addon.id, # Will be set by relationship
            data=recipe_data.data,
        )
        db_addon.recipes.append(db_recipe) # Associate with parent

    # If we didn't add db_addon earlier (for existing case), add it now.
    # However, it's already in the session if it was fetched with session.get().
    # For new addons, it was added. So, this line might be redundant.
    # session.add(db_addon)

    await session.commit()
    await session.refresh(db_addon) # Refresh to get all relationships and server-defaults correctly loaded

    # Eager load relationships again for the returned object, similar to get_addon_details
    # This is important because the refresh might not load them all, or not deeply.
    refreshed_addon_with_relations = await get_addon_details(session, db_addon.id)
    if refreshed_addon_with_relations is None:
        # This should not happen if commit was successful
        raise Exception("Failed to retrieve addon after upsert operation.")

    return refreshed_addon_with_relations


# Addon Asset Management CRUD functions

async def create_addon_asset(
    session: AsyncSession,
    addon_id: PyUUID,
    file: UploadFile,
    asset_type: str
) -> models.AddonAsset:
    """
    Creates an AddonAsset record and saves the asset file to storage.
    """
    # Ensure the addon exists
    addon = await session.get(models.Addon, addon_id)
    if not addon:
        # This case should ideally be caught by the endpoint before calling crud
        raise ValueError(f"Addon with id {addon_id} not found.")

    asset_id = uuid_pkg.uuid4()
    # Sanitize filename slightly, though UploadFile.filename should be relatively safe
    original_filename = file.filename if file.filename else "unknown_asset"

    # Construct path: backend/addon_assets/{addon_id}/{asset_id}_{original_filename}
    # Using asset_id in filename for uniqueness to avoid overwrites if original_filename is not unique
    # and to make it easier to locate if only asset_id is known.
    asset_filename = f"{asset_id}_{original_filename}"
    addon_asset_dir = os.path.join(BASE_ASSET_PATH, str(addon_id))
    os.makedirs(addon_asset_dir, exist_ok=True)

    file_path = os.path.join(addon_asset_dir, asset_filename)

    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close() # Ensure the spooled temporary file is closed

    # Relative path for DB storage
    relative_path = os.path.join(str(addon_id), asset_filename)

    db_asset = models.AddonAsset(
        id=asset_id,
        addon_id=addon_id,
        type=asset_type,
        path=relative_path, # Store relative path
        original_filename=original_filename
    )
    session.add(db_asset)
    await session.commit()
    await session.refresh(db_asset)
    return db_asset

async def get_addon_asset(session: AsyncSession, asset_id: PyUUID) -> Optional[models.AddonAsset]:
    """
    Retrieves a specific addon asset by its ID.
    """
    return await session.get(models.AddonAsset, asset_id)

async def update_addon_asset(
    session: AsyncSession,
    asset_id: PyUUID,
    file: UploadFile
) -> Optional[models.AddonAsset]:
    """
    Updates an existing asset's file and metadata.
    The old file is replaced. Path might change if original_filename changes.
    """
    db_asset = await session.get(models.AddonAsset, asset_id)
    if not db_asset:
        return None

    # Delete the old file
    old_full_path = os.path.join(BASE_ASSET_PATH, db_asset.path)
    if os.path.exists(old_full_path):
        os.remove(old_full_path)

    # Construct new path and save the new file
    new_original_filename = file.filename if file.filename else "unknown_asset"
    new_asset_filename = f"{db_asset.id}_{new_original_filename}" # Use existing asset_id
    addon_asset_dir = os.path.join(BASE_ASSET_PATH, str(db_asset.addon_id))
    os.makedirs(addon_asset_dir, exist_ok=True) # Ensure directory exists

    new_file_path = os.path.join(addon_asset_dir, new_asset_filename)

    try:
        with open(new_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Update database record
    db_asset.path = os.path.join(str(db_asset.addon_id), new_asset_filename) # New relative path
    db_asset.original_filename = new_original_filename
    # updated_at is handled by SQLAlchemy's onupdate

    await session.commit()
    await session.refresh(db_asset)
    return db_asset

async def delete_addon_asset(session: AsyncSession, asset_id: PyUUID) -> Optional[models.AddonAsset]:
    """
    Deletes an asset file from storage and its record from the database.
    """
    db_asset = await session.get(models.AddonAsset, asset_id)
    if not db_asset:
        return None

    # Delete the file from storage
    full_path = os.path.join(BASE_ASSET_PATH, db_asset.path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            # Consider removing parent directory if empty, but be careful
            # For now, leave empty directories.
        except OSError as e:
            # Log error, but proceed to delete DB record if file deletion fails for some reason
            print(f"Error deleting asset file {full_path}: {e}")


    await session.delete(db_asset)
    await session.commit()
    return db_asset # Return the deleted asset's data for confirmation

async def create_addon_asset_from_local_path(
    session: AsyncSession,
    addon_id: PyUUID,
    source_file_path: str, # Local path to the source file
    asset_type: str,
    original_filename: str # The intended original filename for storage and reference
) -> models.AddonAsset:
    """
    Creates an AddonAsset record from a local file path and saves the asset file to storage.
    """
    # Ensure the addon exists
    addon = await session.get(models.Addon, addon_id)
    if not addon:
        raise ValueError(f"Addon with id {addon_id} not found.")

    if not os.path.exists(source_file_path):
        raise FileNotFoundError(f"Source asset file not found: {source_file_path}")

    asset_id = uuid_pkg.uuid4()
    # Use the provided original_filename, sanitize if necessary
    sane_original_filename = original_filename if original_filename else "unknown_asset"

    asset_filename = f"{asset_id}_{sane_original_filename}"
    addon_asset_dir = os.path.join(BASE_ASSET_PATH, str(addon_id))
    os.makedirs(addon_asset_dir, exist_ok=True)

    destination_file_path = os.path.join(addon_asset_dir, asset_filename)

    # Copy the file
    shutil.copy(source_file_path, destination_file_path)

    relative_path = os.path.join(str(addon_id), asset_filename)

    db_asset = models.AddonAsset(
        id=asset_id,
        addon_id=addon_id,
        type=asset_type,
        path=relative_path,
        original_filename=sane_original_filename
    )
    session.add(db_asset)
    await session.commit()
    await session.refresh(db_asset)
    return db_asset


# Feedback CRUD functions

async def create_feedback(
    session: AsyncSession,
    job_id: uuid.UUID,
    feedback_type: str,
    user_id: Optional[str] = None,
    comment: Optional[str] = None,
) -> models.ConversionFeedback:
    """
    Creates a new feedback entry for a given conversion job.
    """
    feedback = models.ConversionFeedback(
        job_id=job_id,
        feedback_type=feedback_type,
        user_id=user_id,
        comment=comment,
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def get_feedback_by_job_id(
    session: AsyncSession, job_id: uuid.UUID
) -> List[models.ConversionFeedback]:
    """
    Retrieves all feedback entries for a specific conversion job.
    """
    stmt = select(models.ConversionFeedback).where(
        models.ConversionFeedback.job_id == job_id
    ).order_by(models.ConversionFeedback.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def list_all_feedback(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.ConversionFeedback]:
    """
    Retrieves all feedback entries with pagination.
    """
    stmt = (
        select(models.ConversionFeedback)
        .order_by(models.ConversionFeedback.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# CRUD operations for DocumentEmbedding

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
