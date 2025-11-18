from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from db.base import get_db
from db import behavior_templates_crud
import uuid
from datetime import datetime

router = APIRouter()

# Pydantic models for behavior templates
class BehaviorTemplateCreate(BaseModel):
    """Request model for creating a behavior template"""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category (block_behavior, entity_behavior, recipe, loot_table, logic_flow)")
    template_type: str = Field(..., description="Specific template type (e.g., 'custom_block', 'mob_drops', 'crafting_recipe')")
    template_data: Dict[str, Any] = Field(..., description="Template configuration and default values")
    tags: List[str] = Field(default=[], description="Tags for search and filtering")
    is_public: bool = Field(default=False, description="Whether template is publicly available")
    version: str = Field(default="1.0.0", description="Template version")

class BehaviorTemplateUpdate(BaseModel):
    """Request model for updating a behavior template"""
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: Optional[str] = Field(None, description="Template category")
    template_type: Optional[str] = Field(None, description="Specific template type")
    template_data: Optional[Dict[str, Any]] = Field(None, description="Template configuration")
    tags: Optional[List[str]] = Field(None, description="Tags for search and filtering")
    is_public: Optional[bool] = Field(None, description="Whether template is publicly available")
    version: Optional[str] = Field(None, description="Template version")

class BehaviorTemplateResponse(BaseModel):
    """Response model for behavior template"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    template_type: str = Field(..., description="Specific template type")
    template_data: Dict[str, Any] = Field(..., description="Template configuration")
    tags: List[str] = Field(..., description="Tags for search and filtering")
    is_public: bool = Field(..., description="Whether template is publicly available")
    version: str = Field(..., description="Template version")
    created_by: Optional[str] = Field(None, description="Creator user ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

class BehaviorTemplateCategory(BaseModel):
    """Model for template category"""
    name: str = Field(..., description="Category name")
    display_name: str = Field(..., description="Display name for UI")
    description: str = Field(..., description="Category description")
    icon: Optional[str] = Field(None, description="Icon name or identifier")

# Predefined template categories
TEMPLATE_CATEGORIES = [
    BehaviorTemplateCategory(
        name="block_behavior",
        display_name="Block Behaviors",
        description="Templates for custom block behaviors and properties",
        icon="block"
    ),
    BehaviorTemplateCategory(
        name="entity_behavior", 
        display_name="Entity Behaviors",
        description="Templates for entity AI, behaviors, and components",
        icon="entity"
    ),
    BehaviorTemplateCategory(
        name="recipe",
        display_name="Recipes",
        description="Templates for crafting and smelting recipes",
        icon="recipe"
    ),
    BehaviorTemplateCategory(
        name="loot_table",
        display_name="Loot Tables",
        description="Templates for entity and block loot tables",
        icon="loot"
    ),
    BehaviorTemplateCategory(
        name="logic_flow",
        display_name="Logic Flows",
        description="Templates for visual logic programming and event handling",
        icon="logic"
    ),
    BehaviorTemplateCategory(
        name="item_behavior",
        display_name="Item Behaviors", 
        description="Templates for custom item behaviors and properties",
        icon="item"
    )
]

@router.get("/templates/categories",
           response_model=List[BehaviorTemplateCategory],
           summary="Get all template categories")
async def get_template_categories():
    """
    Get all available behavior template categories.
    
    Returns predefined categories with display names and descriptions.
    """
    return TEMPLATE_CATEGORIES

@router.get("/templates",
           response_model=List[BehaviorTemplateResponse],
           summary="Get behavior templates")
async def get_behavior_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
) -> List[BehaviorTemplateResponse]:
    """
    Get behavior templates with filtering and search options.
    
    Supports filtering by category, type, tags, and public status.
    Also supports text search in name and description.
    """
    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Get templates from database
    templates = await behavior_templates_crud.get_behavior_templates(
        db,
        category=category,
        template_type=template_type,
        tags=tag_list,
        search=search,
        is_public=is_public,
        skip=skip,
        limit=limit
    )
    
    return [
        BehaviorTemplateResponse(
            id=str(template.id),
            name=template.name,
            description=template.description,
            category=template.category,
            template_type=template.template_type,
            template_data=template.template_data,
            tags=template.tags,
            is_public=template.is_public,
            version=template.version,
            created_by=str(template.created_by) if template.created_by else None,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat()
        )
        for template in templates
    ]

@router.get("/templates/{template_id}",
           response_model=BehaviorTemplateResponse,
           summary="Get specific behavior template")
async def get_behavior_template(
    template_id: str = Path(..., description="Template ID"),
    db: AsyncSession = Depends(get_db)
) -> BehaviorTemplateResponse:
    """
    Get a specific behavior template by ID.
    """
    try:
        uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    template = await behavior_templates_crud.get_behavior_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return BehaviorTemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category,
        template_type=template.template_type,
        template_data=template.template_data,
        tags=template.tags,
        is_public=template.is_public,
        version=template.version,
        created_by=str(template.created_by) if template.created_by else None,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )

@router.post("/templates",
            response_model=BehaviorTemplateResponse,
            summary="Create behavior template",
            status_code=201)
async def create_behavior_template(
    request: BehaviorTemplateCreate = ...,
    user_id: Optional[str] = None,  # Would come from authentication
    db: AsyncSession = Depends(get_db)
) -> BehaviorTemplateResponse:
    """
    Create a new behavior template.
    
    Templates can be created for reuse across different conversions.
    """
    # Validate category
    valid_categories = [cat.name for cat in TEMPLATE_CATEGORIES]
    if request.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )

    # Create template
    try:
        template = await behavior_templates_crud.create_behavior_template(
            db,
            name=request.name,
            description=request.description,
            category=request.category,
            template_type=request.template_type,
            template_data=request.template_data,
            tags=request.tags,
            is_public=request.is_public,
            version=request.version,
            created_by=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")

    return BehaviorTemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category,
        template_type=template.template_type,
        template_data=template.template_data,
        tags=template.tags,
        is_public=template.is_public,
        version=template.version,
        created_by=str(template.created_by) if template.created_by else None,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )

@router.put("/templates/{template_id}",
           response_model=BehaviorTemplateResponse,
           summary="Update behavior template")
async def update_behavior_template(
    template_id: str = Path(..., description="Template ID"),
    request: BehaviorTemplateUpdate = ...,
    db: AsyncSession = Depends(get_db)
) -> BehaviorTemplateResponse:
    """
    Update an existing behavior template.
    """
    try:
        uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    # Check if template exists
    existing_template = await behavior_templates_crud.get_behavior_template(db, template_id)
    if not existing_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Validate category if provided
    if request.category:
        valid_categories = [cat.name for cat in TEMPLATE_CATEGORIES]
        if request.category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

    # Update template
    try:
        updated_template = await behavior_templates_crud.update_behavior_template(
            db,
            template_id=template_id,
            updates=request.dict(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")

    return BehaviorTemplateResponse(
        id=str(updated_template.id),
        name=updated_template.name,
        description=updated_template.description,
        category=updated_template.category,
        template_type=updated_template.template_type,
        template_data=updated_template.template_data,
        tags=updated_template.tags,
        is_public=updated_template.is_public,
        version=updated_template.version,
        created_by=str(updated_template.created_by) if updated_template.created_by else None,
        created_at=updated_template.created_at.isoformat(),
        updated_at=updated_template.updated_at.isoformat()
    )

@router.delete("/templates/{template_id}",
              status_code=204,
              summary="Delete behavior template")
async def delete_behavior_template(
    template_id: str = Path(..., description="Template ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a behavior template.
    """
    try:
        uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    # Delete template
    success = await behavior_templates_crud.delete_behavior_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

    # Return 204 No Content
    return

@router.get("/templates/{template_id}/apply",
            response_model=Dict[str, Any],
            summary="Apply template to behavior file")
async def apply_behavior_template(
    template_id: str = Path(..., description="Template ID"),
    conversion_id: str = Query(..., description="Conversion ID to apply template to"),
    file_path: Optional[str] = Query(None, description="Specific file path to apply template to"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Apply a behavior template to generate behavior file content.
    
    Returns the generated content that can be used to create or update behavior files.
    """
    try:
        uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    # Get template
    template = await behavior_templates_crud.get_behavior_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if conversion exists
    from db import crud
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Apply template logic (would implement in a service)
    try:
        result = await behavior_templates_crud.apply_behavior_template(
            db,
            template_id=template_id,
            conversion_id=conversion_id,
            file_path=file_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply template: {str(e)}")

    return {
        "template_id": template_id,
        "conversion_id": conversion_id,
        "generated_content": result.get("content"),
        "file_path": result.get("file_path"),
        "file_type": result.get("file_type"),
        "applied_at": datetime.utcnow().isoformat()
    }

# Predefined templates endpoint for quick start
@router.get("/templates/predefined",
            response_model=List[BehaviorTemplateResponse],
            summary="Get predefined templates")
async def get_predefined_templates():
    """
    Get predefined behavior templates included with the system.
    
    These are commonly used templates that are always available.
    """
    predefined_templates = [
        {
            "id": "simple_block",
            "name": "Simple Custom Block",
            "description": "A basic custom block with standard properties",
            "category": "block_behavior",
            "template_type": "simple_block",
            "template_data": {
                "format_version": "1.16.0",
                "minecraft:block": {
                    "description": {"identifier": "custom:simple_block"},
                    "components": {
                        "minecraft:destroy_time": 1.0,
                        "minecraft:friction": 0.6,
                        "minecraft:explosion_resistance": 6.0,
                        "minecraft:map_color": "#FFFFFF"
                    }
                }
            },
            "tags": ["basic", "block", "custom"],
            "is_public": True,
            "version": "1.0.0"
        },
        {
            "id": "basic_recipe",
            "name": "Basic Crafting Recipe", 
            "description": "A simple shaped crafting recipe",
            "category": "recipe",
            "template_type": "shaped_crafting",
            "template_data": {
                "format_version": "1.16.0",
                "minecraft:recipe_shaped": {
                    "description": {"identifier": "custom:basic_recipe"},
                    "tags": ["crafting_table"],
                    "pattern": ["#", "X", "#"],
                    "key": {
                        "#": {"item": "minecraft:stick"},
                        "X": {"item": "minecraft:planks"}
                    },
                    "result": {
                        "item": "custom:basic_item",
                        "count": 4
                    }
                }
            },
            "tags": ["crafting", "basic", "recipe"],
            "is_public": True,
            "version": "1.0.0"
        },
        {
            "id": "entity_loot_table",
            "name": "Entity Loot Table",
            "description": "Basic loot table for entity drops",
            "category": "loot_table", 
            "template_type": "entity_drops",
            "template_data": {
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "item",
                                "name": "minecraft:arrow",
                                "weight": 1,
                                "functions": [
                                    {
                                        "function": "set_count",
                                        "count": {
                                            "min": 0,
                                            "max": 2
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "tags": ["loot", "entity", "drops"],
            "is_public": True,
            "version": "1.0.0"
        }
    ]

    return [
        BehaviorTemplateResponse(
            id=template["id"],
            name=template["name"],
            description=template["description"],
            category=template["category"],
            template_type=template["template_type"],
            template_data=template["template_data"],
            tags=template["tags"],
            is_public=template["is_public"],
            version=template["version"],
            created_by=None,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        for template in predefined_templates
    ]
