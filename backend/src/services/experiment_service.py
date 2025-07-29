"""
Service for managing A/B testing experiments and traffic allocation.
"""

import random
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from db import crud, models


class ExperimentService:
    """Service for managing A/B testing experiments."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_active_experiments(self) -> List[models.Experiment]:
        """Get all active experiments."""
        return await crud.list_experiments(self.db, status="active")
    
    async def get_experiment_variants(self, experiment_id: uuid.UUID) -> List[models.ExperimentVariant]:
        """Get all variants for an experiment."""
        return await crud.list_experiment_variants(self.db, experiment_id)
    
    async def allocate_variant(self, experiment_id: uuid.UUID) -> Optional[models.ExperimentVariant]:
        """
        Allocate a variant for the given experiment based on traffic allocation settings.
        
        Returns the allocated variant, or None if no variant could be allocated.
        """
        # Get the experiment
        experiment = await crud.get_experiment(self.db, experiment_id)
        if not experiment or experiment.status != "active":
            return None
        
        # Get all variants for this experiment
        variants = await self.get_experiment_variants(experiment_id)
        if not variants:
            return None
        
        # Check if we should allocate to this experiment based on traffic allocation
        if random.randint(1, 100) > experiment.traffic_allocation:
            return None
        
        # Allocate to a variant based on equal distribution
        # In a more advanced implementation, we could implement weighted distribution
        return random.choice(variants)
    
    async def get_control_variant(self, experiment_id: uuid.UUID) -> Optional[models.ExperimentVariant]:
        """Get the control variant for an experiment."""
        variants = await self.get_experiment_variants(experiment_id)
        for variant in variants:
            if variant.is_control:
                return variant
        return None
    
    async def record_experiment_result(
        self,
        variant_id: uuid.UUID,
        session_id: uuid.UUID,
        kpi_quality: Optional[float] = None,
        kpi_speed: Optional[int] = None,
        kpi_cost: Optional[float] = None,
        user_feedback_score: Optional[float] = None,
        user_feedback_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> models.ExperimentResult:
        """Record results for an experiment variant."""
        return await crud.create_experiment_result(
            self.db,
            variant_id=variant_id,
            session_id=session_id,
            kpi_quality=kpi_quality,
            kpi_speed=kpi_speed,
            kpi_cost=kpi_cost,
            user_feedback_score=user_feedback_score,
            user_feedback_text=user_feedback_text,
            metadata=metadata,
        )