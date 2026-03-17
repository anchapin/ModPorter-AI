from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class ModConversionStatus(TypedDict):
    name: str
    version: str
    status: str  # e.g., "Converted", "Partially Converted", "Failed"
    warnings: Optional[List[str]]
    errors: Optional[List[str]]


class SmartAssumption(TypedDict):
    originalFeature: str
    assumptionApplied: str
    impact: str  # "Low", "Medium", "High"
    description: str
    userExplanation: str
    visualExamples: Optional[List[str]]  # URLs or base64 encoded images


class SummaryReport(TypedDict):
    overall_success_rate: float
    total_features: int
    converted_features: int
    partially_converted_features: int
    failed_features: int
    assumptions_applied_count: int
    processing_time_seconds: float
    download_url: Optional[str]
    quick_statistics: Dict[str, Any]  # e.g., features_converted, time_taken, file_size


class FeatureConversionDetail(TypedDict):
    feature_name: str
    status: str  # "Success", "Partial Success", "Failed"
    compatibility_notes: str
    visual_comparison_before: Optional[str]  # Description or image URL
    visual_comparison_after: Optional[str]  # Description or image URL
    impact_of_assumption: Optional[str]


class FeatureAnalysis(TypedDict):
    per_feature_status: List[FeatureConversionDetail]
    compatibility_mapping_summary: str  # General notes on compatibility
    visual_comparisons_overview: Optional[str]  # General notes on visual changes
    impact_assessment_summary: str  # General notes on assumption impacts


class AssumptionDetail(TypedDict):
    assumption_id: str
    feature_affected: str
    description: str
    reasoning: str
    impact_level: str  # "Low", "Medium", "High"
    user_explanation: str
    technical_notes: Optional[str]


class AssumptionsReport(TypedDict):
    assumptions: List[AssumptionDetail]
    what_changed: Optional[List[Dict[str, str]]]


class LogEntry(TypedDict):
    timestamp: str
    level: str  # "INFO", "WARNING", "ERROR"
    message: str
    details: Optional[Dict[str, Any]]


class DeveloperLog(TypedDict):
    code_translation_details: List[LogEntry]
    api_mapping_issues: List[LogEntry]
    file_processing_log: List[LogEntry]
    performance_metrics: Dict[
        str, Any
    ]  # e.g., { "total_time_seconds": 60.5, "memory_peak_mb": 256 }
    error_summary: List[
        Dict[str, Any]
    ]  # { "error_message": "...", "stack_trace": "..." }


class InteractiveReport(TypedDict):
    job_id: str
    report_generation_date: str
    summary: SummaryReport
    converted_mods: List[ModConversionStatus]
    failed_mods: List[ModConversionStatus]
    feature_analysis: Optional[FeatureAnalysis]
    smart_assumptions_report: Optional[
        AssumptionsReport
    ]  # This uses AssumptionDetail now
    developer_log: Optional[DeveloperLog]


# Example of how the main report structure might look, referencing the PRD
class FullConversionReport(TypedDict):
    summary: SummaryReport
    converted_mods: List[ModConversionStatus]  # Simplified for now
    failed_mods: List[ModConversionStatus]  # Simplified for now
    smart_assumptions: List[
        SmartAssumption
    ]  # From PRD, maps to SmartAssumptionsReport content
    developer_log: DeveloperLog  # From PRD
    # Detailed feature analysis will be part of a sub-section or fetched on demand
    # For now, focusing on the PRD's top-level structure
