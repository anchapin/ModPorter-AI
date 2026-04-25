# ai-engine/models/__init__.py
from .comparison import ComparisonResult, FeatureMapping
from .smart_assumptions import (
    AppliedAssumptionReportItem,
    AssumptionImpact,
    AssumptionReport,
    AssumptionResult,
    ConversionPlan,
    ConversionPlanComponent,
    FeatureContext,
    SmartAssumption,
    SmartAssumptionEngine,
)
from .validation import (
    AssetValidationResult,
    BehaviorPredictionResult,
    ManifestValidationResult,
    SemanticAnalysisResult,
    ValidationReport,
)

__all__ = [
    "SmartAssumption",
    "SmartAssumptionEngine",
    "FeatureContext",
    "AssumptionResult",
    "ConversionPlanComponent",
    "ConversionPlan",
    "AssumptionReport",
    "AppliedAssumptionReportItem",
    "AssumptionImpact",
    "ComparisonResult",
    "FeatureMapping",
    "SemanticAnalysisResult",
    "BehaviorPredictionResult",
    "AssetValidationResult",
    "ManifestValidationResult",
    "ValidationReport",
]
