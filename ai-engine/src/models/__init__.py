# ai-engine/src/models/__init__.py
from .smart_assumptions import (
    SmartAssumption, 
    SmartAssumptionEngine, 
    FeatureContext, 
    AssumptionResult, 
    ConversionPlanComponent, 
    AssumptionReport,
    AssumptionImpact
)
from .comparison import ComparisonResult, FeatureMapping
from .validation import (
    SemanticAnalysisResult,
    BehaviorPredictionResult,
    AssetValidationResult,
    ManifestValidationResult,
    ValidationReport
)

__all__ = [
    "SmartAssumption",
    "SmartAssumptionEngine",
    "FeatureContext",
    "AssumptionResult",
    "ConversionPlanComponent",
    "AssumptionReport",
    "AssumptionImpact",
    "ComparisonResult",
    "FeatureMapping",
    "SemanticAnalysisResult",
    "BehaviorPredictionResult",
    "AssetValidationResult",
    "ManifestValidationResult",
    "ValidationReport"
]
