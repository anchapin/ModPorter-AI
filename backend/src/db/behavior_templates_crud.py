from typing import Optional, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from datetime import datetime

from db import models

async def create_behavior_template(
    session: AsyncSession,
    *,
    name: str,
    description: str,
    category: str,
    template_type: str,
    template_data: dict,
    tags: List[str],
    is_public: bool = False,
    version: str = "1.0.0",
    created_by: Optional[str] = None,
    commit: bool = True,
) -> models.BehaviorTemplate:
    """Create a new behavior template."""
    template = models.BehaviorTemplate(
        name=name,
        description=description,
        category=category,
        template_type=template_type,
        template_data=template_data,
        tags=tags,
        is_public=is_public,
        version=version,
        created_by=uuid.UUID(created_by) if created_by else None,
    )

    session.add(template)
    if commit:
        await session.commit()
        await session.refresh(template)

    return template


async def get_behavior_template(
    session: AsyncSession,
    template_id: str,
) -> Optional[models.BehaviorTemplate]:
    """Get a behavior template by ID."""
    try:
        template_uuid = uuid.UUID(template_id)
    except ValueError:
        raise ValueError(f"Invalid template ID format: {template_id}")

    stmt = select(models.BehaviorTemplate).where(models.BehaviorTemplate.id == template_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_behavior_templates(
    session: AsyncSession,
    *,
    category: Optional[str] = None,
    template_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    is_public: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[models.BehaviorTemplate]:
    """Get behavior templates with filtering and search."""
    stmt = select(models.BehaviorTemplate)

    # Apply filters
    if category:
        stmt = stmt.where(models.BehaviorTemplate.category == category)
    
    if template_type:
        stmt = stmt.where(models.BehaviorTemplate.template_type == template_type)
    
    if is_public is not None:
        stmt = stmt.where(models.BehaviorTemplate.is_public == is_public)
    
    if tags:
        # Filter by tags - any tag match
        tag_conditions = [models.BehaviorTemplate.tags.any(tag=tag) for tag in tags]
        stmt = stmt.where(func.or_(*tag_conditions))
    
    if search:
        # Search in name and description
        search_filter = func.or_(
            models.BehaviorTemplate.name.ilike(f"%{search}%"),
            models.BehaviorTemplate.description.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    # Apply pagination and ordering
    stmt = stmt.offset(skip).limit(limit).order_by(
        models.BehaviorTemplate.is_public.desc(),
        models.BehaviorTemplate.updated_at.desc()
    )

    result = await session.execute(stmt)
    return result.scalars().all()


async def update_behavior_template(
    session: AsyncSession,
    template_id: str,
    updates: dict,
    commit: bool = True,
) -> Optional[models.BehaviorTemplate]:
    """Update a behavior template."""
    try:
        template_uuid = uuid.UUID(template_id)
    except ValueError:
        raise ValueError(f"Invalid template ID format: {template_id}")

    # Build update statement with provided fields
    update_values = {
        key: value for key, value in updates.items() 
        if value is not None and key in [
            'name', 'description', 'category', 'template_type', 
            'template_data', 'tags', 'is_public', 'version'
        ]
    }
    
    if update_values:
        update_values['updated_at'] = datetime.now(datetime.UTC)
        
        stmt = (
            update(models.BehaviorTemplate)
            .where(models.BehaviorTemplate.id == template_uuid)
            .values(**update_values)
            .returning(models.BehaviorTemplate)
        )
        result = await session.execute(stmt)
        
        if commit:
            await session.commit()
        
        return result.scalar_one_or_none()
    
    # No updates provided
    return await get_behavior_template(session, template_id)


async def delete_behavior_template(
    session: AsyncSession,
    template_id: str,
    commit: bool = True,
) -> bool:
    """Delete a behavior template."""
    try:
        template_uuid = uuid.UUID(template_id)
    except ValueError:
        raise ValueError(f"Invalid template ID format: {template_id}")

    # Check if template exists
    existing_template = await get_behavior_template(session, template_id)
    if not existing_template:
        return False

    stmt = delete(models.BehaviorTemplate).where(models.BehaviorTemplate.id == template_uuid)
    result = await session.execute(stmt)
    
    if commit:
        await session.commit()
    
    return result.rowcount > 0


async def apply_behavior_template(
    session: AsyncSession,
    template_id: str,
    conversion_id: str,
    file_path: Optional[str] = None,
) -> dict:
    """Apply a behavior template to generate content."""
    # Get template
    template = await get_behavior_template(session, template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # Generate file path if not provided
    if not file_path:
        file_path = f"generated/{template.template_type}_{template_id}.json"

    # Generate content based on template type
    content = template.template_data.copy()
    
    # Add template metadata
    if isinstance(content, dict):
        content["_template_info"] = {
            "template_id": str(template.id),
            "template_name": template.name,
            "template_version": template.version,
            "generated_at": datetime.now(datetime.UTC).isoformat()
        }

    # Determine file type based on category
    file_type_map = {
        "block_behavior": "block_behavior",
        "entity_behavior": "entity_behavior", 
        "recipe": "recipe",
        "loot_table": "loot_table",
        "logic_flow": "logic_flow",
        "item_behavior": "item_behavior"
    }
    
    file_type = file_type_map.get(template.category, "custom")

    return {
        "content": content,
        "file_path": file_path,
        "file_type": file_type
    }
