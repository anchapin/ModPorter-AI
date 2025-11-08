from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from db.base import get_db
from db import crud
from services import addon_exporter
from fastapi.responses import StreamingResponse
from io import BytesIO
import uuid
import json
from datetime import datetime

router = APIRouter()

class ExportRequest(BaseModel):
    """Request model for behavior export"""
    conversion_id: str = Field(..., description="Conversion job ID to export")
    file_types: List[str] = Field(default=[], description="Specific file types to export (empty = all)")
    include_templates: bool = Field(default=True, description="Include template metadata")
    export_format: str = Field(default="mcaddon", description="Export format: mcaddon, zip, json")

class ExportResponse(BaseModel):
    """Response model for export metadata"""
    conversion_id: str
    export_format: str
    file_count: int
    template_count: int
    export_size: int  # in bytes
    exported_at: str

@router.post("/export/behavior-pack",
            response_model=ExportResponse,
            summary="Export behavior pack")
async def export_behavior_pack(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
) -> ExportResponse:
    """
    Export behavior files as a Minecraft behavior pack.
    
    Supports multiple formats:
    - mcaddon: Minecraft add-on package (default)
    - zip: Standard ZIP archive
    - json: Raw JSON data
    """
    try:
        uuid.UUID(request.conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, request.conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Get behavior files
    behavior_files = await crud.get_behavior_files_by_conversion(db, request.conversion_id)
    
    if not behavior_files:
        raise HTTPException(status_code=400, detail="No behavior files found for conversion")

    # Filter by file types if specified
    if request.file_types:
        behavior_files = [f for f in behavior_files if f.file_type in request.file_types]

    # Get addon details (for proper export structure)
    addon_details = await crud.get_addon_details(db, uuid.UUID(request.conversion_id))
    if not addon_details:
        # Create minimal addon details if not found
        addon_details = type('AddonDetails', (), {
            'id': uuid.UUID(request.conversion_id),
            'name': f'Behavior Pack {request.conversion_id}',
            'description': 'Exported behavior pack',
            'blocks': [],
            'recipes': [],
            'assets': []
        })()

    # Prepare export data
    export_data = {
        "conversion_id": request.conversion_id,
        "export_format": request.export_format,
        "files": [
            {
                "path": file.file_path,
                "type": file.file_type,
                "content": file.content,
                "created_at": file.created_at.isoformat(),
                "updated_at": file.updated_at.isoformat()
            }
            for file in behavior_files
        ],
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "conversion_status": conversion.status,
            "file_count": len(behavior_files),
            "include_templates": request.include_templates
        }
    }

    # Add template metadata if requested
    template_count = 0
    if request.include_templates:
        template_info = {
            "used_templates": [],
            "generated_from_templates": []
        }
        
        # Check for template metadata in file content
        for file in behavior_files:
            try:
                content = json.loads(file.content)
                if isinstance(content, dict) and "_template_info" in content:
                    template_info["used_templates"].append(content["_template_info"])
                    template_count += 1
            except (json.JSONDecodeError, TypeError):
                pass  # Skip invalid JSON
        
        export_data["template_info"] = template_info

    # Generate export based on format
    if request.export_format == "json":
        # Return raw JSON
        return ExportResponse(
            conversion_id=request.conversion_id,
            export_format=request.export_format,
            file_count=len(behavior_files),
            template_count=template_count,
            export_size=len(json.dumps(export_data).encode('utf-8')),
            exported_at=datetime.utcnow().isoformat()
        )
    
    elif request.export_format == "zip":
        # Create ZIP archive
        import zipfile
        from services.cache import CacheService
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add behavior files
            for file in behavior_files:
                zip_file.writestr(file.file_path, file.content)
            
            # Add export metadata
            zip_file.writestr("export_metadata.json", json.dumps(export_data["metadata"], indent=2))
            
            # Add template info if included
            if request.include_templates and "template_info" in export_data:
                zip_file.writestr("template_info.json", json.dumps(export_data["template_info"], indent=2))
        
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()
        
        # Store in cache for download
        cache = CacheService()
        await cache.set_export_data(request.conversion_id, zip_bytes)
        
        return ExportResponse(
            conversion_id=request.conversion_id,
            export_format=request.export_format,
            file_count=len(behavior_files),
            template_count=template_count,
            export_size=len(zip_bytes),
            exported_at=datetime.utcnow().isoformat()
        )
    
    else:  # mcaddon (default)
        # Use existing addon exporter
        from db import crud
        
        try:
            # Get asset base path
            asset_base_path = crud.BASE_ASSET_PATH
            
            # Create mcaddon zip using existing service
            zip_bytes_io = addon_exporter.create_mcaddon_zip(
                addon_pydantic=addon_details,
                asset_base_path=asset_base_path
            )
            
            # Add export metadata to the zip
            zip_bytes_io.seek(0)
            import zipfile
            
            # Read existing zip content and add metadata
            with zipfile.ZipFile(zip_bytes_io, 'a') as mcaddon_zip:
                mcaddon_zip.writestr("export_metadata.json", json.dumps(export_data["metadata"], indent=2))
                
                if request.include_templates and "template_info" in export_data:
                    mcaddon_zip.writestr("template_info.json", json.dumps(export_data["template_info"], indent=2))
            
            zip_bytes_io.seek(0)
            zip_bytes = zip_bytes_io.getvalue()
            
            # Store in cache
            cache = CacheService()
            await cache.set_export_data(request.conversion_id, zip_bytes)
            
            return ExportResponse(
                conversion_id=request.conversion_id,
                export_format=request.export_format,
                file_count=len(behavior_files),
                template_count=template_count,
                export_size=len(zip_bytes),
                exported_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create MCADDON: {str(e)}")


@router.get("/export/behavior-pack/{conversion_id}/download",
            summary="Download exported behavior pack")
async def download_exported_pack(
    conversion_id: str = Path(..., description="Conversion job ID"),
    format: str = Query(default="mcaddon", description="Export format"),
    db: AsyncSession = Depends(get_db)
):
    """
    Download previously exported behavior pack.
    """
    try:
        uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Get export data from cache
    from services.cache import CacheService
    cache = CacheService()
    export_data = await cache.get_export_data(conversion_id)
    
    if not export_data:
        raise HTTPException(status_code=404, detail="Export not found. Please export first.")

    # Determine filename and media type
    if format == "zip":
        filename = f"behavior_pack_{conversion_id}.zip"
        media_type = "application/zip"
    else:  # mcaddon
        filename = f"behavior_pack_{conversion_id}.mcaddon"
        media_type = "application/zip"  # MCADDON is also a ZIP file

    return StreamingResponse(
        content=BytesIO(export_data),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )


@router.get("/export/formats",
            response_model=List[Dict[str, str]],
            summary="Get available export formats")
async def get_export_formats():
    """
    Get available export formats and their descriptions.
    """
    return [
        {
            "format": "mcaddon",
            "name": "Minecraft Add-On",
            "description": "Standard Minecraft Bedrock Edition add-on package",
            "extension": ".mcaddon"
        },
        {
            "format": "zip",
            "name": "ZIP Archive",
            "description": "Standard ZIP archive containing behavior files",
            "extension": ".zip"
        },
        {
            "format": "json",
            "name": "JSON Data",
            "description": "Raw JSON export of all behavior file data",
            "extension": ".json"
        }
    ]


@router.get("/export/preview/{conversion_id}",
            summary="Preview export data")
async def preview_export(
    conversion_id: str = Path(..., description="Conversion job ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Preview what would be included in an export without creating files.
    """
    try:
        uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Get behavior files
    behavior_files = await crud.get_behavior_files_by_conversion(db, conversion_id)
    
    if not behavior_files:
        raise HTTPException(status_code=400, detail="No behavior files found for conversion")

    # Analyze files
    file_analysis = {
        "total_files": len(behavior_files),
        "file_types": {},
        "template_usage": {
            "files_with_templates": 0,
            "unique_templates": set()
        }
    }

    for file in behavior_files:
        # Count file types
        file_type = file.file_type
        file_analysis["file_types"][file_type] = file_analysis["file_types"].get(file_type, 0) + 1
        
        # Check for template usage
        try:
            content = json.loads(file.content)
            if isinstance(content, dict) and "_template_info" in content:
                template_info = content["_template_info"]
                file_analysis["template_usage"]["files_with_templates"] += 1
                file_analysis["template_usage"]["unique_templates"].add(
                    f"{template_info['template_name']} v{template_info['template_version']}"
                )
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # Convert set to list for JSON serialization
    file_analysis["template_usage"]["unique_templates"] = list(
        file_analysis["template_usage"]["unique_templates"]
    )

    return {
        "conversion_id": conversion_id,
        "conversion_status": conversion.status,
        "analysis": file_analysis,
        "files_preview": [
            {
                "path": file.file_path,
                "type": file.file_type,
                "size": len(file.content),
                "has_template": "_template_info" in json.loads(file.content) if file.content else False,
                "updated_at": file.updated_at.isoformat()
            }
            for file in behavior_files[:10]  # Preview first 10 files
        ]
    }
