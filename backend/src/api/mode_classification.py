"""
Mode Classification API Endpoints for v2.5 Milestone

Provides REST endpoints for:
- POST /api/v1/classify - Classify a mod's conversion mode
- GET /api/v1/classify/{classification_id} - Get classification result
- GET /api/v1/classify/modes - Get available modes
- GET /api/v1/classify/pipeline/{mode} - Get pipeline config for mode

See: docs/GAP-ANALYSIS-v2.5.md
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse

from src.models.conversion_mode import (
    ConversionMode,
    ModeClassificationRequest,
    ModeClassificationResponse,
    ModeSpecificPipelineConfig,
    ConversionSettings,
)
from src.services.mode_classifier import ModeClassifier, get_mode_classifier


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/classify", tags=["mode-classification"])


@router.post(
    "",
    response_model=ModeClassificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Classify mod conversion mode",
    description="Automatically classify a mod's conversion complexity and return recommended settings.",
)
async def classify_mod(
    file: UploadFile = File(..., description="Mod JAR/ZIP file to classify"),
    mode_classifier: ModeClassifier = Depends(get_mode_classifier),
) -> ModeClassificationResponse:
    """
    Classify a mod's conversion mode.

    Analyzes the uploaded mod file and returns:
    - The conversion mode (Simple/Standard/Complex/Expert)
    - Confidence score
    - Extracted features
    - Recommended settings
    - Estimated automation level
    """
    try:
        # Read file content
        content = await file.read()

        # Create classification request
        request = ModeClassificationRequest(
            file_content=content,
        )

        # Run classification
        result = await mode_classifier.classify(request)

        # Get recommended settings
        settings = mode_classifier.get_recommended_settings(result.mode)

        # Build response
        warnings = [f.description for f in result.features.complex_features]

        return ModeClassificationResponse(
            mode=result.mode,
            confidence=result.confidence,
            features=result.features,
            alternative_modes=result.alternative_modes,
            convertible_percentage=result.convertible_percentage,
            estimated_time_seconds=result.estimated_time_seconds,
            automation_level=result.automation_level,
            recommended_settings=settings,
            warnings=warnings,
        )

    except ValueError as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid request parameters: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during classification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed unexpectedly",
        )


@router.post(
    "/features",
    response_model=ModeClassificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Classify from pre-extracted features",
    description="Classify using already-extracted mod features.",
)
async def classify_from_features(
    features: ModeClassificationRequest,
    mode_classifier: ModeClassifier = Depends(get_mode_classifier),
) -> ModeClassificationResponse:
    """
    Classify a mod using pre-extracted features.

    Use this endpoint when features have already been extracted
    from the mod file.
    """
    try:
        if not features.features:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="features field is required"
            )

        # Run classification
        result = await mode_classifier.classify(features)

        # Get recommended settings
        settings = mode_classifier.get_recommended_settings(result.mode)

        # Build warnings
        warnings = [f.description for f in result.features.complex_features]

        return ModeClassificationResponse(
            mode=result.mode,
            confidence=result.confidence,
            features=result.features,
            alternative_modes=result.alternative_modes,
            convertible_percentage=result.convertible_percentage,
            estimated_time_seconds=result.estimated_time_seconds,
            automation_level=result.automation_level,
            recommended_settings=settings,
            warnings=warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying from features: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed unexpectedly",
        )


@router.get(
    "/modes",
    response_model=list[dict],
    summary="Get available conversion modes",
    description="Returns all available conversion modes with their characteristics.",
)
async def get_modes() -> JSONResponse:
    """
    Get list of all available conversion modes.

    Returns mode details including:
    - Name and description
    - Automation level
    - Typical use cases
    """
    modes = [
        {
            "mode": ConversionMode.SIMPLE.value,
            "name": "Simple",
            "description": "Basic mods with 1-5 classes and minimal dependencies",
            "automation_level": 99,
            "typical_classes": "1-5",
            "typical_dependencies": "0-2",
            "features": ["items", "blocks", "basic recipes"],
            "requires_human_review": False,
        },
        {
            "mode": ConversionMode.STANDARD.value,
            "name": "Standard",
            "description": "Moderate mods with 5-20 classes including entities and recipes",
            "automation_level": 95,
            "typical_classes": "5-20",
            "typical_dependencies": "2-5",
            "features": ["items", "blocks", "entities", "recipes", "GUI"],
            "requires_human_review": False,
        },
        {
            "mode": ConversionMode.COMPLEX.value,
            "name": "Complex",
            "description": "Complex mods with 20-50 classes including multiblock structures",
            "automation_level": 85,
            "typical_classes": "20-50",
            "typical_dependencies": "5-10",
            "features": ["multiblock", "machines", "custom AI", "advanced entities"],
            "requires_human_review": True,
        },
        {
            "mode": ConversionMode.EXPERT.value,
            "name": "Expert",
            "description": "Expert-level mods with 50+ classes including dimensions and world generation",
            "automation_level": 70,
            "typical_classes": "50+",
            "typical_dependencies": "10+",
            "features": ["dimensions", "worldgen", "custom biomes", "network packets", "ASM"],
            "requires_human_review": True,
        },
    ]

    return JSONResponse(content=modes)


@router.get(
    "/pipeline/{mode}",
    response_model=ModeSpecificPipelineConfig,
    summary="Get pipeline configuration for mode",
    description="Returns the conversion pipeline configuration for a specific mode.",
)
async def get_pipeline(
    mode: ConversionMode,
    mode_classifier: ModeClassifier = Depends(get_mode_classifier),
) -> ModeSpecificPipelineConfig:
    """
    Get the conversion pipeline configuration for a specific mode.

    Returns:
    - Pipeline name
    - Processing steps
    - Estimated success rate
    - Special requirements
    """
    config = mode_classifier.get_pipeline_config(mode)
    return config


@router.get(
    "/settings/{mode}",
    response_model=ConversionSettings,
    summary="Get recommended settings for mode",
    description="Returns the recommended conversion settings for a specific mode.",
)
async def get_settings(
    mode: ConversionMode,
    mode_classifier: ModeClassifier = Depends(get_mode_classifier),
) -> ConversionSettings:
    """
    Get recommended conversion settings for a specific mode.

    Returns settings including:
    - Detail level
    - Validation level
    - Auto-fix behavior
    - Timeout settings
    - Quality threshold
    """
    return mode_classifier.get_recommended_settings(mode)
