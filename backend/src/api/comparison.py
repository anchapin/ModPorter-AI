from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict, List
import uuid

# Attempt to import AI Engine components.
# This assumes 'ai-engine' is structured in a way that it can be imported,
# or that PYTHONPATH is set up accordingly in the execution environment.
# If direct import fails, this subtask will report an error.
try:
    from ai_engine.src.engines.comparison_engine import ComparisonEngine
    from ai_engine.src.models.comparison import ComparisonResult as AIComparisonResult, FeatureMapping as AIFeatureMapping
except ImportError as e:
    # Fallback for environments where ai_engine might not be directly in PYTHONPATH
    # This is a common issue in complex project structures.
    # A more robust solution involves proper packaging or path manipulation at runtime.
    import sys
    import os
    # Assuming backend/src/api/comparison.py and ai-engine/ are siblings in the project root
    # backend/src/api/comparison.py -> backend/src/api -> backend/src -> backend -> project_root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    ai_engine_module_path = os.path.join(project_root) # Add project root so ai_engine.src works
    if ai_engine_module_path not in sys.path:
        sys.path.insert(0, ai_engine_module_path)

    from ai_engine.src.engines.comparison_engine import ComparisonEngine
    from ai_engine.src.models.comparison import ComparisonResult as AIComparisonResult, FeatureMapping as AIFeatureMapping


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload


# Adjust these imports based on your actual database setup location
# from src.db.declarative_base import Base # Base is not directly used here, models are
from src.db.models import ComparisonResultDb, FeatureMappingDb, ConversionJob # ConversionJob for FK check
from src.db.base import get_async_session # Assuming this provides AsyncSession

router = APIRouter()

@router.post("/comparison/", status_code=201) # Changed to 201 for resource creation
async def create_comparison_request(
    conversion_id_str: str, # Renamed to avoid clash if it's a path param elsewhere, and to indicate it's a string
    java_mod_path: str,
    bedrock_addon_path: str,
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:

    engine = ComparisonEngine()
    try:
        # Validate conversion_id_str as UUID and check if ConversionJob exists
        try:
            conversion_uuid = uuid.UUID(conversion_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid conversion_id format: '{conversion_id_str}'. Must be a UUID.")

        conversion_job = await session.get(ConversionJob, conversion_uuid)
        if not conversion_job:
            raise HTTPException(status_code=404, detail=f"ConversionJob with id {conversion_id_str} not found.")

        # AI Engine's compare method expects a string conversion_id
        ai_result: AIComparisonResult = engine.compare(
            java_mod_path=java_mod_path,
            bedrock_addon_path=bedrock_addon_path,
            conversion_id=conversion_id_str
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

    return {"message": "Comparison successfully created", "comparison_id": str(db_comparison_result.id)}

@router.get("/comparison/{comparison_id_str}", response_model=Dict[str, Any]) # Consider creating a Pydantic response_model
async def get_comparison_result(
    comparison_id_str: str,
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
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
            feature_mappings_list.append({
                "id": str(fm_db.id),
                "java_feature": fm_db.java_feature,
                "bedrock_equivalent": fm_db.bedrock_equivalent,
                "mapping_type": fm_db.mapping_type,
                "confidence_score": float(fm_db.confidence_score) if fm_db.confidence_score is not None else None,
            })

    response_data = {
        "id": str(db_comparison.id),
        "conversion_id": str(db_comparison.conversion_id),
        "structural_diff": db_comparison.structural_diff,
        "code_diff": db_comparison.code_diff,
        "asset_diff": db_comparison.asset_diff,
        "assumptions_applied": db_comparison.assumptions_applied,
        "confidence_scores": db_comparison.confidence_scores,
        "created_at": db_comparison.created_at.isoformat() if db_comparison.created_at else None,
        "feature_mappings": feature_mappings_list
    }
    return response_data
