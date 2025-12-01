from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid


class PerformanceBenchmark(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversion_id: Optional[str] = None
    benchmark_suite_version: str = "1.0.0"
    device_type: str = "desktop"
    minecraft_version: str = "latest"
    overall_score: float = 0.0
    cpu_score: float = 0.0
    memory_score: float = 0.0
    network_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scenario_id: str
    scenario_name: str
    status: str = "pending"  # pending, running, completed, failed


class PerformanceMetric(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    benchmark_id: str
    metric_name: str
    metric_category: str
    java_value: Optional[float] = None
    bedrock_value: Optional[float] = None
    unit: str = ""
    improvement_percentage: Optional[float] = None


class BenchmarkRunRequest(BaseModel):
    scenario_id: str
    device_type: str = "desktop"
    minecraft_version: str = "latest"
    conversion_id: Optional[str] = None


class BenchmarkRunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class BenchmarkStatusResponse(BaseModel):
    run_id: str
    status: str
    progress: float = 0.0
    current_stage: str = ""
    estimated_completion: Optional[datetime] = None


class BenchmarkReportResponse(BaseModel):
    run_id: str
    benchmark: Optional[PerformanceBenchmark] = None
    metrics: List[PerformanceMetric]
    analysis: Dict[str, Any]
    comparison_results: Dict[str, Any]
    report_text: str
    optimization_suggestions: List[str]


class ScenarioDefinition(BaseModel):
    scenario_id: str
    scenario_name: str
    description: str
    type: str  # baseline, stress, load, memory, network
    duration_seconds: int
    parameters: Dict[str, Any]
    thresholds: Dict[str, float]


class CustomScenarioRequest(BaseModel):
    scenario_name: str = Field(
        ..., min_length=1, description="Scenario name cannot be empty"
    )
    description: str = Field(
        ..., min_length=1, description="Description cannot be empty"
    )
    type: str
    duration_seconds: int = 300
    parameters: Dict[str, Any] = {}
    thresholds: Dict[str, float] = {}
