# ai-engine/src/models/validation.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SemanticAnalysisResult(BaseModel):
    intent_preserved: bool = Field(..., description="Whether the code's intent is preserved.")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score for semantic analysis.")
    findings: List[str] = Field(default_factory=list, description="Specific findings or issues.")

class BehaviorPredictionResult(BaseModel):
    behavior_diff: str = Field(..., description="Description of predicted behavior differences.")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score for behavior prediction.")
    potential_issues: List[str] = Field(default_factory=list, description="Potential runtime issues identified.")

class AssetValidationResult(BaseModel):
    all_assets_valid: bool = Field(..., description="Whether all assets are valid.")
    corrupted_files: List[str] = Field(default_factory=list, description="List of corrupted or invalid asset files.")
    asset_specific_issues: Dict[str, List[str]] = Field(default_factory=dict, description="Issues specific to certain assets.")

class ManifestValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether the manifest is valid.")
    errors: List[str] = Field(default_factory=list, description="Specific errors found in the manifest.")
    warnings: List[str] = Field(default_factory=list, description="Warnings related to the manifest.")

class ValidationReport(BaseModel):
    conversion_id: str = Field(..., description="ID of the conversion being validated.")
    semantic_analysis: SemanticAnalysisResult
    behavior_prediction: BehaviorPredictionResult
    asset_integrity: AssetValidationResult
    manifest_validation: ManifestValidationResult
    overall_confidence: float = Field(..., ge=0, le=1, description="Overall confidence score for the conversion quality.")
    recommendations: List[str] = Field(default_factory=list, description="Suggestions for improvement or manual adjustments.")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Optional raw data or logs from validation tools.")

# Example Usage (can be removed or kept for testing)
if __name__ == '__main__':
    sample_report = ValidationReport(
        conversion_id="conv_12345",
        semantic_analysis=SemanticAnalysisResult(intent_preserved=True, confidence=0.9, findings=["Minor stylistic differences noted."]),
        behavior_prediction=BehaviorPredictionResult(behavior_diff="No significant differences predicted.", confidence=0.85),
        asset_integrity=AssetValidationResult(all_assets_valid=False, corrupted_files=["texture.png"], asset_specific_issues={"texture.png": ["Invalid format"]}),
        manifest_validation=ManifestValidationResult(is_valid=True, warnings=["Deprecated field used."]),
        overall_confidence=0.87,
        recommendations=["Review texture.png format.", "Consider updating manifest schema."]
    )
    print("Sample Validation Report:")
    print(sample_report.model_dump_json(indent=2))
