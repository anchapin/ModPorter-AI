"""
Comprehensive report data types for the ModPorter AI conversion report system.
Implements Issue #10 - Conversion Report Generation System
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from dataclasses import dataclass
from datetime import datetime
import json


# Core Status Types
class ConversionStatus:
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PROCESSING = "processing"


class ImpactLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Enhanced Report Models
@dataclass
class ReportMetadata:
    """Metadata for the conversion report."""
    report_id: str
    job_id: str
    generation_timestamp: datetime
    version: str = "2.0.0"
    report_type: str = "comprehensive"


@dataclass
class SummaryReport:
    """Enhanced summary report with additional statistics."""
    overall_success_rate: float
    total_features: int
    converted_features: int
    partially_converted_features: int
    failed_features: int
    assumptions_applied_count: int
    processing_time_seconds: float
    download_url: Optional[str] = None
    quick_statistics: Dict[str, Any] = None

    # New enhanced fields
    total_files_processed: int = 0
    output_size_mb: float = 0.0
    conversion_quality_score: float = 0.0
    recommended_actions: List[str] = None

    def __post_init__(self):
        if self.quick_statistics is None:
            self.quick_statistics = {}
        if self.recommended_actions is None:
            self.recommended_actions = []


@dataclass
class FeatureAnalysisItem:
    """Detailed analysis for a single feature."""
    name: str
    original_type: str
    converted_type: Optional[str]
    status: str
    compatibility_score: float
    assumptions_used: List[str]
    impact_assessment: str
    visual_comparison: Optional[Dict[str, str]] = None
    technical_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "original_type": self.original_type,
            "converted_type": self.converted_type,
            "status": self.status,
            "compatibility_score": self.compatibility_score,
            "assumptions_used": self.assumptions_used,
            "impact_assessment": self.impact_assessment,
            "visual_comparison": self.visual_comparison,
            "technical_notes": self.technical_notes
        }


@dataclass
class FeatureAnalysis:
    """Comprehensive feature analysis report."""
    features: List[FeatureAnalysisItem]
    compatibility_mapping_summary: str
    visual_comparisons_overview: Optional[str] = None
    impact_assessment_summary: str = ""

    # New enhanced fields
    total_compatibility_score: float = 0.0
    feature_categories: Dict[str, List[str]] = None
    conversion_patterns: List[str] = None

    def __post_init__(self):
        if self.feature_categories is None:
            self.feature_categories = {}
        if self.conversion_patterns is None:
            self.conversion_patterns = []


@dataclass
class AssumptionReportItem:
    """Detailed smart assumption report item."""
    original_feature: str
    assumption_type: str
    bedrock_equivalent: str
    impact_level: str
    user_explanation: str
    technical_details: str
    visual_example: Optional[Dict[str, str]] = None
    confidence_score: float = 0.0
    alternatives_considered: List[str] = None

    def __post_init__(self):
        if self.alternatives_considered is None:
            self.alternatives_considered = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_feature": self.original_feature,
            "assumption_type": self.assumption_type,
            "bedrock_equivalent": self.bedrock_equivalent,
            "impact_level": self.impact_level,
            "user_explanation": self.user_explanation,
            "technical_details": self.technical_details,
            "visual_example": self.visual_example,
            "confidence_score": self.confidence_score,
            "alternatives_considered": self.alternatives_considered
        }


@dataclass
class AssumptionsReport:
    """Comprehensive assumptions report."""
    assumptions: List[AssumptionReportItem]
    total_assumptions_count: int = 0
    impact_distribution: Dict[str, int] = None
    category_breakdown: Dict[str, List[AssumptionReportItem]] = None
    what_changed: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.impact_distribution is None:
            self.impact_distribution = {"low": 0, "medium": 0, "high": 0}
        if self.category_breakdown is None:
            self.category_breakdown = {}
        self.total_assumptions_count = len(self.assumptions)
        if self.what_changed is None:
            self.what_changed = []
    
    def add_what_changed(self, category: str, original: str, converted: str, reason: str = ""):
        """Add an entry to the What Changed section."""
        if self.what_changed is None:
            self.what_changed = []
        self.what_changed.append({
            "category": category,
            "original": original,
            "converted": converted,
            "reason": reason
        })


@dataclass
class DeveloperLog:
    """Enhanced developer technical log."""
    code_translation_details: List[Dict[str, Any]]
    api_mapping_issues: List[Dict[str, Any]]
    file_processing_log: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    error_details: List[Dict[str, Any]]

    # New enhanced fields
    optimization_opportunities: List[str] = None
    technical_debt_notes: List[str] = None
    benchmark_comparisons: Dict[str, float] = None

    def __post_init__(self):
        if self.optimization_opportunities is None:
            self.optimization_opportunities = []
        if self.technical_debt_notes is None:
            self.technical_debt_notes = []
        if self.benchmark_comparisons is None:
            self.benchmark_comparisons = {}


@dataclass
class InteractiveReport:
    """Main interactive report structure."""
    metadata: ReportMetadata
    summary: SummaryReport
    feature_analysis: FeatureAnalysis
    assumptions_report: AssumptionsReport
    developer_log: DeveloperLog

    # Enhanced interactive features
    navigation_structure: Dict[str, Any] = None
    export_formats: List[str] = None
    user_actions: List[str] = None

    def __post_init__(self):
        if self.navigation_structure is None:
            self.navigation_structure = {
                "sections": ["summary", "features", "assumptions", "developer"],
                "expandable": True,
                "search_enabled": True
            }
        if self.export_formats is None:
            self.export_formats = ["pdf", "json", "html"]
        if self.user_actions is None:
            self.user_actions = ["download", "share", "feedback", "expand_all"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a dictionary for JSON serialization."""
        return {
            "metadata": {
                "report_id": self.metadata.report_id,
                "job_id": self.metadata.job_id,
                "generation_timestamp": self.metadata.generation_timestamp.isoformat(),
                "version": self.metadata.version,
                "report_type": self.metadata.report_type
            },
            "summary": {
                "overall_success_rate": self.summary.overall_success_rate,
                "total_features": self.summary.total_features,
                "converted_features": self.summary.converted_features,
                "partially_converted_features": self.summary.partially_converted_features,
                "failed_features": self.summary.failed_features,
                "assumptions_applied_count": self.summary.assumptions_applied_count,
                "processing_time_seconds": self.summary.processing_time_seconds,
                "download_url": self.summary.download_url,
                "quick_statistics": self.summary.quick_statistics,
                "total_files_processed": self.summary.total_files_processed,
                "output_size_mb": self.summary.output_size_mb,
                "conversion_quality_score": self.summary.conversion_quality_score,
                "recommended_actions": self.summary.recommended_actions
            },
            "feature_analysis": {
                "features": [f.to_dict() for f in self.feature_analysis.features],
                "compatibility_mapping_summary": self.feature_analysis.compatibility_mapping_summary,
                "visual_comparisons_overview": self.feature_analysis.visual_comparisons_overview,
                "impact_assessment_summary": self.feature_analysis.impact_assessment_summary,
                "total_compatibility_score": self.feature_analysis.total_compatibility_score,
                "feature_categories": self.feature_analysis.feature_categories,
                "conversion_patterns": self.feature_analysis.conversion_patterns
            },
            "assumptions_report": {
                "assumptions": [a.to_dict() for a in self.assumptions_report.assumptions],
                "total_assumptions_count": self.assumptions_report.total_assumptions_count,
                "impact_distribution": self.assumptions_report.impact_distribution,
                "category_breakdown": {k: [a.to_dict() for a in v] for k, v in self.assumptions_report.category_breakdown.items()},
                "what_changed": self.assumptions_report.what_changed or []
            },
            "developer_log": {
                "code_translation_details": self.developer_log.code_translation_details,
                "api_mapping_issues": self.developer_log.api_mapping_issues,
                "file_processing_log": self.developer_log.file_processing_log,
                "performance_metrics": self.developer_log.performance_metrics,
                "error_details": self.developer_log.error_details,
                "optimization_opportunities": self.developer_log.optimization_opportunities,
                "technical_debt_notes": self.developer_log.technical_debt_notes,
                "benchmark_comparisons": self.developer_log.benchmark_comparisons
            },
            "navigation_structure": self.navigation_structure,
            "export_formats": self.export_formats,
            "user_actions": self.user_actions
        }

    def to_json(self) -> str:
        """Convert the report to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


# Legacy compatibility types (for existing frontend)
class ModConversionStatus(TypedDict):
    name: str
    version: str
    status: str
    warnings: Optional[List[str]]
    errors: Optional[List[str]]


class SmartAssumption(TypedDict):
    originalFeature: str
    assumptionApplied: str
    impact: str
    description: str
    userExplanation: str
    visualExamples: Optional[List[str]]


class FeatureConversionDetail(TypedDict):
    feature_name: str
    status: str
    compatibility_notes: str
    visual_comparison_before: Optional[str]
    visual_comparison_after: Optional[str]
    impact_of_assumption: Optional[str]


class AssumptionDetail(TypedDict):
    assumption_id: str
    feature_affected: str
    description: str
    reasoning: str
    impact_level: str
    user_explanation: str
    technical_notes: Optional[str]


class LogEntry(TypedDict):
    timestamp: str
    level: str
    message: str
    details: Optional[Dict[str, Any]]


# Utility functions
def create_report_metadata(job_id: str, report_id: Optional[str] = None) -> ReportMetadata:
    """Create report metadata with current timestamp."""
    if report_id is None:
        report_id = f"report_{job_id}_{int(datetime.now().timestamp())}"

    return ReportMetadata(
        report_id=report_id,
        job_id=job_id,
        generation_timestamp=datetime.now(),
        version="2.0.0",
        report_type="comprehensive"
    )


def calculate_quality_score(summary: SummaryReport) -> float:
    """Calculate overall conversion quality score."""
    if summary.total_features == 0:
        return 0.0

    success_weight = 1.0
    partial_weight = 0.6
    failed_weight = 0.0

    weighted_score = (
        (summary.converted_features * success_weight) +
        (summary.partially_converted_features * partial_weight) +
        (summary.failed_features * failed_weight)
    ) / summary.total_features

    return round(weighted_score * 100, 1)
