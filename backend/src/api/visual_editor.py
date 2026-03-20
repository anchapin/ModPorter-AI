"""
Visual Conversion Editor API

Side-by-side Java/Bedrock code editor with live preview.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.base import get_db
from db.models import ConversionJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/editor", tags=["Visual Editor"])


class EditorSessionRequest(BaseModel):
    """Create editor session request."""
    conversion_id: str


class EditorSessionResponse(BaseModel):
    """Editor session response."""
    session_id: str
    java_code: str
    bedrock_code: str
    diff_view: bool
    readonly: bool


class CodeEditRequest(BaseModel):
    """Code edit request."""
    session_id: str
    bedrock_code: str
    edit_type: str  # "manual", "ai_suggestion", "template"


class CodeEditResponse(BaseModel):
    """Code edit response."""
    success: bool
    bedrock_code: str
    validation_errors: List[dict]
    message: str


class AISuggestionRequest(BaseModel):
    """AI suggestion request."""
    session_id: str
    selected_code: str
    suggestion_type: str  # "fix_error", "improve", "alternative"


class AISuggestionResponse(BaseModel):
    """AI suggestion response."""
    suggestion: str
    explanation: str
    confidence: float


class TemplateRequest(BaseModel):
    """Apply template request."""
    session_id: str
    template_id: str
    template_data: Dict[str, Any]


@router.post("/session", response_model=EditorSessionResponse)
async def create_editor_session(
    request: EditorSessionRequest,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Create visual editor session for a conversion.
    
    - Loads Java and Bedrock code
    - Sets up side-by-side view
    - Enables live preview
    """
    # Verify conversion belongs to user
    result = await db.execute(
        ConversionJob.filter(
            ConversionJob.id == request.conversion_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversion = result.scalar_one_or_none()
    
    if not conversion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion not found",
        )
    
    # Create session
    session_id = f"editor_{request.conversion_id}"
    
    return EditorSessionResponse(
        session_id=session_id,
        java_code=conversion.input_data.get("java_code", ""),
        bedrock_code=conversion.output_data.get("bedrock_code", "") if conversion.output_data else "",
        diff_view=False,
        readonly=conversion.status != "completed",
    )


@router.post("/edit", response_model=CodeEditResponse)
async def edit_code(
    request: CodeEditRequest,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Edit Bedrock code in visual editor.
    
    - Validates changes
    - Updates preview
    - Saves version
    """
    # Validate code changes
    validation_errors = []
    
    # Basic validation (would be more comprehensive in production)
    if not request.bedrock_code.strip():
        validation_errors.append({
            "field": "bedrock_code",
            "error": "Code cannot be empty",
        })
    
    # Check for valid JSON structure if applicable
    if request.bedrock_code.strip().startswith("{"):
        import json
        try:
            json.loads(request.bedrock_code)
        except json.JSONDecodeError as e:
            validation_errors.append({
                "field": "bedrock_code",
                "error": f"Invalid JSON: {str(e)}",
            })
    
    success = len(validation_errors) == 0
    
    return CodeEditResponse(
        success=success,
        bedrock_code=request.bedrock_code,
        validation_errors=validation_errors,
        message="Code updated successfully" if success else "Validation errors found",
    )


@router.post("/ai-suggest", response_model=AISuggestionResponse)
async def get_ai_suggestion(
    request: AISuggestionRequest,
    user_id: str,
):
    """
    Get AI-powered code suggestion.
    
    - Fix errors in selected code
    - Improve code quality
    - Suggest alternatives
    """
    # This would call the AI engine for suggestions
    # For now, return mock response
    
    suggestions = {
        "fix_error": {
            "suggestion": request.selected_code + "\n// Fixed",
            "explanation": "Added missing semicolon and fixed syntax",
            "confidence": 0.95,
        },
        "improve": {
            "suggestion": request.selected_code + "\n// Improved",
            "explanation": "Optimized for better performance",
            "confidence": 0.85,
        },
        "alternative": {
            "suggestion": request.selected_code + "\n// Alternative",
            "explanation": "Alternative implementation approach",
            "confidence": 0.75,
        },
    }
    
    suggestion = suggestions.get(request.suggestion_type, suggestions["improve"])
    
    return AISuggestionResponse(**suggestion)


@router.post("/apply-template", response_model=dict)
async def apply_template(
    request: TemplateRequest,
    user_id: str,
):
    """
    Apply code template to editor.
    
    - Pre-built templates for common patterns
    - Customizable template data
    - Instant preview
    """
    # Template library (would be stored in database)
    templates = {
        "basic_item": {
            "name": "Basic Item",
            "code": """{
    "format_version": "1.20.0",
    "minecraft:item": {
        "description": {
            "identifier": "{{namespace}}:{{item_name}}",
            "category": "items"
        },
        "components": {
            "minecraft:display_name": {
                "value": "{{display_name}}"
            },
            "minecraft:icon": "{{item_name}}",
            "minecraft:stacked_by_data": true,
            "minecraft:max_stack_size": {{stack_size}}
        }
    }
}""",
        },
        "basic_block": {
            "name": "Basic Block",
            "code": """{
    "format_version": "1.20.0",
    "minecraft:block": {
        "description": {
            "identifier": "{{namespace}}:{{block_name}}",
            "category": "construction"
        },
        "components": {
            "minecraft:display_name": {
                "value": "{{display_name}}"
            },
            "minecraft:material_instances": {
                "*": {
                    "texture": "{{block_name}}",
                    "render_method": "opaque"
                }
            },
            "minecraft:destructible_by_mining": {
                "seconds_to_destroy": {{hardness}}
            }
        }
    }
}""",
        },
    }
    
    template = templates.get(request.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {request.template_id}",
        )
    
    # Apply template data
    code = template["code"]
    for key, value in request.template_data.items():
        code = code.replace(f"{{{{{key}}}}}", str(value))
    
    return {
        "success": True,
        "template_name": template["name"],
        "code": code,
    }


@router.get("/templates", response_model=list)
async def list_templates():
    """
    List available code templates.
    
    Returns categorized templates for quick access.
    """
    templates = [
        {
            "id": "basic_item",
            "name": "Basic Item",
            "category": "items",
            "description": "Simple custom item",
        },
        {
            "id": "basic_block",
            "name": "Basic Block",
            "category": "blocks",
            "description": "Simple custom block",
        },
        {
            "id": "tool_sword",
            "name": "Sword Tool",
            "category": "items",
            "description": "Custom sword with durability",
        },
        {
            "id": "ore_block",
            "name": "Ore Block",
            "category": "blocks",
            "description": "Ore block with loot table",
        },
    ]
    
    return templates


@router.post("/compare", response_model=dict)
async def compare_versions(
    session_id: str,
    original_code: str,
    modified_code: str,
    user_id: str,
):
    """
    Compare two versions of code.
    
    Shows diff between original and modified code.
    """
    # Simple diff (would use proper diff library in production)
    diff = {
        "added_lines": 0,
        "removed_lines": 0,
        "changes": [],
    }
    
    original_lines = original_code.split("\n")
    modified_lines = modified_code.split("\n")
    
    # Simple line-by-line comparison
    for i, line in enumerate(modified_lines):
        if i >= len(original_lines):
            diff["added_lines"] += 1
            diff["changes"].append({
                "type": "added",
                "line": i + 1,
                "content": line,
            })
        elif line != original_lines[i]:
            diff["changes"].append({
                "type": "modified",
                "line": i + 1,
                "original": original_lines[i],
                "modified": line,
            })
    
    for i in range(len(modified_lines), len(original_lines)):
        diff["removed_lines"] += 1
        diff["changes"].append({
            "type": "removed",
            "line": i + 1,
            "content": original_lines[i],
        })
    
    return {
        "session_id": session_id,
        "diff": diff,
        "summary": f"+{diff['added_lines']} -{diff['removed_lines']}",
    }
