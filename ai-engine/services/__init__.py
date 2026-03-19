"""
AI Engine Services

Model clients and routing for code translation.
"""

# Import model clients with optional dependencies
try:
    from .modal_client import ModalClient, get_modal_client
except ImportError:
    ModalClient = None
    get_modal_client = None

try:
    from .deepseek_client import DeepSeekClient, get_deepseek_client
except ImportError:
    DeepSeekClient = None
    get_deepseek_client = None

try:
    from .ollama_client import OllamaClient, get_ollama_client
except ImportError:
    OllamaClient = None
    get_ollama_client = None

try:
    from .model_router import ModelRouter, get_model_router
except ImportError:
    ModelRouter = None
    get_model_router = None

try:
    from .cost_tracker import CostTracker, get_cost_tracker
except ImportError:
    CostTracker = None
    get_cost_tracker = None

# Behavior analysis services (Phase 12-02)
from .behavior_analyzer import (
    BehaviorAnalyzer,
    BehaviorAnalysisResult,
    BehaviorGap,
    BehaviorGapSeverity,
    BehaviorGapCategory,
    analyze_behavior,
)
from .event_mapper import EventMapper, EventMapping, get_event_mapping
from .state_analyzer import StateAnalyzer, StateVariable, StateMapping, analyze_state
from .behavior_gap_reporter import (
    BehaviorGapReporter,
    GapReportConfig,
    ReportFormat,
    generate_gap_report,
    save_gap_report,
)

# Conversion metrics services (Phase 12-03)
from .conversion_metrics import (
    MetricsCollector,
    SuccessRateCalculator,
    ConversionStatus,
    ComplexityLevel,
    ErrorCategory,
    ConversionMetrics,
    AggregatedMetrics,
    create_metrics_report,
)

# Quality improvement pipeline (Phase 12-04)
from .quality_score import (
    QualityScoreCalculator,
    IssueDetector,
    FeedbackGenerator,
    RecommendationEngine,
    QualityPipeline,
    Issue,
    IssueSeverity,
    IssueCategory,
    QualityScore,
    QualityLevel,
    Recommendation,
    create_quality_report,
)

# Report generation (Phase 12-05)
from .report_generator import (
    ReportGenerator,
    ReportBuilder,
    ReportFormat,
    EnhancedConversionReport,
    ConversionMetadata,
    FileMetrics,
    QualityMetrics,
    RecommendationItem,
    ConversionResult,
    create_sample_report,
)

__all__ = [
    "ModalClient",
    "get_modal_client",
    "DeepSeekClient",
    "get_deepseek_client",
    "OllamaClient",
    "get_ollama_client",
    "ModelRouter",
    "get_model_router",
    "CostTracker",
    "get_cost_tracker",
    # Behavior analysis
    "BehaviorAnalyzer",
    "BehaviorAnalysisResult",
    "BehaviorGap",
    "BehaviorGapSeverity",
    "BehaviorGapCategory",
    "analyze_behavior",
    "EventMapper",
    "EventMapping",
    "get_event_mapping",
    "StateAnalyzer",
    "StateVariable",
    "StateMapping",
    "analyze_state",
    "BehaviorGapReporter",
    "GapReportConfig",
    "ReportFormat",
    "generate_gap_report",
    "save_gap_report",
    # Conversion metrics
    "MetricsCollector",
    "SuccessRateCalculator",
    "ConversionStatus",
    "ComplexityLevel",
    "ErrorCategory",
    "ConversionMetrics",
    "AggregatedMetrics",
    "create_metrics_report",
    # Quality pipeline
    "QualityScoreCalculator",
    "IssueDetector",
    "FeedbackGenerator",
    "RecommendationEngine",
    "QualityPipeline",
    "Issue",
    "IssueSeverity",
    "IssueCategory",
    "QualityScore",
    "QualityLevel",
    "Recommendation",
    "create_quality_report",
    # Report generation
    "ReportGenerator",
    "ReportBuilder",
    "ReportFormat",
    "EnhancedConversionReport",
    "ConversionMetadata",
    "FileMetrics",
    "QualityMetrics",
    "RecommendationItem",
    "ConversionResult",
    "create_sample_report",
]
