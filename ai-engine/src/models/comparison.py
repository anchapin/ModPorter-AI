from dataclasses import dataclass, field
from typing import List, Dict, Any
import uuid

@dataclass
class FeatureMapping:
    java_feature: str
    bedrock_equivalent: str
    mapping_type: str  # e.g., "DIRECT", "ASSUMED", "MANUAL"
    confidence_score: float
    assumption_applied: str = None # Identifier for the assumption, if any

@dataclass
class ComparisonResult:
    comparison_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversion_id: str # From the main conversion process
    structural_diff: Dict[str, List[str]] # e.g., {"files_added": [...], "files_removed": [...]}
    code_diff: Dict[str, Any] # Detailed code differences
    asset_diff: Dict[str, Any] # Detailed asset differences
    feature_mappings: List[FeatureMapping] = field(default_factory=list)
    assumptions_applied: List[Dict[str, Any]] = field(default_factory=list) # List of assumptions and their context
    confidence_scores: Dict[str, float] = field(default_factory=dict) # Overall or per-category scores
    # Consider adding created_at timestamp if not handled by DB automatically on this model

if __name__ == '__main__':
    # Example usage
    fm = FeatureMapping(
        java_feature="Custom Block with GUI",
        bedrock_equivalent="Block + Sign Interface",
        mapping_type="ASSUMED",
        confidence_score=0.75,
        assumption_applied="GUI_TO_SIGN_INTERFACE"
    )
    print(fm)

    cr = ComparisonResult(
        conversion_id="conv_123",
        structural_diff={"files_added": ["bp/blocks/custom.json"], "files_removed": ["java/com/example/MyBlock.java"]},
        code_diff={"logic_preserved": 0.85},
        asset_diff={"textures_changed": ["tex.png"]},
        feature_mappings=[fm],
        assumptions_applied=[{"assumption": "GUI_TO_SIGN_INTERFACE", "details": "Converted Java GUI to Bedrock sign."}],
        confidence_scores={"overall": 0.80}
    )
    print(cr)
