from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict, List
from pydantic import BaseModel, Field
import uuid

# Import AI Engine components with fallback for testing
try:
    import sys
    import os
    # Add AI engine to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    ai_engine_path = os.path.join(project_root, 'ai-engine')
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)
    
    from src.engines.comparison_engine import ComparisonEngine
    from src.models.comparison import ComparisonResult as AIComparisonResult, FeatureMapping as AIFeatureMapping
except ImportError:
    # Mock classes for testing environments
    from dataclasses import dataclass, field
    from typing import List, Dict, Any
    
    @dataclass
    class FeatureMapping:
        java_feature: str
        bedrock_equivalent: str
        mapping_type: str
        confidence_score: float
        assumption_applied: str = None
    
    @dataclass
    class ComparisonResult:
        conversion_id: str
        structural_diff: Dict[str, List[str]]
        code_diff: Dict[str, Any]
        asset_diff: Dict[str, Any]
        feature_mappings: List[FeatureMapping] = field(default_factory=list)
        assumptions_applied: List[Dict[str, Any]] = field(default_factory=list)
        confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    class ComparisonEngine:
        def compare(self, java_mod_path: str, bedrock_addon_path: str, conversion_id: str) -> ComparisonResult:
            return ComparisonResult(
                conversion_id=conversion_id,
                structural_diff={"files_added": ["test.js"], "files_removed": ["test.java"], "files_modified": []},
                code_diff={"logic_preserved": 0.85},
                asset_diff={"textures_converted": 5},
                feature_mappings=[
                    FeatureMapping(
                        java_feature="Test Java Feature",
                        bedrock_equivalent="Test Bedrock Feature",
                        mapping_type="TEST_MAPPING",
                        confidence_score=0.75
                    )
                ],
                assumptions_applied=[{"id": "TEST_ASSUMPTION", "description": "Test assumption"}],
                confidence_scores={"overall": 0.8}
            )
    
    AIComparisonResult = ComparisonResult
    AIFeatureMapping = FeatureMapping


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload


# Adjust these imports based on your actual database setup location
# from src.db.declarative_base import Base # Base is not directly used here, models are
from src.db.models import ComparisonResultDb, FeatureMappingDb, ConversionJob # ConversionJob for FK check
from src.db.base import get_db

router = APIRouter()

class CreateComparisonRequest(BaseModel):
    conversion_id: str = Field(..., description="UUID of the conversion job")
    java_mod_path: str = Field(..., description="Path to the original Java mod")
    bedrock_addon_path: str = Field(..., description="Path to the converted Bedrock add-on")

class ComparisonResponse(BaseModel):
    message: str
    comparison_id: str

@router.post("/", status_code=201, response_model=ComparisonResponse)
async def create_comparison(
    request: CreateComparisonRequest,
    session: AsyncSession = Depends(get_db)
) -> ComparisonResponse:

    engine = ComparisonEngine()
    try:
        # Validate conversion_id as UUID and check if ConversionJob exists
        try:
            conversion_uuid = uuid.UUID(request.conversion_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid conversion_id format: '{request.conversion_id}'. Must be a UUID.")

        conversion_job = await session.get(ConversionJob, conversion_uuid)
        if not conversion_job:
            raise HTTPException(status_code=404, detail=f"ConversionJob with id {request.conversion_id} not found.")

        # AI Engine's compare method expects a string conversion_id
        ai_result: AIComparisonResult = engine.compare(
            java_mod_path=request.java_mod_path,
            bedrock_addon_path=request.bedrock_addon_path,
            conversion_id=request.conversion_id
        )
    except HTTPException: # Re-raise HTTPExceptions from validation
        raise
    except Exception as e:
        # Log the exception e here if logging is set up
        # logger.error(f"Comparison engine failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison engine failed: {str(e)}")

    # Map AI Engine models to SQLAlchemy DB models
    db_comparison_result = ComparisonResultDb(
        conversion_id=conversion_uuid, # Use the validated UUID
        structural_diff=ai_result.structural_diff,
        code_diff=ai_result.code_diff,
        asset_diff=ai_result.asset_diff,
        assumptions_applied=ai_result.assumptions_applied,
        confidence_scores=ai_result.confidence_scores
    )

    if ai_result.feature_mappings:
        for ai_mapping in ai_result.feature_mappings:
            db_mapping = FeatureMappingDb(
                java_feature=ai_mapping.java_feature,
                bedrock_equivalent=ai_mapping.bedrock_equivalent,
                mapping_type=ai_mapping.mapping_type,
                confidence_score=ai_mapping.confidence_score
                # comparison_id will be set by the relationship
            )
            db_comparison_result.feature_mappings.append(db_mapping)

    try:
        session.add(db_comparison_result)
        await session.commit()
        await session.refresh(db_comparison_result)
        # Refresh related feature_mappings if their IDs are needed immediately, though often not.
        # for fm in db_comparison_result.feature_mappings:
        # await session.refresh(fm)
    except Exception as e:
        await session.rollback()
        # Log the exception e here
        # logger.error(f"Database error during comparison creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return ComparisonResponse(
        message="Comparison successfully created",
        comparison_id=str(db_comparison_result.id)
    )

class FeatureMappingResponse(BaseModel):
    id: str
    java_feature: str | None
    bedrock_equivalent: str | None
    mapping_type: str | None
    confidence_score: float | None

class ComparisonResultResponse(BaseModel):
    id: str
    conversion_id: str
    structural_diff: Dict[str, Any] | None
    code_diff: Dict[str, Any] | None
    asset_diff: Dict[str, Any] | None
    assumptions_applied: Dict[str, Any] | None
    confidence_scores: Dict[str, Any] | None
    created_at: str | None
    feature_mappings: List[FeatureMappingResponse]

@router.get("/{comparison_id_str}", response_model=ComparisonResultResponse)
async def get_comparison_result(
    comparison_id_str: str,
    session: AsyncSession = Depends(get_db)
) -> ComparisonResultResponse:
    try:
        comparison_uuid = uuid.UUID(comparison_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comparison_id format. Must be a UUID.")

    stmt = (
        select(ComparisonResultDb)
        .where(ComparisonResultDb.id == comparison_uuid)
        .options(selectinload(ComparisonResultDb.feature_mappings))
    )
    result = await session.execute(stmt)
    db_comparison = result.scalar_one_or_none()

    if db_comparison is None:
        raise HTTPException(status_code=404, detail="Comparison not found")

    feature_mappings_list = []
    if db_comparison.feature_mappings:
        for fm_db in db_comparison.feature_mappings:
            feature_mappings_list.append(FeatureMappingResponse(
                id=str(fm_db.id),
                java_feature=fm_db.java_feature,
                bedrock_equivalent=fm_db.bedrock_equivalent,
                mapping_type=fm_db.mapping_type,
                confidence_score=float(fm_db.confidence_score) if fm_db.confidence_score is not None else None
            ))

    return ComparisonResultResponse(
        id=str(db_comparison.id),
        conversion_id=str(db_comparison.conversion_id),
        structural_diff=db_comparison.structural_diff,
        code_diff=db_comparison.code_diff,
        asset_diff=db_comparison.asset_diff,
        assumptions_applied=db_comparison.assumptions_applied,
        confidence_scores=db_comparison.confidence_scores,
        created_at=db_comparison.created_at.isoformat() if db_comparison.created_at else None,
        feature_mappings=feature_mappings_list
    )
