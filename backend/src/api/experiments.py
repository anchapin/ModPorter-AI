"""
A/B Testing API endpoints for managing experiments and variants.
"""

import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from db.base import get_db
from db import crud

# Configure logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()


class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    traffic_allocation: Optional[int] = 100  # Percentage (0-100)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None  # draft, active, paused, completed
    traffic_allocation: Optional[int] = None  # Percentage (0-100)


class ExperimentVariantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_control: Optional[bool] = False
    strategy_config: Optional[Dict[str, Any]] = None


class ExperimentVariantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_control: Optional[bool] = None
    strategy_config: Optional[Dict[str, Any]] = None


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str
    traffic_allocation: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ExperimentVariantResponse(BaseModel):
    id: str
    experiment_id: str
    name: str
    description: Optional[str] = None
    is_control: bool
    strategy_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ExperimentResultCreate(BaseModel):
    variant_id: str
    session_id: str
    kpi_quality: Optional[float] = None
    kpi_speed: Optional[int] = None  # milliseconds
    kpi_cost: Optional[float] = None
    user_feedback_score: Optional[float] = None
    user_feedback_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExperimentResultResponse(BaseModel):
    id: str
    variant_id: str
    session_id: str
    kpi_quality: Optional[float] = None
    kpi_speed: Optional[int] = None
    kpi_cost: Optional[float] = None
    user_feedback_score: Optional[float] = None
    user_feedback_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    experiment: ExperimentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new A/B testing experiment."""
    logger.info(f"Creating new experiment: {experiment.name}")
    
    # Validate traffic allocation
    if experiment.traffic_allocation is not None:
        if experiment.traffic_allocation < 0 or experiment.traffic_allocation > 100:
            raise HTTPException(
                status_code=400,
                detail="Traffic allocation must be between 0 and 100"
            )
    
    try:
        db_experiment = await crud.create_experiment(
            db,
            name=experiment.name,
            description=experiment.description,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            traffic_allocation=experiment.traffic_allocation or 100
        )
        
        return ExperimentResponse(
            id=str(db_experiment.id),
            name=db_experiment.name,
            description=db_experiment.description,
            start_date=db_experiment.start_date,
            end_date=db_experiment.end_date,
            status=db_experiment.status,
            traffic_allocation=db_experiment.traffic_allocation,
            created_at=db_experiment.created_at,
            updated_at=db_experiment.updated_at
        )
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating experiment"
        )


@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[str] = Query(None, description="Filter by status (draft, active, paused, completed)"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all A/B testing experiments."""
    logger.info(f"Listing experiments: status={status}, skip={skip}, limit={limit}")
    
    # Validate parameters
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be non-negative")
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    
    try:
        experiments = await crud.list_experiments(db, status=status, skip=skip, limit=limit)
        
        return [
            ExperimentResponse(
                id=str(exp.id),
                name=exp.name,
                description=exp.description,
                start_date=exp.start_date,
                end_date=exp.end_date,
                status=exp.status,
                traffic_allocation=exp.traffic_allocation,
                created_at=exp.created_at,
                updated_at=exp.updated_at
            )
            for exp in experiments
        ]
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error listing experiments"
        )


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific A/B testing experiment."""
    logger.info(f"Getting experiment: {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    
    try:
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        return ExperimentResponse(
            id=str(db_experiment.id),
            name=db_experiment.name,
            description=db_experiment.description,
            start_date=db_experiment.start_date,
            end_date=db_experiment.end_date,
            status=db_experiment.status,
            traffic_allocation=db_experiment.traffic_allocation,
            created_at=db_experiment.created_at,
            updated_at=db_experiment.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error getting experiment"
        )


@router.put("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str,
    experiment: ExperimentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an A/B testing experiment."""
    logger.info(f"Updating experiment: {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    
    # Validate status if provided
    if experiment.status:
        valid_statuses = ['draft', 'active', 'paused', 'completed']
        if experiment.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
    
    # Validate traffic allocation if provided
    if experiment.traffic_allocation is not None:
        if experiment.traffic_allocation < 0 or experiment.traffic_allocation > 100:
            raise HTTPException(
                status_code=400,
                detail="Traffic allocation must be between 0 and 100"
            )
    
    try:
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        updated_experiment = await crud.update_experiment(
            db,
            experiment_uuid,
            name=experiment.name,
            description=experiment.description,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            status=experiment.status,
            traffic_allocation=experiment.traffic_allocation
        )
        
        return ExperimentResponse(
            id=str(updated_experiment.id),
            name=updated_experiment.name,
            description=updated_experiment.description,
            start_date=updated_experiment.start_date,
            end_date=updated_experiment.end_date,
            status=updated_experiment.status,
            traffic_allocation=updated_experiment.traffic_allocation,
            created_at=updated_experiment.created_at,
            updated_at=updated_experiment.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error updating experiment"
        )


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an A/B testing experiment."""
    logger.info(f"Deleting experiment: {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    
    try:
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        await crud.delete_experiment(db, experiment_uuid)
        
        return {"message": "Experiment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error deleting experiment"
        )


@router.post("/experiments/{experiment_id}/variants", response_model=ExperimentVariantResponse)
async def create_experiment_variant(
    experiment_id: str,
    variant: ExperimentVariantCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new variant for an A/B testing experiment."""
    logger.info(f"Creating variant for experiment {experiment_id}: {variant.name}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    
    try:
        # Check if experiment exists
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        db_variant = await crud.create_experiment_variant(
            db,
            experiment_id=experiment_uuid,
            name=variant.name,
            description=variant.description,
            is_control=variant.is_control or False,
            strategy_config=variant.strategy_config
        )
        
        return ExperimentVariantResponse(
            id=str(db_variant.id),
            experiment_id=str(db_variant.experiment_id),
            name=db_variant.name,
            description=db_variant.description,
            is_control=db_variant.is_control,
            strategy_config=db_variant.strategy_config,
            created_at=db_variant.created_at,
            updated_at=db_variant.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating variant for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating experiment variant"
        )


@router.get("/experiments/{experiment_id}/variants", response_model=List[ExperimentVariantResponse])
async def list_experiment_variants(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all variants for an A/B testing experiment."""
    logger.info(f"Listing variants for experiment: {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    
    try:
        # Check if experiment exists
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        variants = await crud.list_experiment_variants(db, experiment_uuid)
        
        return [
            ExperimentVariantResponse(
                id=str(variant.id),
                experiment_id=str(variant.experiment_id),
                name=variant.name,
                description=variant.description,
                is_control=variant.is_control,
                strategy_config=variant.strategy_config,
                created_at=variant.created_at,
                updated_at=variant.updated_at
            )
            for variant in variants
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing variants for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error listing experiment variants"
        )


@router.get("/experiments/{experiment_id}/variants/{variant_id}", response_model=ExperimentVariantResponse)
async def get_experiment_variant(
    experiment_id: str,
    variant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific variant in an A/B testing experiment."""
    logger.info(f"Getting variant {variant_id} for experiment {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
        variant_uuid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    try:
        # Check if experiment exists
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        db_variant = await crud.get_experiment_variant(db, variant_uuid)
        if not db_variant:
            raise HTTPException(status_code=404, detail="Variant not found")
            
        # Verify the variant belongs to the experiment
        if db_variant.experiment_id != experiment_uuid:
            raise HTTPException(status_code=404, detail="Variant not found in this experiment")
            
        return ExperimentVariantResponse(
            id=str(db_variant.id),
            experiment_id=str(db_variant.experiment_id),
            name=db_variant.name,
            description=db_variant.description,
            is_control=db_variant.is_control,
            strategy_config=db_variant.strategy_config,
            created_at=db_variant.created_at,
            updated_at=db_variant.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting variant {variant_id} for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error getting experiment variant"
        )


@router.put("/experiments/{experiment_id}/variants/{variant_id}", response_model=ExperimentVariantResponse)
async def update_experiment_variant(
    experiment_id: str,
    variant_id: str,
    variant: ExperimentVariantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a variant in an A/B testing experiment."""
    logger.info(f"Updating variant {variant_id} for experiment {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
        variant_uuid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    try:
        # Check if experiment exists
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        db_variant = await crud.get_experiment_variant(db, variant_uuid)
        if not db_variant:
            raise HTTPException(status_code=404, detail="Variant not found")
            
        # Verify the variant belongs to the experiment
        if db_variant.experiment_id != experiment_uuid:
            raise HTTPException(status_code=404, detail="Variant not found in this experiment")
            
        updated_variant = await crud.update_experiment_variant(
            db,
            variant_uuid,
            name=variant.name,
            description=variant.description,
            is_control=variant.is_control,
            strategy_config=variant.strategy_config
        )
        
        return ExperimentVariantResponse(
            id=str(updated_variant.id),
            experiment_id=str(updated_variant.experiment_id),
            name=updated_variant.name,
            description=updated_variant.description,
            is_control=updated_variant.is_control,
            strategy_config=updated_variant.strategy_config,
            created_at=updated_variant.created_at,
            updated_at=updated_variant.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating variant {variant_id} for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error updating experiment variant"
        )


@router.delete("/experiments/{experiment_id}/variants/{variant_id}")
async def delete_experiment_variant(
    experiment_id: str,
    variant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a variant from an A/B testing experiment."""
    logger.info(f"Deleting variant {variant_id} from experiment {experiment_id}")
    
    try:
        experiment_uuid = uuid.UUID(experiment_id)
        variant_uuid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    try:
        # Check if experiment exists
        db_experiment = await crud.get_experiment(db, experiment_uuid)
        if not db_experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
            
        db_variant = await crud.get_experiment_variant(db, variant_uuid)
        if not db_variant:
            raise HTTPException(status_code=404, detail="Variant not found")
            
        # Verify the variant belongs to the experiment
        if db_variant.experiment_id != experiment_uuid:
            raise HTTPException(status_code=404, detail="Variant not found in this experiment")
            
        await crud.delete_experiment_variant(db, variant_uuid)
        
        return {"message": "Variant deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting variant {variant_id} from experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error deleting experiment variant"
        )


@router.post("/experiment_results", response_model=ExperimentResultResponse)
async def create_experiment_result(
    result: ExperimentResultCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record results from an A/B testing experiment."""
    logger.info(f"Recording experiment result for variant {result.variant_id}")
    
    try:
        variant_uuid = uuid.UUID(result.variant_id)
        session_uuid = uuid.UUID(result.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Validate KPI values
    if result.kpi_quality is not None and (result.kpi_quality < 0 or result.kpi_quality > 100):
        raise HTTPException(status_code=400, detail="kpi_quality must be between 0 and 100")
    
    if result.user_feedback_score is not None and (result.user_feedback_score < 1 or result.user_feedback_score > 5):
        raise HTTPException(status_code=400, detail="user_feedback_score must be between 1 and 5")
    
    try:
        # Check if variant exists
        db_variant = await crud.get_experiment_variant(db, variant_uuid)
        if not db_variant:
            raise HTTPException(status_code=404, detail="Variant not found")
            
        db_result = await crud.create_experiment_result(
            db,
            variant_id=variant_uuid,
            session_id=session_uuid,
            kpi_quality=result.kpi_quality,
            kpi_speed=result.kpi_speed,
            kpi_cost=result.kpi_cost,
            user_feedback_score=result.user_feedback_score,
            user_feedback_text=result.user_feedback_text,
            metadata=result.metadata
        )
        
        return ExperimentResultResponse(
            id=str(db_result.id),
            variant_id=str(db_result.variant_id),
            session_id=str(db_result.session_id),
            kpi_quality=db_result.kpi_quality,
            kpi_speed=db_result.kpi_speed,
            kpi_cost=db_result.kpi_cost,
            user_feedback_score=db_result.user_feedback_score,
            user_feedback_text=db_result.user_feedback_text,
            metadata=db_result.metadata,
            created_at=db_result.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording experiment result: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error recording experiment result"
        )


@router.get("/experiment_results", response_model=List[ExperimentResultResponse])
async def list_experiment_results(
    variant_id: Optional[str] = Query(None, description="Filter by variant ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List experiment results."""
    logger.info(f"Listing experiment results: variant_id={variant_id}, session_id={session_id}, skip={skip}, limit={limit}")
    
    # Validate parameters
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be non-negative")
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    
    try:
        variant_uuid = uuid.UUID(variant_id) if variant_id else None
        session_uuid = uuid.UUID(session_id) if session_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    try:
        results = await crud.list_experiment_results(
            db,
            variant_id=variant_uuid,
            session_id=session_uuid,
            skip=skip,
            limit=limit
        )
        
        return [
            ExperimentResultResponse(
                id=str(result.id),
                variant_id=str(result.variant_id),
                session_id=str(result.session_id),
                kpi_quality=result.kpi_quality,
                kpi_speed=result.kpi_speed,
                kpi_cost=result.kpi_cost,
                user_feedback_score=result.user_feedback_score,
                user_feedback_text=result.user_feedback_text,
                metadata=result.metadata,
                created_at=result.created_at
            )
            for result in results
        ]
    except Exception as e:
        logger.error(f"Error listing experiment results: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error listing experiment results"
        )