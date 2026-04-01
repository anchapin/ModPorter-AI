"""
One-Click Converter for v2.5 Milestone

Implements a streamlined one-click conversion workflow using the Pipeline pattern:
Upload → Classify → Apply Defaults → Ready

This service provides a simplified interface for users who want to convert
a mod with minimal configuration.

See: docs/GAP-ANALYSIS-v2.5.md

Pattern: Pipeline + Supervisor
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from src.models.conversion_mode import (
    ConversionMode,
    ConversionSettings,
    ModFeatures,
    ModeClassificationRequest,
)
from src.services.mode_classifier import get_mode_classifier
from src.services.smart_defaults import get_smart_defaults_engine, SmartDefaultsResult
from src.services.user_preferences import get_user_preferences_service


logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Stages
# =============================================================================

class PipelineStage(str, Enum):
    """One-click converter pipeline stages."""
    
    UPLOAD = "upload"
    CLASSIFY = "classify"
    APPLY_DEFAULTS = "apply_defaults"
    READY = "ready"
    ERROR = "error"


class PipelineStatus(BaseModel):
    """Status of the one-click conversion pipeline."""
    
    pipeline_id: str
    current_stage: PipelineStage
    completed_stages: List[PipelineStage] = Field(default_factory=list)
    mode: Optional[ConversionMode] = None
    settings: Optional[ConversionSettings] = None
    features: Optional[ModFeatures] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        return self.current_stage == PipelineStage.READY
    
    @property
    def is_error(self) -> bool:
        return self.current_stage == PipelineStage.ERROR
    
    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()


# =============================================================================
# Request/Response Models
# =============================================================================

class OneClickConvertRequest(BaseModel):
    """Request for one-click conversion."""
    
    file_path: Optional[str] = None
    file_content: Optional[bytes] = None
    user_id: Optional[str] = None
    auto_start: bool = False  # If True, immediately start conversion after ready


class OneClickConvertResponse(BaseModel):
    """Response from one-click conversion request."""
    
    pipeline_id: str
    status: PipelineStatus
    recommended_settings: ConversionSettings
    confidence: float = Field(ge=0.0, le=1.0)
    personalization_source: Optional[str] = None
    
    
class ReadyToConvert(BaseModel):
    """Result when pipeline is complete and ready to convert."""
    
    pipeline_id: str
    mode: ConversionMode
    settings: ConversionSettings
    features: ModFeatures
    estimated_duration_seconds: int
    automation_level: int
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# Pipeline Supervisor
# =============================================================================

class OneClickPipelineSupervisor:
    """
    Supervisor for the One-Click Converter Pipeline.
    
    Coordinates the pipeline stages and validates outputs.
    Implements the Supervisor pattern for quality control.
    """
    
    def __init__(self):
        self.mode_classifier = get_mode_classifier()
        self.smart_defaults = get_smart_defaults_engine()
        self.user_prefs = get_user_preferences_service()
    
    async def execute(self, request: OneClickConvertRequest) -> PipelineStatus:
        """
        Execute the full one-click conversion pipeline.
        
        Pipeline stages:
        1. UPLOAD - Receive and validate uploaded file
        2. CLASSIFY - Auto-detect mode from uploaded file
        3. APPLY_DEFAULTS - Apply smart defaults based on mode and user history
        4. READY - Return configured conversion ready to start
        """
        pipeline_id = str(uuid.uuid4())
        status = PipelineStatus(
            pipeline_id=pipeline_id,
            current_stage=PipelineStage.UPLOAD,
        )
        
        logger.info(f"Starting one-click pipeline {pipeline_id}")
        
        try:
            # Stage 1: Upload
            status = await self._stage_upload(request, status)
            
            # Stage 2: Classify
            status = await self._stage_classify(request, status)
            
            # Stage 3: Apply Defaults
            status = await self._stage_apply_defaults(request, status)
            
            # Stage 4: Ready
            status = self._stage_ready(status)
            
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} error: {e}")
            status.current_stage = PipelineStage.ERROR
            status.errors.append(str(e))
        
        return status
    
    async def _stage_upload(
        self,
        request: OneClickConvertRequest,
        status: PipelineStatus,
    ) -> PipelineStatus:
        """Stage 1: Upload - Receive and validate uploaded file."""
        logger.info(f"Pipeline {status.pipeline_id}: Stage UPLOAD")
        
        if not request.file_path and not request.file_content:
            raise ValueError("Must provide file_path or file_content")
        
        # If file_path provided, read content
        if request.file_path:
            try:
                with open(request.file_path, 'rb') as f:
                    request.file_content = f.read()
            except Exception as e:
                raise ValueError(f"Failed to read file: {e}")
        
        status.completed_stages.append(PipelineStage.UPLOAD)
        status.current_stage = PipelineStage.CLASSIFY
        
        return status
    
    async def _stage_classify(
        self,
        request: OneClickConvertRequest,
        status: PipelineStatus,
    ) -> PipelineStatus:
        """Stage 2: Classify - Auto-detect mode from uploaded file."""
        logger.info(f"Pipeline {status.pipeline_id}: Stage CLASSIFY")
        
        if not request.file_content:
            raise ValueError("No file content available for classification")
        
        # Create classification request
        classify_request = ModeClassificationRequest(
            file_content=request.file_content,
            user_id=request.user_id,
        )
        
        # Run classification
        classification_result = await self.mode_classifier.classify(classify_request)
        
        status.mode = classification_result.mode
        status.features = classification_result.features
        status.completed_stages.append(PipelineStage.CLASSIFY)
        status.current_stage = PipelineStage.APPLY_DEFAULTS
        
        # Add any classification warnings
        status.warnings.extend([
            f"Mode detected: {classification_result.mode.value}",
            f"Confidence: {classification_result.confidence:.0%}",
            f"Automation level: {classification_result.automation_level}%",
        ])
        
        if classification_result.alternative_modes:
            status.warnings.append(
                f"Alternative modes: {[m.mode.value for m in classification_result.alternative_modes]}"
            )
        
        return status
    
    async def _stage_apply_defaults(
        self,
        request: OneClickConvertRequest,
        status: PipelineStatus,
    ) -> PipelineStatus:
        """Stage 3: Apply Defaults - Apply smart defaults based on mode and user."""
        logger.info(f"Pipeline {status.pipeline_id}: Stage APPLY_DEFAULTS")
        
        if not status.mode:
            raise ValueError("Mode not set - classification must complete first")
        
        # Get historical data for pattern matching
        historical_data = None
        if request.user_id:
            history = await self.user_prefs.get_conversion_history(request.user_id)
            if history:
                # Convert to HistoricalConversion format for smart defaults
                from src.services.smart_defaults import HistoricalConversion
                historical_data = [
                    HistoricalConversion(
                        conversion_id=h.conversion_id,
                        user_id=h.user_id,
                        mode=ConversionMode(h.mode),
                        features={},
                        settings_used=h.settings_used,
                        success=h.success,
                        duration_seconds=h.duration_seconds,
                    )
                    for h in history
                ]
        
        # Get smart defaults
        smart_result: SmartDefaultsResult = await self.smart_defaults.get_defaults(
            mode=status.mode,
            user_id=request.user_id,
            historical_data=historical_data,
            features=status.features,
        )
        
        status.settings = smart_result.settings
        status.completed_stages.append(PipelineStage.APPLY_DEFAULTS)
        status.current_stage = PipelineStage.READY
        
        # Add any warnings from smart defaults
        status.warnings.extend(smart_result.warnings)
        
        return status
    
    def _stage_ready(self, status: PipelineStatus) -> PipelineStatus:
        """Stage 4: Ready - Mark pipeline as ready."""
        logger.info(f"Pipeline {status.pipeline_id}: Stage READY")
        
        status.completed_stages.append(PipelineStage.READY)
        status.completed_at = datetime.utcnow()
        
        return status


# =============================================================================
# One-Click Converter Service
# =============================================================================

class OneClickConverter:
    """
    One-click conversion service implementing Pipeline + Supervisor pattern.
    
    Provides a streamlined interface for converting mods with minimal user input:
    - Upload mod file
    - Auto-detect conversion mode
    - Apply smart defaults
    - Return configured conversion ready to start
    """
    
    def __init__(self):
        self.supervisor = OneClickPipelineSupervisor()
        self._pipelines: Dict[str, PipelineStatus] = {}
    
    async def initiate(self, request: OneClickConvertRequest) -> OneClickConvertResponse:
        """
        Initiate a one-click conversion.
        
        This starts the pipeline and returns immediately with the pipeline status.
        The pipeline runs through all stages to produce recommended settings.
        
        Args:
            request: One-click conversion request
            
        Returns:
            OneClickConvertResponse with status and recommended settings
        """
        logger.info(f"Initiating one-click conversion for user {request.user_id}")
        
        # Execute pipeline
        status = await self.supervisor.execute(request)
        
        # Store pipeline status
        self._pipelines[status.pipeline_id] = status
        
        # Build response
        response = OneClickConvertResponse(
            pipeline_id=status.pipeline_id,
            status=status,
            recommended_settings=status.settings or ConversionSettings(
                mode=status.mode or ConversionMode.STANDARD
            ),
            confidence=0.8 if status.settings else 0.0,
        )
        
        # Add personalization source if available
        if request.user_id:
            prefs = await self.supervisor.user_prefs.get_preferences(request.user_id)
            if prefs and prefs.total_conversions > 0:
                response.personalization_source = f"learned_from_{prefs.total_conversions}_conversions"
        
        return response
    
    async def get_status(self, pipeline_id: str) -> Optional[PipelineStatus]:
        """Get the status of a pipeline."""
        return self._pipelines.get(pipeline_id)
    
    async def get_ready_conversion(self, pipeline_id: str) -> Optional[ReadyToConvert]:
        """
        Get a ready-to-convert object if the pipeline is complete.
        
        Returns None if the pipeline is not yet complete or has errored.
        """
        status = self._pipelines.get(pipeline_id)
        
        if not status:
            return None
        
        if not status.is_complete:
            return None
        
        if not status.mode or not status.settings or not status.features:
            return None
        
        # Estimate duration based on mode
        duration_estimates = {
            ConversionMode.SIMPLE: 60,
            ConversionMode.STANDARD: 180,
            ConversionMode.COMPLEX: 300,
            ConversionMode.EXPERT: 600,
        }
        
        return ReadyToConvert(
            pipeline_id=status.pipeline_id,
            mode=status.mode,
            settings=status.settings,
            features=status.features,
            estimated_duration_seconds=duration_estimates.get(status.mode, 180),
            automation_level={
                ConversionMode.SIMPLE: 99,
                ConversionMode.STANDARD: 95,
                ConversionMode.COMPLEX: 85,
                ConversionMode.EXPERT: 70,
            }.get(status.mode, 80),
            warnings=status.warnings,
        )
    
    async def learn_from_completion(
        self,
        pipeline_id: str,
        success: bool,
        duration_seconds: int,
    ) -> None:
        """
        Record the outcome of a conversion for learning.
        
        This should be called after a conversion completes to update
        user preferences and pattern library.
        """
        status = self._pipelines.get(pipeline_id)
        
        if not status:
            logger.warning(f"Unknown pipeline {pipeline_id} for learning")
            return
        
        if not status.settings:
            logger.warning(f"Pipeline {pipeline_id} has no settings to learn from")
            return
        
        # Learn from conversion if user_id available
        # We need to find the user_id from the original request
        # For now, just log the learning
        logger.info(
            f"Recording conversion outcome: pipeline={pipeline_id}, "
            f"success={success}, duration={duration_seconds}s"
        )
        
        # In a full implementation, we would also:
        # 1. Update user preferences service
        # 2. Update smart defaults pattern library


# =============================================================================
# Singleton Instance
# =============================================================================

_one_click_converter: Optional[OneClickConverter] = None


def get_one_click_converter() -> OneClickConverter:
    """Get singleton OneClickConverter instance."""
    global _one_click_converter
    if _one_click_converter is None:
        _one_click_converter = OneClickConverter()
    return _one_click_converter
