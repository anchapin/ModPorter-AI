from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.db.base import get_db
from src.db import crud
import uuid

router = APIRouter()

# Pydantic models for API requests/responses
class BehaviorFileCreate(BaseModel):
    """Request model for creating a behavior file"""
    file_path: str = Field(..., description="Path of the behavior file within the mod structure")
    file_type: str = Field(..., description="Type of behavior file (entity_behavior, block_behavior, script, recipe)")
    content: str = Field(..., description="Text content of the behavior file")

class BehaviorFileUpdate(BaseModel):
    """Request model for updating a behavior file"""
    content: str = Field(..., description="Updated text content of the behavior file")

class BehaviorFileResponse(BaseModel):
    """Response model for behavior file data"""
    id: str = Field(..., description="Unique identifier of the behavior file")
    conversion_id: str = Field(..., description="ID of the associated conversion job")
    file_path: str = Field(..., description="Path of the behavior file within the mod structure")
    file_type: str = Field(..., description="Type of behavior file")
    content: str = Field(..., description="Text content of the behavior file")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

class BehaviorFileTreeNode(BaseModel):
    """Model for file tree structure"""
    id: str = Field(..., description="File ID for leaf nodes, empty for directories")
    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Full path from root")
    type: str = Field(..., description="'file' or 'directory'")
    file_type: str = Field(default="", description="Behavior file type for files")
    children: List['BehaviorFileTreeNode'] = Field(default=[], description="Child nodes for directories")

# Allow forward references
BehaviorFileTreeNode.model_rebuild()

@router.get("/conversions/{conversion_id}/behaviors",
           response_model=List[BehaviorFileTreeNode],
           summary="Get behavior file tree")
async def get_conversion_behavior_files(
    conversion_id: str = Path(..., description="Conversion job ID"),
    db: AsyncSession = Depends(get_db)
) -> List[BehaviorFileTreeNode]:
    """
    Get all editable behavior files for a conversion as a file tree structure.

    Returns a hierarchical structure of files and directories for easy navigation
    in the behavior editor interface.
    """
    try:
        uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Get all behavior files for this conversion
    behavior_files = await crud.get_behavior_files_by_conversion(db, conversion_id)

    if not behavior_files:
        return []

    # Build file tree structure
    tree_root: Dict[str, Any] = {}

    for file in behavior_files:
        parts = file.file_path.split('/')
        current = tree_root

        # Build directory structure
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {
                    'name': part,
                    'path': '/'.join(parts[:i+1]),
                    'type': 'directory',
                    'children': {}
                }
            current = current[part]['children']

        # Add file
        filename = parts[-1]
        current[filename] = {
            'id': str(file.id),
            'name': filename,
            'path': file.file_path,
            'type': 'file',
            'file_type': file.file_type,
            'children': {}
        }

    def dict_to_tree_nodes(node_dict: Dict[str, Any]) -> List[BehaviorFileTreeNode]:
        """Convert dictionary structure to tree nodes"""
        nodes = []
        for key, value in node_dict.items():
            children = dict_to_tree_nodes(value['children']) if value['children'] else []
            node = BehaviorFileTreeNode(
                id=value.get('id', ''),
                name=value['name'],
                path=value['path'],
                type=value['type'],
                file_type=value.get('file_type', ''),
                children=children
            )
            nodes.append(node)
        return sorted(nodes, key=lambda x: (x.type == 'file', x.name))

    return dict_to_tree_nodes(tree_root)

@router.get("/behaviors/{file_id}",
           response_model=BehaviorFileResponse,
           summary="Get behavior file content")
async def get_behavior_file(
    file_id: str = Path(..., description="Behavior file ID"),
    db: AsyncSession = Depends(get_db)
) -> BehaviorFileResponse:
    """
    Retrieve the current content of a specific behavior file.
    """
    try:
        uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    behavior_file = await crud.get_behavior_file(db, file_id)
    if not behavior_file:
        raise HTTPException(status_code=404, detail="Behavior file not found")

    return BehaviorFileResponse(
        id=str(behavior_file.id),
        conversion_id=str(behavior_file.conversion_id),
        file_path=behavior_file.file_path,
        file_type=behavior_file.file_type,
        content=behavior_file.content,
        created_at=behavior_file.created_at.isoformat(),
        updated_at=behavior_file.updated_at.isoformat()
    )

@router.put("/behaviors/{file_id}",
           response_model=BehaviorFileResponse,
           summary="Update behavior file content")
async def update_behavior_file(
    file_id: str = Path(..., description="Behavior file ID"),
    request: BehaviorFileUpdate = ...,
    db: AsyncSession = Depends(get_db)
) -> BehaviorFileResponse:
    """
    Update the content of a specific behavior file.

    This is the primary "save" endpoint for the behavior editor.
    """
    try:
        uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    # Check if file exists
    existing_file = await crud.get_behavior_file(db, file_id)
    if not existing_file:
        raise HTTPException(status_code=404, detail="Behavior file not found")

    # Update the file content
    updated_file = await crud.update_behavior_file_content(db, file_id, request.content)
    if not updated_file:
        raise HTTPException(status_code=500, detail="Failed to update behavior file")

    return BehaviorFileResponse(
        id=str(updated_file.id),
        conversion_id=str(updated_file.conversion_id),
        file_path=updated_file.file_path,
        file_type=updated_file.file_type,
        content=updated_file.content,
        created_at=updated_file.created_at.isoformat(),
        updated_at=updated_file.updated_at.isoformat()
    )

@router.post("/conversions/{conversion_id}/behaviors",
            response_model=BehaviorFileResponse,
            summary="Create new behavior file",
            status_code=201)
async def create_behavior_file(
    conversion_id: str = Path(..., description="Conversion job ID"),
    request: BehaviorFileCreate = ...,
    db: AsyncSession = Depends(get_db)
) -> BehaviorFileResponse:
    """
    Create a new behavior file for a conversion.

    This endpoint can be used to add new behavior files during editing.
    """
    try:
        uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Create the behavior file
    try:
        behavior_file = await crud.create_behavior_file(
            db,
            conversion_id=conversion_id,
            file_path=request.file_path,
            file_type=request.file_type,
            content=request.content
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create behavior file: {str(e)}")

    return BehaviorFileResponse(
        id=str(behavior_file.id),
        conversion_id=str(behavior_file.conversion_id),
        file_path=behavior_file.file_path,
        file_type=behavior_file.file_type,
        content=behavior_file.content,
        created_at=behavior_file.created_at.isoformat(),
        updated_at=behavior_file.updated_at.isoformat()
    )

@router.delete("/behaviors/{file_id}",
              status_code=204,
              summary="Delete behavior file")
async def delete_behavior_file(
    file_id: str = Path(..., description="Behavior file ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a behavior file.

    This removes the file from the database. Use with caution.
    """
    try:
        uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    # Delete the file
    success = await crud.delete_behavior_file(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="Behavior file not found")

    # Return 204 No Content (no response body)
    return

@router.get("/conversions/{conversion_id}/behaviors/types/{file_type}",
           response_model=List[BehaviorFileResponse],
           summary="Get behavior files by type")
async def get_behavior_files_by_type(
    conversion_id: str = Path(..., description="Conversion job ID"),
    file_type: str = Path(..., description="Behavior file type to filter by"),
    db: AsyncSession = Depends(get_db)
) -> List[BehaviorFileResponse]:
    """
    Get all behavior files of a specific type for a conversion.

    Useful for filtering files by category (e.g., all entity behaviors).
    """
    try:
        uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Get behavior files by type
    behavior_files = await crud.get_behavior_files_by_type(db, conversion_id, file_type)

    return [
        BehaviorFileResponse(
            id=str(file.id),
            conversion_id=str(file.conversion_id),
            file_path=file.file_path,
            file_type=file.file_type,
            content=file.content,
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat()
        )
        for file in behavior_files
    ]
